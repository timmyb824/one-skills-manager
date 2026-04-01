"""Sync logic: create/update symlinks from central store to agent skill directories."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .agents import get_agent
from .config import Config, SkillRecord


@dataclass
class SyncResult:
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
    agents_to_sync = [agent_filter] if agent_filter else record.agents

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


def unsync_skill(record: SkillRecord, config: Config, agent_id: str) -> SyncResult:
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
