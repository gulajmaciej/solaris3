"""Simple MCP server/router for tool calls."""

from typing import Any, Callable, Dict

from mcp.context import ToolContext


class MCPServer:
    def __init__(self) -> None:
        self._read_tools: Dict[str, Callable[..., Dict[str, Any]]] = {}
        self._write_tools: Dict[str, Callable[..., Dict[str, Any]]] = {}

    def register_read_tool(self, name: str, tool: Callable[..., Dict[str, Any]]) -> None:
        self._read_tools[name] = tool

    def register_write_tool(self, name: str, tool: Callable[..., Dict[str, Any]]) -> None:
        self._write_tools[name] = tool

    def call_read(self, name: str, context: ToolContext, **kwargs: Any) -> Dict[str, Any]:
        if name not in self._read_tools:
            raise KeyError(f"Read tool not registered: {name}")
        return self._read_tools[name](context, **kwargs)

    def call_write(self, name: str, context: ToolContext, **kwargs: Any) -> Dict[str, Any]:
        if name not in self._write_tools:
            raise KeyError(f"Write tool not registered: {name}")
        return self._write_tools[name](context, **kwargs)
