# one-skills-manager

```
   ___               ___ _   _ _ _        __  __
  / _ \ _ _  ___ ___/ __| |_(_) | |______|  \/  |__ _ _ _  __ _ __ _ ___ _ _
 | (_) | ' \/ -_)___\__ \ / / | | (_-<___| |\/| / _` | ' \/ _` / _` / -_) '_|
  \___/|_||_\___|   |___/_\_\_|_|_/__/   |_|  |_\__,_|_||_\__,_\__, \___|_|
                                                               |___/
```

Manage and sync AI agent skills, rules, and MCP servers across Claude Code, Cursor, Windsurf, Codex, and shared `.agents` targets from a single central store.

**Features:**

- 🧭 **Interactive Mode** - Guided menu-driven UI for all common workflows
- 📊 **Status Dashboard** - See exactly what's in sync at a glance
- 📦 **Skills** - Install once, symlink everywhere
- 📝 **Rules** - Manage custom rules/memories across agents
- 🔌 **MCP Servers** - Configure Model Context Protocol servers with guided wizard
- 👤 **Profiles** - Different configurations for work, personal, etc.
- 📥 **Import** - Import existing configs from any agent
- 🔄 **Sync Tracking** - Know when each agent was last synced

## Installation

```bash
pip install one-skills-manager
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install one-skills-manager
```

## Quick Start

The easiest way to get started is the interactive mode — just run the command with no arguments:

```bash
one-skills
```

This launches a guided menu for every common workflow. Or use the direct commands:

```bash
# Check what's installed and in sync
one-skills status

# Import your existing Cursor configuration
one-skills import cursor --dry-run  # inspect what would be imported
one-skills import cursor

# Create a profile and add agents
one-skills profile create work
one-skills profile add-agent cursor --profile work
one-skills profile add-agent windsurf --profile work
one-skills profile activate work

# Sync everything to your active profile's agents
one-skills sync
```

## Core Concepts

### Profiles

Profiles let you maintain different configurations for different contexts (work, personal, etc.). Each profile can:

- Enable specific agents
- Configure which MCP servers are available
- Override MCP server transports per agent
- Exclude specific MCP servers per agent

### Central Storage

Everything is stored once in `~/.one-skills/`:

- **Skills**: `~/.one-skills/skills/<skill-name>/`
- **Rules**: `~/.one-skills/rules/<rule-name>`
- **MCP Servers**: `~/.one-skills/mcp.json`
- **Profiles**: `~/.one-skills/profiles.json`

When you sync, symlinks are created from each agent's directory to the central store.

## Usage

### Interactive Mode

Run `one-skills` with no arguments (or `one-skills ui`) to launch the interactive guided menu:

```bash
one-skills      # launch interactive mode
one-skills ui   # explicit alias
```

The menu provides guided flows for:

- **Status** — dashboard of everything installed and synced
- **Add skill** — install from URL or local path, then choose agents interactively
- **Add rule** — install a rule file, then choose agents interactively
- **Add MCP server** — step-by-step wizard (transport type, package, env vars, profile assignment)
- **Manage profile** — add/remove agents and MCP servers from a profile
- **Sync** — choose scope (all/skills/rules/MCP) and agents, with optional dry-run

### Status

See the full state of your installation at a glance:

```bash
one-skills status
```

Output includes:

- Active profile, enabled agents, and last synced time
- Each skill with per-agent symlink status (`✓` synced, `○` not linked, `✗` broken)
- Each rule with per-agent status (including `☁` for cloud-based Cursor rules)
- MCP servers with profile assignment and available transports

Exits with code **1** if anything is out of sync — useful as a `chezmoi` post-apply hook.

### Import Existing Configuration

Import from an existing agent installation:

```bash
# Preview what would be imported
one-skills import cursor --dry-run

# Import skills, rules, and MCP servers
one-skills import cursor
one-skills import windsurf
one-skills import codex
one-skills import claude-code
```

### Profile Management

```bash
# Create a new profile
one-skills profile create personal

# List all profiles
one-skills profile list

# Show profile details
one-skills profile show personal

# Activate a profile
one-skills profile activate personal

# Add an agent to a profile
one-skills profile add-agent cursor --profile personal

# Remove an agent from a profile
one-skills profile remove-agent cursor --profile personal

# Delete a profile
one-skills profile delete personal
```

### Skills

```bash
# Install from GitHub — prompts to choose agents interactively when run in a terminal
one-skills skill install https://github.com/owner/repo/tree/main/skill-name

# Install from local path
one-skills skill install ~/my-skills/skill-name

# Install and assign to specific agents (non-interactive / scripting)
one-skills skill install https://github.com/owner/repo/tree/main/skill-name --agents cursor,windsurf

# Install without assigning (skip the prompt)
one-skills skill install ~/my-skills/skill-name --no-assign

# List all skills
one-skills list

# Assign to agents
one-skills skill assign skill-name cursor,windsurf

# Unassign from agents
one-skills skill unassign skill-name cursor

# Remove a skill
one-skills skill remove skill-name
```

### Rules

```bash
# Install a rule — prompts to choose agents interactively when run in a terminal
one-skills rule install ~/rules/my-rule.md

# Install and assign to specific agents (non-interactive / scripting)
one-skills rule install ~/rules/my-rule.md --agents claude-code,codex

