"""Import existing Claude Code configurations."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..config import SkillRecord
from ..mcp import MCPConfig, MCPServer, MCPTransport


def import_mcp_servers(source_path: Path, mcp_config: MCPConfig) -> list[str]:
    """Import MCP servers from Claude Code's ~/.claude.json."""
    if not source_path.exists():
        return []

    data = json.loads(source_path.read_text())
    mcp_servers = data.get("mcpServers", {})

    imported = []
    for server_name, server_config in mcp_servers.items():
        if server_name in mcp_config.servers:
            continue

        server_type = server_config.get("type", "stdio")
        description = f"Imported from Claude Code ({server_type})"

        server = MCPServer(name=server_name, description=description)

        if server_type == "stdio":
            transport = MCPTransport(
                type="stdio",
                command=server_config.get("command"),
                args=server_config.get("args", []),
                env=server_config.get("env", {}),
            )
            transport_name = _detect_transport_name(server_config.get("command", ""))
            server.transports[transport_name] = transport
        elif server_type in ("sse", "http"):
            transport = MCPTransport(
                type=server_type,
                url=server_config.get("url"),
                headers=server_config.get("headers", {}),
            )
            server.transports[server_type] = transport

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


def import_rules(source_dir: Path, dest_dir: Path) -> list[str]:
    """Import rules from Claude Code's ~/.claude/rules/."""
    if not source_dir.exists():
        return []

    dest_dir.mkdir(parents=True, exist_ok=True)
    imported = []

    for rule_file in source_dir.rglob("*.md"):
        if rule_file.is_file():
            rel_path = rule_file.relative_to(source_dir)
            dest_file = dest_dir / rel_path

            if not dest_file.exists():
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(rule_file, dest_file)
                imported.append(str(rel_path))

    return imported


def import_skills(source_dir: Path, config) -> list[str]:
    """Import skills from Claude Code's ~/.claude/skills/."""

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
                    agents=["claude-code"],
                )
                config.add_skill(record)
                imported.append(skill_name)

    return imported


def suggest_profile_config(
    imported_servers: list[str], mcp_config: MCPConfig
) -> dict[str, str]:
    """Suggest profile MCP server configuration based on imported servers."""
    suggestions = {}
    for server_name in imported_servers:
        if server_name in mcp_config.servers:
            server = mcp_config.servers[server_name]
            if server.transports:
                transport_name = next(iter(server.transports.keys()))
                suggestions[server_name] = transport_name
    return suggestions
