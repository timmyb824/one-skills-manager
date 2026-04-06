"""MCP server management: server definitions with multiple transport options."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_HOME = Path("~/.one-skills").expanduser()
MCP_SERVERS_FILE = DEFAULT_HOME / "mcp-servers.json"


@dataclass
class MCPTransport:
    """Represents a transport configuration for an MCP server."""

    type: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the MCPTransport to a dictionary."""
        result: dict[str, Any] = {"type": self.type}
        if self.command:
            result["command"] = self.command
        if self.args:
            result["args"] = self.args
        if self.env:
            result["env"] = self.env
        if self.url:
            result["url"] = self.url
        if self.headers:
            result["headers"] = self.headers
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCPTransport:
        """Create an MCPTransport from a dictionary."""
        return cls(
            type=data["type"],
            command=data.get("command"),
            args=data.get("args", []),
            env=data.get("env", {}),
            url=data.get("url"),
            headers=data.get("headers", {}),
        )


@dataclass
class MCPServer:
    """Represents an MCP server with multiple transport configurations."""

    name: str
    description: str
    transports: dict[str, MCPTransport] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the MCPServer to a dictionary."""
        return {
            "description": self.description,
            "transports": {
                name: transport.to_dict() for name, transport in self.transports.items()
            },
        }

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> MCPServer:
        """Create an MCPServer from a dictionary."""
        return cls(
            name=name,
            description=data["description"],
            transports={
                tname: MCPTransport.from_dict(tdata)
                for tname, tdata in data.get("transports", {}).items()
            },
        )


@dataclass
class MCPConfig:
    """Manages MCP server configurations."""

    servers: dict[str, MCPServer] = field(default_factory=dict)
    _path: Path = field(default_factory=lambda: MCP_SERVERS_FILE, repr=False)

    def save(self) -> None:
        """Save the MCP configuration to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "servers": {name: server.to_dict() for name, server in self.servers.items()}
        }
        self._path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path = MCP_SERVERS_FILE) -> MCPConfig:
        """Load the MCP configuration from disk."""
        if not path.exists():
            return cls(_path=path)
        data = json.loads(path.read_text())
        return cls(
            servers={
                name: MCPServer.from_dict(name, sdata)
                for name, sdata in data.get("servers", {}).items()
            },
            _path=path,
        )

    def add_server(self, name: str, description: str) -> MCPServer:
        """Add a new MCP server to the configuration."""
        if name in self.servers:
            raise ValueError(f"MCP server '{name}' already exists")
        server = MCPServer(name=name, description=description)
        self.servers[name] = server
        self.save()
        return server

    def remove_server(self, name: str) -> None:
        """Remove an MCP server from the configuration."""
        if name not in self.servers:
            raise ValueError(f"MCP server '{name}' does not exist")
        del self.servers[name]
        self.save()

    def add_transport(
        self, server_name: str, transport_name: str, transport: MCPTransport
    ) -> None:
        """Add a transport to an MCP server."""
        if server_name not in self.servers:
            raise ValueError(f"MCP server '{server_name}' does not exist")
        self.servers[server_name].transports[transport_name] = transport
        self.save()

    def remove_transport(self, server_name: str, transport_name: str) -> None:
        """Remove a transport from an MCP server."""
        if server_name not in self.servers:
            raise ValueError(f"MCP server '{server_name}' does not exist")
        self.servers[server_name].transports.pop(transport_name, None)
        self.save()

    def get_server_transport(
        self, server_name: str, transport_name: str
    ) -> MCPTransport:
        """Get a specific transport for an MCP server."""
        if server_name not in self.servers:
            raise ValueError(f"MCP server '{server_name}' does not exist")
        server = self.servers[server_name]
        if transport_name not in server.transports:
            raise ValueError(
                f"Transport '{transport_name}' not found for server '{server_name}'. "
                f"Available transports: {', '.join(server.transports.keys())}"
            )
        return server.transports[transport_name]

    def validate_profile_servers(self, profile_servers: dict[str, str]) -> list[str]:
        """Validate profile server assignments. Returns list of error messages."""
        errors = []
        for server_name, transport_name in profile_servers.items():
            if server_name not in self.servers:
                errors.append(f"Server '{server_name}' is not defined")
                continue
            server = self.servers[server_name]
            if transport_name not in server.transports:
                available = ", ".join(server.transports.keys())
                errors.append(
                    f"Transport '{transport_name}' not available for server '{server_name}'. "
                    f"Available: {available}"
                )
        return errors
