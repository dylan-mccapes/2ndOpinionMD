"""
Print receipts - Append-only print materialization records.

Records:
- What was printed (artifact_id, hash)
- Who printed it (operator_id)
- When it was printed (timestamp)
- What consent was given (verbatim text)
- No verification performed (honest limitation)
"""

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PrintReceipt:
    """Immutable record of a print materialization."""
    
    receipt_id: str
    artifact_id: str
    artifact_hash: str
    operator_id: str
    timestamp: str
    consent_text: str
    note: str = "Materialized via external printer. No verification performed."
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PrintReceipt":
        return cls(**data)


class PrintReceiptStore:
    """
    Append-only store for print receipts.
    
    Receipts:
    - Are immutable (no updates, no deletes)
    - Are append-only (always growing)
    - Affect OECS positively but minimally
    - Are stored alongside PortalVision artifacts
    """
    
    def __init__(self, receipts_dir: str):
        self.receipts_dir = Path(receipts_dir)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_file = self.receipts_dir / "print_receipts.json"
        self._receipts = self._load_receipts()
    
    def _load_receipts(self) -> List[PrintReceipt]:
        if not self.receipts_file.exists():
            return []
        
        with open(self.receipts_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return [PrintReceipt.from_dict(r) for r in data.get("receipts", [])]
    
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
        return f"PRINT-{count+1:06d}-{timestamp.replace(':', '-')}"
    
    def record(
        self,
        artifact_id: str,
        artifact_hash: str,
        operator_id: str,
        consent_text: str,
    ) -> PrintReceipt:
        """
        Record a print materialization.
        
        Args:
            artifact_id: The artifact that was printed
            artifact_hash: The artifact's content hash
            operator_id: The operator who printed it
            consent_text: The exact consent text provided
        
        Returns:
            PrintReceipt with receipt_id and timestamp
        """
        receipt = PrintReceipt(
            receipt_id=self._generate_receipt_id(),
            artifact_id=artifact_id,
            artifact_hash=artifact_hash,
            operator_id=operator_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            consent_text=consent_text,
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
    ) -> List[PrintReceipt]:
        """
        List receipts with optional filters.
        
        Args:
            artifact_id: Filter by artifact
            operator_id: Filter by operator
        
        Returns:
            List of matching receipts
        """
        receipts = self._receipts
        
        if artifact_id:
            receipts = [r for r in receipts if r.artifact_id == artifact_id]
        
        if operator_id:
            receipts = [r for r in receipts if r.operator_id == operator_id]
        
        return receipts
    
    def get_receipt(self, receipt_id: str) -> Optional[PrintReceipt]:
        """Get a specific receipt by ID."""
        for receipt in self._receipts:
            if receipt.receipt_id == receipt_id:
                return receipt
        return None

