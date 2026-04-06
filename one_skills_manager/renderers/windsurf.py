"""Render Windsurf configuration files."""

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
    profile: Profile, mcp_config: MCPConfig, agent_id: str = "windsurf"
) -> dict[str, Any]:
    """Generate mcpServers configuration for Windsurf.

    Windsurf does not require the 'type' field in server configs.
    """
    return render_mcp_servers(
        profile, mcp_config, include_type=False, agent_id=agent_id
    )


# Re-export common functions for backward compatibility
__all__ = ["render_mcp_config", "merge_with_existing", "write_config"]
