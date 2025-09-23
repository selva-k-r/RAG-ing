"""Confluence connector for extracting documents."""

from typing import List, Dict, Any, Optional
from langchain.docstore.document import Document
import requests
from requests.auth import HTTPBasicAuth
import logging
from urllib.parse import urljoin
import time

from .base import BaseConnector
from ..utils.exceptions import ConnectionError, AuthenticationError, APIError, DocumentProcessingError

logger = logging.getLogger(__name__)


class ConfluenceConnector(BaseConnector):
    """Connector for Confluence documents."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Confluence connector.
        
        Config should contain:
        - base_url: Confluence base URL
        - username: Username for authentication
        - api_token: API token for authentication
        - space_key: Optional space key to limit search
        """
        super().__init__(config)
        self.base_url = config.get("base_url", "").rstrip("/")
        self.username = config.get("username")
        self.api_token = config.get("api_token")
        self.space_key = config.get("space_key")
        self.session = None
    
    def connect(self) -> bool:
        """Establish connection to Confluence."""
        try:
            self.session = requests.Session()
            self.session.auth = HTTPBasicAuth(self.username, self.api_token)
            self.session.headers.update({
                "Accept": "application/json",
                "Content-Type": "application/json"
            })
            
            # Test connection
            return self.test_connection()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Confluence: {e}")
            raise ConnectionError(f"Unable to connect to Confluence at {self.base_url}") from e
    
    def test_connection(self) -> bool:
        """Test Confluence connection."""
        if not self.session:
            raise ConnectionError("Session not established.")
        
        try:
            url = urljoin(self.base_url, "/rest/api/space")
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                return True
            elif response.status_code in [401, 403]:
                raise AuthenticationError("Authentication failed. Please check your username and API token.")
            else:
                raise APIError(f"Confluence API returned status {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Confluence connection test failed: {e}")
            raise ConnectionError(f"Connection test to {self.base_url} failed.") from e
    
    def fetch_documents(self, limit: int = 50, include_attachments: bool = False) -> List[Document]:
        """Fetch documents from Confluence."""
        if not self.session:
            self.connect()
        
        documents = []
        start = 0
        
        while len(documents) < limit:
            batch_size = min(25, limit - len(documents))  # Confluence API limit
            
            # Build query parameters
            params = {
                "limit": batch_size,
                "start": start,
                "expand": "body.storage,metadata.labels,space,version"
            }
            
            if self.space_key:
                params["cql"] = f"space = '{self.space_key}'"
            
            try:
                url = urljoin(self.base_url, "/rest/api/content/search" if self.space_key else "/rest/api/content")
                response = self.session.get(url, params=params, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                
                if not results:
                    break
                
                for item in results:
                    doc = self._convert_to_document(item)
                    if doc:
                        documents.append(doc)
                
                start += len(results)
                
                # Rate limiting
                time.sleep(0.5)
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code in [401, 403]:
                    raise AuthenticationError("Authentication failed during document fetch.") from e
                else:
                    raise APIError(f"Error fetching Confluence documents: {e.response.status_code}") from e
            except requests.exceptions.RequestException as e:
                raise ConnectionError("Connection error during document fetch.") from e
        
        logger.info(f"Fetched {len(documents)} documents from Confluence")
        return documents[:limit]
    
    def _convert_to_document(self, item: Dict[str, Any]) -> Optional[Document]:
        """Convert Confluence item to Document."""
        try:
            # Extract content
            body = item.get("body", {}).get("storage", {})
            content = body.get("value", "")
            
            if not content:
                return None
            
            # Clean HTML tags (basic cleaning)
            import re
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Extract metadata
            metadata = {
                "source": "confluence",
                "id": item.get("id"),
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "url": urljoin(self.base_url, item.get("_links", {}).get("webui", "")),
                "space": item.get("space", {}).get("name", ""),
                "space_key": item.get("space", {}).get("key", ""),
                "created": item.get("version", {}).get("when", ""),
                "creator": item.get("version", {}).get("by", {}).get("displayName", ""),
            }
            
            # Add labels if present
            labels = item.get("metadata", {}).get("labels", {}).get("results", [])
            if labels:
                metadata["labels"] = [label.get("name") for label in labels]
            
            return Document(page_content=content, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Error converting Confluence item to document: {e}")
            raise DocumentProcessingError(f"Failed to process document {item.get('id')}") from e
    
    def search_documents(self, query: str, limit: int = 25) -> List[Document]:
        """Search for specific documents in Confluence."""
        if not self.session:
            self.connect()
        
        try:
            # Use Confluence search API
            params = {
                "cql": f"text ~ '{query}'",
                "limit": limit,
                "expand": "content.body.storage,content.metadata.labels,content.space,content.version"
            }
            
            if self.space_key:
                params["cql"] = f"space = '{self.space_key}' AND {params['cql']}"
            
            url = urljoin(self.base_url, "/rest/api/content/search")
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            results = data.get("results", [])
            
            documents = []
            for item in results:
                content_data = item.get("content", item)  # Handle both formats
                doc = self._convert_to_document(content_data)
                if doc:
                    documents.append(doc)
            
            logger.info(f"Found {len(documents)} documents for query: {query}")
            return documents
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403]:
                raise AuthenticationError("Authentication failed during search.") from e
            else:
                raise APIError(f"Error searching Confluence documents: {e.response.status_code}") from e
        except requests.exceptions.RequestException as e:
            raise ConnectionError("Connection error during search.") from e