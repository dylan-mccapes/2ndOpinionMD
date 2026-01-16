"""
Epistemic HTML Vault - Artifact storage.

Stores HTML artifacts with provenance and integrity verification.
"""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class EpistemicArtifact:
    """An epistemic HTML artifact with provenance."""
    
    artifact_id: str
    content_hash: str
    html_content: str
    created_at: str
    provenance: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpistemicArtifact":
        return cls(**data)


class EpistemicHTMLVault:
    """
    Storage for epistemic HTML artifacts.
    
    Artifacts are:
    - Content-addressed (hash-based)
    - Immutable (no updates)
    - Provenance-tracked (origin, mode, timestamp)
    """
    
    def __init__(self, vault_dir: str):
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir = self.vault_dir / "artifacts"
        self.artifacts_dir.mkdir(exist_ok=True)
        self.index_path = self.vault_dir / "index.json"
        self._index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        if self.index_path.exists():
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"artifacts": {}}
    
    def _save_index(self):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2, ensure_ascii=False)
    
    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    def _generate_artifact_id(self) -> str:
        """Generate a unique artifact ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        raw = f"{timestamp}-{os.urandom(8).hex()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    
    def store(
        self,
        html_content: str,
        provenance: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EpistemicArtifact:
        """
        Store an HTML artifact.
        
        Args:
            html_content: The HTML content
            provenance: Provenance information (mode, query, timestamp, etc.)
            metadata: Optional additional metadata
        
        Returns:
            EpistemicArtifact with artifact_id and content_hash
        """
        artifact_id = self._generate_artifact_id()
        content_hash = self._compute_hash(html_content)
        created_at = datetime.now(timezone.utc).isoformat()
        
        artifact = EpistemicArtifact(
            artifact_id=artifact_id,
            content_hash=content_hash,
            html_content=html_content,
            created_at=created_at,
            provenance=provenance,
            metadata=metadata or {},
        )
        
        # Save artifact
        artifact_path = self.artifacts_dir / f"{artifact_id}.json"
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(artifact.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Update index
        self._index["artifacts"][artifact_id] = {
            "artifact_id": artifact_id,
            "content_hash": content_hash,
            "created_at": created_at,
            "provenance": provenance,
            "metadata": metadata or {},
        }
        self._save_index()
        
        return artifact
    
    def retrieve(self, artifact_id: str) -> Optional[EpistemicArtifact]:
        """Retrieve an artifact by ID."""
        artifact_path = self.artifacts_dir / f"{artifact_id}.json"
        if not artifact_path.exists():
            return None
        
        with open(artifact_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return EpistemicArtifact.from_dict(data)
    
    def list_artifacts(self) -> Dict[str, Dict[str, Any]]:
        """List all artifacts (metadata only, no content)."""
        return self._index["artifacts"]
    
    def verify_integrity(self, artifact_id: str) -> bool:
        """Verify artifact integrity (hash matches content)."""
        artifact = self.retrieve(artifact_id)
        if not artifact:
            return False
        
        computed_hash = self._compute_hash(artifact.html_content)
        return computed_hash == artifact.content_hash

