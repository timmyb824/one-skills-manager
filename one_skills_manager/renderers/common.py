"""Common rendering utilities shared across agent renderers."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ..mcp import MCPConfig, MCPTransport
from ..profiles import Profile


def _expand_path_variables(value: str) -> str:
    """Expand environment variables and home references in a string value.

    Args:
        value: Raw string value that may contain shell-like variables

    Returns:
        Expanded string value
    """
    expanded = os.path.expandvars(value)
    return os.path.expanduser(expanded)


def build_transport_config(transport: MCPTransport) -> dict[str, Any]:
    """Build transport configuration dictionary from MCPTransport.

    Args:
        transport: The MCP transport to convert

    Returns:
        Dictionary with transport configuration
    """
    server_config: dict[str, Any] = {}

    if transport.type == "stdio":
        if transport.command:
            server_config["command"] = _expand_path_variables(transport.command)
        if transport.args:
            server_config["args"] = [
                _expand_path_variables(arg) for arg in transport.args
            ]
        if transport.env:
            server_config["env"] = {
                key: _expand_path_variables(value)
                for key, value in transport.env.items()
            }
    elif transport.type in ("sse", "http"):
        if transport.url:
            server_config["url"] = _expand_path_variables(transport.url)
        if transport.headers:
            server_config["headers"] = {
                key: _expand_path_variables(value)
                for key, value in transport.headers.items()
            }

    return server_config


def render_mcp_servers(
    profile: Profile,
    mcp_config: MCPConfig,
    include_type: bool = False,
    agent_id: str | None = None,
) -> dict[str, Any]:
    """Render MCP servers configuration from profile.

    Args:
        profile: The profile containing server assignments
        mcp_config: The MCP configuration with server definitions
        include_type: Whether to include "type" field (Claude Code needs it)
        agent_id: Agent ID for resolving agent-specific transport overrides

    Returns:
        Dictionary of server configurations
    """
    mcp_servers = {}

    for server_name in profile.mcp_servers.keys():
        # Use agent-specific transport if available, otherwise use default
        if agent_id:
            transport_name = profile.get_transport_for_agent(server_name, agent_id)
        else:
            transport_name = profile.mcp_servers.get(server_name)

        if not transport_name:
            continue

        transport = mcp_config.get_server_transport(server_name, transport_name)
        server_config = build_transport_config(transport)

        if include_type:
            server_config["type"] = transport.type

        mcp_servers[server_name] = server_config

    return mcp_servers


def merge_with_existing(
    new_mcp_config: dict[str, Any],
    existing_path: Path,
    dry_run: bool = False,
) -> tuple[dict[str, Any], str | None]:
    """Merge new MCP config with existing agent config.

    Args:
        new_mcp_config: New MCP servers configuration
        existing_path: Path to existing config file
        dry_run: If True, don't create backup

    Returns:
        Tuple of (merged_config, backup_path)
    """
    if existing_path.exists():
        existing_data = json.loads(existing_path.read_text())
    else:
        existing_data = {}

    merged = existing_data.copy()
    merged["mcpServers"] = new_mcp_config

    backup_path = None
    if existing_path.exists() and not dry_run:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{existing_path}.backup-{timestamp}"
        existing_path.rename(backup_path)

    return merged, backup_path


def write_config(
    config_data: dict[str, Any],
    target_path: Path,
    dry_run: bool = False,
) -> None:
    """Write configuration atomically to file.

    Args:
        config_data: Configuration data to write
        target_path: Path to write to
        dry_run: If True, skip writing
    """
    if dry_run:
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=target_path.parent,
        delete=False,
        suffix=".json",
    ) as tmp:
        json.dump(config_data, tmp, indent=2)
        tmp.write("\n")
        tmp_path = Path(tmp.name)

    tmp_path.rename(target_path)
