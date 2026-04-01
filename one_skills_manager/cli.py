"""CLI entry point for one-skills-manager."""

from __future__ import annotations

import sys

import click
from rich.console import Console
from rich.table import Table

from .agents import AGENT_IDS, AGENTS
from .config import Config
from .skills import install, remove
from .sync import sync_all, sync_skill, unsync_skill

console = Console()
err_console = Console(stderr=True)


def _load_config() -> Config:
    return Config.load()


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="one-skills-manager")
def cli() -> None:
    """Manage and sync AI agent skills across Claude Code, Cursor, Windsurf, and Codex."""


# ---------------------------------------------------------------------------
# agents
# ---------------------------------------------------------------------------


@cli.command("agents")
def cmd_agents() -> None:
    """List supported agents and their skill directories."""
    table = Table(title="Supported Agents", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Skills Directory", style="dim")

    for agent in AGENTS.values():
        table.add_row(agent.id, agent.name, str(agent.skills_dir))

    console.print(table)


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


@cli.command("install")
@click.argument("source")
@click.option(
    "--agents",
    "-a",
    default="",
    help="Comma-separated agent IDs to assign (e.g. claude-code,cursor). "
    f"Valid: {', '.join(AGENT_IDS)}",
)
def cmd_install(source: str, agents: str) -> None:
    """Install a skill from a GitHub URL or local path.

    SOURCE can be a GitHub directory URL or a local filesystem path.

    \b
    Examples:
      one-skills install https://github.com/owner/repo/tree/main/my-skill --agents claude-code
      one-skills install ~/my-skills/my-skill --agents claude-code,cursor
    """
    agent_list: list[str] = [a.strip() for a in agents.split(",") if a.strip()]

    # Validate agent IDs up-front
    for aid in agent_list:
        if aid not in AGENT_IDS:
            err_console.print(
                f"[red]Unknown agent '{aid}'. Valid agents: {', '.join(AGENT_IDS)}[/red]"
            )
            sys.exit(1)

    config = _load_config()

    try:
        with console.status(f"Installing from [cyan]{source}[/cyan]..."):
            record = install(source, config, agent_list)
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[red]Install failed:[/red] {exc}")
        sys.exit(1)

    console.print(f"[green]✓[/green] Installed skill [bold]{record.name}[/bold]")

    if agent_list:
        # Auto-sync immediately
        results = sync_skill(record, config)
        for r in results:
            icon = "[green]✓[/green]" if r.action not in ("error",) else "[red]✗[/red]"
            console.print(f"  {icon} synced to [cyan]{r.agent}[/cyan] ({r.action})")
    else:
        console.print(
            "  [dim]No agents assigned yet. Use `one-skills assign` to add some.[/dim]"
        )


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@cli.command("list")
def cmd_list() -> None:
    """List installed skills and their agent assignments."""
    config = _load_config()

    if not config.skills:
        console.print("[dim]No skills installed yet.[/dim]")
        return

    table = Table(title="Installed Skills", show_lines=True)
    table.add_column("Skill", style="bold")
    table.add_column("Source", style="dim")
    table.add_column("Type")
    table.add_column("Agents")

    for rec in config.skills.values():
        agents_str = ", ".join(rec.agents) if rec.agents else "[dim]none[/dim]"
        table.add_row(rec.name, rec.source, rec.source_type, agents_str)

    console.print(table)


# ---------------------------------------------------------------------------
# assign / unassign
# ---------------------------------------------------------------------------


@cli.command("assign")
@click.argument("skill")
@click.argument("agent")
def cmd_assign(skill: str, agent: str) -> None:
    """Assign SKILL to AGENT and sync it immediately.

    \b
    Example:
      one-skills assign my-skill claude-code
    """
    if agent not in AGENT_IDS:
        err_console.print(
            f"[red]Unknown agent '{agent}'. Valid: {', '.join(AGENT_IDS)}[/red]"
        )
        sys.exit(1)

    config = _load_config()

    if skill not in config.skills:
        err_console.print(
            f"[red]Skill '{skill}' not found. Run `one-skills list` to see installed skills.[/red]"
        )
        sys.exit(1)

    config.assign_agent(skill, agent)
    record = config.skills[skill]
    results = sync_skill(record, config, agent_filter=agent)
    for r in results:
        icon = "[green]✓[/green]" if r.action != "error" else "[red]✗[/red]"
        msg = r.detail if r.action == "error" else r.action
        console.print(f"{icon} {skill} → {agent} ({msg})")


@cli.command("unassign")
@click.argument("skill")
@click.argument("agent")
def cmd_unassign(skill: str, agent: str) -> None:
    """Remove SKILL from AGENT and delete the symlink.

    \b
    Example:
      one-skills unassign my-skill cursor
    """
    config = _load_config()

    if skill not in config.skills:
        err_console.print(f"[red]Skill '{skill}' not found.[/red]")
        sys.exit(1)

    config.unassign_agent(skill, agent)
    record = config.skills[skill]
    result = unsync_skill(record, config, agent)
    icon = "[green]✓[/green]" if result.action != "error" else "[red]✗[/red]"
    msg = result.detail if result.action == "error" else result.action
    console.print(f"{icon} {skill} ✗ {agent} ({msg})")


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------


@cli.command("sync")
@click.option("--skill", "-s", default=None, help="Only sync this skill.")
@click.option(
    "--agent",
    "-a",
    default=None,
    help=f"Only sync to this agent. Valid: {', '.join(AGENT_IDS)}",
)
def cmd_sync(skill: str | None, agent: str | None) -> None:
    """Sync skills to their assigned agent directories."""
    if agent and agent not in AGENT_IDS:
        err_console.print(
            f"[red]Unknown agent '{agent}'. Valid: {', '.join(AGENT_IDS)}[/red]"
        )
        sys.exit(1)

    config = _load_config()

    if skill:
        if skill not in config.skills:
            err_console.print(f"[red]Skill '{skill}' not found.[/red]")
            sys.exit(1)
        results = sync_skill(config.skills[skill], config, agent_filter=agent)
    else:
        results = sync_all(config, agent_filter=agent)

    if not results:
        console.print("[dim]Nothing to sync.[/dim]")
        return

    table = Table(show_lines=False, show_header=True)
    table.add_column("Skill", style="bold")
    table.add_column("Agent", style="cyan")
    table.add_column("Result")

    for r in results:
        color = "green" if r.action not in ("error",) else "red"
        detail = f" — {r.detail}" if r.detail else ""
        table.add_row(r.skill, r.agent, f"[{color}]{r.action}{detail}[/{color}]")

    console.print(table)


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


@cli.command("remove")
@click.argument("skill")
@click.confirmation_option(
    prompt="This will delete the skill from the central store. Continue?"
)
def cmd_remove(skill: str) -> None:
    """Remove a skill from the central store and all symlinks."""
    config = _load_config()

    if skill not in config.skills:
        err_console.print(f"[red]Skill '{skill}' not found.[/red]")
        sys.exit(1)

    record = config.skills[skill]

    # Remove all symlinks first
    for agent_id in list(record.agents):
        result = unsync_skill(record, config, agent_id)
        if result.action == "removed":
            console.print(f"  [dim]removed symlink for {agent_id}[/dim]")

    remove(skill, config)
    console.print(f"[green]✓[/green] Removed skill [bold]{skill}[/bold]")
