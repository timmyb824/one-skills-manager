"""CLI entry point for one-skills-manager with profiles, MCP, and rules support."""

from __future__ import annotations

import sys
import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .agents import AGENT_IDS, AGENTS
from .config import Config, RuleRecord
from .dryrun import DryRunCollector, render_detailed, render_summary
from .mcp import MCPConfig, MCPTransport
from .profiles import AgentConfig, ProfileConfig
from .rules import install_rule, remove_rule, sync_rule, unsync_rule
from .skills import install, remove
from .sync import sync_all, sync_mcp_servers, sync_rules_all, sync_skill, unsync_skill

console = Console()
err_console = Console(stderr=True)


def _load_config() -> Config:
    return Config.load()


def _load_profiles() -> ProfileConfig:
    return ProfileConfig.load()


def _load_mcp() -> MCPConfig:
    return MCPConfig.load()


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(package_name="one-skills-manager")
def cli() -> None:
    """Manage and sync AI agent configurations across Claude Code, Cursor, Windsurf, and Codex."""


# ---------------------------------------------------------------------------
# agents
# ---------------------------------------------------------------------------


@cli.command("agents")
def cmd_agents() -> None:
    """List supported agents and their directories."""
    table = Table(title="Supported Agents", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Skills Dir", style="dim")
    table.add_column("Rules Dir", style="dim")

    for agent in AGENTS.values():
        table.add_row(
            agent.id,
            agent.name,
            str(agent.skills_dir),
            str(agent.rules_dir),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# profile commands
# ---------------------------------------------------------------------------


@cli.group("profile")
def profile_group() -> None:
    """Manage machine profiles."""


@profile_group.command("list")
def profile_list() -> None:
    """List all profiles."""
    profiles = _load_profiles()

    if not profiles.profiles:
        console.print("[dim]No profiles configured yet.[/dim]")
        return

    table = Table(title="Profiles", show_lines=True)
    table.add_column("Name", style="bold")
    table.add_column("Active", style="green")
    table.add_column("MCP Servers")
    table.add_column("Agents")

    for name, profile in profiles.profiles.items():
        is_active = "✓" if name == profiles.active_profile else ""
        servers = f"{len(profile.mcp_servers)} servers"
        agents = ", ".join(profile.agents.keys()) if profile.agents else "none"

        table.add_row(name, is_active, servers, agents)

    console.print(table)


@profile_group.command("create")
@click.argument("name")
def profile_create(name: str) -> None:
    """Create a new profile."""
    profiles = _load_profiles()

    try:
        profiles.create_profile(name)
        console.print(f"[green]✓[/green] Created profile [bold]{name}[/bold]")
        if profiles.active_profile == name:
            console.print("  [dim]Set as active profile[/dim]")
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@profile_group.command("activate")
@click.argument("name")
def profile_activate(name: str) -> None:
    """Set the active profile."""
    profiles = _load_profiles()

    try:
        profiles.set_active_profile(name)
        console.print(f"[green]✓[/green] Activated profile [bold]{name}[/bold]")
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@profile_group.command("delete")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to delete this profile?")
def profile_delete(name: str) -> None:
    """Delete a profile."""
    profiles = _load_profiles()

    try:
        profiles.delete_profile(name)
        console.print(f"[green]✓[/green] Deleted profile [bold]{name}[/bold]")
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@profile_group.command("add-server")
@click.argument("server")
@click.argument("transport")
@click.option("--profile", default=None, help="Profile name (defaults to active)")
def profile_add_server(server: str, transport: str, profile: str | None) -> None:
    """Add an MCP server to a profile."""
    profiles = _load_profiles()
    mcp_config = _load_mcp()

    profile_name = profile or profiles.active_profile
    if not profile_name:
        err_console.print("[red]No active profile. Create one first.[/red]")
        sys.exit(1)

    # Validate server and transport exist
    if server not in mcp_config.servers:
        err_console.print(
            f"[red]Server '{server}' not defined. Use 'one-skills mcp add' first.[/red]"
        )
        sys.exit(1)

    if transport not in mcp_config.servers[server].transports:
        available = ", ".join(mcp_config.servers[server].transports.keys())
        err_console.print(
            f"[red]Transport '{transport}' not available for '{server}'. "
            f"Available: {available}[/red]"
        )
        sys.exit(1)

    try:
        profiles.add_server_to_profile(profile_name, server, transport)
        console.print(
            f"[green]✓[/green] Added {server} ({transport}) to profile {profile_name}"
        )
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@profile_group.command("remove-server")
@click.argument("server")
@click.option("--profile", default=None, help="Profile name (defaults to active)")
def profile_remove_server(server: str, profile: str | None) -> None:
    """Remove an MCP server from a profile."""
    profiles = _load_profiles()

    profile_name = profile or profiles.active_profile
    if not profile_name:
        err_console.print("[red]No active profile.[/red]")
        sys.exit(1)

    try:
        profiles.remove_server_from_profile(profile_name, server)
        console.print(f"[green]✓[/green] Removed {server} from profile {profile_name}")
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@profile_group.command("show")
@click.argument("name", required=False)
def profile_show(name: str | None) -> None:
    """Show profile details."""
    profiles = _load_profiles()

    profile_name = name or profiles.active_profile
    if not profile_name:
        err_console.print("[red]No active profile.[/red]")
        sys.exit(1)

    if profile_name not in profiles.profiles:
        err_console.print(f"[red]Profile '{profile_name}' not found.[/red]")
        sys.exit(1)

    profile = profiles.profiles[profile_name]

    console.print(f"\n[bold]Profile: {profile_name}[/bold]")
    if profile_name == profiles.active_profile:
        console.print("[green]  (active)[/green]")

    console.print(f"\n[bold]MCP Servers ({len(profile.mcp_servers)}):[/bold]")
    if profile.mcp_servers:
        for server, transport in profile.mcp_servers.items():
            console.print(f"  • {server} → {transport}")
    else:
        console.print("  [dim]None configured[/dim]")

    console.print("\n[bold]Agents:[/bold]")
    if profile.agents:
        for agent_id, agent_cfg in profile.agents.items():
            status = "enabled" if agent_cfg.enabled else "disabled"
            console.print(f"  • {agent_id}: {status} (scope: {agent_cfg.mcp_scope})")
    else:
        console.print("  [dim]None configured[/dim]")

    if profile.agent_overrides:
        console.print("\n[bold]Agent-Specific Transport Overrides:[/bold]")
        for agent_id, overrides in profile.agent_overrides.items():
            console.print(f"  [cyan]{agent_id}:[/cyan]")
            for server, transport in overrides.items():
                console.print(f"    • {server} → {transport}")


@profile_group.command("set-override")
@click.argument("agent")
@click.argument("server")
@click.argument("transport")
@click.option("--profile", default=None, help="Profile name (defaults to active)")
def profile_set_override(
    agent: str, server: str, transport: str, profile: str | None
) -> None:
    """Set agent-specific transport override for a server.

    Use this when an agent needs a different transport than the default.
    Example: windsurf might need 'npx' while claude-code uses 'sse'.
    """
    profiles = _load_profiles()
    profile_name = profile or profiles.active_profile

    if not profile_name:
        err_console.print("[red]No active profile.[/red]")
        sys.exit(1)

    if agent not in AGENT_IDS:
        err_console.print(f"[red]Unknown agent '{agent}'.[/red]")
        sys.exit(1)

    try:
        profiles.set_agent_override(profile_name, agent, server, transport)
        console.print(
            f"[green]✓[/green] Set override for {agent}: {server} → {transport}"
        )
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@profile_group.command("remove-override")
@click.argument("agent")
@click.argument("server")
@click.option("--profile", default=None, help="Profile name (defaults to active)")
def profile_remove_override(agent: str, server: str, profile: str | None) -> None:
    """Remove agent-specific transport override."""
    profiles = _load_profiles()
    profile_name = profile or profiles.active_profile

    if not profile_name:
        err_console.print("[red]No active profile.[/red]")
        sys.exit(1)

    try:
        profiles.remove_agent_override(profile_name, agent, server)
        console.print(f"[green]✓[/green] Removed override for {agent}: {server}")
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# mcp commands
# ---------------------------------------------------------------------------


@cli.group("mcp")
def mcp_group() -> None:
    """Manage MCP server definitions."""


@mcp_group.command("list")
def mcp_list() -> None:
    """List all MCP servers."""
    mcp_config = _load_mcp()

    if not mcp_config.servers:
        console.print("[dim]No MCP servers defined yet.[/dim]")
        return

    table = Table(title="MCP Servers", show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Description")
    table.add_column("Transports")

    for server in mcp_config.servers.values():
        transports = ", ".join(server.transports.keys())
        table.add_row(server.name, server.description, transports)

    console.print(table)


@mcp_group.command("add")
@click.argument("name")
@click.option("--description", "-d", required=True, help="Server description")
def mcp_add(name: str, description: str) -> None:
    """Create a new MCP server definition."""
    mcp_config = _load_mcp()

    try:
        mcp_config.add_server(name, description)
        console.print(f"[green]✓[/green] Created MCP server [bold]{name}[/bold]")
        console.print("  [dim]Add transports with 'one-skills mcp add-transport'[/dim]")
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@mcp_group.command("add-transport")
@click.argument("server")
@click.argument("transport_name")
@click.option("--npx", help="NPX package name")
@click.option("--uvx", help="UVX package name")
@click.option("--sse", help="SSE URL")
@click.option("--http", help="HTTP URL")
@click.option("--args", multiple=True, help="Command arguments")
@click.option("--env", multiple=True, help="Environment variables (KEY=VALUE)")
@click.option("--header", multiple=True, help="HTTP headers (KEY=VALUE)")
def mcp_add_transport(
    server: str,
    transport_name: str,
    npx: str | None,
    uvx: str | None,
    sse: str | None,
    http: str | None,
    args: tuple[str, ...],
    env: tuple[str, ...],
    header: tuple[str, ...],
) -> None:
    """Add a transport to an MCP server."""
    mcp_config = _load_mcp()

    if server not in mcp_config.servers:
        err_console.print(
            f"[red]Server '{server}' not found. Create it first with 'mcp add'.[/red]"
        )
        sys.exit(1)

    # Determine transport type
    transport: MCPTransport | None = None

    if npx:
        transport = MCPTransport(
            type="stdio",
            command="npx",
            args=["-y", npx, *args],
        )
    elif uvx:
        transport = MCPTransport(
            type="stdio",
            command="uvx",
            args=[uvx, *args],
        )
    elif sse:
        transport = MCPTransport(
            type="sse",
            url=sse,
        )
    elif http:
        transport = MCPTransport(
            type="http",
            url=http,
        )
    else:
        err_console.print("[red]Must specify one of: --npx, --uvx, --sse, --http[/red]")
        sys.exit(1)

    # Add env vars
    if env:
        env_dict = {}
        for e in env:
            if "=" not in e:
                err_console.print(f"[red]Invalid env format: {e}. Use KEY=VALUE[/red]")
                sys.exit(1)
            key, value = e.split("=", 1)
            env_dict[key] = value
        transport.env = env_dict

    # Add headers
    if header:
        header_dict = {}
        for h in header:
            if "=" not in h:
                err_console.print(
                    f"[red]Invalid header format: {h}. Use KEY=VALUE[/red]"
                )
                sys.exit(1)
            key, value = h.split("=", 1)
            header_dict[key] = value
        transport.headers = header_dict

    try:
        mcp_config.add_transport(server, transport_name, transport)
        console.print(f"[green]✓[/green] Added {transport_name} transport to {server}")
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@mcp_group.command("remove")
@click.argument("name")
@click.confirmation_option(prompt="Remove this MCP server and all its transports?")
def mcp_remove(name: str) -> None:
    """Remove an MCP server definition."""
    mcp_config = _load_mcp()

    try:
        mcp_config.remove_server(name)
        console.print(f"[green]✓[/green] Removed MCP server [bold]{name}[/bold]")
    except ValueError as exc:
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@mcp_group.command("show")
@click.argument("name")
def mcp_show(name: str) -> None:
    """Show MCP server details."""
    mcp_config = _load_mcp()

    if name not in mcp_config.servers:
        err_console.print(f"[red]Server '{name}' not found.[/red]")
        sys.exit(1)

    server = mcp_config.servers[name]

    console.print(f"\n[bold]{server.name}[/bold]")
    console.print(f"  {server.description}\n")

    if server.transports:
        console.print("[bold]Transports:[/bold]")
        for tname, transport in server.transports.items():
            console.print(f"\n  [cyan]{tname}[/cyan] ({transport.type})")
            if transport.command:
                console.print(f"    Command: {transport.command}")
            if transport.args:
                console.print(f"    Args: {' '.join(transport.args)}")
            if transport.url:
                console.print(f"    URL: {transport.url}")
            if transport.env:
                console.print("    Env:")
                for k, v in transport.env.items():
                    console.print(f"      {k}={v}")
            if transport.headers:
                console.print("    Headers:")
                for k, v in transport.headers.items():
                    console.print(f"      {k}={v}")
    else:
        console.print("[dim]No transports configured[/dim]")


# ---------------------------------------------------------------------------
# rule commands
# ---------------------------------------------------------------------------


@cli.group("rule")
def rule_group() -> None:
    """Manage rules."""


@rule_group.command("install")
@click.argument("source")
@click.option(
    "--agents",
    "-a",
    default="",
    help=f"Comma-separated agent IDs. Valid: {', '.join(AGENT_IDS)}",
)
def rule_install(source: str, agents: str) -> None:
    """Install a rule file."""
    agent_list: list[str] = [a.strip() for a in agents.split(",") if a.strip()]

    for aid in agent_list:
        if aid not in AGENT_IDS:
            err_console.print(f"[red]Unknown agent '{aid}'.[/red]")
            sys.exit(1)

    config = _load_config()

    try:
        rule_name = install_rule(source, config, agent_list)
        console.print(f"[green]✓[/green] Installed rule [bold]{rule_name}[/bold]")

        if agent_list:
            for agent_id in agent_list:
                action = sync_rule(rule_name, agent_id, config)
                console.print(f"  → {agent_id}: {action}")
    except Exception as exc:  # noqa: BLE001
        err_console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


@rule_group.command("list")
def rule_list() -> None:
    """List installed rules."""
    config = _load_config()

    if not config.rules:
        console.print("[dim]No rules installed yet.[/dim]")
        return

    table = Table(title="Installed Rules", show_lines=True)
    table.add_column("Rule", style="bold")
    table.add_column("Source", style="dim")
    table.add_column("Agents")

    for rec in config.rules.values():
        agents_str = ", ".join(rec.agents) if rec.agents else "[dim]none[/dim]"
        table.add_row(rec.name, rec.source, agents_str)

    console.print(table)


@rule_group.command("assign")
@click.argument("rule")
@click.argument("agent")
def rule_assign(rule: str, agent: str) -> None:
    """Assign a rule to an agent."""
    if agent not in AGENT_IDS:
        err_console.print(f"[red]Unknown agent '{agent}'.[/red]")
        sys.exit(1)

    config = _load_config()

    if rule not in config.rules:
        err_console.print(f"[red]Rule '{rule}' not found.[/red]")
        sys.exit(1)

    config.assign_rule_to_agent(rule, agent)
    action = sync_rule(rule, agent, config)
    console.print(f"[green]✓[/green] {rule} → {agent} ({action})")


@rule_group.command("unassign")
@click.argument("rule")
@click.argument("agent")
def rule_unassign(rule: str, agent: str) -> None:
    """Unassign a rule from an agent."""
    config = _load_config()

    if rule not in config.rules:
        err_console.print(f"[red]Rule '{rule}' not found.[/red]")
        sys.exit(1)

    config.unassign_rule_from_agent(rule, agent)
    action = unsync_rule(rule, agent)
    console.print(f"[green]✓[/green] {rule} ✗ {agent} ({action})")


@rule_group.command("register")
@click.argument("rule_name")
@click.option(
    "--agents",
    "-a",
    default="",
    help=f"Comma-separated agent IDs. Valid: {', '.join(AGENT_IDS)}",
)
def rule_register(rule_name: str, agents: str) -> None:
    """Register an existing rule file that's already in the rules directory."""
    config = _load_config()

    rule_path = config.rules_dir / rule_name
    if not rule_path.exists():
        err_console.print(f"[red]Rule file not found: {rule_path}[/red]")
        sys.exit(1)

    if rule_name in config.rules:
        err_console.print(f"[red]Rule '{rule_name}' is already registered.[/red]")
        sys.exit(1)

    agent_list: list[str] = [a.strip() for a in agents.split(",") if a.strip()]

    for aid in agent_list:
        if aid not in AGENT_IDS:
            err_console.print(f"[red]Unknown agent '{aid}'.[/red]")
            sys.exit(1)

    record = RuleRecord(
        name=rule_name,
        source=str(rule_path),
        agents=agent_list,
    )
    config.add_rule(record)
    console.print(f"[green]✓[/green] Registered rule [bold]{rule_name}[/bold]")

    if agent_list:
        for agent_id in agent_list:
            action = sync_rule(rule_name, agent_id, config)
            console.print(f"  → {agent_id}: {action}")


@rule_group.command("remove")
@click.argument("rule")
@click.confirmation_option(prompt="Remove this rule from the central store?")
def rule_remove(rule: str) -> None:
    """Remove a rule."""
    config = _load_config()

    if rule not in config.rules:
        err_console.print(f"[red]Rule '{rule}' not found.[/red]")
        sys.exit(1)

    record = config.rules[rule]
    if agents_to_unsync := list(record.agents):
        console.print(f"Removing rule [bold]{rule}[/bold] from agents:")
        for agent_id in agents_to_unsync:
            action = unsync_rule(rule, agent_id)
            if action == "removed":
                console.print(
                    f"  [green]✓[/green] Unsynced from [cyan]{agent_id}[/cyan]"
                )
            else:
                console.print(f"  [yellow]○[/yellow] {agent_id}: {action}")

    remove_rule(rule, config)
    config.remove_rule(rule)
    console.print(
        f"\n[green]✓[/green] Removed rule [bold]{rule}[/bold] from central store"
    )


# ---------------------------------------------------------------------------
# import command
# ---------------------------------------------------------------------------


@cli.command("import")
@click.argument("source", type=click.Choice(["claude-code", "windsurf"]))
@click.option("--dry-run", is_flag=True, help="Preview what would be imported")
def cmd_import(source: str, dry_run: bool) -> None:
    """Import existing configuration from an AI agent."""
    mcp_config = _load_mcp()
    config = _load_config()
    profiles = _load_profiles()

    # Set paths based on source
    if source == "claude-code":
        from .importers.claude_code import (
            import_mcp_servers as import_mcp,
            import_rules as import_rules_fn,
            import_skills as import_skills_fn,
            suggest_profile_config,
        )

        mcp_path = Path("~/.claude.json").expanduser()
        rules_path = Path("~/.claude/rules").expanduser()
        skills_path = Path("~/.claude/skills").expanduser()
        agent_id = "claude-code"
    else:
        from .importers.windsurf import (
            import_mcp_servers as import_mcp,
            import_rules as import_rules_fn,
            import_skills as import_skills_fn,
            suggest_profile_config,
        )

        mcp_path = Path("~/.codeium/windsurf/mcp_config.json").expanduser()
        rules_path = Path("~/.codeium/windsurf/memories/global_rules.md").expanduser()
        skills_path = Path("~/.codeium/windsurf/skills").expanduser()
        agent_id = "windsurf"

    # Preview mode - just scan without importing
    if dry_run:
        console.print("[yellow]Dry-run mode:[/yellow] Scanning for importable items\n")

        # Scan skills
        preview_skills = []
        existing_skills = []
        if skills_path.exists():
            for skill_dir in skills_path.iterdir():
                if skill_dir.is_dir() and not skill_dir.name.startswith("."):
                    if skill_dir.name in config.skills:
                        existing_skills.append(skill_dir.name)
                    else:
                        preview_skills.append(skill_dir.name)

        # Scan MCP servers
        preview_servers = []
        existing_servers = []
        if mcp_path.exists():

            data = json.loads(mcp_path.read_text(encoding="utf-8"))
            mcp_servers = data.get("mcpServers", {})
            for server_name, _ in mcp_servers.items():
                if server_name in mcp_config.servers:
                    existing_servers.append(server_name)
                else:
                    preview_servers.append(server_name)

        # Scan rules
        preview_rules = []
        existing_rules = []
        # Scan rules (handle both directory and single file)
        if rules_path.exists():
            if rules_path.is_file():
                # Windsurf: single global_rules.md file
                rule_name = "windsurf-global-rules.md"
                dest_file = config.rules_dir / rule_name
                if dest_file.exists() or rule_name in config.rules:
                    existing_rules.append(rule_name)
                else:
                    preview_rules.append(rule_name)
            else:
                # Claude Code: directory of rule files
                for rule_file in rules_path.rglob("*.md"):
                    if rule_file.is_file():
                        rel_path = rule_file.relative_to(rules_path)
                        rule_name = str(rel_path)
                        dest_file = config.rules_dir / rel_path
                        if dest_file.exists() or rule_name in config.rules:
                            existing_rules.append(rule_name)
                        else:
                            preview_rules.append(rule_name)

        # Display preview
        console.print("[bold]Would import:[/bold]")
        console.print(f"  • {len(preview_skills)} skills")
        console.print(f"  • {len(preview_servers)} MCP servers")
        console.print(f"  • {len(preview_rules)} rules")

        if preview_skills:
            console.print("\n[bold]Skills to import:[/bold]")
            for skill in preview_skills:
                console.print(f"  • {skill}")

        if preview_servers:
            console.print("\n[bold]MCP Servers to import:[/bold]")
            for server in preview_servers:
                console.print(f"  • {server}")

        if preview_rules:
            console.print("\n[bold]Rules to import:[/bold]")
            for rule in preview_rules:
                console.print(f"  • {rule}")

            # Show already managed items
        if existing_skills or existing_servers or existing_rules:
            console.print("\n[bold]Already managed by one-skills:[/bold]")
        if existing_skills:
            console.print(
                f"  • {len(existing_skills)} skills: {', '.join(existing_skills)}"
            )
        if existing_servers:
            console.print(
                f"  • {len(existing_servers)} MCP servers: {', '.join(existing_servers)}"
            )
        if existing_rules:
            console.print(
                f"  • {len(existing_rules)} rules: {', '.join(existing_rules)}"
            )

        if not preview_skills and not preview_servers and not preview_rules:
            console.print(
                "\n[dim]Nothing new to import - all items already managed[/dim]"
            )
        else:
            console.print("\n[dim]Run without --dry-run to perform the import[/dim]")

        return

    # Import skills
    imported_skills = import_skills_fn(skills_path, config)

    # Import MCP servers
    imported_servers = import_mcp(mcp_path, mcp_config)

    imported_rules = import_rules_fn(rules_path, config.rules_dir)
    # Import rules
    for rule_name in imported_rules:
        if rule_name not in config.rules:
            if source == "claude-code":
                record = RuleRecord(
                    name=rule_name,
                    source=str(rules_path / rule_name),
                    agents=[agent_id],
                )
            else:
                record = RuleRecord(
                    name=rule_name,
                    source=str(rules_path),
                    agents=[agent_id],
                )
            config.add_rule(record)
    # Report results
    console.print("\n[green]✓[/green] Import complete")
    console.print(f"  • Imported {len(imported_skills)} skills")
    console.print(f"  • Imported {len(imported_servers)} MCP servers")
    console.print(f"  • Imported {len(imported_rules)} rules")

    if imported_skills:
        console.print("\n[bold]Imported Skills:[/bold]")
        for skill in imported_skills:
            console.print(f"  • {skill}")

    if imported_servers:
        console.print("\n[bold]Imported MCP Servers:[/bold]")
        for server in imported_servers:
            console.print(f"  • {server}")

    if imported_rules:
        console.print("\n[bold]Imported Rules:[/bold]")
        for rule in imported_rules:
            console.print(f"  • {rule}")

    # Suggest profile creation
    if imported_servers and not profiles.active_profile:
        console.print(
            "\n[yellow]Suggestion:[/yellow] Create a profile with these servers:"
        )
        suggestions = suggest_profile_config(imported_servers, mcp_config)

        if click.confirm("\nCreate a profile now?", default=True):
            profile_name = click.prompt("Profile name", default="imported")
            try:
                profiles.create_profile(profile_name)
                profiles.add_agent_to_profile(
                    profile_name, agent_id, AgentConfig(enabled=True)
                )

                for server, transport in suggestions.items():
                    profiles.add_server_to_profile(profile_name, server, transport)

                console.print(
                    f"\n[green]✓[/green] Created profile '{profile_name}' with {len(suggestions)} servers"
                )
            except ValueError as exc:
                err_console.print(f"[red]Error:[/red] {exc}")


# ---------------------------------------------------------------------------
# sync command (enhanced)
# ---------------------------------------------------------------------------


@cli.command("sync")
@click.option("--agent", "-a", default=None, help="Sync only to this agent")
@click.option("--skills-only", is_flag=True, help="Sync only skills")
@click.option("--rules-only", is_flag=True, help="Sync only rules")
@click.option("--mcp-only", is_flag=True, help="Sync only MCP servers")
@click.option("--dry-run", is_flag=True, help="Show what would be done")
@click.option("--verbose", "-v", is_flag=True, help="Verbose dry-run output")
def cmd_sync(
    agent: str | None,
    skills_only: bool,
    rules_only: bool,
    mcp_only: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Sync skills, rules, and MCP servers to agents."""
    if agent and agent not in AGENT_IDS:
        err_console.print(f"[red]Unknown agent '{agent}'.[/red]")
        sys.exit(1)

    config = _load_config()
    profiles = _load_profiles()
    mcp_config = _load_mcp()

    collector = DryRunCollector() if dry_run else None

    all_results = []

    # Sync skills
    if not rules_only and not mcp_only:
        results = sync_all(config, agent_filter=agent)
        all_results.extend(results)

    # Sync rules
    if not skills_only and not mcp_only:
        results = sync_rules_all(config, agent, dry_run, collector)
        all_results.extend(results)

    if not skills_only and not rules_only:
        if agent:
            result = sync_mcp_servers(profiles, mcp_config, agent, dry_run, collector)
            all_results.append(result)
        elif profile := profiles.get_active_profile():
            for agent_id, agent_cfg in profile.agents.items():
                if agent_cfg.enabled:
                    result = sync_mcp_servers(
                        profiles, mcp_config, agent_id, dry_run, collector
                    )
                    all_results.append(result)

    # Display results
    if dry_run and collector:
        if verbose:
            console.print(render_detailed(collector))
        else:
            console.print(render_summary(collector))
    else:
        if not all_results:
            console.print("[dim]Nothing to sync.[/dim]")
            return

        table = Table(show_lines=False, show_header=True)
        table.add_column("Item", style="bold")
        table.add_column("Agent", style="cyan")
        table.add_column("Result")

        for r in all_results:
            color = "green" if r.action not in ("error", "skipped") else "red"
            detail = f" — {r.detail}" if r.detail else ""
            table.add_row(r.skill, r.agent, f"[{color}]{r.action}{detail}[/{color}]")

        console.print(table)


# ---------------------------------------------------------------------------
# skill commands
# ---------------------------------------------------------------------------


@cli.group("skill")
def skill_group() -> None:
    """Manage skills."""


@skill_group.command("install")
@click.argument("source")
@click.option(
    "--agents",
    "-a",
    default="",
    help=f"Comma-separated agent IDs. Valid: {', '.join(AGENT_IDS)}",
)
def skill_install(source: str, agents: str) -> None:
    """Install a skill from a GitHub URL or local path."""
    agent_list: list[str] = [a.strip() for a in agents.split(",") if a.strip()]

    for aid in agent_list:
        if aid not in AGENT_IDS:
            err_console.print(f"[red]Unknown agent '{aid}'.[/red]")
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
        results = sync_skill(record, config)
        for r in results:
            icon = "[green]✓[/green]" if r.action != "error" else "[red]✗[/red]"
            console.print(f"  {icon} synced to [cyan]{r.agent}[/cyan] ({r.action})")


@skill_group.command("register")
@click.argument("skill_name")
@click.option(
    "--agents",
    "-a",
    default="",
    help=f"Comma-separated agent IDs. Valid: {', '.join(AGENT_IDS)}",
)
def skill_register(skill_name: str, agents: str) -> None:
    """Register an existing skill directory that's already in the skills directory."""
    config = _load_config()

    skill_path = config.skills_dir / skill_name
    if not skill_path.exists():
        err_console.print(f"[red]Skill directory not found: {skill_path}[/red]")
        sys.exit(1)

    if not skill_path.is_dir():
        err_console.print(f"[red]'{skill_path}' is not a directory.[/red]")
        sys.exit(1)

    if skill_name in config.skills:
        err_console.print(f"[red]Skill '{skill_name}' is already registered.[/red]")
        sys.exit(1)

    agent_list: list[str] = [a.strip() for a in agents.split(",") if a.strip()]

    for aid in agent_list:
        if aid not in AGENT_IDS:
            err_console.print(f"[red]Unknown agent '{aid}'.[/red]")
            sys.exit(1)

    from .config import SkillRecord

    record = SkillRecord(
        name=skill_name,
        source=str(skill_path),
        source_type="local",
        agents=agent_list,
    )
    config.add_skill(record)
    console.print(f"[green]✓[/green] Registered skill [bold]{skill_name}[/bold]")

    if agent_list:
        results = sync_skill(record, config)
        for r in results:
            icon = "[green]✓[/green]" if r.action != "error" else "[red]✗[/red]"
            console.print(f"  {icon} synced to [cyan]{r.agent}[/cyan] ({r.action})")


@skill_group.command("list")
def skill_list() -> None:
    """List installed skills."""
    config = _load_config()

    if not config.skills:
        console.print("[dim]No skills installed yet.[/dim]")
        return

    table = Table(title="Skills", show_lines=True)
    table.add_column("Name", style="bold")
    table.add_column("Source", style="dim")
    table.add_column("Type")
    table.add_column("Agents")

    for rec in config.skills.values():
        agents_str = ", ".join(rec.agents) if rec.agents else "[dim]none[/dim]"
        table.add_row(rec.name, rec.source, rec.source_type, agents_str)

    console.print(table)


@skill_group.command("assign")
@click.argument("skill")
@click.argument("agent")
def skill_assign(skill: str, agent: str) -> None:
    """Assign a skill to an agent."""
    if agent not in AGENT_IDS:
        err_console.print(f"[red]Unknown agent '{agent}'.[/red]")
        sys.exit(1)

    config = _load_config()

    if skill not in config.skills:
        err_console.print(f"[red]Skill '{skill}' not found.[/red]")
        sys.exit(1)

    config.assign_agent(skill, agent)
    record = config.skills[skill]
    results = sync_skill(record, config, agent_filter=agent)
    for r in results:
        icon = "[green]✓[/green]" if r.action != "error" else "[red]✗[/red]"
        msg = r.detail if r.action == "error" else r.action
        console.print(f"{icon} {skill} → {agent} ({msg})")


@skill_group.command("unassign")
@click.argument("skill")
@click.argument("agent")
def skill_unassign(skill: str, agent: str) -> None:
    """Unassign a skill from an agent."""
    config = _load_config()

    if skill not in config.skills:
        err_console.print(f"[red]Skill '{skill}' not found.[/red]")
        sys.exit(1)

    config.unassign_agent(skill, agent)
    record = config.skills[skill]
    result = unsync_skill(record, agent)
    icon = "[green]✓[/green]" if result.action != "error" else "[red]✗[/red]"
    msg = result.detail if result.action == "error" else result.action
    console.print(f"{icon} {skill} ✗ {agent} ({msg})")


@skill_group.command("remove")
@click.argument("skill")
@click.confirmation_option(prompt="Remove this skill from the central store?")
def skill_remove(skill: str) -> None:
    """Remove a skill."""
    config = _load_config()

    if skill not in config.skills:
        err_console.print(f"[red]Skill '{skill}' not found.[/red]")
        sys.exit(1)

    record = config.skills[skill]
    if agents_to_unsync := list(record.agents):
        console.print(f"Removing skill [bold]{skill}[/bold] from agents:")
        for agent_id in agents_to_unsync:
            result = unsync_skill(record, agent_id)
            if result.action == "removed":
                console.print(
                    f"  [green]✓[/green] Unsynced from [cyan]{agent_id}[/cyan]"
                )
            else:
                console.print(f"  [yellow]○[/yellow] {agent_id}: {result.action}")

    remove(skill, config)
    console.print(
        f"\n[green]✓[/green] Removed skill [bold]{skill}[/bold] from central store"
    )


@cli.command("list")
def cmd_list() -> None:
    """List all installed resources (skills, rules, MCP servers)."""
    config = _load_config()
    mcp_config = _load_mcp()

    # Skills
    if config.skills:
        table = Table(title="Skills", show_lines=True)
        table.add_column("Name", style="bold")
        table.add_column("Source", style="dim")
        table.add_column("Type")
        table.add_column("Agents")

        for rec in config.skills.values():
            agents_str = ", ".join(rec.agents) if rec.agents else "[dim]none[/dim]"
            table.add_row(rec.name, rec.source, rec.source_type, agents_str)

        console.print(table)
        console.print()

    # Rules
    if config.rules:
        table = Table(title="Rules", show_lines=True)
        table.add_column("Name", style="bold")
        table.add_column("Source", style="dim")
        table.add_column("Agents")

        for rec in config.rules.values():
            agents_str = ", ".join(rec.agents) if rec.agents else "[dim]none[/dim]"
            table.add_row(rec.name, rec.source, agents_str)

        console.print(table)
        console.print()

    # MCP Servers
    if mcp_config.servers:
        profiles = _load_profiles()

        table = Table(title="MCP Servers", show_lines=True)
        table.add_column("Name", style="bold cyan")
        table.add_column("Description")
        table.add_column("Transports")
        table.add_column("Used in Profiles")

        for server in mcp_config.servers.values():
            transports = ", ".join(server.transports.keys())

            # Find which profiles use this server
            using_profiles = []
            for profile_name, profile in profiles.profiles.items():
                if server.name in profile.mcp_servers:
                    transport = profile.mcp_servers[server.name]
                    marker = "●" if profile_name == profiles.active_profile else "○"
                    using_profiles.append(f"{marker} {profile_name} ({transport})")

            profiles_str = (
                "\n".join(using_profiles) if using_profiles else "[dim]none[/dim]"
            )
            table.add_row(server.name, server.description, transports, profiles_str)

        console.print(table)
        console.print()
        console.print("[dim]● = active profile, ○ = inactive profile[/dim]")
        console.print()

    if not config.skills and not config.rules and not mcp_config.servers:
        console.print("[dim]No resources installed yet.[/dim]")
        console.print("\n[bold]Get started:[/bold]")
        console.print(
            "  • Install a skill: [cyan]one-skills skill install <source>[/cyan]"
        )
        console.print(
            "  • Install a rule: [cyan]one-skills rule install <source>[/cyan]"
        )
        console.print("  • Add MCP server: [cyan]one-skills mcp add <name>[/cyan]")
