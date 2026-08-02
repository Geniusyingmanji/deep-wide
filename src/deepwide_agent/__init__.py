"""Label-blind DeepWide search runtime with side-effect-free lazy exports."""

from __future__ import annotations

from typing import Any

__all__ = [
    "AnthropicSearchClient",
    "AzureNativeSearchClient",
    "DeepWideRuntime",
    "RuntimeConfig",
    "load_manifest",
]


def __getattr__(name: str) -> Any:
    """Preserve the public API without importing unrelated runtimes eagerly."""

    if name in {"DeepWideRuntime", "RuntimeConfig", "load_manifest"}:
        from . import runtime

        return getattr(runtime, name)
    if name == "AzureNativeSearchClient":
        from .native_search import AzureNativeSearchClient

        return AzureNativeSearchClient
    if name == "AnthropicSearchClient":
        from .anthropic_search import AnthropicSearchClient

        return AnthropicSearchClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
