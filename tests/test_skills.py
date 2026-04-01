"""Tests for skill install (local path only — GitHub requires network)."""

import shutil
from pathlib import Path

import pytest

from one_skills_manager.config import Config
from one_skills_manager.skills import install_from_local, remove


def _make_config(tmp_path: Path) -> Config:
    cfg = Config.load(tmp_path / "config.json")
    cfg.skills_dir = tmp_path / "skills"
    cfg.skills_dir.mkdir(parents=True, exist_ok=True)
    return cfg


def test_install_local_directory(tmp_path: Path) -> None:
    src = tmp_path / "my-skill"
    src.mkdir()
    (src / "skill.md").write_text("# hello")

    config = _make_config(tmp_path)
    record = install_from_local(str(src), config, agents=["claude-code"])

    assert record.name == "my-skill"
    assert record.source_type == "local"
    assert record.agents == ["claude-code"]
    assert (config.skills_dir / "my-skill" / "skill.md").exists()
    assert "my-skill" in config.skills


def test_install_local_file(tmp_path: Path) -> None:
    src = tmp_path / "my-skill.md"
    src.write_text("# skill content")

    config = _make_config(tmp_path)
    record = install_from_local(str(src), config, agents=[])

    assert record.name == "my-skill.md"
    assert (config.skills_dir / "my-skill.md" / "my-skill.md").exists()


def test_install_nonexistent_path_raises(tmp_path: Path) -> None:
    config = _make_config(tmp_path)
    with pytest.raises(FileNotFoundError):
        install_from_local(str(tmp_path / "does-not-exist"), config, agents=[])


def test_install_overwrites_existing(tmp_path: Path) -> None:
    src = tmp_path / "my-skill"
    src.mkdir()
    (src / "v1.md").write_text("v1")

    config = _make_config(tmp_path)
    install_from_local(str(src), config, agents=[])

    # Modify source and re-install
    (src / "v1.md").unlink()
    (src / "v2.md").write_text("v2")
    install_from_local(str(src), config, agents=[])

    assert not (config.skills_dir / "my-skill" / "v1.md").exists()
    assert (config.skills_dir / "my-skill" / "v2.md").exists()


def test_remove_deletes_files_and_config(tmp_path: Path) -> None:
    src = tmp_path / "my-skill"
    src.mkdir()
    (src / "skill.md").write_text("x")

    config = _make_config(tmp_path)
    install_from_local(str(src), config, agents=[])
    remove("my-skill", config)

    assert not (config.skills_dir / "my-skill").exists()
    assert "my-skill" not in config.skills
