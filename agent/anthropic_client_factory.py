"""
Anthropic SDK client factory.
"""

from typing import Dict, Tuple, Any

try:
    import anthropic
except ImportError as exc:  # pragma: no cover - handled at runtime
    anthropic = None
    _import_error = exc
else:
    _import_error = None

_clients: Dict[Tuple[str, str, int, bool], Any] = {}


def get_anthropic_client(api_key: str, base_url: str, timeout: int) -> Any:
    if anthropic is None:
        raise ImportError(
            "anthropic SDK is not installed. Install anthropic to use Anthropic-compatible providers."
        ) from _import_error

    normalized_base_url = (base_url or "").lower()
    use_bearer_auth = bool(normalized_base_url) and "api.anthropic.com" not in normalized_base_url
    cache_key = (api_key, base_url, int(timeout), use_bearer_auth)
    if cache_key not in _clients:
        if use_bearer_auth:
            _clients[cache_key] = anthropic.Anthropic(
                auth_token=api_key,
                base_url=base_url,
                timeout=timeout
            )
        else:
            _clients[cache_key] = anthropic.Anthropic(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout
            )
    return _clients[cache_key]
