"""Import existing Cursor configuration."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..config import SkillRecord
from ..mcp import MCPConfig, MCPServer, MCPTransport


def import_mcp_servers(source_path: Path, mcp_config: MCPConfig) -> list[str]:
    """Import MCP servers from Cursor's mcp.json."""
    if not source_path.exists():
        return []

    data = json.loads(source_path.read_text())
    mcp_servers = data.get("mcpServers", {})
    imported = []

    for server_name, server_data in mcp_servers.items():
        if server_name in mcp_config.servers:
            continue

        # Detect transport type
        if "url" in server_data:
            # SSE transport
            transport_name = "sse"
            transport = MCPTransport(
                type="sse",
                url=server_data["url"],
                headers=server_data.get("headers", {}),
            )
        elif "command" in server_data:
            # stdio transport
            transport_name = _detect_transport_name(server_data["command"])
            transport = MCPTransport(
                type="stdio",
                command=server_data["command"],
                args=server_data.get("args", []),
                env=server_data.get("env", {}),
            )
        else:
            # Unknown transport type, skip
            continue

        # Create server with transport
        server = MCPServer(
            name=server_name,
            description=f"Imported from Cursor ({transport_name})",
            transports={transport_name: transport},
        )

        mcp_config.servers[server_name] = server
        imported.append(server_name)

    if imported:
        mcp_config.save()

    return imported


def _detect_transport_name(command: str) -> str:
    """Detect transport name from command."""
    if "npx" in command:
        return "npx"
    if "uvx" in command:
        return "uvx"
    return "docker" if "docker" in command or "podman" in command else "custom"


def import_rules(source_file: Path, dest_dir: Path) -> list[str]:
    """Import Cursor rules - creates placeholder file with warning.

    Cursor stores rules in the cloud, so we create a global rules file
    that users can populate manually.
    """
    dest_file = dest_dir / "cursor-global-rules.md"

    if dest_file.exists():
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Create placeholder file with instructions
    dest_file.write_text(
        "# Cursor Global Rules\n\n"
        "**Note:** Cursor stores user rules in the cloud and they can only be "
        "set via Cursor settings.\n\n"
        "This file serves as a source of truth for your Cursor rules. "
        "Add your rules here, and when you sync,\n"
        "they will be displayed in a copy-friendly format for you to paste "
        "into Cursor settings.\n\n"
        "## Your Rules\n\n"
        "Add your rules below:\n\n"
    )

    return ["cursor-global-rules.md"]


def import_skills(source_dir: Path, config) -> list[str]:
    """Import skills from Cursor's ~/.cursor/skills/."""
    if not source_dir.exists():
        return []

    imported = []

    for skill_dir in source_dir.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith("."):
            skill_name = skill_dir.name

            if skill_name in config.skills:
                continue

            # Check if it's a symlink pointing to our central store
            if skill_dir.is_symlink():
                resolved = skill_dir.resolve()
                if resolved.parent == config.skills_dir:
                    continue

            # Import as local skill
            dest_dir = config.skills_dir / skill_name
            if not dest_dir.exists():
                shutil.copytree(skill_dir, dest_dir, symlinks=True)

                record = SkillRecord(
                    name=skill_name,
                    source=str(skill_dir),
                    source_type="local",
                    agents=["cursor"],
                )
                config.add_skill(record)
                imported.append(skill_name)

    return imported


def suggest_profile_config(
    imported_servers: list[str], mcp_config: MCPConfig
) -> dict[str, str]:
    """Suggest profile configuration for imported servers."""
    suggestions = {}
    for server_name in imported_servers:
        server = mcp_config.servers[server_name]
        # Pick the first available transport
        if server.transports:
            transport_name = next(iter(server.transports.keys()))
            suggestions[server_name] = transport_name
    return suggestions
