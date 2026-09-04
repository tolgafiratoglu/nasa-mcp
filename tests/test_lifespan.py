"""Lifespan and import tests — no live NASA HTTP calls."""

from __future__ import annotations

import pytest

from nasa_mcp.server import app_lifespan, mcp


def test_import_server_has_no_module_level_clients():
    """Importing the server must not construct NASA clients at module scope."""
    import nasa_mcp.server as server_mod

    assert not hasattr(server_mod, "_apod_client")
    assert not hasattr(server_mod, "_neows_client")
    assert not hasattr(server_mod, "_donki_client")
    assert not hasattr(server_mod, "_eonet_client")
    assert server_mod.mcp is not None


@pytest.mark.asyncio
async def test_lifespan_creates_clients():
    async with app_lifespan(mcp) as ctx:
        assert ctx.apod is not None
        assert ctx.neows is not None
        assert ctx.donki is not None
        assert ctx.eonet is not None
        assert ctx.http is not None
        assert not ctx.http.is_closed
        # Adapters share the same HTTP client (not owned per client)
        assert ctx.apod._http is ctx.http
        assert ctx.neows._http is ctx.http


@pytest.mark.asyncio
async def test_lifespan_closes_shared_http_client():
    async with app_lifespan(mcp) as ctx:
        http = ctx.http
        assert not http.is_closed

    assert http.is_closed
