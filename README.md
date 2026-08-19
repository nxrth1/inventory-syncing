# Northstar Inventory Sync — Polling Version (Day 3 spec)

A basic FastAPI service matching the original spec: poll a warehouse
API every 5 minutes, cache the stock levels, and expose a query
endpoint. One file, logging throughout, no database, no retries — just
enough to see the polling pattern clearly before you pivot it.

## Run it

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

For local testing, override the poll interval so you don't have to
wait 5 minutes to see it work:
```bash
POLL_INTERVAL_SECONDS=5 uvicorn main:app --reload
```

## Endpoints

- `GET /` — health check, shows when the cache last synced.
- `GET /stock` — the whole cache.
- `GET /stock/{product_id}` — one product's cached quantity, `404` if unknown.

## About the pivot (Assignment 2)

This deliberately stops at the Day 3 deliverable. `poll_warehouse_loop()`
and `fetch_from_warehouse()` in `main.py` are marked in comments as the
two things Day 4 kills — that part's the graded exercise (Assignment 2:
Mid-Sprint Change Log & Refactored Deliverable, plus the Scope Delta
Analysis), so it's yours to do. Roughly, you'll be:

1. Adding a `POST /webhook/stock-update` endpoint that receives a push
   from the warehouse instead of you polling for it.
2. Removing (or clearly deprecating, per the non-negotiable rules —
   not leaving it running in parallel) `poll_warehouse_loop`,
   `fetch_from_warehouse`, and the lifespan hook that starts the loop.
3. Deciding what your Scope Delta Analysis actually says: what did you
   drop (the interval/schedule logic, "freshness" guarantees between
   polls), what did you add (whatever validation/idempotency a push
   endpoint needs that a pull loop didn't), what stayed the same (the
   cache and query endpoints — worth noting that explicitly, since
   "what didn't have to change" is as informative as what did).

Happy to talk through concepts, review what you build, or answer
questions about *why* something's failing once you're mid-pivot — just
didn't want to build the actual pivot for you, since that's the part
being graded.
