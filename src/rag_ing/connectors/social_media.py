"""Social media connectors for various platforms."""

from typing import List, Dict, Any, Optional
from langchain.docstore.document import Document
import requests
import logging
from datetime import datetime
import re

from .base import BaseConnector

logger = logging.getLogger(__name__)


class TwitterConnector(BaseConnector):
    """Connector for Twitter/X posts."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Twitter connector.
        
        Config should contain:
        - bearer_token: Twitter API v2 Bearer Token
        - username: Optional username to fetch tweets from
        """
        super().__init__(config)
        self.bearer_token = config.get("bearer_token")
        self.username = config.get("username")
        self.session = None
    
    def connect(self) -> bool:
        """Establish connection to Twitter API."""
        try:
            self.session = requests.Session()
            self.session.headers.update({
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            })
            
            return self.test_connection()
        except Exception as e:
            logger.error(f"Failed to connect to Twitter: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test Twitter API connection."""
        if not self.session:
            return False
        
        try:
            # Test with a simple API call
            url = "https://api.twitter.com/2/users/me"
            response = self.session.get(url, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Twitter connection test failed: {e}")
            return False
    
    def fetch_documents(self, limit: int = 50, include_replies: bool = False) -> List[Document]:
        """Fetch tweets as documents."""
        if not self.session:
            raise ValueError("Not connected to Twitter. Call connect() first.")
        
        documents = []
        
        try:
            if self.username:
                # Get user ID first
                user_id = self._get_user_id(self.username)
                if user_id:
                    documents = self._fetch_user_tweets(user_id, limit, include_replies)
            else:
                logger.warning("No username provided for Twitter connector")
        
        except Exception as e:
            logger.error(f"Error fetching Twitter documents: {e}")
        
        logger.info(f"Fetched {len(documents)} documents from Twitter")
        return documents
    
    def _get_user_id(self, username: str) -> Optional[str]:
        """Get user ID from username."""
        try:
            username = username.lstrip("@")
            url = f"https://api.twitter.com/2/users/by/username/{username}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", {}).get("id")
        
        except Exception as e:
            logger.error(f"Error getting user ID for {username}: {e}")
            return None
    
    def _fetch_user_tweets(self, user_id: str, limit: int, include_replies: bool) -> List[Document]:
        """Fetch tweets for a specific user."""
        try:
            params = {
                "max_results": min(100, limit),  # API limit
                "tweet.fields": "created_at,author_id,public_metrics,context_annotations",
                "user.fields": "name,username,description",
                "expansions": "author_id"
            }
            
            if not include_replies:
                params["exclude"] = "replies"
            
            url = f"https://api.twitter.com/2/users/{user_id}/tweets"
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            tweets = data.get("data", [])
            users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}
            
            documents = []
            for tweet in tweets:
                doc = self._convert_tweet_to_document(tweet, users)
                if doc:
                    documents.append(doc)
            
            return documents
        
        except Exception as e:
            logger.error(f"Error fetching user tweets: {e}")
            return []
    
    def _convert_tweet_to_document(self, tweet: Dict[str, Any], users: Dict[str, Dict]) -> Optional[Document]:
        """Convert tweet to Document."""
        try:
            content = tweet.get("text", "")
            if not content:
                return None
            
            # Get author info
            author_id = tweet.get("author_id")
            author_info = users.get(author_id, {})
            
            metadata = {
                "source": "twitter",
                "tweet_id": tweet.get("id"),
                "author_id": author_id,
                "author_name": author_info.get("name", ""),
                "author_username": author_info.get("username", ""),
                "created_at": tweet.get("created_at", ""),
                "public_metrics": tweet.get("public_metrics", {}),
                "platform": "Twitter/X"
            }
            
            # Add context annotations if available
            context_annotations = tweet.get("context_annotations", [])
            if context_annotations:
                metadata["context"] = [ann.get("entity", {}).get("name") for ann in context_annotations]
            
            return Document(page_content=content, metadata=metadata)
        
        except Exception as e:
            logger.error(f"Error converting tweet to document: {e}")
            return None


