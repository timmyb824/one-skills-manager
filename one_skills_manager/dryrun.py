"""Dry-run functionality: collect and display planned actions without executing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ActionType(Enum):
    """Types of actions that can be performed in dry-run mode."""

    CREATE_SYMLINK = "create_symlink"
    UPDATE_SYMLINK = "update_symlink"
    DELETE_SYMLINK = "delete_symlink"
    CREATE_FILE = "create_file"
    MODIFY_FILE = "modify_file"
    DELETE_FILE = "delete_file"
    BACKUP_FILE = "backup_file"


class Severity(Enum):
    """Severity levels for dry-run actions."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DryRunAction:
    """Represents a planned action in dry-run mode."""

    action_type: ActionType
    target: str
    details: str = ""
    severity: Severity = Severity.INFO
    source: str | None = None
    diff: str | None = None


@dataclass
class DryRunCollector:
    """Collects and manages dry-run actions."""

    actions: list[DryRunAction] = field(default_factory=list)

    def add_symlink(self, source: str, target: str, status: str = "create") -> None:
        """Record a symlink operation."""
        if status == "create":
            action_type = ActionType.CREATE_SYMLINK
            details = f"Link to {source}"
        elif status == "update":
            action_type = ActionType.UPDATE_SYMLINK
            details = f"Update link to {source}"
        else:
            action_type = ActionType.CREATE_SYMLINK
            details = f"Already linked to {source}"

        self.actions.append(
            DryRunAction(
                action_type=action_type,
                target=target,
                details=details,
                source=source,
            )
        )

    def add_file_modification(
        self, path: str, change_summary: str, diff: str | None = None
    ) -> None:
        """Record a file modification."""
        self.actions.append(
            DryRunAction(
                action_type=ActionType.MODIFY_FILE,
                target=path,
                details=change_summary,
                diff=diff,
            )
        )

    def add_file_creation(self, path: str, content_preview: str = "") -> None:
        """Record a file creation."""
        self.actions.append(
            DryRunAction(
                action_type=ActionType.CREATE_FILE,
                target=path,
                details=content_preview,
            )
        )

    def add_deletion(self, path: str, item_type: str = "file") -> None:
        """Record a deletion."""
        action_type = (
            ActionType.DELETE_SYMLINK
            if item_type == "symlink"
            else ActionType.DELETE_FILE
        )
        self.actions.append(
            DryRunAction(
                action_type=action_type,
                target=path,
                details=f"Remove {item_type}",
            )
        )

    def add_backup(self, original: str, backup: str) -> None:
        """Record a backup operation."""
        self.actions.append(
            DryRunAction(
                action_type=ActionType.BACKUP_FILE,
                target=original,
                details=f"Backup to {backup}",
                source=backup,
            )
        )

    def get_summary(self) -> dict[str, int]:
        """Get summary counts by action type."""
        summary: dict[str, int] = {}
        for action in self.actions:
            key = action.action_type.value
            summary[key] = summary.get(key, 0) + 1
        return summary

    def has_changes(self) -> bool:
        """Check if there are any changes to apply."""
        return len(self.actions) > 0


def render_summary(collector: DryRunCollector) -> str:
    """Render high-level summary of planned actions."""
    if not collector.has_changes():
        return "No changes needed - everything is up to date"

    lines = ["Dry-run mode: No changes will be made\n", "Planned actions:"]

    symlinks_create = sum(
        a.action_type == ActionType.CREATE_SYMLINK for a in collector.actions
    )
    symlinks_update = sum(
        a.action_type == ActionType.UPDATE_SYMLINK for a in collector.actions
    )
    files_modify = sum(
        a.action_type == ActionType.MODIFY_FILE for a in collector.actions
    )
    files_create = sum(
        a.action_type == ActionType.CREATE_FILE for a in collector.actions
    )
    backups = sum(a.action_type == ActionType.BACKUP_FILE for a in collector.actions)

    if symlinks_create:
        lines.append(f"  + Create {symlinks_create} symlink(s)")
    if symlinks_update:
        lines.append(f"  ~ Update {symlinks_update} symlink(s)")
    if files_modify:
        lines.append(f"  ~ Modify {files_modify} file(s)")
    if files_create:
        lines.append(f"  + Create {files_create} file(s)")
    if backups:
        lines.append(f"  ⚠ Create {backups} backup(s)")

    lines.extend(
        (
            f"\nSummary: {symlinks_create + symlinks_update} symlinks, {files_modify + files_create} files",
            "Run without --dry-run to apply changes",
        )
    )
    return "\n".join(lines)


def render_detailed(collector: DryRunCollector) -> str:
    """Render detailed view of planned actions."""
    if not collector.has_changes():
        return "No changes needed - everything is up to date"

    lines = ["Dry-run mode (verbose): No changes will be made\n"]

    symlinks = [
        a
        for a in collector.actions
        if a.action_type in (ActionType.CREATE_SYMLINK, ActionType.UPDATE_SYMLINK)
    ]
    files = [
        a
        for a in collector.actions
        if a.action_type in (ActionType.MODIFY_FILE, ActionType.CREATE_FILE)
    ]
    backups = [a for a in collector.actions if a.action_type == ActionType.BACKUP_FILE]

    if symlinks:
        lines.append("=== Symlinks ===")
        for action in symlinks:
            status = (
                "CREATE"
                if action.action_type == ActionType.CREATE_SYMLINK
                else "UPDATE"
            )
            lines.append(f"[{status}] {action.target}")
            if action.source:
                lines.append(f"  → {action.source}")
        lines.append("")

    if backups:
        lines.append("=== Backups ===")
        for action in backups:
            lines.extend((f"[BACKUP] {action.target}", f"  → {action.source}"))
        lines.append("")

    if files:
        lines.append("=== File Changes ===")
        for action in files:
            status = (
                "CREATE" if action.action_type == ActionType.CREATE_FILE else "MODIFY"
            )
            lines.append(f"[{status}] {action.target}")
            if action.details:
                lines.append(f"  {action.details}")
            if action.diff:
                lines.append(f"\n{action.diff}")
        lines.append("")

    summary = collector.get_summary()
    total = sum(summary.values())
    lines.extend((f"Total actions: {total}", "Run without --dry-run to apply changes"))
    return "\n".join(lines)
