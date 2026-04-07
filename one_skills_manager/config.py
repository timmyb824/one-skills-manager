"""Persistent configuration: skill registry and per-skill agent assignments."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_HOME = Path("~/.one-skills").expanduser()
CONFIG_FILE = DEFAULT_HOME / "config.json"
SKILLS_DIR = DEFAULT_HOME / "skills"
RULES_DIR = DEFAULT_HOME / "rules"


def path_to_portable(path: Path) -> str:
    """Convert an absolute path to a portable format using ~/ if under home.

    Args:
        path: Absolute path to convert

    Returns:
        String path with ~/ prefix if under home directory, otherwise absolute
    """
    try:
        home = Path.home()
        # Check if path is under home directory
        path.relative_to(home)
        # Convert to string with ~/ prefix
        return str(Path("~") / path.relative_to(home))
    except ValueError:
        # Path is not under home directory, return as absolute
        return str(path)


def portable_to_path(path_str: str) -> Path:
    """Convert a portable path string to an absolute Path.

    Args:
        path_str: Path string, possibly with ~/ prefix

    Returns:
        Absolute Path with ~ expanded
    """
    return Path(path_str).expanduser()


@dataclass
class SkillRecord:
    """Record of a skill in the configuration."""

    name: str
    source: str  # original URL or absolute local path
    source_type: str  # "github" | "local"
    agents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the SkillRecord to a dictionary."""
        # Convert source to portable format if it's a local path
        source = self.source
        if self.source_type == "local":
            try:
                source = path_to_portable(Path(self.source))
            except Exception:  # noqa: BLE001
                # If conversion fails, keep original
                pass

        return {
            "name": self.name,
            "source": source,
            "source_type": self.source_type,
            "agents": self.agents,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillRecord:
        """Create a SkillRecord from a dictionary."""
        return cls(
            name=data["name"],
            source=data["source"],
            source_type=data["source_type"],
            agents=data.get("agents", []),
        )


@dataclass
class RuleRecord:
    """Record of a rule in the configuration."""

    name: str
    source: str
    agents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the RuleRecord to a dictionary."""
        # Convert source to portable format if it's a local path
        source = self.source
        try:
            source = path_to_portable(Path(self.source))
        except Exception:  # noqa: BLE001
            # If conversion fails, keep original
            pass

        return {
            "name": self.name,
            "source": source,
            "agents": self.agents,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuleRecord:
        """Create a RuleRecord from a dictionary."""
        return cls(
            name=data["name"],
            source=data["source"],
            agents=data.get("agents", []),
        )


@dataclass
class Config:
    skills_dir: Path = field(default_factory=lambda: SKILLS_DIR)
    skills: dict[str, SkillRecord] = field(default_factory=dict)
    rules_dir: Path = field(default_factory=lambda: RULES_DIR)
    rules: dict[str, RuleRecord] = field(default_factory=dict)
    _path: Path = field(default_factory=lambda: CONFIG_FILE, repr=False)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1",
            "skills_dir": path_to_portable(self.skills_dir),
            "skills": {name: rec.to_dict() for name, rec in self.skills.items()},
            "rules_dir": path_to_portable(self.rules_dir),
            "rules": {name: rec.to_dict() for name, rec in self.rules.items()},
        }
        self._path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> Config:
        """Load the configuration from a file."""
        if not path.exists():
            cfg = cls(_path=path)
            cfg.skills_dir.mkdir(parents=True, exist_ok=True)
            cfg.rules_dir.mkdir(parents=True, exist_ok=True)
            return cfg
        data = json.loads(path.read_text())
        cfg = cls(
            skills_dir=portable_to_path(data.get("skills_dir", str(SKILLS_DIR))),
            skills={
                name: SkillRecord.from_dict(rec)
                for name, rec in data.get("skills", {}).items()
            },
            rules_dir=portable_to_path(data.get("rules_dir", str(RULES_DIR))),
            rules={
                name: RuleRecord.from_dict(rec)
                for name, rec in data.get("rules", {}).items()
            },
            _path=path,
        )
        cfg.skills_dir.mkdir(parents=True, exist_ok=True)
        cfg.rules_dir.mkdir(parents=True, exist_ok=True)
        return cfg

    # ------------------------------------------------------------------
    # Skill helpers
    # ------------------------------------------------------------------

    def add_skill(self, record: SkillRecord) -> None:
        """Add a skill to the configuration."""
        self.skills[record.name] = record
        self.save()

    def remove_skill(self, name: str) -> None:
        """Remove a skill from the configuration."""
        self.skills.pop(name, None)
        self.save()

    def assign_agent(self, skill_name: str, agent_id: str) -> None:
        """Assign an agent to a skill."""
        rec = self.skills[skill_name]
        if agent_id not in rec.agents:
            rec.agents.append(agent_id)
            self.save()

    def unassign_agent(self, skill_name: str, agent_id: str) -> None:
        """Unassign an agent from a skill."""
        rec = self.skills[skill_name]
        if agent_id in rec.agents:
            rec.agents.remove(agent_id)
            self.save()

    # ------------------------------------------------------------------
    # Rule helpers
    # ------------------------------------------------------------------

    def add_rule(self, record: RuleRecord) -> None:
        """Add a rule to the configuration."""
        self.rules[record.name] = record
        self.save()

    def remove_rule(self, name: str) -> None:
        """Remove a rule from the configuration."""
        self.rules.pop(name, None)
        self.save()

    def assign_rule_to_agent(self, rule_name: str, agent_id: str) -> None:
        """Assign a rule to an agent."""
        rec = self.rules[rule_name]
        if agent_id not in rec.agents:
            rec.agents.append(agent_id)
            self.save()

    def unassign_rule_from_agent(self, rule_name: str, agent_id: str) -> None:
        """Unassign a rule from an agent."""
        rec = self.rules[rule_name]
        if agent_id in rec.agents:
            rec.agents.remove(agent_id)
            self.save()
