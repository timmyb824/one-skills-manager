"""Import existing Codex configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from one_skills_manager.config import Config
    from one_skills_manager.mcp import MCPConfig


def import_mcp_servers(mcp_path: Path, mcp_config: MCPConfig) -> list[str]:
    """Import MCP servers from Codex config.toml.
    
    Args:
        mcp_path: Path to ~/.codex/config.toml
        mcp_config: The MCP configuration to import into
        
    Returns:
        List of imported server names
    """
    if not mcp_path.exists():
        return []
    
    imported = []
    
    with open(mcp_path, "rb") as f:
        data = tomllib.load(f)
    
    mcp_servers = data.get("mcp_servers", {})
    
    for server_name, server_config in mcp_servers.items():
        if server_name in mcp_config.servers:
            continue
        
        # Determine transport type based on config fields
        if "command" in server_config:
            # STDIO transport
            transport_type = "stdio"
            command = server_config.get("command")
            args = server_config.get("args", [])
            env = server_config.get("env", {})
            
            mcp_config.add_server(server_name)
            mcp_config.add_transport(
                server_name,
                "default",
                transport_type,
                command=command,
                args=args,
                env=env or None,
            )
        elif "url" in server_config:
            # HTTP/SSE transport
            transport_type = "sse"
            url = server_config.get("url")
            headers = server_config.get("headers", {})
            
            mcp_config.add_server(server_name)
            mcp_config.add_transport(
                server_name,
                "default",
                transport_type,
                url=url,
                headers=headers or None,
            )
        else:
            continue
        
        imported.append(server_name)
    
    return imported


def import_skills(skills_path: Path, config: Config) -> list[str]:
    """Import skills from Codex skills directory.
    
    Args:
        skills_path: Path to ~/.agents/skills
        config: The config to import into
        
    Returns:
        List of imported skill names
    """
    if not skills_path.exists():
        return []
    
    imported = []
    
    for skill_dir in skills_path.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        
        if skill_dir.name in config.skills:
            continue
        
        from one_skills_manager.config import SkillRecord
        
        record = SkillRecord(
            name=skill_dir.name,
            source=str(skill_dir),
            source_type="local",
            agents=["codex"],
        )
        config.add_skill(record)
        imported.append(skill_dir.name)
    
    return imported


def import_rules(rules_path: Path, config: Config) -> list[str]:
    """Import rules from Codex rules directory.
    
    Args:
        rules_path: Path to ~/.codex/rules
        config: The config to import into
        
    Returns:
        List of imported rule names
    """
    if not rules_path.exists():
        return []
    
    imported = []
    
    for rule_file in rules_path.rglob("*.rules"):
        if not rule_file.is_file():
            continue
        
        rel_path = rule_file.relative_to(rules_path)
        rule_name = str(rel_path)
        
        if rule_name in config.rules:
            continue
        
        # Copy to one-skills rules directory
        dest_file = config.rules_dir / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        dest_file.write_text(rule_file.read_text(encoding="utf-8"), encoding="utf-8")
        
        from one_skills_manager.config import RuleRecord
        
        record = RuleRecord(
            name=rule_name,
            source=str(dest_file),
            agents=["codex"],
        )
        config.add_rule(record)
        imported.append(rule_name)
    
    return imported


def suggest_profile_config(
    imported_skills: list[str],
    imported_servers: list[str],
    imported_rules: list[str],
) -> dict[str, list[str]]:
    """Suggest profile configuration for imported Codex items.
    
    Args:
        imported_skills: List of imported skill names
        imported_servers: List of imported MCP server names
        imported_rules: List of imported rule names
        
    Returns:
        Dictionary with suggested profile config
    """
    return {
        "mcp_servers": imported_servers,
        "agents": ["codex"],
    }
