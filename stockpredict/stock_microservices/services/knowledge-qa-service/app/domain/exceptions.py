"""Domain-specific exceptions for Knowledge QA."""


class KnowledgeQAError(Exception):
    """Base exception for the Knowledge QA domain."""
    pass


class GraphConnectionError(KnowledgeQAError):
    """Raised when Neo4j connection fails."""
    pass


class LLMConnectionError(KnowledgeQAError):
    """Raised when LLM service is unreachable."""
    pass


class SessionNotFoundError(KnowledgeQAError):
    """Raised when a chat session is not found."""
    pass


class EmptyQueryError(KnowledgeQAError):
    """Raised when the user query is empty or invalid."""
    pass


class GraphQueryError(KnowledgeQAError):
    """Raised when a graph query fails."""
    pass
