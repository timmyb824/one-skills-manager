"""Guided interactive flows for skills, rules, MCP servers, profiles, and sync."""

from __future__ import annotations

from datetime import datetime, timezone

import questionary
from rich.console import Console
from rich.table import Table

from ..agents import AGENT_IDS
from ..config import Config
from ..mcp import MCPConfig, MCPTransport
from ..profiles import AgentConfig, ProfileConfig
from ..rules import install_rule, remove_rule, sync_rule, unsync_rule
from ..skills import install, remove
from ..sync import (
    SyncResult,
    sync_all,
    sync_mcp_servers,
    sync_rules_all,
    sync_skill,
    unsync_skill,
)
from ._style import STYLE
from .status import _check_skill_link

console = Console()


# ---------------------------------------------------------------------------
# Guided: Add skill
# ---------------------------------------------------------------------------


def guided_add_skill() -> None:
    """Interactive flow: install a skill and assign it to agents."""
    config = Config.load()

    source = questionary.text(
        "Skill source (GitHub URL or local path):",
        style=STYLE,
    ).ask()
    if not source:
        return

    console.print(f"[dim]Installing from {source}...[/dim]")
    try:
        with console.status("Installing..."):
            record = install(source, config, [])
        console.print(f"[green]✓[/green] Installed skill [bold]{record.name}[/bold]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Install failed:[/red] {exc}")
        return

    selected = questionary.checkbox(
        "Assign to which agents? (space to select)",
        choices=AGENT_IDS,
        style=STYLE,
    ).ask()
    if not selected:
        console.print(
            "[dim]Skill installed without agent assignment. Assign later with:[/dim]"
        )
        console.print(f"  [cyan]one-skills skill assign {record.name} <agent>[/cyan]")
        return

    for agent_id in selected:
        config.assign_agent(record.name, agent_id)

    results = sync_skill(record, config)
    for r in results:
        icon = "[green]✓[/green]" if r.action != "error" else "[red]✗[/red]"
        console.print(f"  {icon} synced to [cyan]{r.agent}[/cyan] ({r.action})")


# ---------------------------------------------------------------------------
# Guided: Add rule
# ---------------------------------------------------------------------------


def guided_add_rule() -> None:
    """Interactive flow: install a rule and assign it to agents."""
    config = Config.load()

    source = questionary.path(
        "Rule file path:",
        style=STYLE,
    ).ask()
    if not source:
        return

    selected = questionary.checkbox(
        "Assign to which agents? (space to select)",
        choices=AGENT_IDS,
        style=STYLE,
    ).ask()
    agent_list: list[str] = selected or []

    try:
        rule_name = install_rule(source, config, agent_list)
        console.print(f"[green]✓[/green] Installed rule [bold]{rule_name}[/bold]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Install failed:[/red] {exc}")
        return

    if agent_list:
        for agent_id in agent_list:
            action = sync_rule(rule_name, agent_id, config)
            console.print(f"  → [cyan]{agent_id}[/cyan]: {action}")
    else:
        console.print(
            "[dim]Rule installed without agent assignment. Assign later with:[/dim]"
        )
        console.print(f"  [cyan]one-skills rule assign {rule_name} <agent>[/cyan]")


# ---------------------------------------------------------------------------
# Guided: Remove skill
# ---------------------------------------------------------------------------


def guided_remove_skill() -> None:
    """Interactive flow: remove an installed skill and unsync from agents."""
    config = Config.load()

    if not config.skills:
        console.print("[yellow]No skills installed.[/yellow]")
        return

    if not (
        skill_name := questionary.select(
            "Select skill to remove:",
            choices=sorted(config.skills.keys()),
            style=STYLE,
        ).ask()
    ):
        return

    record = config.skills[skill_name]
    agents_list = record.agents[:]

    confirmed = questionary.confirm(
        f"Remove skill '{skill_name}' from all agents and central store?",
        default=False,
        style=STYLE,
    ).ask()
    if not confirmed:
        console.print("[dim]Cancelled.[/dim]")
        return

    if agents_list:
        console.print(f"Removing [bold]{skill_name}[/bold] from agents:")
        for agent_id in agents_list:
            result = unsync_skill(record, agent_id, force=True)
            if result.action == "removed":
                console.print(
                    f"  [green]✓[/green] Unsynced from [cyan]{agent_id}[/cyan]"
                )
            else:
                console.print(f"  [yellow]○[/yellow] {agent_id}: {result.action}")

    remove(skill_name, config)
    console.print(
        f"\n[green]✓[/green] Removed skill [bold]{skill_name}[/bold] from central store"
    )


