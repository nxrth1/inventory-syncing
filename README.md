# Northstar Inventory Sync — polling version

A basic FastAPI inventory sync service, built to the ORIGINAL spec:
poll a warehouse API on a fixed interval, cache the stock levels, and
expose a query endpoint so another system (the support tool) can ask
"is this in stock?" and get a fast, cached answer instead of hitting
the warehouse system directly every time.

Deliberately basic: no retries, no database, no idempotency — just a
polling loop, an in-memory cache, and logging so you can see exactly
what's happening at each step.

## Structure

```
app/
  __init__.py
  cache.py    # simulated warehouse call, in-memory cache, polling loop
  routes.py   # the query endpoints (/, /stock, /stock/{product_id})
  main.py     # entrypoint: creates the app, wires lifespan + routes
requirements.txt
```

Split by responsibility instead of one file: `cache.py` owns the
state and the background loop, `routes.py` only reads that state to
answer requests, and `main.py` just assembles the two. Makes each
piece independently readable and testable, and makes the Day 4 pivot
cleaner — that day only touches `cache.py`, `routes.py` and `main.py`
are untouched.

## Run it

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Poll interval defaults to 5 minutes per the spec. Override it to
actually watch a few cycles happen while testing locally:

```
POLL_INTERVAL_SECONDS=5 uvicorn app.main:app --reload
```

## Endpoints

- `GET /` — health check, shows `last_synced_at` and how many
  products are cached.
- `GET /stock/{product_id}` — cached stock for one product. 404 if
  the product_id has never been polled.
- `GET /stock` — the whole cache, handy for eyeballing while testing.

## A bug worth knowing about

`routes.py` reads state via `from app import cache` and then
`cache.last_synced_at` / `cache.stock_cache` at request time — it
does **not** do `from app.cache import last_synced_at`.

The reason: `from x import y` binds a name to whatever value `y` held
at the moment of import. `stock_cache` is safe either way because
it's a dict that only ever gets *mutated* in place (`.update(...)`),
so every module holding a reference to it sees the same object
change. `last_synced_at` is different — `poll_warehouse_loop()`
*reassigns* it on every cycle (`last_synced_at = datetime.now(...)`),
which only rebinds `cache.py`'s own module-level name. A separate
`from app.cache import last_synced_at` in `routes.py` would keep
pointing at whatever value existed at import time (typically `None`)
and would never see an update — the endpoint would report
`last_synced_at: null` forever, even after hundreds of successful
poll cycles.

## Where the pivot will happen (Day 4 — don't do this yet)

`poll_warehouse_loop()` in `app/cache.py` is the function a webhook
makes obsolete. Right now, this service reaches out and asks "what's
the stock?" every `POLL_INTERVAL_SECONDS`. After the pivot, the
warehouse system pushes updates the moment something changes, via a
POST to an endpoint you expose — you stop asking on a timer entirely.
Everything else (the cache, the query endpoints, the logging) stays
useful either way; `poll_warehouse_loop` and `fetch_from_warehouse`
are the two things that get replaced.
