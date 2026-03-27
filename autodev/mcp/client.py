from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.tools import StructuredTool
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import Field, create_model

from autodev.config import ServerConfig


@dataclass
class MCPToolSpec:
    server_name: str
    tool_name: str
    description: str
    input_schema: dict[str, Any]
    caller: Callable[[dict[str, Any]], str]


@dataclass
class MCPServerStatus:
    server_name: str
    connected: bool
    tool_count: int
    error: str | None = None


class MCPClient:
    """Stdio MCP client that dynamically loads tools from configured servers."""

    def __init__(self, servers: list[ServerConfig]) -> None:
        self.servers = servers
        self._tool_specs: list[MCPToolSpec] = []
        self._server_statuses: list[MCPServerStatus] = []

    @staticmethod
    def _server_env(server: ServerConfig) -> dict[str, str] | None:
        if not server.env:
            return None
        merged = dict(os.environ)
        merged.update(server.env)
        return merged

    async def _list_tools_async(self, server: ServerConfig):
        params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=self._server_env(server),
            cwd=None,
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await session.list_tools()

    async def _call_tool_async(self, server: ServerConfig, tool_name: str, args: dict[str, Any]) -> str:
        params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=self._server_env(server),
            cwd=None,
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
        chunks = []
        for part in getattr(result, "content", []) or []:
            text = getattr(part, "text", None)
            if text:
                chunks.append(text)
        return "\n".join(chunks) if chunks else str(result)

    @staticmethod
    def _run(coro):
        return asyncio.run(coro)

    @staticmethod
    def _json_schema_type(schema: dict[str, Any]):
        schema_type = schema.get("type")
        if schema_type == "integer":
            return int
        if schema_type == "number":
            return float
        if schema_type == "boolean":
            return bool
        if schema_type == "array":
            return list
        if schema_type == "object":
            return dict
        return str

    def connect(self) -> None:
        self._tool_specs.clear()
        self._server_statuses.clear()
        for server in self.servers:
            try:
                list_result = self._run(self._list_tools_async(server))
            except Exception as exc:  # noqa: BLE001
                self._server_statuses.append(
                    MCPServerStatus(
                        server_name=server.name,
                        connected=False,
                        tool_count=0,
                        error=str(exc),
                    )
                )
                # Keep running even if one server is unavailable.
                self._tool_specs.append(
                    MCPToolSpec(
                        server_name=server.name,
                        tool_name="server_unavailable",
                        description=f"MCP server {server.name} unavailable: {exc}",
                        input_schema={"type": "object", "properties": {}},
                        caller=lambda _args, e=exc: f"Server unavailable: {e}",
                    )
                )
                continue

            listed_tools = getattr(list_result, "tools", [])
            self._server_statuses.append(
                MCPServerStatus(
                    server_name=server.name,
                    connected=True,
                    tool_count=len(listed_tools),
                )
            )
            for tool in listed_tools:
                input_schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
                tool_name = getattr(tool, "name", "unknown_tool")
                description = getattr(tool, "description", "") or "MCP tool"

                def _caller(args: dict[str, Any], s=server, n=tool_name):
                    return self._run(self._call_tool_async(s, n, args))

                self._tool_specs.append(
                    MCPToolSpec(
                        server_name=server.name,
                        tool_name=tool_name,
                        description=description,
                        input_schema=input_schema,
                        caller=_caller,
                    )
                )

    def dynamic_tools(self) -> list[StructuredTool]:
        tools: list[StructuredTool] = []
        for spec in self._tool_specs:
            properties = spec.input_schema.get("properties", {})
            required = set(spec.input_schema.get("required", []))
            fields: dict[str, tuple[Any, Any]] = {}
            for field_name, field_schema in properties.items():
                if field_name in required:
                    default = ...
                elif "default" in field_schema:
                    default = field_schema["default"]
                else:
                    default = None
                fields[field_name] = (
                    self._json_schema_type(field_schema),
                    Field(default=default, description=field_schema.get("description", "")),
                )
            schema_model = create_model(f"{spec.server_name}_{spec.tool_name}_Input", **fields)

            def _make_func(caller: Callable[[dict[str, Any]], str]):
                def _func(**kwargs):
                    cleaned = {k: v for k, v in kwargs.items() if v is not None}
                    return caller(cleaned)

                return _func

            tools.append(
                StructuredTool.from_function(
                    func=_make_func(spec.caller),
                    name=f"{spec.server_name}__{spec.tool_name}",
                    description=spec.description,
                    args_schema=schema_model,
                )
            )
        return tools

    def connection_statuses(self) -> list[MCPServerStatus]:
        return list(self._server_statuses)
