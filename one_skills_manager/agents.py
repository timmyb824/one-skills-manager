"""Agent definitions: known AI agents and their skill directory paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Agent:
    id: str
    name: str
    skills_dir: Path  # resolved global skills directory


# fmt: off
_AGENT_DEFS: list[tuple[str, str, str]] = [
    # (id,            display name,    relative-to-home path)
    ("claude-code",  "Claude Code",   "~/.claude/skills"),
    ("cursor",       "Cursor",        "~/.cursor/skills"),
    ("windsurf",     "Windsurf",      "~/.codeium/windsurf/skills/"),
    ("codex",        "OpenAI Codex",  "~/.codex/skills"),
]
# fmt: on

AGENTS: dict[str, Agent] = {
    aid: Agent(id=aid, name=name, skills_dir=Path(path).expanduser())
    for aid, name, path in _AGENT_DEFS
}

AGENT_IDS: list[str] = list(AGENTS.keys())


def get_agent(agent_id: str) -> Agent:
    if agent_id not in AGENTS:
        raise ValueError(
            f"Unknown agent '{agent_id}'. Valid agents: {', '.join(AGENT_IDS)}"
        )
    return AGENTS[agent_id]
