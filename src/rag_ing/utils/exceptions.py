"""Custom exception classes for the RAG-ing application."""

class RAGingError(Exception):
    """Base exception class for all custom exceptions in this application."""
    pass

class ConnectionError(RAGingError):
    """Raised when there is an issue connecting to an external service."""
    pass

class AuthenticationError(RAGingError):
    """Raised when authentication with an external service fails."""
    pass

class APIError(RAGingError):
    """Raised when an API call to an external service fails for reasons other than authentication."""
    pass

class ConfigurationError(RAGingError):
    """Raised when there is a configuration problem."""
    pass

class DocumentProcessingError(RAGingError):
    """Raised during the document chunking or embedding process."""
    pass
