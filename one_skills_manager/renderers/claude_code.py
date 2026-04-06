"""Render Claude Code configuration files."""

from __future__ import annotations

from typing import Any

from ..mcp import MCPConfig
from ..profiles import Profile
from .common import (
    merge_with_existing,
    render_mcp_servers,
    write_config,
)


def render_mcp_config(
    profile: Profile, mcp_config: MCPConfig, agent_id: str = "claude-code"
) -> dict[str, Any]:
    """Generate mcpServers configuration for Claude Code.

    Claude Code requires the 'type' field in server configs.
    """
    return render_mcp_servers(profile, mcp_config, include_type=True, agent_id=agent_id)


# Re-export common functions for backward compatibility
__all__ = ["render_mcp_config", "merge_with_existing", "write_config"]
