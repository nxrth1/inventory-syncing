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


stock_cache: dict[int, int] = {}
last_synced_at: datetime | None = None


def apply_stock_update(data: dict[int, int]) -> int:
    
    global last_synced_at
    
    
    stock_cache.update(data)
    last_synced_at = datetime.now(timezone.utc)
    logger.info(f"Stock cache updated with {len(data)} items at {last_synced_at.isoformat()}")
    
    return len(data)