# ---------------------------------------------------------------------------
# Guided: Remove rule
# ---------------------------------------------------------------------------


def guided_remove_rule() -> None:
    """Interactive flow: remove an installed rule and unsync from agents."""
    config = Config.load()

    if not config.rules:
        console.print("[yellow]No rules installed.[/yellow]")
        return

    if not (
        rule_name := questionary.select(
            "Select rule to remove:",
            choices=sorted(config.rules.keys()),
            style=STYLE,
        ).ask()
    ):
        return

    record = config.rules[rule_name]
    agents_list = record.agents[:]

    confirmed = questionary.confirm(
        f"Remove rule '{rule_name}' from all agents and central store?",
        default=False,
        style=STYLE,
    ).ask()
    if not confirmed:
        console.print("[dim]Cancelled.[/dim]")
        return

    if agents_list:
        console.print(f"Removing [bold]{rule_name}[/bold] from agents:")
        for agent_id in agents_list:
            action = unsync_rule(rule_name, agent_id, force=True)
            if action == "removed":
                console.print(
                    f"  [green]✓[/green] Unsynced from [cyan]{agent_id}[/cyan]"
                )
            else:
                console.print(f"  [yellow]○[/yellow] {agent_id}: {action}")

    remove_rule(rule_name, config)
    console.print(
        f"\n[green]✓[/green] Removed rule [bold]{rule_name}[/bold] from central store"
    )


# ---------------------------------------------------------------------------
# Guided: Remove MCP server
# ---------------------------------------------------------------------------


def guided_remove_mcp_server() -> None:
    """Interactive flow: remove an MCP server definition and all its transports."""
    mcp_config = MCPConfig.load()

    if not mcp_config.servers:
        console.print("[yellow]No MCP servers defined.[/yellow]")
        return

    server_name = questionary.select(
        "Select MCP server to remove:",
        choices=sorted(mcp_config.servers.keys()),
        style=STYLE,
    ).ask()
    if not server_name:
        return

    confirmed = questionary.confirm(
        f"Remove MCP server '{server_name}' and all its transports?",
        default=False,
        style=STYLE,
    ).ask()
    if not confirmed:
        console.print("[dim]Cancelled.[/dim]")
        return

    try:
        mcp_config.remove_server(server_name)
        console.print(f"[green]✓[/green] Removed MCP server [bold]{server_name}[/bold]")
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")


# ---------------------------------------------------------------------------
# Guided: Add MCP server
# ---------------------------------------------------------------------------


def guided_add_mcp_server_with_name(initial_name: str) -> None:
    """Invoke the MCP server wizard with a pre-filled server name.

    Args:
        initial_name: Server name provided on the command line
    """
    guided_add_mcp_server(initial_name=initial_name)


