"""
Fetch tool - HTTP requests.

Uses aiohttp for async HTTP operations.
"""

from typing import Optional, Dict
from .base import tool, ToolResult


@tool
async def fetch_url(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    timeout: int = 30,
) -> ToolResult:
    """
    Fetch content from a URL.

    Args:
        url: The URL to fetch
        method: HTTP method (GET, POST, PUT, DELETE)
        headers: Optional HTTP headers
        body: Optional request body for POST/PUT
        timeout: Request timeout in seconds

    Returns:
        status_code, headers, body

    Security:
        - URL allowlist/blocklist configurable
        - Timeout enforced
        - Response size limit
        - No file:// or internal IPs by default
    """
    # TODO: Implement with aiohttp
    # import aiohttp
    # async with aiohttp.ClientSession() as session:
    #     async with session.request(method, url, headers=headers, data=body, timeout=timeout) as resp:
    #         return ToolResult(success=True, data={
    #             "status_code": resp.status,
    #             "headers": dict(resp.headers),
    #             "body": await resp.text(),
    #         })

    return ToolResult(success=False, error="Not implemented")
