"""Profile management: machine-specific configurations with MCP server assignments."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_HOME = Path("~/.one-skills").expanduser()
PROFILES_FILE = DEFAULT_HOME / "profiles.json"


@dataclass
class AgentConfig:
    """Configuration for an AI agent in a profile."""

    enabled: bool = True
    mcp_scope: str = "local"

    def to_dict(self) -> dict[str, Any]:
        """Convert the AgentConfig to a dictionary."""
        return {
            "enabled": self.enabled,
            "mcp_scope": self.mcp_scope,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentConfig:
        """Create an AgentConfig from a dictionary."""
        return cls(
            enabled=data.get("enabled", True),
            mcp_scope=data.get("mcp_scope", "local"),
        )


@dataclass
class Profile:
    """Represents a machine-specific profile with MCP server assignments.

    Agent overrides allow specifying different transports for specific agents
    when they don't support the default transport for a server.

    Agent exclusions allow excluding specific servers from specific agents
    (e.g., when an agent has a built-in version of that server).
    """

    name: str
    mcp_servers: dict[str, str] = field(default_factory=dict)
    agents: dict[str, AgentConfig] = field(default_factory=dict)
    agent_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    agent_exclusions: dict[str, list[str]] = field(default_factory=dict)

    def is_server_excluded(self, server_name: str, agent_id: str) -> bool:
        """Check if a server is excluded for a specific agent.

        Args:
            server_name: Name of the MCP server
            agent_id: ID of the agent

        Returns:
            True if server is excluded for this agent
        """
        if agent_id in self.agent_exclusions:
            return server_name in self.agent_exclusions[agent_id]
        return False

    def get_transport_for_agent(self, server_name: str, agent_id: str) -> str | None:
        """Get the transport for a server, checking exclusions and overrides.

        Args:
            server_name: Name of the MCP server
            agent_id: ID of the agent

        Returns:
            Transport name, or None if server not in profile or excluded
        """
        # Check if server is excluded for this agent
        if self.is_server_excluded(server_name, agent_id):
            return None

        # Check agent-specific override first
        if (
            agent_id in self.agent_overrides
            and server_name in self.agent_overrides[agent_id]
        ):
            return self.agent_overrides[agent_id][server_name]

        # Fall back to default transport
        return self.mcp_servers.get(server_name)

    def to_dict(self) -> dict[str, Any]:
        """Convert the Profile to a dictionary."""
        data = {
            "name": self.name,
            "mcp_servers": self.mcp_servers,
            "agents": {aid: cfg.to_dict() for aid, cfg in self.agents.items()},
        }
        # Only include agent_overrides if not empty
        if self.agent_overrides:
            data["agent_overrides"] = self.agent_overrides
        # Only include agent_exclusions if not empty
        if self.agent_exclusions:
            data["agent_exclusions"] = self.agent_exclusions
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Profile:
        """Create a Profile from a dictionary."""
        return cls(
            name=data["name"],
            mcp_servers=data.get("mcp_servers", {}),
            agents={
                aid: AgentConfig.from_dict(cfg)
                for aid, cfg in data.get("agents", {}).items()
            },
            agent_overrides=data.get("agent_overrides", {}),
            agent_exclusions=data.get("agent_exclusions", {}),
        )


@dataclass
class ProfileConfig:
    """Configuration for profile management."""

    active_profile: str | None = None
    profiles: dict[str, Profile] = field(default_factory=dict)
    _path: Path = field(default_factory=lambda: PROFILES_FILE, repr=False)

    def save(self) -> None:
        """Save the profile configuration to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "active_profile": self.active_profile,
            "profiles": {name: prof.to_dict() for name, prof in self.profiles.items()},
        }
        self._path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path = PROFILES_FILE) -> ProfileConfig:
        """Load the profile configuration from disk."""
        if not path.exists():
            return cls(_path=path)
        data = json.loads(path.read_text())
        return cls(
            active_profile=data.get("active_profile"),
            profiles={
                name: Profile.from_dict(prof)
                for name, prof in data.get("profiles", {}).items()
            },
            _path=path,
        )

    def get_active_profile(self) -> Profile | None:
        """Get the currently active profile."""
        if self.active_profile and self.active_profile in self.profiles:
            return self.profiles[self.active_profile]
        return None

    def set_active_profile(self, name: str) -> None:
        """Set the active profile."""
        if name not in self.profiles:
            raise ValueError(f"Profile '{name}' does not exist")
        self.active_profile = name
        self.save()

    def create_profile(self, name: str) -> Profile:
        """Create a new profile."""
        if name in self.profiles:
            raise ValueError(f"Profile '{name}' already exists")
        profile = Profile(name=name)
        self.profiles[name] = profile
        if not self.active_profile:
            self.active_profile = name
        self.save()
        return profile

    def delete_profile(self, name: str) -> None:
        """Delete a profile."""
        if name not in self.profiles:
            raise ValueError(f"Profile '{name}' does not exist")
        del self.profiles[name]
        if self.active_profile == name:
            self.active_profile = next(iter(self.profiles.keys()), None)
        self.save()

    def add_server_to_profile(
        self, profile_name: str, server_name: str, transport_name: str
    ) -> None:
        """Add an MCP server to a profile."""
        if profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' does not exist")
        self.profiles[profile_name].mcp_servers[server_name] = transport_name
        self.save()

    def remove_server_from_profile(self, profile_name: str, server_name: str) -> None:
        """Remove an MCP server from a profile."""
        if profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' does not exist")
        self.profiles[profile_name].mcp_servers.pop(server_name, None)
        self.save()

    def add_agent_to_profile(
        self, profile_name: str, agent_id: str, config: AgentConfig | None = None
    ) -> None:
        """Add an agent to a profile."""
        if profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' does not exist")
        self.profiles[profile_name].agents[agent_id] = config or AgentConfig()
        self.save()

    def set_agent_override(
        self,
        profile_name: str,
        agent_id: str,
        server_name: str,
        transport_name: str,
    ) -> None:
        """Set an agent-specific transport override for a server.

        Args:
            profile_name: Name of the profile
            agent_id: ID of the agent
            server_name: Name of the MCP server
            transport_name: Transport to use for this agent
        """
        if profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' does not exist")

        profile = self.profiles[profile_name]

        # Ensure agent_overrides dict exists for this agent
        if agent_id not in profile.agent_overrides:
            profile.agent_overrides[agent_id] = {}

        profile.agent_overrides[agent_id][server_name] = transport_name
        self.save()

    def remove_agent_override(
        self, profile_name: str, agent_id: str, server_name: str
    ) -> None:
        """Remove an agent-specific transport override.

        Args:
            profile_name: Name of the profile
            agent_id: ID of the agent
            server_name: Name of the MCP server
        """
        if profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' does not exist")

        profile = self.profiles[profile_name]

        if agent_id in profile.agent_overrides:
            profile.agent_overrides[agent_id].pop(server_name, None)
            # Clean up empty agent override dicts
            if not profile.agent_overrides[agent_id]:
                del profile.agent_overrides[agent_id]

        self.save()

    def exclude_server_from_agent(
        self, profile_name: str, agent_id: str, server_name: str
    ) -> None:
        """Exclude a server from a specific agent.

        Args:
            profile_name: Name of the profile
            agent_id: ID of the agent
            server_name: Name of the MCP server to exclude
        """
        if profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' does not exist")

        profile = self.profiles[profile_name]

        # Ensure agent_exclusions list exists for this agent
        if agent_id not in profile.agent_exclusions:
            profile.agent_exclusions[agent_id] = []

        # Add server to exclusion list if not already there
        if server_name not in profile.agent_exclusions[agent_id]:
            profile.agent_exclusions[agent_id].append(server_name)

        self.save()

    def include_server_for_agent(
        self, profile_name: str, agent_id: str, server_name: str
    ) -> None:
        """Remove a server exclusion for a specific agent.

        Args:
            profile_name: Name of the profile
            agent_id: ID of the agent
            server_name: Name of the MCP server to include
        """
        if profile_name not in self.profiles:
            raise ValueError(f"Profile '{profile_name}' does not exist")

        profile = self.profiles[profile_name]

        if agent_id in profile.agent_exclusions:
            if server_name in profile.agent_exclusions[agent_id]:
                profile.agent_exclusions[agent_id].remove(server_name)
            # Clean up empty agent exclusion lists
            if not profile.agent_exclusions[agent_id]:
                del profile.agent_exclusions[agent_id]

        self.save()