def guided_add_mcp_server(initial_name: str | None = None) -> None:
    """Interactive flow: add an MCP server with transport and optional profile assignment.

    Args:
        initial_name: Optional server name to pre-fill (skips the name prompt)
    """
    mcp_config = MCPConfig.load()
    profiles = ProfileConfig.load()

    # ── Basic info ────────────────────────────────────────────────────────
    if initial_name:
        name = initial_name
        console.print(f"[bold]Adding MCP server:[/bold] {name}")
    else:
        name = questionary.text("Server name:", style=STYLE).ask()
        if not name:
            return

    if name in mcp_config.servers:
        console.print(f"[red]Server '{name}' already exists.[/red]")
        return

    description = questionary.text(
        "Description:",
        default=f"{name} MCP server",
        style=STYLE,
    ).ask()
    if description is None:
        return

    transport_name = questionary.text(
        "Transport name (used when assigning to profiles):",
        default="default",
        style=STYLE,
    ).ask()
    if not transport_name:
        return

    # ── Transport type ────────────────────────────────────────────────────
    transport_type = questionary.select(
        "Transport type:",
        choices=[
            questionary.Choice(
                "stdio  — local process (npx, uvx, or custom command)", "stdio"
            ),
            questionary.Choice("sse    — Server-Sent Events (remote URL)", "sse"),
            questionary.Choice("http   — HTTP stream (remote URL)", "http"),
        ],
        style=STYLE,
    ).ask()
    if not transport_type:
        return

    transport: MCPTransport | None = None

    if transport_type == "stdio":
        pkg_mgr = questionary.select(
            "Package manager / launcher:",
            choices=["npx", "uvx", "command"],
            style=STYLE,
        ).ask()
        if not pkg_mgr:
            return

        if pkg_mgr in ("npx", "uvx"):
            pkg = questionary.text(f"Package name for {pkg_mgr}:", style=STYLE).ask()
            if not pkg:
                return
            extra_args_str = questionary.text(
                "Extra arguments (space-separated, leave blank for none):",
                default="",
                style=STYLE,
            ).ask()
            extra_args = (
                extra_args_str.split()
                if extra_args_str and extra_args_str.strip()
                else []
            )
            if pkg_mgr == "npx":
                transport = MCPTransport(
                    type="stdio", command="npx", args=["-y", pkg, *extra_args]
                )
            else:
                transport = MCPTransport(
                    type="stdio", command="uvx", args=[pkg, *extra_args]
                )
        else:
            cmd = questionary.text("Command:", style=STYLE).ask()
            if not cmd:
                return
            args_str = questionary.text(
                "Arguments (space-separated, leave blank for none):",
                default="",
                style=STYLE,
            ).ask()
            args = args_str.split() if args_str and args_str.strip() else []
            transport = MCPTransport(type="stdio", command=cmd, args=args)

    elif url := questionary.text(f"URL for {transport_type}:", style=STYLE).ask():
        transport = MCPTransport(type=transport_type, url=url)

    else:
        return
    # ── Optional env vars ─────────────────────────────────────────────────
    if questionary.confirm(
        "Add environment variables?", default=False, style=STYLE
    ).ask():
        env: dict[str, str] = {}
        while True:
            key = questionary.text("Key (blank to finish):", style=STYLE).ask()
            if not key:
                break
            value = questionary.text(f"Value for {key}:", style=STYLE).ask()
            if value is None:
                break
            env[key] = value
        if env:
            transport.env = env

    # ── Create ────────────────────────────────────────────────────────────
    mcp_config.add_server(name, description)
    mcp_config.add_transport(name, transport_name, transport)
    console.print(
        f"\n[green]✓[/green] Created MCP server [bold]{name}[/bold] "
        f"with {transport_name} ({transport_type}) transport"
    )

    # ── Optional: add to profile ──────────────────────────────────────────
    if profiles.active_profile and profiles.get_active_profile():
        if questionary.confirm(
            f"Add to active profile '{profiles.active_profile}'?",
            default=True,
            style=STYLE,
        ).ask():
            try:
                profiles.add_server_to_profile(
                    profiles.active_profile, name, transport_name
                )
                console.print(
                    f"[green]✓[/green] Added to profile [bold]{profiles.active_profile}[/bold]"
                )
            except ValueError as exc:
                console.print(f"[red]Error adding to profile:[/red] {exc}")
    else:
        console.print(
            f"[dim]Add to a profile later with:[/dim] "
            f"[cyan]one-skills profile add-server {name} {transport_name}[/cyan]"
        )


# ---------------------------------------------------------------------------
# Guided: Manage profile
# ---------------------------------------------------------------------------


