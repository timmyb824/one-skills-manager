"""Codex MCP renderer - outputs to TOML format."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from one_skills_manager.mcp import MCPConfig
    from one_skills_manager.profiles import Profile


def render_mcp_config(profile: Profile, mcp_config: MCPConfig) -> dict[str, Any]:
    """Render MCP config for Codex in TOML format.

    Codex supports:
    - STDIO servers: command + args + env
    - HTTP/SSE servers: url + headers (bearer token, OAuth)

    Format: [mcp_servers.<name>]
            command = "..."  # for stdio
            args = [...]
            env = {...}
            url = "..."      # for http/sse
            headers = {...}

    Args:
        profile: The profile containing MCP server assignments
        mcp_config: The MCP configuration

    Returns:
        Dictionary suitable for TOML serialization
    """
    mcp_servers = {}

    for server_name, transport_name in profile.mcp_servers.items():
        # Skip if excluded for codex
        if profile.is_server_excluded(server_name, "codex"):
            continue

        # Get transport (with agent-specific override if exists)
        transport_name_for_agent = profile.get_transport_for_agent(server_name, "codex")
        if not transport_name_for_agent:
            continue

        transport = mcp_config.get_server_transport(
            server_name, transport_name_for_agent
        )

        server_config: dict[str, Any] = {}

        if transport.type == "stdio":
            # STDIO server
            if transport.command:
                server_config["command"] = transport.command
            if transport.args:
                server_config["args"] = transport.args
            if transport.env:
                server_config["env"] = transport.env
        elif transport.type in ("sse", "http"):
            # HTTP/SSE server
            if transport.url:
                server_config["url"] = transport.url
            if transport.headers:
                server_config["headers"] = transport.headers

        if server_config:
            mcp_servers[server_name] = server_config

    return {"mcp_servers": mcp_servers}


def write_mcp_config(
    profile: Profile, mcp_config: MCPConfig, config_path: Path, dry_run: bool = False
) -> str:
    """Write Codex MCP configuration to config.toml.

    Args:
        profile: The profile containing MCP server assignments
        mcp_config: The MCP configuration
        config_path: Path to ~/.codex/config.toml
        dry_run: If True, don't actually write the file

    Returns:
        Action description string
    """
    import tomli_w

    rendered = render_mcp_config(profile, mcp_config)
    mcp_servers = rendered.get("mcp_servers", {})

    # Read existing config if it exists
    existing_config = {}
    if config_path.exists():
        import tomllib

        with open(config_path, "rb") as f:
            existing_config = tomllib.load(f)

    # Merge: keep non-mcp_servers sections, replace mcp_servers
    merged_config = {k: v for k, v in existing_config.items() if k != "mcp_servers"}
    if mcp_servers:
        merged_config["mcp_servers"] = mcp_servers

    if not dry_run:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "wb") as f:
            tomli_w.dump(merged_config, f)

    server_count = len(mcp_servers)
    return f"updated — {server_count} servers configured"
