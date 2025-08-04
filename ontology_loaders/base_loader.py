from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseOntologyLoader(ABC):
    """Base class for all ontology loaders"""
    
    def __init__(self, system: str, version: str):
        self.system = system
        self.version = version
        self.stats = {
            'total_processed': 0,
            'successful_inserts': 0,
            'failed_inserts': 0,
            'duplicates_found': 0
        }
    
    @abstractmethod
    async def load_data(self, file_path: str) -> int:
        """Load data from file and return number of records processed"""
        pass
    
    @abstractmethod
    async def generate_embeddings(self, batch_size: int = 100) -> bool:
        """Generate embeddings for loaded data"""
        pass
    
    @abstractmethod
    async def validate_hierarchy(self) -> bool:
        """Validate the hierarchical structure of loaded data"""
        pass
    
    def export_statistics(self) -> Dict[str, Any]:
        """Export loading statistics"""
        return {
            'system': self.system,
            'version': self.version,
            'statistics': self.stats,
            'success_rate': self.stats['successful_inserts'] / max(self.stats['total_processed'], 1) * 100
        }
    
    def log_progress(self, processed: int, total: int):
        """Log loading progress"""
        if processed % 1000 == 0:
            logger.info(f"Processed {processed}/{total} records for {self.system} v{self.version}")
