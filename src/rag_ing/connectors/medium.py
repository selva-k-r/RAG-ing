"""Medium connector for extracting articles."""

from typing import List, Dict, Any, Optional
from langchain.docstore.document import Document
import requests
from bs4 import BeautifulSoup
import logging
import time
import re
from urllib.parse import urljoin, urlparse

from .base import BaseConnector

logger = logging.getLogger(__name__)


class MediumConnector(BaseConnector):
    """Connector for Medium articles."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Medium connector.
        
        Config should contain:
        - user_id: Medium user ID or username
        - api_token: Optional Medium API token (if available)
        - rss_url: Optional RSS feed URL
        """
        super().__init__(config)
        self.user_id = config.get("user_id")
        self.api_token = config.get("api_token")
        self.rss_url = config.get("rss_url")
        self.session = None
    
    def connect(self) -> bool:
        """Establish connection to Medium."""
        try:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (compatible; RAG-ing/1.0)"
            })
            
            if self.api_token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.api_token}"
                })
            
            return self.test_connection()
        except Exception as e:
            logger.error(f"Failed to connect to Medium: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test Medium connection."""
        if not self.session:
            return False
        
        try:
            # Test with a simple request to Medium
            response = self.session.get("https://medium.com", timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Medium connection test failed: {e}")
            return False
    
    def fetch_documents(self, limit: int = 50) -> List[Document]:
        """Fetch articles from Medium."""
        if not self.session:
            raise ValueError("Not connected to Medium. Call connect() first.")
        
        documents = []
        
        try:
            if self.rss_url:
                documents.extend(self._fetch_from_rss(limit))
            elif self.user_id:
                documents.extend(self._fetch_from_user_profile(limit))
            else:
                logger.warning("No user_id or rss_url provided for Medium connector")
        
        except Exception as e:
            logger.error(f"Error fetching Medium documents: {e}")
        
        logger.info(f"Fetched {len(documents)} documents from Medium")
        return documents[:limit]
    
    def _fetch_from_rss(self, limit: int) -> List[Document]:
        """Fetch articles from RSS feed."""
        try:
            import feedparser
            
            feed = feedparser.parse(self.rss_url)
            documents = []
            
            for entry in feed.entries[:limit]:
                doc = self._convert_rss_entry_to_document(entry)
                if doc:
                    documents.append(doc)
                
                # Rate limiting
                time.sleep(0.5)
            
            return documents
            
        except ImportError:
            logger.error("feedparser library not available. Install with: pip install feedparser")
            return []
        except Exception as e:
            logger.error(f"Error fetching from RSS: {e}")
            return []
    
    def _fetch_from_user_profile(self, limit: int) -> List[Document]:
        """Fetch articles from user profile (web scraping approach)."""
        try:
            # Construct Medium user URL
            if self.user_id.startswith("@"):
                profile_url = f"https://medium.com/{self.user_id}"
            else:
                profile_url = f"https://medium.com/@{self.user_id}"
            
            response = self.session.get(profile_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article links (this is a simplified approach)
            article_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.startswith('/') and len(href.split('/')) >= 2:
                    # Medium article URLs typically follow a pattern
                    if re.match(r'^/[^/]+/[^/]+-[a-f0-9]+$', href):
                        article_links.append(urljoin("https://medium.com", href))
            
            # Fetch content for each article
            documents = []
            for url in article_links[:limit]:
                doc = self._fetch_article_content(url)
                if doc:
                    documents.append(doc)
                
                # Rate limiting to be respectful
                time.sleep(1)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error fetching from user profile: {e}")
            return []
    
    def _fetch_article_content(self, url: str) -> Optional[Document]:
        """Fetch full article content from URL."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title_elem = soup.find('h1') or soup.find('title')
            title = title_elem.get_text().strip() if title_elem else ""
            
            # Extract article content (Medium uses various selectors)
            content_selectors = [
                'article',
                '[data-testid="storyContent"]',
                '.postArticle-content',
                '.js-postField'
            ]
            
            content = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Remove script and style elements
                    for script in content_elem(["script", "style"]):
                        script.decompose()
                    
                    content = content_elem.get_text()
                    break
            
            if not content:
                logger.warning(f"Could not extract content from {url}")
                return None
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Extract author and publication date
            author = ""
            pub_date = ""
            
            # Try to find author
            author_elem = soup.select_one('[data-testid="authorName"]') or \
                         soup.select_one('.postMetaInline-authorLockup a')
            if author_elem:
                author = author_elem.get_text().strip()
            
            # Extract metadata
            metadata = {
                "source": "medium",
                "url": url,
                "title": title,
                "author": author,
                "published_date": pub_date,
                "platform": "Medium"
            }
            
            return Document(page_content=content, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Error fetching article from {url}: {e}")
            return None
    
    def _convert_rss_entry_to_document(self, entry) -> Optional[Document]:
        """Convert RSS entry to Document."""
        try:
            # Extract content from RSS entry
            content = entry.get('summary', '') or entry.get('description', '')
            
            # If we have a link, try to fetch full content
            if hasattr(entry, 'link') and entry.link:
                full_doc = self._fetch_article_content(entry.link)
                if full_doc:
                    return full_doc
            
            # Fallback to RSS summary
            if not content:
                return None
            
            # Clean HTML from summary
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.get_text()
            content = re.sub(r'\s+', ' ', content).strip()
            
            # Extract metadata from RSS entry
            metadata = {
                "source": "medium",
                "title": entry.get('title', ''),
                "author": entry.get('author', ''),
                "published_date": entry.get('published', ''),
                "url": entry.get('link', ''),
                "platform": "Medium"
            }
            
            return Document(page_content=content, metadata=metadata)
            
        except Exception as e:
            logger.error(f"Error converting RSS entry to document: {e}")
            return None