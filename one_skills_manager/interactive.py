"""Interactive guided mode for one-skills-manager using questionary."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .agents import AGENT_IDS, get_agent
from .config import Config
from .mcp import MCPConfig, MCPTransport
from .profiles import AgentConfig, ProfileConfig
from .rules import install_rule, sync_rule
from .skills import install
from .sync import sync_all, sync_mcp_servers, sync_rules_all, sync_skill

console = Console()

_STYLE = questionary.Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:green"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:green"),
        ("separator", "fg:cyan"),
        ("instruction", "fg:gray"),
    ]
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_interactive() -> None:
    """Run the main interactive guided menu loop.

    Presents a menu of common workflows and routes to the appropriate
    guided flow. Returns when the user selects Exit or presses Ctrl-C.
    """
    console.print()
    console.print(
        Panel(
            "[bold cyan]one-skills-manager[/bold cyan]  interactive mode\n"
            "[dim]Use arrow keys to navigate, Enter to select, Ctrl-C to quit[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print()

    while True:
        try:
            action = questionary.select(
                "What would you like to do?",
                choices=[
                    questionary.Choice(
                        "  Status — see what's installed and synced", "status"
                    ),
                    questionary.Choice("  Add skill", "add_skill"),
                    questionary.Choice("  Add rule", "add_rule"),
                    questionary.Choice("  Add MCP server", "add_mcp"),
                    questionary.Choice("  Manage profile", "profile"),
                    questionary.Choice("  Sync", "sync"),
                    questionary.Separator(),
                    questionary.Choice("  Exit", "exit"),
                ],
                style=_STYLE,
            ).ask()
        except KeyboardInterrupt:
            action = None

        if action is None or action == "exit":
            console.print("[dim]Goodbye.[/dim]")
            break

        console.print()

        try:
            if action == "status":
                _show_status()
            elif action == "add_skill":
                _guided_add_skill()
            elif action == "add_rule":
                _guided_add_rule()
            elif action == "add_mcp":
                _guided_add_mcp_server()
            elif action == "profile":
                _guided_manage_profile()
            elif action == "sync":
                _guided_sync()
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled.[/dim]")

        console.print()


# ---------------------------------------------------------------------------
# Status display (shared with cli status command)
# ---------------------------------------------------------------------------


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
    if link.exists():
        return "conflict"
    return "missing"


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
    if link.exists():
        return "conflict"
    return "missing"


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
        if delta.seconds >= 60:
            return f"{delta.seconds // 60}m ago"
        return "just now"
    except Exception:  # noqa: BLE001
        return "unknown"


def _show_status() -> bool:
    """Display current sync status of all resources.

    Returns:
        True if everything is in sync, False if any item is out of sync.
    """
    config = Config.load()
    profiles = ProfileConfig.load()
    mcp_config = MCPConfig.load()

    profile = profiles.get_active_profile()
    profile_name = profiles.active_profile

    all_in_sync = True

    # ── Profile header ──────────────────────────────────────────────────────
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
            "[yellow]No active profile set. Run:[/yellow] [cyan]one-skills profile create <name>[/cyan]"
        )
    console.print()

    # ── Skills ──────────────────────────────────────────────────────────────
    if config.skills:
        skill_table = Table(
            title="Skills", show_lines=False, show_header=True, header_style="bold"
        )
        skill_table.add_column("Name", style="bold", min_width=20)
        skill_table.add_column("Agents / Status")

        unsynced_skills = 0
        for rec in config.skills.values():
            if not rec.agents:
                skill_table.add_row(rec.name, "[dim]not assigned[/dim]")
                all_in_sync = False
                unsynced_skills += 1
                continue

            parts = []
            for aid in rec.agents:
                state = _check_skill_link(rec.name, aid, config.skills_dir)
                if state != "linked":
                    all_in_sync = False
                    unsynced_skills += 1
                parts.append(f"{_status_icon(state)} {aid}")

            skill_table.add_row(rec.name, "  ".join(parts))

        console.print(skill_table)
        console.print()
    else:
        console.print(
            "[dim]No skills installed.[/dim]  [cyan]one-skills skill install <url>[/cyan]"
        )
        console.print()

    # ── Rules ───────────────────────────────────────────────────────────────
    if config.rules:
        rule_table = Table(
            title="Rules", show_lines=False, show_header=True, header_style="bold"
        )
        rule_table.add_column("Name", style="bold", min_width=20)
        rule_table.add_column("Agents / Status")

        for rec in config.rules.values():
            if not rec.agents:
                rule_table.add_row(rec.name, "[dim]not assigned[/dim]")
                all_in_sync = False
                continue

            parts = []
            for aid in rec.agents:
                state = _check_rule_link(rec.name, aid, config.rules_dir)
                if state not in ("linked", "cloud"):
                    all_in_sync = False
                parts.append(f"{_status_icon(state)} {aid}")

            rule_table.add_row(rec.name, "  ".join(parts))

        console.print(rule_table)
        console.print()
    else:
        console.print(
            "[dim]No rules installed.[/dim]  [cyan]one-skills rule install <file>[/cyan]"
        )
        console.print()

    # ── MCP Servers ─────────────────────────────────────────────────────────
    if mcp_config.servers:
        mcp_table = Table(
            title=f"MCP Servers{f'  (profile: {profile_name})' if profile_name else ''}",
            show_lines=False,
            show_header=True,
            header_style="bold",
        )
        mcp_table.add_column("Server", style="bold cyan", min_width=20)
        mcp_table.add_column("Profile", min_width=12)
        mcp_table.add_column("Transports", style="dim")

        for server in mcp_config.servers.values():
            in_profile = profile and server.name in profile.mcp_servers
            profile_cell = (
                f"[green]✓[/green] {profile.mcp_servers[server.name]}"
                if in_profile
                else "[dim]—[/dim]"
            )
            transports = ", ".join(server.transports.keys()) or "[dim]none[/dim]"
            mcp_table.add_row(server.name, profile_cell, transports)

        console.print(mcp_table)
        console.print()
    else:
        console.print(
            "[dim]No MCP servers defined.[/dim]  [cyan]one-skills mcp add-server <name>[/cyan]"
        )
        console.print()

    # ── Legend ───────────────────────────────────────────────────────────────
    console.print(
        "[green]✓[/green] synced  "
        "[yellow]○[/yellow] not linked  "
        "[red]✗[/red] broken  "
        "[blue]☁[/blue] cloud (cursor)  "
        "[red]![/red] conflict"
    )

    if all_in_sync:
        console.print("\n[green]Everything is up to date.[/green]")
    else:
        console.print(
            "\n[yellow]Some items are out of sync. Run:[/yellow] [cyan]one-skills sync[/cyan]"
        )

    return all_in_sync


# ---------------------------------------------------------------------------
# Guided: Add skill
# ---------------------------------------------------------------------------


def _guided_add_skill() -> None:
    """Interactive flow: install a skill and assign it to agents."""
    config = Config.load()

    source = questionary.text(
        "Skill source (GitHub URL or local path):",
        style=_STYLE,
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
        style=_STYLE,
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


def _guided_add_rule() -> None:
    """Interactive flow: install a rule and assign it to agents."""
    config = Config.load()

    source = questionary.path(
        "Rule file path:",
        style=_STYLE,
    ).ask()
    if not source:
        return

    selected = questionary.checkbox(
        "Assign to which agents? (space to select)",
        choices=AGENT_IDS,
        style=_STYLE,
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
# Guided: Add MCP server
# ---------------------------------------------------------------------------


def _guided_add_mcp_server_with_name(initial_name: str) -> None:
    """Invoke the MCP server wizard with a pre-filled server name.

    Args:
        initial_name: Server name provided on the command line
    """
    _guided_add_mcp_server(initial_name=initial_name)


def _guided_add_mcp_server(initial_name: str | None = None) -> None:
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
        name = questionary.text("Server name:", style=_STYLE).ask()
        if not name:
            return

    if name in mcp_config.servers:
        console.print(f"[red]Server '{name}' already exists.[/red]")
        return

    description = questionary.text(
        "Description:",
        default=f"{name} MCP server",
        style=_STYLE,
    ).ask()
    if description is None:
        return

    transport_name = questionary.text(
        "Transport name (used when assigning to profiles):",
        default="default",
        style=_STYLE,
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
        style=_STYLE,
    ).ask()
    if not transport_type:
        return

    transport: MCPTransport | None = None

    if transport_type == "stdio":
        pkg_mgr = questionary.select(
            "Package manager / launcher:",
            choices=["npx", "uvx", "command"],
            style=_STYLE,
        ).ask()
        if not pkg_mgr:
            return

        if pkg_mgr in ("npx", "uvx"):
            pkg = questionary.text(f"Package name for {pkg_mgr}:", style=_STYLE).ask()
            if not pkg:
                return
            extra_args_str = questionary.text(
                "Extra arguments (space-separated, leave blank for none):",
                default="",
                style=_STYLE,
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
            cmd = questionary.text("Command:", style=_STYLE).ask()
            if not cmd:
                return
            args_str = questionary.text(
                "Arguments (space-separated, leave blank for none):",
                default="",
                style=_STYLE,
            ).ask()
            args = args_str.split() if args_str and args_str.strip() else []
            transport = MCPTransport(type="stdio", command=cmd, args=args)

    else:
        url = questionary.text(f"URL for {transport_type}:", style=_STYLE).ask()
        if not url:
            return
        transport = MCPTransport(type=transport_type, url=url)

    # ── Optional env vars ─────────────────────────────────────────────────
    if questionary.confirm(
        "Add environment variables?", default=False, style=_STYLE
    ).ask():
        env: dict[str, str] = {}
        while True:
            key = questionary.text("Key (blank to finish):", style=_STYLE).ask()
            if not key:
                break
            value = questionary.text(f"Value for {key}:", style=_STYLE).ask()
            if value is None:
                break
            env[key] = value
        if env:
            transport.env = env

    # ── Create ────────────────────────────────────────────────────────────
    mcp_config.add_server(name, description)
    mcp_config.add_transport(name, transport_name, transport)
    console.print(
        f"\n[green]✓[/green] Created MCP server [bold]{name}[/bold] with {transport_name} ({transport_type}) transport"
    )

    # ── Optional: add to profile ──────────────────────────────────────────
    if profiles.active_profile and profiles.get_active_profile():
        if questionary.confirm(
            f"Add to active profile '{profiles.active_profile}'?",
            default=True,
            style=_STYLE,
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


def _guided_manage_profile() -> None:
    """Interactive flow: manage profile agents and MCP server assignments."""
    profiles = ProfileConfig.load()
    mcp_config = MCPConfig.load()

    if not profiles.profiles:
        console.print("[yellow]No profiles yet.[/yellow]")
        name = questionary.text("Create a new profile named:", style=_STYLE).ask()
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
        style=_STYLE,
    ).ask()
    if not selected_profile:
        return

    profile = profiles.profiles[selected_profile]

    while True:
        # Build a summary to show state
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
            style=_STYLE,
        ).ask()

        if not action or action == "done":
            break

        if action == "add_agent":
            available = [a for a in AGENT_IDS if a not in profile.agents]
            if not available:
                console.print("[dim]All agents already in profile.[/dim]")
                continue
            selected = questionary.checkbox(
                "Select agents to add:",
                choices=available,
                style=_STYLE,
            ).ask()
            if selected:
                for aid in selected:
                    profiles.add_agent_to_profile(
                        selected_profile, aid, AgentConfig(enabled=True)
                    )
                console.print(f"[green]✓[/green] Added: {', '.join(selected)}")

        elif action == "rm_agent":
            if not profile.agents:
                console.print("[dim]No agents in profile.[/dim]")
                continue
            selected = questionary.checkbox(
                "Select agents to remove:",
                choices=list(profile.agents.keys()),
                style=_STYLE,
            ).ask()
            if selected:
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
                style=_STYLE,
            ).ask()
            if not server_name:
                continue
            transports = list(mcp_config.servers[server_name].transports.keys())
            if not transports:
                console.print(
                    f"[yellow]No transports defined for '{server_name}'.[/yellow]"
                )
                continue
            transport_choice = questionary.select(
                f"Transport for {server_name}:",
                choices=transports,
                style=_STYLE,
            ).ask()
            if transport_choice:
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
            selected = questionary.checkbox(
                "Select servers to remove:",
                choices=list(profile.mcp_servers.keys()),
                style=_STYLE,
            ).ask()
            if selected:
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


def _guided_sync() -> None:
    """Interactive flow: run sync with guided options."""
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
        style=_STYLE,
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
        style=_STYLE,
    ).ask()
    if not agent_scope:
        return

    if agent_scope == "specific":
        agent_filter = questionary.select(
            "Select agent:",
            choices=profile_agents,
            style=_STYLE,
        ).ask()
        if not agent_filter:
            return
        agents_to_sync = [agent_filter]
    else:
        agents_to_sync = profile_agents

    dry_run = questionary.confirm("Dry-run first?", default=False, style=_STYLE).ask()

    console.print()
    if dry_run:
        console.print("[yellow]Dry-run mode (no changes will be made)[/yellow]")

    all_results = []

    for agent_id in agents_to_sync:
        if scope in ("all", "skills"):
            results = sync_all(config, agent_filter=agent_id)
            all_results.extend(results)
        if scope in ("all", "rules"):
            results = sync_rules_all(config, agent_id, dry_run)
            all_results.extend(results)
        if scope in ("all", "mcp"):
            result = sync_mcp_servers(profiles, mcp_config, agent_id, dry_run)
            all_results.append(result)

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
