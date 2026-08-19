"""
app/cache.py — the simulated warehouse call, the in-memory cache, and
the background polling loop that keeps the cache warm.
"""

import logging
from datetime import datetime, timezone

# --- Logging ------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("inventory_sync")


# --- The cache ------------------------------------------------------
# What the query endpoints in routes.py actually read from.
#
# NOTE on last_synced_at: routes.py must import the `cache` MODULE and
# read `cache.last_synced_at` off of it at request time — not do
# `from app.cache import last_synced_at`. A `from x import y` binds a
# name to whatever value `y` held at import time; when this module
# later does `last_synced_at = ...` inside apply_stock_update, that
# rebinds cache.py's own module-level name, but routes.py's separate
# copy of the name never gets touched, so it would freeze at whatever
# it was (typically None) forever. stock_cache doesn't have this
# problem because it's never reassigned — it's a dict that gets
# mutated in place with .update(), so every module holding a reference
# to it sees the same underlying object change.

stock_cache: dict[int, int] = {}
last_synced_at: datetime | None = None


def apply_stock_update(data: dict[int, int]) -> int:
    
    """
    Applies a warehouse-pushed update to the cache.

    Replaces fetch_from_warehouse() + the body of poll_warehouse_loop().
    Called from the webhook route in routes.py whenever a POST comes
    in, instead of being driven by a timer.

    `data` is expected to already be a {product_id: quantity} dict —
    routes.py is responsible for turning the raw webhook payload into
    that shape before calling this.

    Returns the number of products updated, so the webhook route can
    report it back in the response.
    """
    
    global last_synced_at
    
    
    stock_cache.update(data)
    last_synced_at = datetime.now(timezone.utc)
    logger.info(f"Stock cache updated with {len(data)} items at {last_synced_at.isoformat()}")
    
    return len(data)



