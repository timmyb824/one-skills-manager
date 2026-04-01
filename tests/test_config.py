"""Tests for config persistence."""

import json
from pathlib import Path

import pytest

from one_skills_manager.config import Config, SkillRecord


def _make_config(tmp_path: Path) -> Config:
    cfg_file = tmp_path / "config.json"
    return Config.load(cfg_file)


def test_config_creates_skills_dir(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    assert cfg.skills_dir.exists()


def test_add_skill_persists(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    rec = SkillRecord(
        name="my-skill",
        source="/some/path",
        source_type="local",
        agents=["claude-code"],
    )
    cfg.add_skill(rec)

    reloaded = _make_config(tmp_path)
    assert "my-skill" in reloaded.skills
    assert reloaded.skills["my-skill"].agents == ["claude-code"]


def test_assign_agent(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    cfg.add_skill(SkillRecord(name="s", source="x", source_type="local"))
    cfg.assign_agent("s", "cursor")

    reloaded = _make_config(tmp_path)
    assert "cursor" in reloaded.skills["s"].agents


def test_assign_agent_no_duplicates(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    cfg.add_skill(SkillRecord(name="s", source="x", source_type="local"))
    cfg.assign_agent("s", "cursor")
    cfg.assign_agent("s", "cursor")
    assert cfg.skills["s"].agents.count("cursor") == 1


def test_unassign_agent(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    cfg.add_skill(
        SkillRecord(name="s", source="x", source_type="local", agents=["claude-code"])
    )
    cfg.unassign_agent("s", "claude-code")

    reloaded = _make_config(tmp_path)
    assert "claude-code" not in reloaded.skills["s"].agents


def test_remove_skill(tmp_path: Path) -> None:
    cfg = _make_config(tmp_path)
    cfg.add_skill(SkillRecord(name="s", source="x", source_type="local"))
    cfg.remove_skill("s")

    reloaded = _make_config(tmp_path)
    assert "s" not in reloaded.skills
