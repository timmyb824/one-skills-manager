# one-skills-manager

Install and sync AI agent skills across Claude Code, Cursor, Windsurf, and Codex from a single central store.

Skills are stored once in `~/.one-skills/skills/` and symlinked into each agent's expected directory. No duplication, no drift.

## Installation

```bash
pip install one-skills-manager
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install one-skills-manager
```

## Usage

### Install a skill

From a GitHub directory URL:

```bash
one-skills install https://github.com/owner/repo/tree/main/my-skill --agents claude-code
```

From a local path:

```bash
one-skills install ~/my-skills/my-skill --agents claude-code,cursor
```

Omit `--agents` to install without syncing yet.

### List installed skills

```bash
one-skills list
```

### Assign a skill to an agent

```bash
one-skills assign my-skill claude-code
```

### Unassign a skill from an agent

```bash
one-skills unassign my-skill cursor
```

### Sync skills

Sync everything:

```bash
one-skills sync
```

Sync a single skill:

```bash
one-skills sync --skill my-skill
```

Sync to a specific agent only:

```bash
one-skills sync --agent claude-code
```

### List supported agents

```bash
one-skills agents
```

### Remove a skill

```bash
one-skills remove my-skill
```

Removes the skill from the central store and deletes all symlinks.

## Supported agents

| ID | Name | Skills directory |
|----|------|-----------------|
| `claude-code` | Claude Code | `~/.claude/skills` |
| `cursor` | Cursor | `~/.cursor/skills` |
| `windsurf` | Windsurf | `~/.codeium/windsurf/skills/` |
| `codex` | OpenAI Codex | `~/.codex/skills` |

## How it works

Skills are stored centrally in `~/.one-skills/skills/<skill-name>/`. When you assign a skill to an agent, `one-skills` creates a symlink from the agent's skills directory to that central copy. Running `sync` recreates any missing or outdated symlinks.

## License

MIT