class RedditConnector(BaseConnector):
    """Connector for Reddit posts and comments."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Reddit connector.
        
        Config should contain:
        - client_id: Reddit app client ID
        - client_secret: Reddit app client secret
        - user_agent: User agent string
        - subreddit: Subreddit name to fetch from
        """
        super().__init__(config)
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.user_agent = config.get("user_agent", "RAG-ing/1.0")
        self.subreddit = config.get("subreddit")
        self.session = None
        self.access_token = None
    
    def connect(self) -> bool:
        """Establish connection to Reddit API."""
        try:
            # Get access token
            auth = requests.auth.HTTPBasicAuth(self.client_id, self.client_secret)
            data = {
                'grant_type': 'client_credentials'
            }
            headers = {'User-Agent': self.user_agent}
            
            response = requests.post(
                'https://www.reddit.com/api/v1/access_token',
                auth=auth,
                data=data,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            
            if not self.access_token:
                return False
            
            # Setup session
            self.session = requests.Session()
            self.session.headers.update({
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': self.user_agent
            })
            
            return self.test_connection()
        
        except Exception as e:
            logger.error(f"Failed to connect to Reddit: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test Reddit API connection."""
        if not self.session:
            return False
        
        try:
            response = self.session.get('https://oauth.reddit.com/api/v1/me', timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Reddit connection test failed: {e}")
            return False
    
    def fetch_documents(self, limit: int = 50, sort: str = "hot") -> List[Document]:
        """Fetch Reddit posts as documents."""
        if not self.session:
            raise ValueError("Not connected to Reddit. Call connect() first.")
        
        documents = []
        
        try:
            if self.subreddit:
                documents = self._fetch_subreddit_posts(self.subreddit, limit, sort)
            else:
                logger.warning("No subreddit provided for Reddit connector")
        
        except Exception as e:
            logger.error(f"Error fetching Reddit documents: {e}")
        
        logger.info(f"Fetched {len(documents)} documents from Reddit")
        return documents
    
    def _fetch_subreddit_posts(self, subreddit: str, limit: int, sort: str) -> List[Document]:
        """Fetch posts from a specific subreddit."""
        try:
            url = f"https://oauth.reddit.com/r/{subreddit}/{sort}"
            params = {"limit": min(100, limit)}  # Reddit API limit
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            posts = data.get("data", {}).get("children", [])
            
            documents = []
            for post_data in posts:
                post = post_data.get("data", {})
                doc = self._convert_post_to_document(post)
                if doc:
                    documents.append(doc)
            
            return documents
        
        except Exception as e:
            logger.error(f"Error fetching subreddit posts: {e}")
            return []
    
    def _convert_post_to_document(self, post: Dict[str, Any]) -> Optional[Document]:
        """Convert Reddit post to Document."""
        try:
            # Combine title and selftext for content
            title = post.get("title", "")
            selftext = post.get("selftext", "")
            
            content = title
            if selftext:
                content += "\n\n" + selftext
            
            if not content.strip():
                return None
            
            # Clean up content
            content = re.sub(r'\s+', ' ', content).strip()
            
            metadata = {
                "source": "reddit",
                "post_id": post.get("id"),
                "subreddit": post.get("subreddit"),
                "author": post.get("author"),
                "created_utc": post.get("created_utc"),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "url": f"https://reddit.com{post.get('permalink', '')}",
                "platform": "Reddit",
                "flair": post.get("link_flair_text", ""),
                "is_self": post.get("is_self", False)
            }
            
            return Document(page_content=content, metadata=metadata)
        
        except Exception as e:
            logger.error(f"Error converting Reddit post to document: {e}")
            return None


class ConnectorManager:
    """Manages different social media and content connectors."""
    
    def __init__(self):
        self._connectors: Dict[str, BaseConnector] = {}
        self._connector_classes = {
            "twitter": TwitterConnector,
            "reddit": RedditConnector,
        }
    
    def create_connector(self, connector_type: str, config: Dict[str, Any]) -> BaseConnector:
        """Create a connector of the specified type."""
        if connector_type not in self._connector_classes:
            raise ValueError(f"Unsupported connector type: {connector_type}")
        
        connector_class = self._connector_classes[connector_type]
        connector = connector_class(config)
        
        self._connectors[connector_type] = connector
        return connector
    
    def get_connector(self, connector_type: str) -> Optional[BaseConnector]:
        """Get an existing connector."""
        return self._connectors.get(connector_type)
    
    def list_available_connectors(self) -> List[str]:
        """List available connector types."""
        return list(self._connector_classes.keys())


# Global connector manager instance
social_connector_manager = ConnectorManager()