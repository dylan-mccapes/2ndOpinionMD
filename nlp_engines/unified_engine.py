from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class UnifiedQueryEngine(ABC):
    """Unified interface for vector search engines"""
    
    @abstractmethod
    async def query_medical_knowledge(self, query: str, content_types: Optional[List[str]] = None, top_k: int = 5):
        """Query medical knowledge with vector similarity"""
        pass
    
    @abstractmethod
    async def generate_rag_response(self, symptoms: List[str], model: str = "gpt-3.5-turbo", demographics: Optional[Dict[str, Any]] = None):
        """Generate RAG response for medical diagnosis"""
        pass
    
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        pass

class DatabaseAgnosticEngine:
    """Database-agnostic query engine that can switch between ChromaDB and PostgreSQL"""
    
    def __init__(self, primary_engine: str = "postgresql"):
        self.primary_engine = primary_engine
        self.engines = {}
    
    def register_engine(self, name: str, engine: UnifiedQueryEngine):
        """Register a query engine"""
        self.engines[name] = engine
    
    async def query(self, query: str, **kwargs):
        """Query using the primary engine with fallback"""
        try:
            if self.primary_engine in self.engines:
                return await self.engines[self.primary_engine].query_medical_knowledge(query, **kwargs)
        except Exception as e:
            logger.warning(f"Primary engine {self.primary_engine} failed: {e}")
            
        for name, engine in self.engines.items():
            if name != self.primary_engine:
                try:
                    return await engine.query_medical_knowledge(query, **kwargs)
                except Exception as e:
                    logger.warning(f"Fallback engine {name} failed: {e}")
        
        raise Exception("All query engines failed")
