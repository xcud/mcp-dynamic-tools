"""
MCP Dynamic Tools - A dynamic MCP server for automatic tool discovery

Drop Python files in a directory, and they instantly become available as MCP tools
to any compatible AI client.

Created through collaboration between Ben Wilson and Claude (Anthropic).
"""

from .server import DynamicMCPServer

__version__ = "0.1.0"
__author__ = "Ben Wilson and Claude (Anthropic)"

__all__ = ["DynamicMCPServer"]
