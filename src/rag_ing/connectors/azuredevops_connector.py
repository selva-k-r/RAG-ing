"""Azure DevOps connector for project files and documentation ingestion.

Integrates with Azure DevOps REST API to fetch:
- Repository files
- Wiki pages
- Pull request descriptions
- Work item descriptions
"""

import logging
import requests
import base64
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from ..utils.exceptions import ConnectionError, AuthenticationError, APIError

logger = logging.getLogger(__name__)


class AzureDevOpsConnector:
    """Connector for Azure DevOps repositories and documentation."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Azure DevOps connector.
        
        Args:
            config: Configuration dict with:
                - organization: Azure DevOps organization name
                - project: Project name
                - pat_token: Personal Access Token
                - repo_name: Repository name (optional)
                - file_extensions: List of file extensions to fetch (optional)
        """
        self.config = config
        self.organization = config.get("organization")
        self.project = config.get("project")
        self.pat_token = config.get("pat_token")
        self.repo_name = config.get("repo_name")
        self.file_extensions = config.get("file_extensions", [".md", ".py", ".txt", ".json", ".yaml", ".yml"])
        
        if not all([self.organization, self.project, self.pat_token]):
            raise ConnectionError("organization, project, and pat_token are required")
        
        # Azure DevOps REST API base URL
        self.base_url = f"https://dev.azure.com/{self.organization}/{self.project}/_apis"
        
        # Setup authentication - Azure DevOps uses Basic Auth with PAT
        auth_string = f":{self.pat_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Initialized Azure DevOps connector for {self.organization}/{self.project}")
    
    def connect(self) -> bool:
        """Test connection to Azure DevOps.
        
        Returns:
            bool: True if connection successful
            
        Raises:
            AuthenticationError: If authentication fails
            ConnectionError: If connection fails
        """
        try:
            logger.info(f"Testing connection to Azure DevOps...")
            
            # Test with a simple API call - list repositories
            test_url = f"{self.base_url}/git/repositories?api-version=7.0"
            response = requests.get(
                test_url,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 401:
                raise AuthenticationError("Invalid Azure DevOps PAT token")
            elif response.status_code == 403:
                raise AuthenticationError("Access denied - check token permissions")
            elif response.status_code == 404:
                raise ConnectionError(f"Project '{self.project}' not found")
            elif response.status_code != 200:
                raise ConnectionError(f"Connection failed: {response.status_code} - {response.text}")
            
            repos = response.json().get("value", [])
            logger.info(f"Successfully connected! Found {len(repos)} repositories")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Azure DevOps: {e}")
            raise ConnectionError(f"Azure DevOps connection failed: {e}")
    
    def list_repositories(self) -> List[Dict[str, Any]]:
        """List all repositories in the project.
        
        Returns:
            List of repository information dicts
        """
        try:
            url = f"{self.base_url}/git/repositories?api-version=7.0"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                raise APIError(f"Failed to list repositories: {response.status_code}")
            
            repos = response.json().get("value", [])
            logger.info(f"Found {len(repos)} repositories")
            
            return [{
                "id": repo.get("id"),
                "name": repo.get("name"),
                "url": repo.get("webUrl"),
                "default_branch": repo.get("defaultBranch", "refs/heads/main")
            } for repo in repos]
            
        except Exception as e:
            logger.error(f"Error listing repositories: {e}")
            raise APIError(f"Failed to list repositories: {e}")
    
    def get_file_commit_info(self, repo_id: str, file_path: str, branch: str) -> Dict[str, Any]:
        """Get commit information for a specific file.
        
        Returns last modified date and author for change tracking.
        
        Args:
            repo_id: Repository ID
            file_path: File path
            branch: Branch name
            
        Returns:
            Dict with commit info (date, author)
        """
        try:
            # Format branch ref
            if not branch.startswith("refs/heads/"):
                branch = f"refs/heads/{branch}"
            
            url = f"{self.base_url}/git/repositories/{repo_id}/commits"
            params = {
                "api-version": "7.0",
                "searchCriteria.itemPath": file_path,
                "searchCriteria.itemVersion.version": branch.replace("refs/heads/", ""),
                "searchCriteria.itemVersion.versionType": "branch",
                "$top": 1  # Get only the latest commit
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                commits = response.json().get("value", [])
                if commits:
                    latest_commit = commits[0]
                    return {
                        "last_modified_date": latest_commit.get("author", {}).get("date", "unknown"),
                        "last_modified_by": latest_commit.get("author", {}).get("name", "unknown"),
                        "commit_id": latest_commit.get("commitId", "unknown")
                    }
            
            logger.debug(f"No commit info found for {file_path}")
            return {
                "last_modified_date": "unknown",
                "last_modified_by": "unknown",
                "commit_id": "unknown"
            }
        
        except Exception as e:
            logger.warning(f"Failed to get commit info for {file_path}: {e}")
            return {
                "last_modified_date": "unknown",
                "last_modified_by": "unknown",
                "commit_id": "unknown"
            }
    
    def fetch_repository_files(self, repo_name: Optional[str] = None, 
                               branch: str = "main",
                               path: str = "/",
                               recursive: bool = True,
                               include_commit_info: bool = True) -> List[Document]:
        """Fetch files from an Azure DevOps repository.
        
        Args:
            repo_name: Repository name (defaults to config repo_name)
            branch: Branch name (default: main)
            path: Starting path (default: root)
            recursive: Fetch files recursively
            
        Returns:
            List[Document]: List of documents with file content
        """
        repo_name = repo_name or self.repo_name
        if not repo_name:
            raise ValueError("repo_name is required")
        
        logger.info(f"Fetching files from {repo_name}, branch: {branch}, path: {path}")
        
        documents = []
        
        try:
            # Get repository ID first
            repo_id = self._get_repo_id(repo_name)
            
            # List items in the repository
            items = self._list_repo_items(repo_id, branch, path, recursive)
            
            logger.info(f"Found {len(items)} items in repository")
            
            # Fetch content for each file
            for item in items:
                if item.get("gitObjectType") == "blob":  # It's a file
                    file_path = item.get("path")
                    
                    # Check if file extension is in our filter list
                    if not any(file_path.endswith(ext) for ext in self.file_extensions):
                        logger.debug(f"Skipping {file_path} - extension not in filter")
                        continue
                    
                    # Fetch file content
                    try:
                        content = self._fetch_file_content(repo_id, file_path, branch)
                        
                        if content:
                            # Detect language for better metadata
                            file_ext = file_path.split('.')[-1].lower()
                            language_map = {
                                'py': 'python',
                                'sql': 'sql',
                                'yaml': 'yaml',
                                'yml': 'yaml',
                                'json': 'json',
                                'md': 'markdown'
                            }
                            language = language_map.get(file_ext, 'code')
                            
                            # Count lines for metadata
                            line_count = len(content.split('\n'))
                            
                            # Get commit info for change tracking
                            commit_info = {}
                            if include_commit_info:
                                commit_info = self.get_file_commit_info(repo_id, file_path, branch)
                            
                            # Generate web URL for citation
                            web_url = f"https://dev.azure.com/{self.organization}/{self.project}/_git/{repo_name}?path={file_path}&version=GB{branch.replace('refs/heads/', '')}"
                            
                            doc = Document(
                                page_content=content,
                                metadata={
                                    "source": f"Azure DevOps: {repo_name}",
                                    "file_path": file_path,
                                    "repository": repo_name,
                                    "branch": branch,
                                    "type": "azure_devops_file",
                                    "language": language,
                                    "total_lines": line_count,
                                    "url": web_url,
                                    "title": file_path.split("/")[-1],
                                    "organization": self.organization,
                                    "project": self.project,
                                    # Will be enhanced with line ranges during chunking
                                    "is_code": language in ['python', 'sql', 'yaml'],
                                    # Change tracking metadata
                                    "last_modified_date": commit_info.get("last_modified_date", "unknown"),
                                    "last_modified_by": commit_info.get("last_modified_by", "unknown"),
                                    "commit_id": commit_info.get("commit_id", "unknown")
                                }
                            )
                            documents.append(doc)
                            logger.info(f"Added {language} file: {file_path} ({line_count} lines, modified: {commit_info.get('last_modified_date', 'unknown')[:10]})")
                    
                    except Exception as file_error:
                        logger.warning(f"Failed to fetch {file_path}: {file_error}")
                        continue
            
            logger.info(f"Successfully fetched {len(documents)} files")
            return documents
            
        except Exception as e:
            logger.error(f"Error fetching repository files: {e}")
            raise APIError(f"Failed to fetch files: {e}")
    
    def _get_repo_id(self, repo_name: str) -> str:
        """Get repository ID by name."""
        try:
            url = f"{self.base_url}/git/repositories/{repo_name}?api-version=7.0"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                raise APIError(f"Repository '{repo_name}' not found")
            
            return response.json().get("id")
        except Exception as e:
            raise APIError(f"Failed to get repo ID: {e}")
    
    def _list_repo_items(self, repo_id: str, branch: str, path: str, recursive: bool) -> List[Dict]:
        """List items in repository."""
        try:
            # Format branch ref
            if not branch.startswith("refs/heads/"):
                branch = f"refs/heads/{branch}"
            
            url = f"{self.base_url}/git/repositories/{repo_id}/items"
            params = {
                "api-version": "7.0",
                "versionDescriptor.version": branch.replace("refs/heads/", ""),
                "versionDescriptor.versionType": "branch",
                "scopePath": path,
                "recursionLevel": "full" if recursive else "oneLevel"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=60)
            
            if response.status_code != 200:
                raise APIError(f"Failed to list items: {response.status_code} - {response.text}")
            
            return response.json().get("value", [])
        except Exception as e:
            raise APIError(f"Failed to list items: {e}")
    
    def _fetch_file_content(self, repo_id: str, file_path: str, branch: str) -> Optional[str]:
        """Fetch content of a specific file."""
        try:
            # Format branch ref
            if not branch.startswith("refs/heads/"):
                branch = f"refs/heads/{branch}"
            
            url = f"{self.base_url}/git/repositories/{repo_id}/items"
            params = {
                "api-version": "7.0",
                "path": file_path,
                "versionDescriptor.version": branch.replace("refs/heads/", ""),
                "versionDescriptor.versionType": "branch",
                "$format": "text"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.text
            else:
                logger.warning(f"Failed to fetch {file_path}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching file content: {e}")
            return None
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        try:
            is_connected = self.connect()
            repos = self.list_repositories()
            
            return {
                "connected": is_connected,
                "organization": self.organization,
                "project": self.project,
                "repositories_count": len(repos),
                "repositories": [r["name"] for r in repos[:5]],  # First 5
                "auth_configured": bool(self.pat_token)
            }
        except Exception as e:
            return {
                "connected": False,
                "organization": self.organization,
                "project": self.project,
                "error": str(e)
            }

