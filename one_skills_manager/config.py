"""Persistent configuration: skill registry and per-skill agent assignments."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_HOME = Path("~/.one-skills").expanduser()
CONFIG_FILE = DEFAULT_HOME / "config.json"
SKILLS_DIR = DEFAULT_HOME / "skills"


@dataclass
class SkillRecord:
    name: str
    source: str  # original URL or absolute local path
    source_type: str  # "github" | "local"
    agents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "source_type": self.source_type,
            "agents": self.agents,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillRecord:
        return cls(
            name=data["name"],
            source=data["source"],
            source_type=data["source_type"],
            agents=data.get("agents", []),
        )


@dataclass
class Config:
    skills_dir: Path = field(default_factory=lambda: SKILLS_DIR)
    skills: dict[str, SkillRecord] = field(default_factory=dict)
    _path: Path = field(default_factory=lambda: CONFIG_FILE, repr=False)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": "1",
            "skills_dir": str(self.skills_dir),
            "skills": {name: rec.to_dict() for name, rec in self.skills.items()},
        }
        self._path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> Config:
        if not path.exists():
            cfg = cls(_path=path)
            cfg.skills_dir.mkdir(parents=True, exist_ok=True)
            return cfg
        data = json.loads(path.read_text())
        cfg = cls(
            skills_dir=Path(data.get("skills_dir", str(SKILLS_DIR))),
            skills={
                name: SkillRecord.from_dict(rec)
                for name, rec in data.get("skills", {}).items()
            },
            _path=path,
        )
        cfg.skills_dir.mkdir(parents=True, exist_ok=True)
        return cfg

    # ------------------------------------------------------------------
    # Skill helpers
    # ------------------------------------------------------------------

    def add_skill(self, record: SkillRecord) -> None:
        self.skills[record.name] = record
        self.save()

    def remove_skill(self, name: str) -> None:
        self.skills.pop(name, None)
        self.save()

    def assign_agent(self, skill_name: str, agent_id: str) -> None:
        rec = self.skills[skill_name]
        if agent_id not in rec.agents:
            rec.agents.append(agent_id)
            self.save()

    def unassign_agent(self, skill_name: str, agent_id: str) -> None:
        rec = self.skills[skill_name]
        if agent_id in rec.agents:
            rec.agents.remove(agent_id)
            self.save()
