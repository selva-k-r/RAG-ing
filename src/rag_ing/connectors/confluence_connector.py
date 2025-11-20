"""Confluence connector for document ingestion.

Implementation of Confluence integration as specified in Requirement.md:
- Authenticate and fetch pages by space key and filter
- Parse data_source.type: confluence
"""

import logging
import requests
import base64
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from ..utils.exceptions import ConnectionError, AuthenticationError, APIError

logger = logging.getLogger(__name__)


class ConfluenceConnector:
    """Connector for Confluence document retrieval as per Module 1 requirements."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Confluence connector with configuration.
        
        Args:
            config: Confluence configuration dict with base_url, auth_token, etc.
        """
        self.config = config
        self.base_url = config.get("base_url")
        self.username = config.get("username")
        self.auth_token = config.get("auth_token")
        self.space_key = config.get("space_key")
        self.page_filter = config.get("page_filter", [])
        
        if not self.base_url or not self.auth_token:
            raise ConnectionError("Confluence base_url and auth_token are required")
        
        # Setup authentication headers
        if self.username:
            # Use basic auth with username and API token
            auth_string = f"{self.username}:{self.auth_token}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
            self.headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/json"
            }
        else:
            # Use bearer token
            self.headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
        logger.info(f"Initialized Confluence connector for {self.base_url}")
    
    def connect(self) -> bool:
        """Authenticate and connect to Confluence.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If connection fails
        """
        try:
            logger.info(f"Connecting to Confluence at {self.base_url}")
            
            # Test connection with a simple API call
            test_url = f"{self.base_url}/rest/api/content"
            response = requests.get(
                test_url,
                headers=self.headers,
                params={"limit": 1},
                timeout=30
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid Confluence credentials")
            elif response.status_code == 403:
                raise AuthenticationError("Access denied - check permissions")
            elif response.status_code != 200:
                raise ConnectionError(f"Connection failed: {response.status_code} - {response.text}")
            
            logger.info("Successfully connected to Confluence")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Confluence: {e}")
            raise ConnectionError(f"Confluence connection failed: {e}")
    
    def fetch_page_by_title(self, space_key: str, page_title: str) -> Optional[Dict[str, Any]]:
        """Fetch a specific page by space key and title.
        
        Args:
            space_key: Confluence space key
            page_title: Page title to search for
            
        Returns:
            Page data dict or None if not found
        """
        try:
            url = f"{self.base_url}/rest/api/content"
            params = {
                "spaceKey": space_key,
                "title": page_title,
                "expand": "body.storage,version,space,children.page",
                "limit": 1
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch page '{page_title}': {response.status_code}")
                return None
            
            data = response.json()
            results = data.get("results", [])
            
            if results:
                logger.info(f"Found page: '{page_title}'")
                return results[0]
            else:
                logger.warning(f"Page not found: '{page_title}'")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching page '{page_title}': {e}")
            return None
    
    def fetch_child_pages(self, page_id: str, recursive: bool = True) -> List[Dict[str, Any]]:
        """Fetch all child pages of a parent page, optionally recursive.
        
        Args:
            page_id: Parent page ID
            recursive: If True, fetch all descendants; if False, only direct children
            
        Returns:
            List of child page data dicts
        """
        all_children = []
        
        try:
            url = f"{self.base_url}/rest/api/content/{page_id}/child/page"
            params = {
                "expand": "body.storage,version,space,children.page",
                "limit": 100
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch children of page {page_id}: {response.status_code}")
                return all_children
            
            data = response.json()
            children = data.get("results", [])
            
            logger.info(f"Found {len(children)} direct children of page {page_id}")
            
            for child in children:
                all_children.append(child)
                
                # Recursively fetch grandchildren
                if recursive:
                    child_id = child.get("id")
                    grandchildren = self.fetch_child_pages(child_id, recursive=True)
                    all_children.extend(grandchildren)
            
            return all_children
            
        except Exception as e:
            logger.error(f"Error fetching child pages of {page_id}: {e}")
            return all_children
    
    def fetch_documents(self, space_key: Optional[str] = None, 
                       page_filter: Optional[List[str]] = None,
                       parent_page_title: Optional[str] = None,
                       include_children: bool = True) -> List[Document]:
        """Fetch documents from Confluence by space key, with optional parent page filtering.
        
        Args:
            space_key: Confluence space key (defaults to config space_key)
            page_filter: List of page title filters (defaults to config page_filter)
            parent_page_title: If provided, fetch this page and all its children
            include_children: If True and parent_page_title is set, fetch all child pages
            
        Returns:
            List[Document]: List of fetched documents with metadata
            
        Raises:
            APIError: If API call fails
        """
        space_key = space_key or self.space_key
        page_filter = page_filter or self.page_filter
        
        if not space_key:
            raise ValueError("space_key is required for document fetching")
        
        logger.info(f"Fetching documents from space '{space_key}'")
        if parent_page_title:
            logger.info(f"  Parent page: '{parent_page_title}' (include_children={include_children})")
        if page_filter:
            logger.info(f"  Page filter: {page_filter}")
        
        try:
            documents = []
            pages = []
            
            # If parent page specified, fetch it and its children
            if parent_page_title:
                parent_page = self.fetch_page_by_title(space_key, parent_page_title)
                
                if not parent_page:
                    raise APIError(f"Parent page '{parent_page_title}' not found in space '{space_key}'")
                
                # Add parent page
                pages.append(parent_page)
                logger.info(f"Added parent page: '{parent_page_title}'")
                
                # Fetch all child pages recursively
                if include_children:
                    parent_id = parent_page.get("id")
                    children = self.fetch_child_pages(parent_id, recursive=True)
                    pages.extend(children)
                    logger.info(f"Fetched {len(children)} child pages recursively")
            
            else:
                # Original behavior: fetch all pages from space
                params = {
                    "spaceKey": space_key,
                    "expand": "body.storage,version,space",
                    "limit": 50  # Fetch up to 50 pages
                }
                
                url = f"{self.base_url}/rest/api/content"
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                if response.status_code != 200:
                    raise APIError(f"Failed to fetch pages: {response.status_code} - {response.text}")
                
                data = response.json()
                pages = data.get("results", [])
            
            logger.info(f"Found {len(pages)} pages in space '{space_key}'")
            
            for page in pages:
                title = page.get("title", "")
                page_id = page.get("id", "")
                
                # Apply page filter if specified
                if page_filter:
                    if not any(filter_term.lower() in title.lower() for filter_term in page_filter):
                        logger.debug(f"Skipping page '{title}' - doesn't match filter")
                        continue
                
                # Extract content from page
                body = page.get("body", {})
                storage = body.get("storage", {})
                content = storage.get("value", "")
                
                # Clean up HTML content (basic cleanup)
                import re
                # Remove HTML tags for cleaner text
                content = re.sub(r'<[^>]+>', ' ', content)
                # Remove extra whitespace
                content = re.sub(r'\s+', ' ', content).strip()
                
                if not content:
                    logger.debug(f"Skipping page '{title}' - no content")
                    continue
                
                # Create document with metadata
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": f"{self.base_url}/pages/viewpage.action?pageId={page_id}",
                        "title": title,
                        "space_key": space_key,
                        "page_id": page_id,
                        "date": page.get("version", {}).get("when", ""),
                        "author": page.get("version", {}).get("by", {}).get("displayName", ""),
                        "type": "confluence_page",
                        "url": f"{self.base_url}/pages/viewpage.action?pageId={page_id}"
                    }
                )
                documents.append(doc)
                logger.info(f"Added page: '{title}' ({len(content)} chars)")
            
            logger.info(f"Successfully fetched {len(documents)} documents from Confluence")
            return documents
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Confluence documents: {e}")
            raise APIError(f"Document fetching failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching documents: {e}")
            raise APIError(f"Document fetching failed: {e}")
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status and configuration.
        
        Returns:
            Dict with connection status information
        """
        try:
            # Test current connection
            is_connected = self.connect()
            return {
                "connected": is_connected,
                "base_url": self.base_url,
                "space_key": self.space_key,
                "page_filter_count": len(self.page_filter),
                "auth_configured": bool(self.auth_token),
                "username": self.username if self.username else "Token-based"
            }
        except Exception as e:
            return {
                "connected": False,
                "base_url": self.base_url,
                "space_key": self.space_key,
                "page_filter_count": len(self.page_filter),
                "auth_configured": bool(self.auth_token),
                "error": str(e)
            }
