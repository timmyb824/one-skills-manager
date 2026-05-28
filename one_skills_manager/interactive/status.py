"""Sync status display helpers for one-skills-manager."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ..agents import get_agent
from ..config import Config
from ..mcp import MCPConfig
from ..profiles import ProfileConfig

console = Console()


def _check_skill_link(skill_name: str, agent_id: str, skills_dir: Path) -> str:
    """Check symlink state for a skill on a given agent.

    Args:
        skill_name: Name of the skill directory
        agent_id: Agent ID to check
        skills_dir: Central skills directory

    Returns:
        One of: 'linked', 'broken', 'missing', 'conflict', 'unknown'
    """
    try:
        agent = get_agent(agent_id)
    except ValueError:
        return "unknown"

    link = agent.skills_dir / skill_name
    source = skills_dir / skill_name

    if link.is_symlink():
        return (
            "linked"
            if source.exists() and link.resolve() == source.resolve()
            else "broken"
        )
    return "conflict" if link.exists() else "missing"


def _check_rule_link(rule_name: str, agent_id: str, rules_dir: Path) -> str:
    """Check symlink state for a rule on a given agent.

    Args:
        rule_name: Name of the rule file
        agent_id: Agent ID to check
        rules_dir: Central rules directory

    Returns:
        One of: 'linked', 'broken', 'missing', 'conflict', 'cloud', 'unknown'
    """
    if agent_id == "cursor":
        return "cloud"

    try:
        agent = get_agent(agent_id)
    except ValueError:
        return "unknown"

    if agent_id == "windsurf":
        source = rules_dir / "windsurf-global-rules.md"
        link = agent.rules_dir / "global_rules.md"
    else:
        source = rules_dir / rule_name
        link = agent.rules_dir / rule_name

    if link.is_symlink():
        return (
            "linked"
            if source.exists() and link.resolve() == source.resolve()
            else "broken"
        )
    return "conflict" if link.exists() else "missing"


def _status_icon(state: str) -> str:
    """Return a colored Rich markup icon for a sync state.

    Args:
        state: Sync state string

    Returns:
        Rich markup string with icon
    """
    mapping = {
        "linked": "[green]✓[/green]",
        "missing": "[yellow]○[/yellow]",
        "broken": "[red]✗[/red]",
        "conflict": "[red]![/red]",
        "cloud": "[blue]☁[/blue]",
        "unknown": "[dim]?[/dim]",
    }
    return mapping.get(state, "[dim]?[/dim]")


def _relative_time(iso_ts: str) -> str:
    """Convert an ISO timestamp to a human-readable relative time.

    Args:
        iso_ts: ISO 8601 timestamp string

    Returns:
        Human-readable relative time string like '2h ago'
    """
    try:
        dt = datetime.fromisoformat(iso_ts)
        delta = datetime.now(timezone.utc) - dt
        if delta.days > 0:
            return f"{delta.days}d ago"
        if delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h ago"
        return f"{delta.seconds // 60}m ago" if delta.seconds >= 60 else "just now"
    except Exception:  # noqa: BLE001
        return "unknown"


def _print_profile_header(profiles: ProfileConfig) -> None:
    """Print the active profile summary line.

    Args:
        profiles: Loaded ProfileConfig instance
    """
    profile = profiles.get_active_profile()
    profile_name = profiles.active_profile
    if profile_name and profile:
        agent_list = (
            ", ".join(
                f"[cyan]{a}[/cyan]" for a, cfg in profile.agents.items() if cfg.enabled
            )
            or "[dim]none[/dim]"
        )
        last_syncs = [_relative_time(ts) for ts in profile.last_synced.values() if ts]
        sync_info = last_syncs[0] if last_syncs else "[yellow]never[/yellow]"
        console.print(
            f"[bold]Active profile:[/bold] [bold cyan]{profile_name}[/bold cyan]  "
            f"│  Agents: {agent_list}  │  Last synced: {sync_info}"
        )
    else:
        console.print(
            "[yellow]No active profile set. Run:[/yellow]"
            " [cyan]one-skills profile create <name>[/cyan]"
        )
    console.print()


def _fill_resource_table(
    table: Table,
    records: dict,
    check_fn: Callable[[str, str, Path], str],
    is_synced: Callable[[str], bool],
    resources_dir: Path,
) -> bool:
    """Populate a Rich Table with per-agent sync state rows.

    Args:
        table: Table to populate in-place
        records: Mapping of resource name to record (skills or rules)
        check_fn: Function returning sync state for a given resource/agent/dir
        is_synced: Predicate returning True when a state counts as in-sync
        resources_dir: Central directory for the resource type

    Returns:
        True if every record is in sync, False otherwise.
    """
    all_in_sync = True
    for rec in records.values():
        if not rec.agents:
            table.add_row(rec.name, "[dim]not assigned[/dim]")
            all_in_sync = False
            continue
        parts = []
        for aid in rec.agents:
            state = check_fn(rec.name, aid, resources_dir)
            if not is_synced(state):
                all_in_sync = False
            parts.append(f"{_status_icon(state)} {aid}")
        table.add_row(rec.name, "  ".join(parts))
    return all_in_sync


def _print_skills_section(config: Config) -> bool:
    """Print the skills status table.

    Args:
        config: Loaded Config instance

    Returns:
        True if all skills are in sync, False otherwise.
    """
    if config.skills:
        table = Table(
            title="Skills", show_lines=False, show_header=True, header_style="bold"
        )
        table.add_column("Name", style="bold", min_width=20)
        table.add_column("Agents / Status")
        in_sync = _fill_resource_table(
            table,
            config.skills,
            _check_skill_link,
            lambda s: s == "linked",
            config.skills_dir,
        )
        console.print(table)
    else:
        console.print(
            "[dim]No skills installed.[/dim]  [cyan]one-skills skill install <url>[/cyan]"
        )
        in_sync = True
    console.print()
    return in_sync


def _print_rules_section(config: Config) -> bool:
    """Print the rules status table.

    Args:
        config: Loaded Config instance

    Returns:
        True if all rules are in sync, False otherwise.
    """
    if config.rules:
        table = Table(
            title="Rules", show_lines=False, show_header=True, header_style="bold"
        )
        table.add_column("Name", style="bold", min_width=20)
        table.add_column("Agents / Status")
        in_sync = _fill_resource_table(
            table,
            config.rules,
            _check_rule_link,
            lambda s: s in ("linked", "cloud"),
            config.rules_dir,
        )
        console.print(table)
    else:
        console.print(
            "[dim]No rules installed.[/dim]  [cyan]one-skills rule install <file>[/cyan]"
        )
        in_sync = True
    console.print()
    return in_sync


def _mcp_profile_cell(server_name: str, profile: object) -> str:
    """Return the profile assignment cell text for an MCP server row.

    Args:
        server_name: Name of the MCP server
        profile: Active Profile instance, or None

    Returns:
        Rich markup string for the profile cell
    """
    if profile and server_name in profile.mcp_servers:
        return f"[green]✓[/green] {profile.mcp_servers[server_name]}"
    return "[dim]—[/dim]"


def _print_mcp_section(mcp_config: MCPConfig, profiles: ProfileConfig) -> None:
    """Print the MCP servers status table.

    Args:
        mcp_config: Loaded MCPConfig instance
        profiles: Loaded ProfileConfig instance
    """
    profile = profiles.get_active_profile()
    profile_name = profiles.active_profile
    if mcp_config.servers:
        title = f"MCP Servers{f'  (profile: {profile_name})' if profile_name else ''}"
        table = Table(
            title=title, show_lines=False, show_header=True, header_style="bold"
        )
        table.add_column("Server", style="bold cyan", min_width=20)
        table.add_column("Profile", min_width=12)
        table.add_column("Transports", style="dim")
        for server in mcp_config.servers.values():
            transports = ", ".join(server.transports.keys()) or "[dim]none[/dim]"
            table.add_row(
                server.name, _mcp_profile_cell(server.name, profile), transports
            )
        console.print(table)
    else:
        console.print(
            "[dim]No MCP servers defined.[/dim]"
            "  [cyan]one-skills mcp add-server <name>[/cyan]"
        )
    console.print()


def show_status() -> bool:
    """Display current sync status of all resources.

    Returns:
        True if everything is in sync, False if any item is out of sync.
    """
    config = Config.load()
    profiles = ProfileConfig.load()
    mcp_config = MCPConfig.load()

    _print_profile_header(profiles)
    skills_ok = _print_skills_section(config)
    rules_ok = _print_rules_section(config)
    _print_mcp_section(mcp_config, profiles)

    console.print(
        "[green]✓[/green] synced  "
        "[yellow]○[/yellow] not linked  "
        "[red]✗[/red] broken  "
        "[blue]☁[/blue] cloud (cursor)  "
        "[red]![/red] conflict"
    )

    all_in_sync = skills_ok and rules_ok
    if all_in_sync:
        console.print("\n[green]Everything is up to date.[/green]")
    else:
        console.print(
            "\n[yellow]Some items are out of sync. Run:[/yellow]"
            " [cyan]one-skills sync[/cyan]"
        )
    return all_in_sync
