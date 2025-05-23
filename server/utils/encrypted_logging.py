import os
import logging
import logging.handlers
from cryptography.fernet import Fernet
from typing import Optional
import base64
import datetime
import json
from pathlib import Path

class EncryptedLogFormatter(logging.Formatter):
    """
    Custom formatter that encrypts log records before writing them to file.
    """
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, style: str = '%', 
                 key_path: Optional[str] = None):
        super().__init__(fmt, datefmt, style)
        self.key = self._get_or_create_key(key_path)
        self.fernet = Fernet(self.key)
        
    def _get_or_create_key(self, key_path: Optional[str]) -> bytes:
        """Get an existing key or create a new one if it doesn't exist."""
        if key_path is None:
            key_path = os.environ.get('LOG_ENCRYPTION_KEY_PATH', 'log_encryption.key')
            
        key_file = Path(key_path)
        if key_file.exists():
            with open(key_file, 'rb') as file:
                return file.read().strip()
        else:
            key = Fernet.generate_key()
            key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(key_file, 'wb') as file:
                file.write(key)
            return key
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record and encrypt it."""
        formatted_record = super().format(record)
        
        log_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": formatted_record
        }
        
        json_data = json.dumps(log_data)
        
        encrypted_data = self.fernet.encrypt(json_data.encode('utf-8'))
        
        return base64.b64encode(encrypted_data).decode('utf-8')

def setup_encrypted_logging(
    log_dir: Optional[str] = None,
    log_level: int = logging.INFO,
    console_logging: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    key_path: Optional[str] = None
) -> None:
    """
    Set up encrypted file logging with optional console logging.
    
    Args:
        log_dir: Directory to store log files (default from env var or ./logs)
        log_level: Logging level (default INFO)
        console_logging: Whether to also log to console (default True)
        max_bytes: Maximum size of each log file before rotation
        backup_count: Number of backup files to keep
        key_path: Path to the encryption key file
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    if console_logging:
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)
    
    if log_dir is None:
        log_dir = os.environ.get('LOG_DIR', './logs')
    
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'server.log')
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    
    encrypted_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_handler.setFormatter(EncryptedLogFormatter(encrypted_format, key_path=key_path))
    
    root_logger.addHandler(file_handler)
    
    root_logger.info(f"Encrypted logging initialized. Log file: {log_file}")

def decrypt_log_file(
    log_file_path: str,
    output_file_path: Optional[str] = None,
    key_path: Optional[str] = None
) -> None:
    """
    Decrypt a log file and write it to a new file or print to console.
    
    Args:
        log_file_path: Path to the encrypted log file
        output_file_path: Path to write the decrypted logs (None for console)
        key_path: Path to the encryption key file
    """
    if key_path is None:
        key_path = os.environ.get('LOG_ENCRYPTION_KEY_PATH', 'log_encryption.key')
    
    with open(key_path, 'rb') as file:
        key = file.read().strip()
    
    fernet = Fernet(key)
    
    with open(log_file_path, 'r') as file:
        encrypted_lines = file.readlines()
    
    decrypted_logs = []
    for line in encrypted_lines:
        try:
            encrypted_data = base64.b64decode(line.strip())
            decrypted_data = fernet.decrypt(encrypted_data).decode('utf-8')
            log_entry = json.loads(decrypted_data)
            formatted_log = f"{log_entry['timestamp']} - {log_entry['level']} - {log_entry['logger']} - {log_entry['message']}"
            decrypted_logs.append(formatted_log)
        except Exception as e:
            decrypted_logs.append(f"Error decrypting log line: {str(e)}")
    
    if output_file_path:
        with open(output_file_path, 'w') as file:
            for log in decrypted_logs:
                file.write(log + '\n')
        print(f"Decrypted logs written to {output_file_path}")
    else:
        for log in decrypted_logs:
            print(log)
