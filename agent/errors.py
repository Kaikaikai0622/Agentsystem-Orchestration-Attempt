"""
Error taxonomy for Agent System.
"""


class AgentError(Exception):
    """Base class for agent system errors."""

    def __init__(self, message: str, error_type: str = "error", retryable: bool = False):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable


class ValidationError(AgentError):
    """Input validation error."""

    def __init__(self, message: str):
        super().__init__(message, error_type="validation", retryable=False)


class ProviderError(AgentError):
    """Provider/API error that may be retried."""

    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message, error_type="provider", retryable=retryable)


class RetryableError(AgentError):
    """Explicitly retryable error."""

    def __init__(self, message: str):
        super().__init__(message, error_type="retryable", retryable=True)
