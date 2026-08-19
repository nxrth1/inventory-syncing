"""
main.py — a basic FastAPI inventory sync service, built to the
ORIGINAL spec: poll a warehouse API on a fixed interval, cache the
stock levels, and expose a query endpoint so another system (the
support tool) can ask "is this in stock?" and get a fast, cached
answer instead of hitting the warehouse system directly every time.

Deliberately basic: no retries, no database, no idempotency — just a
polling loop, an in-memory cache, and logging so you can see exactly
what's happening at each step.

WHERE THE PIVOT WILL HAPPEN (don't do this part yet — that's the
assignment):
poll_warehouse_loop() below is THE function a webhook makes obsolete.
Right now, this service reaches out and asks "what's the stock?"
every POLL_INTERVAL_SECONDS. After the pivot, the warehouse system
pushes updates to you the moment something changes, via a POST to an
endpoint you expose — you stop asking on a timer entirely. Everything
else here (the cache, the query endpoint, the logging setup) stays
useful either way; poll_warehouse_loop and fetch_from_warehouse are
the two things that get replaced.
"""

import asyncio
import logging
import os
import random
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

# --- Logging ----------------------------------------------------------
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


# --- The cache -----------------------------------------------------
# What the query endpoints below actually read from. This is the
# whole point of caching: a request asking "is this in stock?" never
# waits on the warehouse system directly — it just reads whatever we
# last polled, which is fast and doesn't hammer their API.
stock_cache: dict[int, int] = {}
last_synced_at: datetime | None = None

# 5 minutes per the spec, but overridable via env var so you can
# actually watch a few poll cycles happen while testing locally
# without waiting 5 minutes each time. Try:
#   POLL_INTERVAL_SECONDS=5 uvicorn main:app --reload
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI's "lifespan" runs setup code once when the app starts
    and teardown code once when it shuts down. Starting the poll loop
    here — not inside a request handler — means it runs continuously
    in the background, independent of any individual request.
    """
    logger.info(
        "Starting up. Polling every %s seconds.", POLL_INTERVAL_SECONDS
    )
    task = asyncio.create_task(poll_warehouse_loop())
    yield
    logger.info("Shutting down — cancelling the polling loop.")
    task.cancel()


app = FastAPI(title="Northstar Inventory Sync (polling version)", lifespan=lifespan)


@app.get("/")
def home():
    return {
        "message": "Inventory sync service is running",
        "last_synced_at": last_synced_at,
        "products_cached": len(stock_cache),
    }


@app.get("/stock/{product_id}")
def get_stock(product_id: int):
    """The query endpoint from the spec: "is this in stock?" —
    answered from the CACHE, not a live warehouse call.
    """
    if product_id not in stock_cache:
        logger.warning("Query for unknown product_id %s", product_id)
        raise HTTPException(status_code=404, detail="Unknown product_id")

    return {
        "product_id": product_id,
        "quantity": stock_cache[product_id],
        "last_synced_at": last_synced_at,
    }


@app.get("/stock")
def get_all_stock():
    """Handy for eyeballing the whole cache while testing."""
    return {"last_synced_at": last_synced_at, "stock": stock_cache}
