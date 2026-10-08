"""LLM provider and MCP STDIO client configuration.

LLM choices match travel-rag: Gemini (cloud) or Qwen via Ollama (local).
No OpenAI dependency.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Literal

from mcp import StdioServerParameters, stdio_client
from strands.tools.mcp import MCPClient

LLMProvider = Literal["gemini", "qwen"]

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"
DEFAULT_QWEN_MODEL = "qwen3:1.7b-q4_K_M"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_SECRETS_PATH = "~/.config/rag/.env"

ASTEROID_TOOLS = ("search_asteroids", "get_asteroid")
WEATHER_TOOLS = ("get_space_weather",)
EARTH_TOOLS = ("get_earth_events",)
COMMANDER_MCP_TOOLS = ("get_apod",)


def llm_provider() -> LLMProvider:
    raw = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
    if raw in ("ollama", "qwen"):
        return "qwen"
    return "gemini"


def _load_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    path = Path(os.environ.get("SECRETS_ENV_PATH", DEFAULT_SECRETS_PATH)).expanduser()
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        if name.strip() == "GEMINI_API_KEY":
            return value.strip().strip('"').strip("'")
    return ""


def build_model() -> Any:
    """Build a Strands model for the configured LLM provider."""
    provider = llm_provider()
    if provider == "gemini":
        from strands.models.gemini import GeminiModel

        api_key = _load_gemini_api_key()
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Export it or put it in "
                f"{os.environ.get('SECRETS_ENV_PATH', DEFAULT_SECRETS_PATH)}."
            )
        model_id = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        return GeminiModel(
            client_args={"api_key": api_key},
            model_id=model_id,
            params={"temperature": 0.3},
        )

    from strands.models.ollama import OllamaModel

    model_id = os.environ.get("QWEN_MODEL", DEFAULT_QWEN_MODEL)
    base_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
    return OllamaModel(model_id=model_id, base_url=base_url)


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
    if "NASA_API_KEY" not in env:
        env["NASA_API_KEY"] = "DEMO_KEY"

    return MCPClient(
        lambda: stdio_client(
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "nasa_mcp.server"],
                env=env,
            )
        )
    )
