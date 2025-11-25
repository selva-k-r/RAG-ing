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
                - include_paths: List of paths to include (optional, default: all)
                - exclude_paths: List of paths to exclude (optional)
                - include_file_types: List of file types to include (optional)
                - exclude_file_types: List of file types to exclude (optional)
        """
        self.config = config
        self.organization = config.get("organization")
        self.project = config.get("project")
        self.pat_token = config.get("pat_token")
        self.repo_name = config.get("repo_name")
        self.file_extensions = config.get("file_extensions", [".md", ".py", ".txt", ".json", ".yaml", ".yml"])
        
        # Path filtering
        self.include_paths = config.get("include_paths", [])  # Empty = include all
        self.exclude_paths = config.get("exclude_paths", [])  # Paths to skip
        
        # File type filtering (in addition to file_extensions for backward compatibility)
        self.include_file_types = config.get("include_file_types", [])  # Empty = use file_extensions
        self.exclude_file_types = config.get("exclude_file_types", [])  # Types to skip
        
        # Commit history configuration
        self.fetch_commit_history = config.get("fetch_commit_history", True)  # Fetch detailed history
        self.commits_per_file = config.get("commits_per_file", 10)  # Number of commits to fetch per file
        
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
        
        # Log filtering configuration
        if self.include_paths:
            logger.info(f"Path filter - Include: {self.include_paths}")
        if self.exclude_paths:
            logger.info(f"Path filter - Exclude: {self.exclude_paths}")
        if self.include_file_types:
            logger.info(f"File type filter - Include: {self.include_file_types}")
        if self.exclude_file_types:
            logger.info(f"File type filter - Exclude: {self.exclude_file_types}")
    
    def _should_include_path(self, file_path: str) -> bool:
        """Check if file path should be included based on path filters.
        
        Logic:
        1. If include_paths specified, file must match at least one include path
        2. If exclude_paths specified, file must NOT match any exclude path
        3. Exclude wins over include (if file matches both, it's excluded)
        
        Args:
            file_path: File path to check
            
        Returns:
            bool: True if path should be included
        """
        # Check include paths (if specified)
        if self.include_paths:
            # File must match at least one include path (prefix match)
            matches_include = any(
                file_path.startswith(include_path) 
                for include_path in self.include_paths
            )
            if not matches_include:
                logger.debug(f"Skipping {file_path} - doesn't match include_paths")
                return False
        
        # Check exclude paths (if specified) - exclude wins
        if self.exclude_paths:
            matches_exclude = any(
                file_path.startswith(exclude_path)
                for exclude_path in self.exclude_paths
            )
            if matches_exclude:
                logger.debug(f"Skipping {file_path} - matches exclude_paths")
                return False
        
        return True
    
    def _should_include_file_type(self, file_path: str) -> bool:
        """Check if file type should be included based on file type filters.
        
        Logic:
        1. If include_file_types specified, use it; otherwise use file_extensions
        2. If exclude_file_types specified, file must NOT have excluded extension
        3. Exclude wins over include
        
        Args:
            file_path: File path to check
            
        Returns:
            bool: True if file type should be included
        """
        # Determine which include list to use
        include_types = self.include_file_types if self.include_file_types else self.file_extensions
        
        # Check include file types
        if include_types:
            matches_include = any(file_path.endswith(ext) for ext in include_types)
            if not matches_include:
                logger.debug(f"Skipping {file_path} - extension not in include list")
                return False
        
        # Check exclude file types - exclude wins
        if self.exclude_file_types:
            matches_exclude = any(file_path.endswith(ext) for ext in self.exclude_file_types)
            if matches_exclude:
                logger.debug(f"Skipping {file_path} - extension in exclude list")
                return False
        
        return True
    
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
    
    def get_file_commit_history(self, repo_id: str, file_path: str, branch: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get detailed commit history for a specific file.
        
        Args:
            repo_id: Repository ID
            file_path: File path
            branch: Branch name
            limit: Number of commits to fetch (default: 10)
            
        Returns:
            List of commit dictionaries with detailed information
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
                "$top": limit  # Fetch last N commits
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                commits = response.json().get("value", [])
                
                # Parse and structure commit data
                commit_history = []
                for commit in commits:
                    author = commit.get("author", {})
                    committer = commit.get("committer", {})
                    
                    commit_data = {
                        "commit_id": commit.get("commitId", "unknown"),
                        "short_id": commit.get("commitId", "unknown")[:7],
                        "message": commit.get("comment", "No message"),
                        "author_name": author.get("name", "Unknown"),
                        "author_email": author.get("email", ""),
                        "author_date": author.get("date", "unknown"),
                        "committer_name": committer.get("name", "Unknown"),
                        "committer_date": committer.get("date", "unknown"),
                        "url": commit.get("url", ""),
                        "remote_url": commit.get("remoteUrl", "")
                    }
                    commit_history.append(commit_data)
                
                logger.debug(f"Fetched {len(commit_history)} commits for {file_path}")
                return commit_history
            else:
                logger.warning(f"Failed to fetch commit history for {file_path}: {response.status_code}")
                return []
        
        except Exception as e:
            logger.warning(f"Error fetching commit history for {file_path}: {e}")
            return []
    
    def fetch_repository_files_streaming(self, repo_name: Optional[str] = None,
                                        branch: str = "main",
                                        path: str = "/",
                                        recursive: bool = True,
                                        include_commit_info: bool = True,
                                        batch_size: int = 50):
        """
        Fetch files from Azure DevOps repository in BATCHES (streaming mode).
        
        This generator yields batches of documents as they're fetched, allowing
        incremental processing without waiting for all files to be fetched first.
        
        Benefits:
        - Faster feedback (see progress immediately)
        - Fault tolerance (partial results saved if crash)
        - Lower memory usage (process in batches)
        - Better progress tracking
        
        Args:
            repo_name: Repository name
            branch: Branch name
            path: Starting path
            recursive: Fetch recursively
            include_commit_info: Fetch commit info
            batch_size: Number of documents per batch (default: 50)
            
        Yields:
            List[Document]: Batches of documents
        """
        repo_name = repo_name or self.repo_name
        if not repo_name:
            raise ValueError("repo_name is required")
        
        logger.info(f" Streaming files from {repo_name}, branch: {branch}, path: {path} (batch size: {batch_size})")
        
        try:
            # Get repository ID first
            repo_id = self._get_repo_id(repo_name)
            
            # List items in the repository
            items = self._list_repo_items(repo_id, branch, path, recursive)
            
            logger.info(f"Found {len(items)} items in repository - processing in batches")
            
            # Process files in batches
            batch = []
            files_skipped_path = 0
            files_skipped_type = 0
            files_processed = 0
            
            for item in items:
                if item.get("gitObjectType") == "blob":  # It's a file
                    file_path = item.get("path")
                    
                    # Apply path filtering
                    if not self._should_include_path(file_path):
                        files_skipped_path += 1
                        continue
                    
                    # Apply file type filtering
                    if not self._should_include_file_type(file_path):
                        files_skipped_type += 1
                        continue
                    
                    # Fetch file content
                    try:
                        content = self._fetch_file_content(repo_id, file_path, branch)
                        
                        if content:
                            # Create document (same logic as original method)
                            file_ext = file_path.split('.')[-1].lower()
                            language_map = {
                                'py': 'python', 'sql': 'sql', 'yaml': 'yaml',
                                'yml': 'yaml', 'json': 'json', 'md': 'markdown'
                            }
                            language = language_map.get(file_ext, 'code')
                            line_count = len(content.split('\n'))
                            
                            # Get commit info
                            commit_info = {}
                            if include_commit_info:
                                commit_info = self.get_file_commit_info(repo_id, file_path, branch)
                            
                            # Get commit history if enabled
                            commit_history = []
                            if self.fetch_commit_history:
                                commit_history = self.get_file_commit_history(
                                    repo_id, file_path, branch, limit=self.commits_per_file
                                )
                            
                            # Generate web URL
                            web_url = f"https://dev.azure.com/{self.organization}/{self.project}/_git/{repo_name}?path={file_path}&version=GB{branch.replace('refs/heads/', '')}"
                            
                            # Build metadata
                            metadata = {
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
                                "is_code": language in ['python', 'sql', 'yaml'],
                                "last_modified_date": commit_info.get("last_modified_date", "unknown"),
                                "last_modified_by": commit_info.get("last_modified_by", "unknown"),
                                "commit_id": commit_info.get("commit_id", "unknown")
                            }
                            
                            # Add commit history if available
                            if commit_history:
                                metadata["commit_history"] = commit_history
                                metadata["commit_count"] = len(commit_history)
                                history_summary = self._format_commit_history_summary(commit_history)
                                metadata["commit_history_summary"] = history_summary
                            
                            doc = Document(page_content=content, metadata=metadata)
                            batch.append(doc)
                            files_processed += 1
                            
                            # Yield batch when full
                            if len(batch) >= batch_size:
                                logger.info(f" Yielding batch of {len(batch)} files (total processed: {files_processed})")
                                yield batch
                                batch = []
                    
                    except Exception as file_error:
                        logger.warning(f"Failed to fetch {file_path}: {file_error}")
                        continue
            
            # Yield remaining documents
            if batch:
                logger.info(f" Yielding final batch of {len(batch)} files (total: {files_processed})")
                yield batch
            
            # Log summary
            logger.info(f"Streaming complete: {files_processed} files processed")
            if files_skipped_path > 0:
                logger.info(f"Skipped {files_skipped_path} files due to path filters")
            if files_skipped_type > 0:
                logger.info(f"Skipped {files_skipped_type} files due to file type filters")
                
        except Exception as e:
            logger.error(f"Error in streaming fetch: {e}")
            raise APIError(f"Failed to fetch files: {e}")
    
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
            files_skipped_path = 0
            files_skipped_type = 0
            
            for item in items:
                if item.get("gitObjectType") == "blob":  # It's a file
                    file_path = item.get("path")
                    
                    # Apply path filtering
                    if not self._should_include_path(file_path):
                        files_skipped_path += 1
                        continue
                    
                    # Apply file type filtering
                    if not self._should_include_file_type(file_path):
                        files_skipped_type += 1
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
                            
                            # Get basic commit info for change tracking
                            commit_info = {}
                            if include_commit_info:
                                commit_info = self.get_file_commit_info(repo_id, file_path, branch)
                            
                            # Get detailed commit history if enabled
                            commit_history = []
                            if self.fetch_commit_history:
                                commit_history = self.get_file_commit_history(
                                    repo_id, file_path, branch, limit=self.commits_per_file
                                )
                            
                            # Generate web URL for citation
                            web_url = f"https://dev.azure.com/{self.organization}/{self.project}/_git/{repo_name}?path={file_path}&version=GB{branch.replace('refs/heads/', '')}"
                            
                            # Build metadata dictionary
                            metadata = {
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
                            
                            # Add commit history if available
                            if commit_history:
                                metadata["commit_history"] = commit_history
                                metadata["commit_count"] = len(commit_history)
                                # Create a summary string for easy querying
                                history_summary = self._format_commit_history_summary(commit_history)
                                metadata["commit_history_summary"] = history_summary
                            
                            doc = Document(
                                page_content=content,
                                metadata=metadata
                            )
                            documents.append(doc)
                            
                            # Log with commit history info
                            history_info = f", {len(commit_history)} commits" if commit_history else ""
                            logger.info(f"Added {language} file: {file_path} ({line_count} lines{history_info}, modified: {commit_info.get('last_modified_date', 'unknown')[:10]})")
                    
                    except Exception as file_error:
                        logger.warning(f"Failed to fetch {file_path}: {file_error}")
                        continue
            
            logger.info(f"Successfully fetched {len(documents)} files")
            if files_skipped_path > 0:
                logger.info(f"Skipped {files_skipped_path} files due to path filters")
            if files_skipped_type > 0:
                logger.info(f"Skipped {files_skipped_type} files due to file type filters")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error fetching repository files: {e}")
            raise APIError(f"Failed to fetch files: {e}")
    
    def _format_commit_history_summary(self, commit_history: List[Dict[str, Any]]) -> str:
        """Format commit history into a readable summary string.
        
        Args:
            commit_history: List of commit dictionaries
            
        Returns:
            Formatted string summary of commits
        """
        if not commit_history:
            return "No commit history available"
        
        lines = ["Recent commit history:"]
        for commit in commit_history:
            # Format date for readability
            date_str = commit.get("author_date", "unknown")
            if date_str != "unknown":
                try:
                    # Extract just the date part (YYYY-MM-DD)
                    date_str = date_str.split("T")[0]
                except Exception:
                    pass
            
            # Clean commit message (first line only, truncate if too long)
            message = commit.get("message", "No message").split("\n")[0]
            if len(message) > 80:
                message = message[:77] + "..."
            
            short_id = commit.get("short_id", "???????")
            author = commit.get("author_name", "Unknown")
            
            lines.append(f"- [{date_str}] {short_id} - {message} (by {author})")
        
        return "\n".join(lines)
    
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

