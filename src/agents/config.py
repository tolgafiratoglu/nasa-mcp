"""LLM provider and MCP STDIO client configuration.

LLM choices match travel-rag: Gemini (cloud) or Qwen via Ollama (local).
Settings live in ``agents.settings`` (same env contract as travel-rag).
No OpenAI dependency.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Literal

from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPClient

from agents.settings import settings

LLMProvider = Literal["gemini", "qwen"]

ASTEROID_TOOLS = ("search_asteroids", "get_asteroid")
WEATHER_TOOLS = ("get_space_weather",)
EARTH_TOOLS = ("get_earth_events",)
COMMANDER_MCP_TOOLS = ("get_apod",)


def llm_provider() -> LLMProvider:
    return settings.llm_provider


def build_model() -> Any:
    """Build a Strands model for the configured LLM provider."""
    provider = settings.llm_provider
    if provider == "gemini":
        from strands.models.gemini import GeminiModel

        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Export it or put it in "
                f"{settings.secrets_env_path} (same as travel-rag)."
            )
        return GeminiModel(
            client_args={"api_key": settings.gemini_api_key},
            model_id=settings.gemini_model,
            params={"temperature": 0.3},
        )

    from strands.models.ollama import OllamaModel

    return OllamaModel(
        model_id=settings.qwen_model,
        base_url=settings.ollama_base_url,
    )


def tool_name(tool: Any) -> str:
    """Resolve a Strands/MCP tool object's public name."""
    for attr in ("tool_name", "name"):
        value = getattr(tool, attr, None)
        if isinstance(value, str) and value:
            return value
    spec = getattr(tool, "tool_spec", None) or getattr(tool, "spec", None)
    if isinstance(spec, dict) and spec.get("name"):
        return str(spec["name"])
    raise ValueError(f"Cannot determine tool name for {tool!r}")


def filter_tools_by_name(tools: list[Any], allowed: tuple[str, ...] | list[str]) -> list[Any]:
    """Enforce a tool whitelist by name (agent-level, not prompt-only)."""
    allow = set(allowed)
    selected = [t for t in tools if tool_name(t) in allow]
    missing = allow - {tool_name(t) for t in selected}
    if missing:
        raise RuntimeError(
            f"MCP tools missing from server (whitelist incomplete): {sorted(missing)}"
        )
    return selected


def index_tools(tools: list[Any]) -> dict[str, Any]:
    return {tool_name(t): t for t in tools}


def create_nasa_mcp_client() -> MCPClient:
    """STDIO client pointing at this repo's NASA MCP server."""
    env = os.environ.copy()
    env["NASA_API_KEY"] = settings.nasa_api_key or env.get("NASA_API_KEY", "DEMO_KEY")

    return MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "nasa_mcp.server"],
                env=env,
            )
        )
    )
