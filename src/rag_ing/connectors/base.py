"""Base connector interface for document sources."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from langchain.docstore.document import Document


class BaseConnector(ABC):
    """Base class for all document connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__.replace("Connector", "").lower()
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the document source."""
        pass
    
    @abstractmethod
    def fetch_documents(self, **kwargs) -> List[Document]:
        """Fetch documents from the source."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if connection is working."""
        pass
    
    def get_connector_info(self) -> Dict[str, Any]:
        """Get information about this connector."""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "config_keys": list(self.config.keys())
        }