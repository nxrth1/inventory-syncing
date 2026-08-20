"""
app/routes.py — the query endpoints from the spec: "is this in stock?"
answered from the CACHE, not a live warehouse call.

Imports the `cache` module itself (not individual names out of it) so
that reads like `cache.last_synced_at` always see the current value —
see the note in cache.py for why that distinction matters.
"""


from fastapi import APIRouter, HTTPException

from app import cache
from app.schemas import Stock_Update_item
from app.cache import apply_stock_update
router = APIRouter()


@router.get("/")
def home():
    return {
        "message": "Inventory sync service is running",
        "last_synced_at": cache.last_synced_at,
        "products_cached": len(cache.stock_cache),
    }


@router.get("/stock/{product_id}")
def get_stock(product_id: int):
    """The query endpoint from the spec: "is this in stock?" —
    answered from the CACHE, not a live warehouse call.
    """
    if product_id not in cache.stock_cache:
        cache.logger.warning("Query for unknown product_id %s", product_id)
        raise HTTPException(status_code=404, detail="Unknown product_id")

    return {
        "product_id": product_id,
        "quantity": cache.stock_cache[product_id],
        "last_synced_at": cache.last_synced_at,
    }


@router.get("/stock")
def get_all_stock():
    """Handy for eyeballing the whole cache while testing."""
    return {"last_synced_at": cache.last_synced_at, "stock": cache.stock_cache}


@router.post("/webhook/stock-update")
def receive_stock_update(payload: list[Stock_Update_item]):
    """The webhook endpoint from the spec: "the warehouse will call this
    endpoint to notify us of stock changes." It updates the CACHE, not
    the warehouse.
    """
    data = {item.product_id: item.quantity for item in payload}
    count = cache.apply_stock_update(data)
    return {
        "message": "Stock update received",
        "products_updated": count,
        "last_synced_at": cache.last_synced_at,
    }