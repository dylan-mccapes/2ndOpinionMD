"""
Audio Export Receipts - Append-only audio projection records.

Records:
- Source artifact (HTML)
- Audio file path
- Consent given
- Transformation performed
- Authority hierarchy (HTML is authoritative)
"""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AudioExportReceipt:
    """Immutable record of an audio export."""
    
    receipt_id: str
    artifact_type: str = "audio_projection"
    source_artifact: str = "epistemic_html"
    source_artifact_id: str = ""
    source_artifact_hash: str = ""
    audio_file_path: str = ""
    audio_is_authoritative: bool = False
    authority: str = "html"
    content_transformed: bool = False
    transformation: str = "verbatim narration"
    consent_phrase: str = ""
    operator_id: str = ""
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioExportReceipt":
        return cls(**data)


class AudioReceiptStore:
    """
    Append-only store for audio export receipts.
    
    Receipts:
    - Are immutable (no updates, no deletes)
    - Are append-only (always growing)
    - Record transformation, not interpretation
    - Preserve authority hierarchy (HTML > audio)
    """
    
    def __init__(self, receipts_dir: str):
        self.receipts_dir = Path(receipts_dir)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_file = self.receipts_dir / "audio_receipts.json"
        self._receipts = self._load_receipts()
    
    def _load_receipts(self) -> List[AudioExportReceipt]:
        if not self.receipts_file.exists():
            return []
        
        with open(self.receipts_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return [AudioExportReceipt.from_dict(r) for r in data.get("receipts", [])]
    
    def _save_receipts(self):
        data = {
            "receipts": [r.to_dict() for r in self._receipts],
            "count": len(self._receipts),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        
        with open(self.receipts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _generate_receipt_id(self) -> str:
        """Generate a unique receipt ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        count = len(self._receipts)
        return f"AUDIO-{count+1:06d}-{timestamp.replace(':', '-')}"
    
    def record(
        self,
        source_artifact_id: str,
        source_artifact_hash: str,
        audio_file_path: str,
        operator_id: str,
        consent_phrase: str,
    ) -> AudioExportReceipt:
        """
        Record an audio export.
        
        Args:
            source_artifact_id: The HTML artifact ID
            source_artifact_hash: The HTML artifact hash
            audio_file_path: Path to generated audio file
            operator_id: The operator who requested export
            consent_phrase: The exact consent text provided
        
        Returns:
            AudioExportReceipt with receipt_id and timestamp
        """
        receipt = AudioExportReceipt(
            receipt_id=self._generate_receipt_id(),
            source_artifact_id=source_artifact_id,
            source_artifact_hash=source_artifact_hash,
            audio_file_path=audio_file_path,
            operator_id=operator_id,
            consent_phrase=consent_phrase,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        # Append-only: add to list
        self._receipts.append(receipt)
        
        # Persist
        self._save_receipts()
        
        return receipt
    
    def list_receipts(
        self,
        artifact_id: Optional[str] = None,
        operator_id: Optional[str] = None,
    ) -> List[AudioExportReceipt]:
        """
        List receipts with optional filters.
        
        Args:
            artifact_id: Filter by source artifact
            operator_id: Filter by operator
        
        Returns:
            List of matching receipts
        """
        receipts = self._receipts
        
        if artifact_id:
            receipts = [r for r in receipts if r.source_artifact_id == artifact_id]
        
        if operator_id:
            receipts = [r for r in receipts if r.operator_id == operator_id]
        
        return receipts
    
    def get_receipt(self, receipt_id: str) -> Optional[AudioExportReceipt]:
        """Get a specific receipt by ID."""
        for receipt in self._receipts:
            if receipt.receipt_id == receipt_id:
                return receipt
        return None

