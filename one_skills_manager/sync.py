"""Sync logic: create/update symlinks from central store to agent skill directories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agents import get_agent
from .config import Config, SkillRecord
from .dryrun import DryRunCollector
from .mcp import MCPConfig
from .profiles import ProfileConfig
from .renderers import claude_code, windsurf
from .rules import sync_rule as sync_rule_impl


@dataclass
class SyncResult:
    """Result of syncing a skill to an agent."""

    skill: str
    agent: str
    action: str  # "linked" | "updated" | "up-to-date" | "error"
    detail: str = ""


def _link_skill(skill_dir: Path, target_dir: Path) -> str:
    """Symlink skill_dir into target_dir. Returns action taken."""
    target_dir.mkdir(parents=True, exist_ok=True)
    link = target_dir / skill_dir.name

    if link.is_symlink():
        if link.resolve() == skill_dir.resolve():
            return "up-to-date"
        link.unlink()
        link.symlink_to(skill_dir)
        return "updated"

    if link.exists():
        # Real directory/file already there — don't clobber it
        raise FileExistsError(
            f"'{link}' already exists and is not a symlink. Remove it manually first."
        )

    link.symlink_to(skill_dir)
    return "linked"


def sync_skill(
    record: SkillRecord, config: Config, agent_filter: str | None = None
) -> list[SyncResult]:
    """Sync one skill to all its assigned agents (or a specific one)."""
    skill_dir = config.skills_dir / record.name
    if not skill_dir.exists():
        return [
            SyncResult(
                skill=record.name,
                agent="—",
                action="error",
                detail="skill directory missing",
            )
        ]

    results: list[SyncResult] = []
    # If agent_filter is set, only sync if skill is assigned to that agent
    if agent_filter:
        agents_to_sync = [agent_filter] if agent_filter in record.agents else []
    else:
        agents_to_sync = record.agents

    for agent_id in agents_to_sync:
        try:
            agent = get_agent(agent_id)
        except ValueError as exc:
            results.append(
                SyncResult(
                    skill=record.name, agent=agent_id, action="error", detail=str(exc)
                )
            )
            continue

        try:
            action = _link_skill(skill_dir, agent.skills_dir)
            results.append(SyncResult(skill=record.name, agent=agent_id, action=action))
        except Exception as exc:  # noqa: BLE001
            results.append(
                SyncResult(
                    skill=record.name, agent=agent_id, action="error", detail=str(exc)
                )
            )

    return results


def sync_all(config: Config, agent_filter: str | None = None) -> list[SyncResult]:
    """Sync every registered skill."""
    results: list[SyncResult] = []
    for record in config.skills.values():
        results.extend(sync_skill(record, config, agent_filter))
    return results


def unsync_skill(record: SkillRecord, agent_id: str) -> SyncResult:
    """Remove the symlink for a specific agent."""
    try:
        agent = get_agent(agent_id)
    except ValueError as exc:
        return SyncResult(
            skill=record.name, agent=agent_id, action="error", detail=str(exc)
        )

    link = agent.skills_dir / record.name
    if link.is_symlink():
        link.unlink()
        return SyncResult(skill=record.name, agent=agent_id, action="removed")
    return SyncResult(
        skill=record.name,
        agent=agent_id,
        action="not-linked",
        detail="no symlink found",
    )


def sync_rules_all(
    config: Config,
    agent_filter: str | None = None,
    dry_run: bool = False,
    collector: DryRunCollector | None = None,
) -> list[SyncResult]:
    """Sync all rules to their assigned agents."""
    results: list[SyncResult] = []

    for rule_record in config.rules.values():
        # If agent_filter is set, only sync if rule is assigned to that agent
        if agent_filter:
            agents_to_sync = (
                [agent_filter] if agent_filter in rule_record.agents else []
            )
        else:
            agents_to_sync = rule_record.agents

        for agent_id in agents_to_sync:
            try:
                agent = get_agent(agent_id)
                action = sync_rule_impl(rule_record.name, agent_id, config, dry_run)

                if dry_run and collector:
                    rule_path = config.rules_dir / rule_record.name
                    target_path = agent.rules_dir / rule_record.name
                    if "would-link" in action:
                        collector.add_symlink(
                            str(rule_path), str(target_path), "create"
                        )
                    elif "would-update" in action:
                        collector.add_symlink(
                            str(rule_path), str(target_path), "update"
                        )

                results.append(
                    SyncResult(skill=rule_record.name, agent=agent_id, action=action)
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    SyncResult(
                        skill=rule_record.name,
                        agent=agent_id,
                        action="error",
                        detail=str(exc),
                    )
                )

    return results


def sync_mcp_servers(
    profile_config: ProfileConfig,
    mcp_config: MCPConfig,
    agent_id: str,
    dry_run: bool = False,
    collector: DryRunCollector | None = None,
) -> SyncResult:
    """Sync MCP servers for a specific agent based on active profile."""
    profile = profile_config.get_active_profile()
    if not profile:
        return SyncResult(
            skill="mcp-servers",
            agent=agent_id,
            action="error",
            detail="No active profile",
        )

    if agent_id not in profile.agents or not profile.agents[agent_id].enabled:
        return SyncResult(
            skill="mcp-servers",
            agent=agent_id,
            action="skipped",
            detail="Agent not enabled in profile",
        )

    try:
        agent = get_agent(agent_id)

        if errors := mcp_config.validate_profile_servers(profile.mcp_servers):
            return SyncResult(
                skill="mcp-servers",
                agent=agent_id,
                action="error",
                detail="; ".join(errors),
            )

        # Select renderer based on agent type
        if agent_id == "windsurf":
            renderer = windsurf
        else:
            # Default to claude_code renderer (works for claude-code, cursor, codex)
            renderer = claude_code

        # Render MCP config with agent-specific transport resolution
        mcp_servers_config = renderer.render_mcp_config(
            profile, mcp_config, agent_id=agent_id
        )

        # Merge with existing config
        merged_config, backup_path = renderer.merge_with_existing(
            mcp_servers_config, agent.mcp_config_path, dry_run
        )

        if dry_run and collector:
            if backup_path:
                collector.add_backup(str(agent.mcp_config_path), backup_path)

            server_list = ", ".join(profile.mcp_servers.keys())
            collector.add_file_modification(
                str(agent.mcp_config_path),
                f"Add/update {len(profile.mcp_servers)} MCP servers: {server_list}",
            )

        # Write config
        renderer.write_config(merged_config, agent.mcp_config_path, dry_run)

        action = "would-update" if dry_run else "updated"
        detail = f"{len(profile.mcp_servers)} servers configured"

        return SyncResult(
            skill="mcp-servers", agent=agent_id, action=action, detail=detail
        )

    except Exception as exc:  # noqa: BLE001
        return SyncResult(
            skill="mcp-servers",
            agent=agent_id,
            action="error",
            detail=str(exc),
        )
