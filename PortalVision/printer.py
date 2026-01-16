"""
Printer - OS-native print handoff.

Responsibilities:
- Hand off HTML to OS print subsystem
- Make no assumptions about printer state
- Make no verification claims
- Fail cleanly if OS rejects

Non-responsibilities:
- Printer selection
- Layout configuration
- Success verification
- Retry logic
"""

import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple


class PrintError(Exception):
    """Raised when print handoff fails."""
    pass


class Printer:
    """
    OS-native print handler.
    
    Treats printing as a best-effort handoff.
    If OS accepts the job, we proceed.
    No verification of printer availability or success.
    """
    
    @staticmethod
    def print_html(html_content: str) -> Tuple[bool, Optional[str]]:
        """
        Hand off HTML content to OS print subsystem.
        
        Args:
            html_content: The HTML to print
        
        Returns:
            (success: bool, error_message: Optional[str])
        
        Platform behavior:
        - macOS: Uses `open -a "Safari" <file>` then triggers print dialog
        - Linux: Uses `xdg-open <file>` or `lp <file>`
        - Windows: Uses `start <file>` then opens print dialog
        
        Constraints:
        - No retry
        - No validation
        - No confirmation
        - Best-effort handoff only
        """
        system = platform.system()
        
        # Write HTML to temp file
        try:
            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".html",
                delete=False,
                encoding="utf-8"
            )
            temp_file.write(html_content)
            temp_file.close()
            temp_path = temp_file.name
        except Exception as e:
            return False, f"Failed to create temp file: {e}"
        
        # Attempt OS-specific print handoff
        try:
            if system == "Darwin":  # macOS
                # Open in default browser, operator triggers print manually
                subprocess.run(
                    ["open", temp_path],
                    check=True,
                    capture_output=True,
                    timeout=5,
                )
                return True, None
            
            elif system == "Linux":
                # Try xdg-open first (opens browser), fallback to lp (direct print)
                try:
                    subprocess.run(
                        ["xdg-open", temp_path],
                        check=True,
                        capture_output=True,
                        timeout=5,
                    )
                    return True, None
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Fallback to lp
                    subprocess.run(
                        ["lp", temp_path],
                        check=True,
                        capture_output=True,
                        timeout=5,
                    )
                    return True, None
            
            elif system == "Windows":
                # Open in default browser
                subprocess.run(
                    ["start", temp_path],
                    check=True,
                    capture_output=True,
                    timeout=5,
                    shell=True,
                )
                return True, None
            
            else:
                return False, f"Unsupported OS: {system}"
        
        except subprocess.TimeoutExpired:
            return False, "Print command timeout"
        
        except subprocess.CalledProcessError as e:
            return False, f"Print command failed: {e.stderr.decode() if e.stderr else str(e)}"
        
        except FileNotFoundError as e:
            return False, f"Print command not found: {e}"
        
        except Exception as e:
            return False, f"Unexpected error: {e}"
    
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """Clean up temporary file (best effort)."""
        try:
            os.unlink(file_path)
        except Exception:
            pass  # Silent failure is acceptable for cleanup

