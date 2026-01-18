"""
Reddit Sentiment MCP Server

Provides tools for analyzing Reddit sentiment around stock tickers.
"""

import asyncio
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP not installed. Run: pip install mcp")
    exit(1)

FINANCE_SUBREDDITS = [
    "wallstreetbets", "stocks", "investing", "options",
    "stockmarket", "thetagang", "smallstreetbets",
]

TICKER_PATTERN = re.compile(r'\$?([A-Z]{2,5})\b')

TICKER_BLACKLIST = {
    "I", "A", "THE", "FOR", "AND", "BUT", "NOT", "YOU", "ALL",
    "CAN", "HAD", "HER", "WAS", "ONE", "OUR", "OUT", "ARE", "HAS",
    "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "WAY",
    "WHO", "BOY", "DID", "GET", "HIM", "LET", "PUT", "SAY", "SHE",
    "TOO", "USE", "CEO", "USD", "USA", "ETF", "IPO", "GDP", "FBI",
    "SEC", "FDA", "NYSE", "IMO", "YOLO", "FOMO", "HODL", "TLDR",
    "LOL", "WTF", "FYI", "EDIT", "POST", "JUST", "LIKE", "THIS",
    "THAT", "WITH", "FROM", "HAVE", "BEEN", "MORE", "WHEN", "WILL",
}

BULLISH_WORDS = {
    "moon", "rocket", "bull", "calls", "long", "buy", "buying",
    "pump", "tendies", "gains", "profit", "up", "green", "bullish",
    "squeeze", "breakout", "diamond", "hands", "hold", "holding",
}

BEARISH_WORDS = {
    "puts", "short", "sell", "selling", "dump", "crash", "bear",
    "down", "red", "bearish", "loss", "losses", "overvalued",
    "bubble", "drop", "tank", "drill", "bag", "bagholder", "rip",
}


@dataclass
class RedditPost:
    title: str
    score: int
    num_comments: int
    created_utc: float
    subreddit: str
    selftext: str = ""
    url: str = ""


async def fetch_subreddit(subreddit: str, sort: str = "hot", limit: int = 25):
    if not aiohttp:
        raise RuntimeError("aiohttp not installed")
    
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    headers = {"User-Agent": "reddit-sentiment-mcp/1.0"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
    
    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        posts.append(RedditPost(
            title=d.get("title", ""),
            score=d.get("score", 0),
            num_comments=d.get("num_comments", 0),
            created_utc=d.get("created_utc", 0),
            subreddit=d.get("subreddit", subreddit),
            selftext=d.get("selftext", ""),
            url=f"https://reddit.com{d.get('permalink', '')}",
        ))
    return posts


def extract_tickers(text):
    matches = TICKER_PATTERN.findall(text.upper())
    return [m for m in matches if m not in TICKER_BLACKLIST and len(m) >= 2]


def analyze_sentiment(text):
    words = set(text.lower().split())
    return len(words & BULLISH_WORDS), len(words & BEARISH_WORDS)


server = Server("reddit-sentiment")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="reddit_trending_tickers",
            description="Get trending stock tickers from Reddit finance subreddits",
            inputSchema={
                "type": "object",
                "properties": {
                    "subreddits": {"type": "array", "items": {"type": "string"}},
                    "limit": {"type": "integer", "description": "Posts per sub (max 100)"},
                },
            },
        ),
        Tool(
            name="reddit_ticker_sentiment",
            description="Get Reddit sentiment for a specific stock ticker",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "e.g. TSLA, GME"},
                },
                "required": ["ticker"],
            },
        ),
        Tool(
            name="reddit_wsb_summary",
            description="Get WallStreetBets current activity summary",
            inputSchema={
                "type": "object",
                "properties": {
                    "sort": {"type": "string", "enum": ["hot", "new", "top"]},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "reddit_trending_tickers":
        return await trending_tickers(arguments)
    elif name == "reddit_ticker_sentiment":
        return await ticker_sentiment(arguments)
    elif name == "reddit_wsb_summary":
        return await wsb_summary(arguments)
    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def trending_tickers(args):
    subs = args.get("subreddits", ["wallstreetbets", "stocks", "investing"])
    limit = min(args.get("limit", 25), 100)
    
    counts, scores = Counter(), Counter()
    for sub in subs:
        try:
            for post in await fetch_subreddit(sub, "hot", limit):
                for t in extract_tickers(f"{post.title} {post.selftext}"):
                    counts[t] += 1
                    scores[t] += post.score
        except Exception:
            pass
    
    result = {
        "subreddits": subs,
        "trending": [
            {"ticker": t, "mentions": c, "total_score": scores[t]}
            for t, c in counts.most_common(20)
        ],
        "timestamp": datetime.utcnow().isoformat(),
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def ticker_sentiment(args):
    ticker = args.get("ticker", "").upper().replace("$", "")
    if not ticker:
        return [TextContent(type="text", text="Error: ticker required")]
    
    mentions, bull, bear = [], 0, 0
    for sub in FINANCE_SUBREDDITS:
        try:
            for post in await fetch_subreddit(sub, "hot", 50):
                text = f"{post.title} {post.selftext}"
                if ticker in extract_tickers(text):
                    b, br = analyze_sentiment(text)
                    bull += b
                    bear += br
                    mentions.append({
                        "sub": post.subreddit, "title": post.title[:80],
                        "score": post.score, "url": post.url,
                    })
        except Exception:
            pass
    
    score = (bull - bear) / max(bull + bear, 1)
    result = {
        "ticker": ticker,
        "mentions": len(mentions),
        "sentiment": "bullish" if score > 0.2 else ("bearish" if score < -0.2 else "neutral"),
        "score": round(score, 2),
        "bullish": bull, "bearish": bear,
        "posts": mentions[:10],
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def wsb_summary(args):
    sort = args.get("sort", "hot")
    posts = await fetch_subreddit("wallstreetbets", sort, 50)
    
    counts, bull, bear = Counter(), 0, 0
    hot = []
    for post in posts:
        text = f"{post.title} {post.selftext}"
        for t in extract_tickers(text):
            counts[t] += 1
        b, br = analyze_sentiment(text)
        bull += b
        bear += br
        if post.score > 100:
            hot.append({"title": post.title[:60], "score": post.score})
    
    result = {
        "top_tickers": [{"ticker": t, "mentions": c} for t, c in counts.most_common(10)],
        "mood": "bullish" if bull > bear else "bearish",
        "hot_posts": hot[:5],
    }
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write)

if __name__ == "__main__":
    asyncio.run(main())
