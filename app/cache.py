"""
app/cache.py — the simulated warehouse call, the in-memory cache, and
the background polling loop that keeps the cache warm.

WHERE THE PIVOT WILL HAPPEN (don't do this part yet — that's the
assignment):
poll_warehouse_loop() below is THE function a webhook makes obsolete.
Right now, this service reaches out and asks "what's the stock?"
every POLL_INTERVAL_SECONDS. After the pivot, the warehouse system
pushes updates to you the moment something changes, via a POST to an
endpoint you expose — you stop asking on a timer entirely. Everything
else here (the cache dict, the logging) stays useful either way;
poll_warehouse_loop and fetch_from_warehouse are the two things that
get replaced.
"""

import asyncio
import logging
import os
import random
from datetime import datetime, timezone

# --- Logging ------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("inventory_sync")


# --- Simulated warehouse system -----------------------------------
# Stands in for Northstar's real warehouse API, which you don't have
# access to. In a real integration this would be an HTTP call, e.g.:
#
#     import httpx
#     response = httpx.get("https://warehouse.example.com/api/stock")
#     response.raise_for_status()
#     return response.json()
#
# Here it just returns made-up numbers, with a little randomness so
# you can actually see the cache change between poll cycles when
# testing.
def fetch_from_warehouse() -> dict[int, int]:
    logger.info("Calling warehouse API...")
    data = {
        101: random.randint(0, 50),
        102: random.randint(0, 50),
        103: random.randint(0, 50),
    }
    logger.info("Warehouse API responded with %s product(s)", len(data))
    return data


# --- The cache ------------------------------------------------------
# What the query endpoints in routes.py actually read from. This is
# the whole point of caching: a request asking "is this in stock?"
# never waits on the warehouse system directly — it just reads
# whatever we last polled, which is fast and doesn't hammer their API.
#
# NOTE on last_synced_at: routes.py must import the `cache` MODULE and
# read `cache.last_synced_at` off of it at request time — not do
# `from app.cache import last_synced_at`. A `from x import y` binds a
# name to whatever value `y` held at import time; when this module
# later does `last_synced_at = ...` inside poll_warehouse_loop, that
# rebinds cache.py's own module-level name, but routes.py's separate
# copy of the name never gets touched, so it would freeze at whatever
# it was (typically None) forever. stock_cache doesn't have this
# problem because it's never reassigned — it's a dict that gets
# mutated in place with .update(), so every module holding a reference
# to it sees the same underlying object change.
stock_cache: dict[int, int] = {}
last_synced_at: datetime | None = None

# 5 minutes per the spec, but overridable via env var so you can
# actually watch a few poll cycles happen while testing locally
# without waiting 5 minutes each time. Try:
#   POLL_INTERVAL_SECONDS=5 uvicorn app.main:app --reload
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", str(5 * 60)))


async def poll_warehouse_loop() -> None:
    """Runs forever in the background, polling on a fixed interval.
    This is the function Day 4 kills.
    """
    global last_synced_at
    while True:
        try:
            data = fetch_from_warehouse()
            stock_cache.update(data)
            last_synced_at = datetime.now(timezone.utc)
            logger.info("Cache updated. Current stock: %s", stock_cache)
        except Exception:
            # A more mature version would distinguish a retryable
            # failure (network blip — try again next cycle, which
            # this already effectively does) from a permanent one
            # (bad credentials — alert someone, don't just keep
            # quietly failing every 5 minutes). Kept simple here.
            logger.exception("Poll cycle failed; will try again next interval.")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
