"""Tests for MCP renderer transport expansion behavior."""

import pytest

from one_skills_manager.mcp import MCPConfig, MCPServer, MCPTransport
from one_skills_manager.profiles import Profile
from one_skills_manager.renderers import codex
from one_skills_manager.renderers.common import (
    build_transport_config,
    render_mcp_servers,
)


def _make_mcp_config(transport: MCPTransport) -> MCPConfig:
    """Create an in-memory MCP config with one server and transport."""
    config = MCPConfig()
    config.servers["filesystem"] = MCPServer(
        name="filesystem",
        description="Filesystem MCP",
        transports={"local": transport},
    )
    return config


def _make_profile() -> Profile:
    """Create a profile that enables the filesystem MCP transport."""
    return Profile(name="dev", mcp_servers={"filesystem": "local"})


def test_build_transport_config_expands_stdio_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It expands HOME and env vars for stdio transport values."""
    monkeypatch.setenv("HOME", "/tmp/home-user")
    monkeypatch.setenv("PROJECT_ROOT", "/tmp/project")

    transport = MCPTransport(
        type="stdio",
        command="$HOME/.local/bin/mcp-server",
        args=["$HOME/workspace", "~/notes", "$PROJECT_ROOT/data"],
        env={"ROOT": "$PROJECT_ROOT", "CACHE": "~/cache"},
    )

    rendered = build_transport_config(transport)

    assert rendered["command"] == "/tmp/home-user/.local/bin/mcp-server"
    assert rendered["args"] == [
        "/tmp/home-user/workspace",
        "/tmp/home-user/notes",
        "/tmp/project/data",
    ]
    assert rendered["env"] == {
        "ROOT": "/tmp/project",
        "CACHE": "/tmp/home-user/cache",
    }


def test_render_mcp_servers_expands_and_includes_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It expands variables during profile MCP rendering for JSON agents."""
    monkeypatch.setenv("HOME", "/tmp/home-user")

    transport = MCPTransport(
        type="stdio",
        command="$HOME/.local/bin/fs-mcp",
        args=["~/repo"],
    )
    profile = _make_profile()
    mcp_config = _make_mcp_config(transport)

    rendered = render_mcp_servers(
        profile=profile,
        mcp_config=mcp_config,
        include_type=True,
        agent_id="claude-code",
    )

    assert rendered["filesystem"]["command"] == "/tmp/home-user/.local/bin/fs-mcp"
    assert rendered["filesystem"]["args"] == ["/tmp/home-user/repo"]
    assert rendered["filesystem"]["type"] == "stdio"


def test_codex_render_mcp_config_expands_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It applies the same expansion behavior for Codex TOML rendering."""
    monkeypatch.setenv("HOME", "/tmp/home-user")

    transport = MCPTransport(
        type="stdio",
        command="$HOME/bin/fs-mcp",
        args=["~/documents"],
    )
    profile = _make_profile()
    mcp_config = _make_mcp_config(transport)

    rendered = codex.render_mcp_config(profile, mcp_config)

    assert (
        rendered["mcp_servers"]["filesystem"]["command"] == "/tmp/home-user/bin/fs-mcp"
    )
    assert rendered["mcp_servers"]["filesystem"]["args"] == ["/tmp/home-user/documents"]


def test_build_transport_config_expands_http_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It expands variables in URL and header values for HTTP/SSE transports."""
    monkeypatch.setenv("HOME", "/tmp/home-user")

    transport = MCPTransport(
        type="http",
        url="https://example.local/api?path=$HOME",
        headers={"X-Path": "~/secrets/token"},
    )

    rendered = build_transport_config(transport)

    assert rendered["url"] == "https://example.local/api?path=/tmp/home-user"
    assert rendered["headers"] == {"X-Path": "/tmp/home-user/secrets/token"}