def guided_manage_profile() -> None:
    """Interactive flow: manage profile agents and MCP server assignments."""
    profiles = ProfileConfig.load()
    mcp_config = MCPConfig.load()

    if not profiles.profiles:
        console.print("[yellow]No profiles yet.[/yellow]")
        name = questionary.text("Create a new profile named:", style=STYLE).ask()
        if not name:
            return
        profiles.create_profile(name)
        console.print(f"[green]✓[/green] Created profile [bold]{name}[/bold]")

    profile_choices = []
    for pname in profiles.profiles:
        marker = " (active)" if pname == profiles.active_profile else ""
        profile_choices.append(questionary.Choice(f"{pname}{marker}", pname))

    selected_profile = questionary.select(
        "Select profile:",
        choices=profile_choices,
        style=STYLE,
    ).ask()
    if not selected_profile:
        return

    profile = profiles.profiles[selected_profile]

    while True:
        agents_str = ", ".join(profile.agents.keys()) if profile.agents else "none"
        servers_str = (
            ", ".join(profile.mcp_servers.keys()) if profile.mcp_servers else "none"
        )
        console.print(
            f"\n[bold]{selected_profile}[/bold]"
            f"  │  agents: [cyan]{agents_str}[/cyan]"
            f"  │  servers: [cyan]{servers_str}[/cyan]"
        )

        action = questionary.select(
            "Action:",
            choices=[
                questionary.Choice("Add agent", "add_agent"),
                questionary.Choice("Remove agent", "rm_agent"),
                questionary.Choice("Add MCP server", "add_server"),
                questionary.Choice("Remove MCP server", "rm_server"),
                questionary.Choice("Set as active profile", "activate"),
                questionary.Separator(),
                questionary.Choice("Done", "done"),
            ],
            style=STYLE,
        ).ask()

        if not action or action == "done":
            break

        if action == "add_agent":
            available = [a for a in AGENT_IDS if a not in profile.agents]
            if not available:
                console.print("[dim]All agents already in profile.[/dim]")
                continue
            if selected := questionary.checkbox(
                "Select agents to add:",
                choices=available,
                style=STYLE,
            ).ask():
                for aid in selected:
                    profiles.add_agent_to_profile(
                        selected_profile, aid, AgentConfig(enabled=True)
                    )
                console.print(f"[green]✓[/green] Added: {', '.join(selected)}")

        elif action == "rm_agent":
            if not profile.agents:
                console.print("[dim]No agents in profile.[/dim]")
                continue
            if selected := questionary.checkbox(
                "Select agents to remove:",
                choices=list(profile.agents.keys()),
                style=STYLE,
            ).ask():
                for aid in selected:
                    profile.agents.pop(aid, None)
                profiles.save()
                console.print(f"[green]✓[/green] Removed: {', '.join(selected)}")

        elif action == "add_server":
            available = [s for s in mcp_config.servers if s not in profile.mcp_servers]
            if not available:
                console.print("[dim]All defined servers already in profile.[/dim]")
                continue
            server_name = questionary.select(
                "Select server to add:",
                choices=available,
                style=STYLE,
            ).ask()
            if not server_name:
                continue
            transports = list(mcp_config.servers[server_name].transports.keys())
            if not transports:
                console.print(
                    f"[yellow]No transports defined for '{server_name}'.[/yellow]"
                )
                continue
            if transport_choice := questionary.select(
                f"Transport for {server_name}:",
                choices=transports,
                style=STYLE,
            ).ask():
                profiles.add_server_to_profile(
                    selected_profile, server_name, transport_choice
                )
                console.print(
                    f"[green]✓[/green] Added {server_name} ({transport_choice})"
                )

        elif action == "rm_server":
            if not profile.mcp_servers:
                console.print("[dim]No servers in profile.[/dim]")
                continue
            if selected := questionary.checkbox(
                "Select servers to remove:",
                choices=list(profile.mcp_servers.keys()),
                style=STYLE,
            ).ask():
                for srv in selected:
                    profiles.remove_server_from_profile(selected_profile, srv)
                console.print(f"[green]✓[/green] Removed: {', '.join(selected)}")

        elif action == "activate":
            profiles.set_active_profile(selected_profile)
            console.print(
                f"[green]✓[/green] Activated profile [bold]{selected_profile}[/bold]"
            )


# ---------------------------------------------------------------------------
# Guided: Sync
# ---------------------------------------------------------------------------


