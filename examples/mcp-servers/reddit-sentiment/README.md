# Reddit Sentiment MCP Server

An MCP server that provides Reddit sentiment analysis for stock tickers.

## Installation

```bash
cd examples/mcp-servers/reddit-sentiment
pip install -e .
```

## Usage with Claude Code

Add to your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "reddit-sentiment": {
      "command": "python",
      "args": ["-m", "reddit_sentiment"],
      "cwd": "/path/to/reddit-sentiment"
    }
  }
}
```

## Tools

### reddit_trending_tickers

Get the most mentioned stock tickers across Reddit finance subreddits.

```
Trending tickers from r/wallstreetbets, r/stocks, r/investing
```

### reddit_ticker_sentiment

Get sentiment analysis for a specific ticker.

```
What's the Reddit sentiment on $TSLA?
```

### reddit_wsb_summary

Get a summary of current WallStreetBets activity.

```
What's happening on WSB right now?
```

## How It Works

1. Fetches posts from Reddit's public JSON API (no auth required)
2. Extracts ticker symbols using regex ($TSLA, TSLA, etc.)
3. Analyzes sentiment using bullish/bearish word matching
4. Returns structured JSON with mentions, scores, and sentiment

## Limitations

- Reddit rate limits (~60 requests/minute without auth)
- Simple word-based sentiment (no ML)
- Only scans post titles and selftext (not comments)
- Ticker extraction may have false positives

## Subreddits Scanned

- r/wallstreetbets
- r/stocks
- r/investing
- r/options
- r/stockmarket
- r/thetagang
- r/smallstreetbets
