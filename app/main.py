"""
app/main.py — entrypoint. Creates the FastAPI app, wires the lifespan
hook (which starts/stops the background polling loop) and the routes.

Run with:
    uvicorn app.main:app --reload
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.cache import POLL_INTERVAL_SECONDS, logger, poll_warehouse_loop
from app.routes import router


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
app.include_router(router)
