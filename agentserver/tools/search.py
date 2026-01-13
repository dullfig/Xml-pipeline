"""
Search tool - web search.
"""

from .base import tool, ToolResult


@tool
async def web_search(
    query: str,
    num_results: int = 5,
) -> ToolResult:
    """
    Search the web.

    Args:
        query: Search query
        num_results: Number of results (default: 5, max: 20)

    Returns:
        Array of {title, url, snippet}

    Implementation options:
        - SerpAPI
        - Google Custom Search
        - Bing Search API
        - DuckDuckGo (scraping)
    """
    # TODO: Implement with search provider
    # Options:
    # 1. SerpAPI (paid, reliable)
    # 2. Google Custom Search API (limited free tier)
    # 3. Bing Search API (Azure)
    # 4. DuckDuckGo scraping (free, fragile)

    return ToolResult(success=False, error="Not implemented - configure search provider")
