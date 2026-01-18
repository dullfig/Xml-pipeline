"""Allow running as python -m reddit_sentiment."""
import asyncio
from .reddit_sentiment import main

if __name__ == "__main__":
    asyncio.run(main())
