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

- 📦 **Skills** - Install once, symlink everywhere
- 📝 **Rules** - Manage custom rules/memories across agents
- 🔌 **MCP Servers** - Configure Model Context Protocol servers
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

```bash
# Import your existing Cursor configuration
one-skills import cursor --dry-run # inspect what would be imported
one-skills import cursor

# Create a profile
one-skills profile create work

# Add agents to your profile
one-skills profile add-agent cursor --profile work
one-skills profile add-agent windsurf --profile work

# Activate the profile
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
# Install from GitHub
one-skills skill install https://github.com/owner/repo/tree/main/skill-name

# Install from local path
one-skills skill install ~/my-skills/skill-name

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
# Register an existing rule file
one-skills rule register my-rule.md cursor,windsurf

# Copy a rule from another location
one-skills rule copy ~/rules/my-rule.md my-rule.md cursor

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

```bash
# Add an MCP server with stdio transport
one-skills mcp add-server my-server stdio \
  --command npx \
  --args "-y" "my-mcp-server"

# Add an MCP server with SSE transport
one-skills mcp add-server my-server sse \
  --url https://example.com/mcp

# List all MCP servers
one-skills mcp list

# Add server to a profile
one-skills profile add-server my-server default --profile personal

# Override transport for a specific agent
one-skills profile set-override cursor my-server docker --profile personal

# Exclude a server from an agent
one-skills profile exclude-server cursor my-server --profile personal

# Remove a server
one-skills mcp remove-server my-server
```

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
# List supported agents
one-skills agents

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
5. **Sync Tracking**: Each agent tracks when it was last synced (visible in `profile show`)

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
