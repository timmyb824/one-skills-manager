"""Skill installation: fetch from GitHub or copy from a local path."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import httpx

from .config import Config, SkillRecord

# Match  https://github.com/<owner>/<repo>/tree/<ref>/<path>
_GH_TREE_RE = re.compile(
    r"https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/tree/(?P<ref>[^/]+)/(?P<path>.+)"
)
_GH_API_BASE = "https://api.github.com"


def _download_github_dir(
    owner: str, repo: str, ref: str, dir_path: str, dest: Path
) -> None:
    """Recursively download a directory from GitHub via the Contents API."""
    api_url = f"{_GH_API_BASE}/repos/{owner}/{repo}/contents/{dir_path}?ref={ref}"
    resp = httpx.get(
        api_url,
        headers={"Accept": "application/vnd.github.v3+json"},
        follow_redirects=True,
    )
    resp.raise_for_status()
    entries = resp.json()
    if not isinstance(entries, list):
        raise ValueError(f"Unexpected GitHub API response for {api_url}")
    dest.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        if entry["type"] == "file":
            raw_url = entry["download_url"]
            file_resp = httpx.get(raw_url, follow_redirects=True)
            file_resp.raise_for_status()
            (dest / entry["name"]).write_bytes(file_resp.content)
        elif entry["type"] == "dir":
            _download_github_dir(owner, repo, ref, entry["path"], dest / entry["name"])


def install_from_github(url: str, config: Config, agents: list[str]) -> SkillRecord:
    """Download a skill directory from GitHub and register it."""
    m = _GH_TREE_RE.match(url)
    if not m:
        raise ValueError(
            f"Cannot parse GitHub URL '{url}'.\n"
            "Expected format: https://github.com/<owner>/<repo>/tree/<ref>/<path>"
        )
    owner, repo, ref, dir_path = m["owner"], m["repo"], m["ref"], m["path"]
    skill_name = dir_path.rstrip("/").split("/")[-1]
    dest = config.skills_dir / skill_name

    if dest.exists():
        shutil.rmtree(dest)

    _download_github_dir(owner, repo, ref, dir_path, dest)

    record = SkillRecord(
        name=skill_name, source=url, source_type="github", agents=agents
    )
    config.add_skill(record)
    return record


def install_from_local(source: str, config: Config, agents: list[str]) -> SkillRecord:
    """Copy a local skill directory into the central store and register it."""
    src = Path(source).expanduser().resolve()
    if not src.exists():
        raise FileNotFoundError(f"Local path does not exist: {src}")

    skill_name = src.name
    dest = config.skills_dir / skill_name

    if dest.exists():
        shutil.rmtree(dest)

    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / src.name)

    record = SkillRecord(
        name=skill_name, source=str(src), source_type="local", agents=agents
    )
    config.add_skill(record)
    return record


def install(source: str, config: Config, agents: list[str]) -> SkillRecord:
    """Route to the appropriate installer based on the source string."""
    if source.startswith("https://github.com") or source.startswith(
        "http://github.com"
    ):
        return install_from_github(source, config, agents)
    return install_from_local(source, config, agents)


def remove(skill_name: str, config: Config) -> None:
    """Delete a skill from the central store and config."""
    dest = config.skills_dir / skill_name
    if dest.exists():
        shutil.rmtree(dest)
    config.remove_skill(skill_name)
