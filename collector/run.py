"""
Run the collector once: fetch messages from all channels in DB.
Usage:
  python -m collector.run [limit_per_channel]
Example:
  python -m collector.run 500
"""
import asyncio
import sys

from collector.fetcher import run_once


def main() -> None:
    limit = 200
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    asyncio.run(run_once(limit_per_channel=limit))


if __name__ == "__main__":
    main()