# Install without assigning (skip the prompt)
one-skills rule install ~/rules/my-rule.md --no-assign

# List all rules
one-skills rule list

# Assign to agents
one-skills rule assign my-rule.md cursor

# Unassign from agents
one-skills rule unassign my-rule.md cursor

# Remove a rule
one-skills rule remove my-rule.md
```

### MCP Servers

The easiest way to add a server is the guided wizard, which walks through transport type, package/URL, env vars, and profile assignment in one flow:

```bash
# Interactive wizard (prompts for all details)
one-skills mcp add-server my-server

# Non-interactive shortcuts for scripting
one-skills mcp add-server my-server --npx @modelcontextprotocol/server-github
one-skills mcp add-server my-server --uvx mcp-server-git --description "Git MCP"
one-skills mcp add-server my-server --sse https://example.com/sse
one-skills mcp add-server my-server --http https://example.com/mcp

# Optionally assign to a profile in the same command
one-skills mcp add-server my-server --npx my-pkg --profile personal
```

Other MCP commands:

```bash
# List all MCP servers
one-skills mcp list

# Show details for a server
one-skills mcp show my-server

# Add server to a profile (after creation)
one-skills profile add-server my-server default --profile personal

# Override transport for a specific agent
one-skills profile set-override cursor my-server docker --profile personal

# Exclude a server from an agent
one-skills profile exclude-server cursor my-server --profile personal

# Remove a server
one-skills mcp remove my-server
```

> **Low-level commands**: `one-skills mcp add` and `one-skills mcp add-transport` are still available for scripted/advanced use.

### Sync

Sync skills, rules, and MCP servers to agents in your active profile:

```bash
# Sync everything
one-skills sync

# Dry-run to preview changes
one-skills sync --dry-run

# Sync only to a specific agent
one-skills sync --agent cursor

# Sync only skills
one-skills sync --skills-only

# Sync only rules
one-skills sync --rules-only

# Sync only MCP servers
one-skills sync --mcp-only
```

### Other Commands

```bash
# Show sync status dashboard
one-skills status

# Launch interactive guided mode
one-skills ui

# List supported agents
one-skills agents

# List all installed resources
one-skills list

# Show version
one-skills --version
```

## Supported Agents

| ID            | Name           | Skills                       | Rules                          | MCP Config                            |
| ------------- | -------------- | ---------------------------- | ------------------------------ | ------------------------------------- |
| `claude-code` | Claude Code    | `~/.claude/skills`           | `~/.claude/rules`              | `~/.claude.json`                      |
| `cursor`      | Cursor         | `~/.cursor/skills`           | Cloud-based                    | `~/.cursor/mcp.json`                  |
| `windsurf`    | Windsurf       | `~/.codeium/windsurf/skills` | `~/.codeium/windsurf/memories` | `~/.codeium/windsurf/mcp_config.json` |
| `codex`       | Codex          | `~/.agents/skills`           | `~/.codex/rules`               | `~/.codex/config.toml`                |
| `shared`      | Shared .agents | `~/.agents/skills`           | `~/.agents/rules`              | _Not synced_                          |

`shared` is a sync target for shared skills/rules only. MCP sync is intentionally skipped for this agent.

## MCP Server Transports

MCP servers can use different transport mechanisms:

- **stdio**: Local process (command + args + env)
- **sse**: Server-Sent Events (url + headers)
- **http**: HTTP (url + headers)

You can define multiple transports for the same server and override which transport each agent uses via profiles.

## Example Workflow

```bash
# 1. Import your existing Cursor setup
one-skills import cursor

# 2. Create work and personal profiles
one-skills profile create work
one-skills profile create personal

# 3. Configure work profile
one-skills profile activate work
one-skills profile add-agent cursor --profile work
one-skills profile add-agent windsurf --profile work

# Add work-specific MCP servers to profile
one-skills profile add-server github-mcp-server default --profile work
one-skills profile add-server jira-server default --profile work

# 4. Configure personal profile
one-skills profile activate personal
one-skills profile add-agent claude-code --profile personal
one-skills profile add-agent codex --profile personal

# Exclude work servers from personal profile
one-skills profile exclude-server claude-code jira-server --profile personal

# 5. Sync to active profile
one-skills sync

# 6. Switch contexts
one-skills profile activate work
one-skills sync
```

## How It Works

1. **Central Storage**: Skills, rules, and MCP configs are stored once in `~/.one-skills/`
2. **Profiles**: Define which agents and MCP servers are active for different contexts
3. **Symlinks**: Skills and rules are symlinked from central storage to each agent's directory
4. **MCP Rendering**: MCP configs are rendered per-agent based on profile settings
5. **Sync Tracking**: Each agent tracks when it was last synced (visible in `profile show` and `status`)
6. **Interactive Mode**: `one-skills` (no args) launches a guided menu for all common workflows
7. **Status Dashboard**: `one-skills status` shows symlink health and profile assignments; exits 1 if out of sync (useful for `chezmoi` hooks)

## Configuration Files

All configuration is stored in `~/.one-skills/`:

- `config.json` - Skills and rules registry
- `mcp.json` - MCP servers and transports
- `profiles.json` - Profile configurations
- `skills/` - Skill directories
- `rules/` - Rule files

Paths are stored using `~/` for portability across machines.

## License

MIT
