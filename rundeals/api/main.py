from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import create_tables, SessionLocal
from routes.deals import router as deals_router
from routes.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch(headless=True).close()
    except Exception:
        pass

    from scrapers.scheduler import start_scheduler
    scheduler = start_scheduler(SessionLocal)

    yield

    scheduler.shutdown(wait=False)


app = FastAPI(title="RunDeals API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deals_router)
app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok"}
