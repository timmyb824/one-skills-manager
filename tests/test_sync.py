"""Tests for symlink sync logic."""

from pathlib import Path

from one_skills_manager.agents import Agent
from one_skills_manager.config import Config, SkillRecord
from one_skills_manager.mcp import MCPConfig
from one_skills_manager.profiles import ProfileConfig
from one_skills_manager.sync import (
    _link_skill,
    sync_mcp_servers,
    sync_skill,
    unsync_skill,
)


def _make_config(tmp_path: Path) -> Config:
    cfg = Config.load(tmp_path / "config.json")
    cfg.skills_dir = tmp_path / "skills"
    cfg.skills_dir.mkdir(parents=True, exist_ok=True)
    return cfg


def _make_skill_dir(config: Config, name: str) -> Path:
    d = config.skills_dir / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "skill.md").write_text("# skill")
    return d


def test_link_skill_creates_symlink(tmp_path: Path) -> None:
    source = tmp_path / "my-skill"
    source.mkdir()
    target_dir = tmp_path / "agent-skills"
    action = _link_skill(source, target_dir)
    link = target_dir / "my-skill"
    assert action == "linked"
    assert link.is_symlink()
    assert link.resolve() == source.resolve()


def test_link_skill_up_to_date_when_already_correct(tmp_path: Path) -> None:
    source = tmp_path / "my-skill"
    source.mkdir()
    target_dir = tmp_path / "agent-skills"
    _link_skill(source, target_dir)
    action = _link_skill(source, target_dir)
    assert action == "up-to-date"


def test_link_skill_updated_when_stale(tmp_path: Path) -> None:
    source1 = tmp_path / "v1"
    source1.mkdir()
    source2 = tmp_path / "my-skill"
    source2.mkdir()
    target_dir = tmp_path / "agent-skills"
    target_dir.mkdir()
    link = target_dir / "my-skill"
    link.symlink_to(source1)  # stale symlink

    action = _link_skill(source2, target_dir)
    assert action == "updated"
    assert link.resolve() == source2.resolve()


def test_sync_skill_creates_links(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    agent_dir = tmp_path / "claude-skills"
    # Monkey-patch agents table for the test
    from one_skills_manager import agents as agents_module

    original = agents_module.AGENTS.copy()
    agents_module.AGENTS["claude-code"] = Agent(
        id="claude-code",
        name="Claude Code",
        skills_dir=agent_dir,
        rules_dir=agent_dir,
        mcp_config_path=agent_dir,
    )
    try:
        _make_skill_dir(config, "my-skill")
        record = SkillRecord(
            name="my-skill", source="local", source_type="local", agents=["claude-code"]
        )
        config.add_skill(record)
        results = sync_skill(record, config)
        assert len(results) == 1
        assert results[0].action == "linked"
        assert (agent_dir / "my-skill").is_symlink()
    finally:
        agents_module.AGENTS.clear()
        agents_module.AGENTS.update(original)


def test_unsync_skill_removes_link(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    agent_dir = tmp_path / "claude-skills"
    agent_dir.mkdir()

    from one_skills_manager import agents as agents_module

    original = agents_module.AGENTS.copy()
    agents_module.AGENTS["claude-code"] = Agent(
        id="claude-code",
        name="Claude Code",
        skills_dir=agent_dir,
        rules_dir=agent_dir,
        mcp_config_path=agent_dir,
    )
    try:
        skill_dir = _make_skill_dir(config, "my-skill")
        link = agent_dir / "my-skill"
        link.symlink_to(skill_dir)

        record = SkillRecord(
            name="my-skill", source="local", source_type="local", agents=["claude-code"]
        )
        config.add_skill(record)
        result = unsync_skill(record, "claude-code")
        assert result.action == "removed"
        assert not link.exists()
    finally:
        agents_module.AGENTS.clear()
        agents_module.AGENTS.update(original)


def test_sync_missing_skill_dir_returns_error(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    record = SkillRecord(
        name="ghost", source="x", source_type="local", agents=["claude-code"]
    )
    config.add_skill(record)
    results = sync_skill(record, config)
    assert results[0].action == "error"


def test_sync_mcp_servers_shared_skips_without_profile(tmp_path: Path) -> None:
    """Shared MCP sync should skip unconditionally and avoid file writes."""
    from one_skills_manager import agents as agents_module

    placeholder_mcp_path = tmp_path / "shared-mcp.json"
    original = agents_module.AGENTS.copy()
    agents_module.AGENTS["shared"] = Agent(
        id="shared",
        name="Shared .agents",
        skills_dir=tmp_path / "shared-skills",
        rules_dir=tmp_path / "shared-rules",
        mcp_config_path=placeholder_mcp_path,
    )

    try:
        profile_config = ProfileConfig()
        mcp_config = MCPConfig()

        result = sync_mcp_servers(profile_config, mcp_config, "shared")

        assert result.action == "skipped"
        assert result.detail == "MCP sync not supported for shared"
        assert not placeholder_mcp_path.exists()
    finally:
        agents_module.AGENTS.clear()
        agents_module.AGENTS.update(original)
