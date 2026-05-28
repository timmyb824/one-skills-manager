"""Interactive guided mode for one-skills-manager.

Public API (consumed by cli.py):
    run_interactive()                     — main menu loop
    _show_status()                        — status dashboard (also used by `one-skills status`)
    _guided_add_mcp_server_with_name(name)— MCP wizard pre-filled with a server name
"""

from __future__ import annotations

import questionary
from rich.console import Console
from rich.panel import Panel

from ._style import STYLE as _STYLE
from .flows import (
    guided_add_mcp_server,
    guided_add_mcp_server_with_name,
    guided_add_rule,
    guided_add_skill,
    guided_manage_profile,
    guided_sync,
)
from .status import show_status

console = Console()

# ---------------------------------------------------------------------------
# Public aliases — preserved for cli.py and external callers
# ---------------------------------------------------------------------------

_show_status = show_status
_guided_add_mcp_server_with_name = guided_add_mcp_server_with_name


# ---------------------------------------------------------------------------
# Main interactive loop
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
                show_status()
            elif action == "add_skill":
                guided_add_skill()
            elif action == "add_rule":
                guided_add_rule()
            elif action == "add_mcp":
                guided_add_mcp_server()
            elif action == "profile":
                guided_manage_profile()
            elif action == "sync":
                guided_sync()
        except KeyboardInterrupt:
            console.print("\n[dim]Cancelled.[/dim]")

        console.print()


__all__ = [
    "run_interactive",
    "_show_status",
    "_guided_add_mcp_server_with_name",
]
