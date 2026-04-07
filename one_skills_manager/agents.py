"""Agent definitions: known AI agents and their skill directory paths."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Agent:
    """Represents an AI agent with its configuration."""

    id: str
    name: str
    skills_dir: Path
    rules_dir: Path
    mcp_config_path: Path


# fmt: off
_AGENT_DEFS: list[tuple[str, str, str, str, str]] = [
    # (id, display name, skills path, rules path, mcp config path)
    ("claude-code", "Claude Code", "~/.claude/skills", "~/.claude/rules", "~/.claude.json"),
    ("cursor", "Cursor", "~/.cursor/skills", "~/.cursor/rules", "~/.cursor/mcp.json"),
    ("windsurf", "Windsurf", "~/.codeium/windsurf/skills", "~/.codeium/windsurf/memories", "~/.codeium/windsurf/mcp_config.json"),
    ("codex", "OpenAI Codex", "~/.codex/skills", "~/.codex/rules", "~/.codex.json"),
]
# fmt: on

AGENTS: dict[str, Agent] = {
    aid: Agent(
        id=aid,
        name=name,
        skills_dir=Path(skills_path).expanduser(),
        rules_dir=Path(rules_path).expanduser(),
        mcp_config_path=Path(mcp_path).expanduser(),
    )
    for aid, name, skills_path, rules_path, mcp_path in _AGENT_DEFS
}

AGENT_IDS: list[str] = list(AGENTS.keys())


def get_agent(agent_id: str) -> Agent:
    """Get an agent by its ID.

    Args:
        agent_id: The ID of the agent to retrieve

    Returns:
        The Agent instance

    Raises:
        ValueError: If the agent ID is unknown
    """
    if agent_id not in AGENTS:
        raise ValueError(
            f"Unknown agent '{agent_id}'. Valid agents: {', '.join(AGENT_IDS)}"
        )
    return AGENTS[agent_id]
