"""
Native tools for agents.

Tools are sandboxed, permission-controlled functions that agents can invoke
to interact with the outside world.
"""

from .base import Tool, ToolResult, tool, get_tool_registry
from .calculate import calculate
from .fetch import fetch_url
from .files import read_file, write_file, list_dir
from .shell import run_command
from .search import web_search
from .keyvalue import key_value_get, key_value_set, key_value_delete
from .librarian import librarian_store, librarian_get, librarian_query, librarian_search

__all__ = [
    # Base
    "Tool",
    "ToolResult",
    "tool",
    "get_tool_registry",
    # Tools
    "calculate",
    "fetch_url",
    "read_file",
    "write_file",
    "list_dir",
    "run_command",
    "web_search",
    "key_value_get",
    "key_value_set",
    "key_value_delete",
    "librarian_store",
    "librarian_get",
    "librarian_query",
    "librarian_search",
]
