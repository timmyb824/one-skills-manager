# CHANGELOG

<!-- version list -->

## v1.9.0 (2026-05-14)

### Features

- **agents**: Add support for shared .agents target in agent management and synchronization
  ([`9abe18c`](https://github.com/timmyb824/one-skills-manager/commit/9abe18c9a06ff208c281c9f1477508261d1fcc02))

- **sync**: Prevent removal of shared symlinks when unassigning skills and rules
  ([`092e356`](https://github.com/timmyb824/one-skills-manager/commit/092e35673c5e720733427e2c3f330602f9d6ce3d))


## v1.8.1 (2026-04-17)

### Bug Fixes

- Exclude servers for agents during MCP sync
  ([`725252d`](https://github.com/timmyb824/one-skills-manager/commit/725252ddda99d3aa5ce4c1ca503ee9427a00ffa0))


## v1.8.0 (2026-04-16)

### Code Style

- Pre-commit clean up and format changes
  ([`881a4cc`](https://github.com/timmyb824/one-skills-manager/commit/881a4cc3f8cd5cc73bfce46e697687d2efc3ae41))

### Features

- Add support for path expansion when syncing mcp servers to providers
  ([`d936210`](https://github.com/timmyb824/one-skills-manager/commit/d936210c1109c13151704e3159e82970333d6954))


## v1.7.0 (2026-04-11)

### Features

- **docs**: Enhance README with new features, quick start guide, and core concepts section
  ([`444702b`](https://github.com/timmyb824/one-skills-manager/commit/444702b428ca4f4c544158269c78aafd1395ec15))


## v1.6.0 (2026-04-10)

### Features

- Add support for Codex configuration import/export
  ([`0f02c37`](https://github.com/timmyb824/one-skills-manager/commit/0f02c37b6c6fb3e54240d6dddfb0b0e4d52bb793))


## v1.5.1 (2026-04-09)

### Bug Fixes

- Simplify agent synchronization logic in CLI
  ([`d881421`](https://github.com/timmyb824/one-skills-manager/commit/d881421f3d2ea9d450d2036a295ff4aee5680214))


## v1.5.0 (2026-04-09)

### Features

- Track last synced timestamps for agents
  ([`20541b6`](https://github.com/timmyb824/one-skills-manager/commit/20541b62cc87878415cf65bc9ae993e8977ea98d))


## v1.4.4 (2026-04-09)

### Refactoring

- Enhance profile show output with agent details
  ([`a7e5f72`](https://github.com/timmyb824/one-skills-manager/commit/a7e5f7239389e4246e4827006080b7f7d75b3f34))


## v1.4.3 (2026-04-07)

### Bug Fixes

- **sync**: Ensure agent_filter syncs correctly with agents
  ([`4e5e9c9`](https://github.com/timmyb824/one-skills-manager/commit/4e5e9c9d8284b17abb0af0cd73ff6a7f089ed01f))


## v1.4.2 (2026-04-07)

### Bug Fixes

- **sync**: Consolidate agent selection logic and simplify sync flow
  ([`c0a72c5`](https://github.com/timmyb824/one-skills-manager/commit/c0a72c5ef3a9f08c6dd8069473736241ba3c34c5))


## v1.4.1 (2026-04-07)

### Chores

- **config**: Add portable path handling and ignore windsurf directory
  ([`81b07bc`](https://github.com/timmyb824/one-skills-manager/commit/81b07bca15de25d6813d6d7c69196c028458e340))


## v1.4.0 (2026-04-07)

### Features

- **cursor**: Add full support for Cursor agent import and sync
  ([`9f924df`](https://github.com/timmyb824/one-skills-manager/commit/9f924df8a1d2a0dd7d941ae37f9fcb04e7d1a38d))


## v1.3.0 (2026-04-07)

### Features

- **profile**: Add server exclusion commands for agents
  ([`9c3cd25`](https://github.com/timmyb824/one-skills-manager/commit/9c3cd256f11703a35c042876a8fea73ca4254659))


## v1.2.0 (2026-04-06)

### Features

- **profile**: Add commands to manage agents in profiles
  ([`214fac2`](https://github.com/timmyb824/one-skills-manager/commit/214fac203e69f417f4bf4920c67a64e1f0b584d3))


## v1.1.0 (2026-04-06)

### Features

- Add support for importing Claude Code and Windsurf configurations
  ([`ae860f2`](https://github.com/timmyb824/one-skills-manager/commit/ae860f23fd427615e9e4109c6cc9bde5aa00bbbb))


## v1.0.0 (2026-04-01)

- Initial Release
