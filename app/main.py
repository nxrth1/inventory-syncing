"""
app/main.py — entrypoint. Creates the FastAPI app, wires the lifespan
hook (which starts/stops the background polling loop) and the routes.

Run with:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.cache import logger
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info(
        "starting up. Waiting for webhook pushes at /webhook/stock-update." 
    )
    yield
    logger.info("Shutting down ")



app = FastAPI(title="Northstar Inventory Sync (webhook version)", lifespan=lifespan)
app.include_router(router)
