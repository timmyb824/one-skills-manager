"""Rules management: install and sync rule files across agents."""

from __future__ import annotations

import shutil
from pathlib import Path

from .agents import get_agent
from .config import Config, RuleRecord


def install_rule(source: str, config: Config, agents: list[str]) -> str:
    """Install a rule from source path. Returns rule name."""
    source_path = Path(source).expanduser().resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"Rule source not found: {source}")

    if not source_path.is_file():
        raise ValueError(f"Rule source must be a file: {source}")

    rule_name = source_path.name
    dest_path = config.rules_dir / rule_name

    if dest_path.exists():
        raise FileExistsError(f"Rule '{rule_name}' already exists")

    config.rules_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)

    record = RuleRecord(
        name=rule_name,
        source=str(source_path),
        agents=agents,
    )
    config.add_rule(record)

    return rule_name


def sync_windsurf_global_rules(config: Config, dry_run: bool = False) -> str:
    """Sync Windsurf's special global_rules.md file. Returns action taken."""
    # Windsurf uses a single global_rules.md file
    source_file = config.rules_dir / "windsurf-global-rules.md"
    agent = get_agent("windsurf")
    target_file = agent.rules_dir / "global_rules.md"

    # Create source file if it doesn't exist
    if not source_file.exists():
        if not dry_run:
            config.rules_dir.mkdir(parents=True, exist_ok=True)
            template = (
                "# Windsurf Global Rules\n\nAdd your Windsurf-specific rules here.\n"
            )
            source_file.write_text(template)
        return "created-template"

    agent.rules_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        if target_file.is_symlink():
            return (
                "up-to-date"
                if target_file.resolve() == source_file.resolve()
                else "would-update"
            )
        else:
            return (
                "error: file exists (not symlink)"
                if target_file.exists()
                else "would-link"
            )

    if target_file.is_symlink():
        if target_file.resolve() == source_file.resolve():
            return "up-to-date"
        target_file.unlink()
        target_file.symlink_to(source_file)
        return "updated"

    if target_file.exists():
        raise FileExistsError(
            f"'{target_file}' already exists and is not a symlink. "
            "Remove it manually first."
        )

    target_file.symlink_to(source_file)
    return "linked"


def sync_rule(
    rule_name: str, agent_id: str, config: Config, dry_run: bool = False
) -> str:
    """Sync a rule to an agent. Returns action taken."""
    # Special handling for Windsurf's global rules file
    if agent_id == "windsurf":
        return sync_windsurf_global_rules(config, dry_run)

    rule_path = config.rules_dir / rule_name
    if not rule_path.exists():
        return "error: rule file missing"

    agent = get_agent(agent_id)
    agent.rules_dir.mkdir(parents=True, exist_ok=True)
    link = agent.rules_dir / rule_name

    if dry_run:
        if link.is_symlink():
            return (
                "up-to-date"
                if link.resolve() == rule_path.resolve()
                else "would-update"
            )
        else:
            return "error: file exists (not symlink)" if link.exists() else "would-link"
    if link.is_symlink():
        if link.resolve() == rule_path.resolve():
            return "up-to-date"
        link.unlink()
        link.symlink_to(rule_path)
        return "updated"

    if link.exists():
        raise FileExistsError(
            f"'{link}' already exists and is not a symlink. Remove it manually first."
        )

    link.symlink_to(rule_path)
    return "linked"


def unsync_rule(rule_name: str, agent_id: str, dry_run: bool = False) -> str:
    """Remove rule symlink from agent. Returns action taken."""
    agent = get_agent(agent_id)
    link = agent.rules_dir / rule_name

    if dry_run:
        return "would-remove" if link.is_symlink() else "not-linked"
    if link.is_symlink():
        link.unlink()
        return "removed"
    return "not-linked"


def remove_rule(rule_name: str, config: Config) -> None:
    """Remove rule from central store."""
    rule_path = config.rules_dir / rule_name
    if rule_path.exists():
        rule_path.unlink()