def _dry_run_skills(config: Config, agent_id: str) -> list[SyncResult]:
    """Simulate skills sync for dry-run display without touching the filesystem.

    Args:
        config: Loaded Config instance
        agent_id: Agent ID to simulate sync for

    Returns:
        List of SyncResult with would-* actions
    """
    action_map = {
        "linked": "up-to-date",
        "missing": "would-link",
        "broken": "would-update",
        "conflict": "would-skip (conflict)",
        "unknown": "would-skip (unknown agent)",
    }
    results = []
    for rec in config.skills.values():
        if agent_id not in rec.agents:
            continue
        state = _check_skill_link(rec.name, agent_id, config.skills_dir)
        results.append(
            SyncResult(
                skill=rec.name, agent=agent_id, action=action_map.get(state, state)
            )
        )
    return results


def guided_sync() -> None:
    """Interactive flow: run sync with guided scope, agent, and dry-run options."""
    profiles = ProfileConfig.load()
    config = Config.load()
    mcp_config = MCPConfig.load()

    profile = profiles.get_active_profile()
    if not profile:
        console.print("[yellow]No active profile. Create one first.[/yellow]")
        return

    profile_agents = [aid for aid, cfg in profile.agents.items() if cfg.enabled]
    if not profile_agents:
        console.print("[yellow]No agents in active profile.[/yellow]")
        return

    console.print(
        f"[bold]Profile:[/bold] [cyan]{profiles.active_profile}[/cyan]  │  "
        f"Agents: [cyan]{', '.join(profile_agents)}[/cyan]"
    )

    scope = questionary.select(
        "What to sync?",
        choices=[
            questionary.Choice("Everything (skills + rules + MCP)", "all"),
            questionary.Choice("Skills only", "skills"),
            questionary.Choice("Rules only", "rules"),
            questionary.Choice("MCP servers only", "mcp"),
        ],
        style=STYLE,
    ).ask()
    if not scope:
        return

    agent_scope = questionary.select(
        "Which agents?",
        choices=[
            questionary.Choice(
                f"All agents in profile ({', '.join(profile_agents)})", "all"
            ),
            questionary.Choice("Specific agent...", "specific"),
        ],
        style=STYLE,
    ).ask()
    if not agent_scope:
        return

    if agent_scope == "specific":
        agent_filter = questionary.select(
            "Select agent:",
            choices=profile_agents,
            style=STYLE,
        ).ask()
        if not agent_filter:
            return
        agents_to_sync = [agent_filter]
    else:
        agents_to_sync = profile_agents

    dry_run = questionary.confirm("Dry-run first?", default=False, style=STYLE).ask()

    console.print()
    if dry_run:
        console.print("[yellow]Dry-run mode (no changes will be made)[/yellow]")

    all_results: list[SyncResult] = []

    for agent_id in agents_to_sync:
        if scope in ("all", "skills"):
            # Use dry-run simulation for skills so no symlinks are created/modified
            if dry_run:
                all_results.extend(_dry_run_skills(config, agent_id))
            else:
                all_results.extend(sync_all(config, agent_filter=agent_id))
        if scope in ("all", "rules"):
            all_results.extend(sync_rules_all(config, agent_id, dry_run))
        if scope in ("all", "mcp"):
            all_results.append(
                sync_mcp_servers(profiles, mcp_config, agent_id, dry_run)
            )

    if not all_results:
        console.print("[dim]Nothing to sync.[/dim]")
        return

    table = Table(show_lines=False, show_header=True)
    table.add_column("Item", style="bold")
    table.add_column("Agent", style="cyan")
    table.add_column("Result")

    for r in all_results:
        color = (
            "green"
            if r.action not in ("error", "skipped")
            else ("red" if r.action == "error" else "dim")
        )
        detail = f" — {r.detail}" if r.detail else ""
        table.add_row(r.skill, r.agent, f"[{color}]{r.action}{detail}[/{color}]")

    console.print(table)

    if not dry_run and profile:
        timestamp = datetime.now(timezone.utc).isoformat()
        for agent_id in agents_to_sync:
            profile.last_synced[agent_id] = timestamp
        profiles.save()
