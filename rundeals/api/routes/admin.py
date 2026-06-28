from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db, ScrapeRun, Product

router = APIRouter()

SCRAPER_NAMES = [
    "saucony", "brooks", "nike", "adidas", "asics", "hoka",
    "new_balance", "on_running", "dicks", "running_warehouse",
    "marathon_sports", "heartbreak_hill", "shoebecca",
]


def _get_scraper(name: str):
    import importlib
    try:
        mod = importlib.import_module(f"scrapers.{name}")
        cls_map = {
            "saucony": "SauconyScraper",
            "brooks": "BrooksScraper",
            "nike": "NikeScraper",
            "adidas": "AdidasScraper",
            "asics": "AsicsScraper",
            "hoka": "HokaScraper",
            "new_balance": "NewBalanceScraper",
            "on_running": "OnRunningScraper",
            "dicks": "DicksScraper",
            "running_warehouse": "RunningWarehouseScraper",
            "marathon_sports": "MarathonSportsScraper",
            "heartbreak_hill": "HeartbreakHillScraper",
            "shoebecca": "ShoebeccaScraper",
        }
        cls = getattr(mod, cls_map[name])
        return cls()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _run_scraper_task(name: str):
    from database import SessionLocal
    db = SessionLocal()
    try:
        scraper = _get_scraper(name)
        products = scraper.scrape()
        scraper.upsert_products(db, products)
    finally:
        db.close()


@router.get("/api/admin/scrapers")
def list_scrapers(db: Session = Depends(get_db)):
    result = []
    for name in SCRAPER_NAMES:
        last_run = (
            db.query(ScrapeRun)
            .filter(ScrapeRun.scraper_name == name)
            .order_by(desc(ScrapeRun.started_at))
            .first()
        )
        result.append({
            "name": name,
            "last_run": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
            "status": last_run.status if last_run else "never",
            "items_found": last_run.items_found if last_run else None,
            "error_message": last_run.error_message if last_run else None,
        })
    return result


@router.post("/api/admin/scrapers/{name}/run")
def run_scraper(name: str, background_tasks: BackgroundTasks):
    if name not in SCRAPER_NAMES:
        raise HTTPException(status_code=404, detail=f"Scraper '{name}' not found")
    background_tasks.add_task(_run_scraper_task, name)
    return {"status": "triggered", "scraper": name}


@router.post("/api/admin/scrapers/run-all")
def run_all_scrapers(background_tasks: BackgroundTasks):
    for name in SCRAPER_NAMES:
        background_tasks.add_task(_run_scraper_task, name)
    return {"status": "triggered", "scrapers": SCRAPER_NAMES}


@router.get("/api/admin/runs")
def get_runs(db: Session = Depends(get_db)):
    runs = (
        db.query(ScrapeRun)
        .order_by(desc(ScrapeRun.started_at))
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "scraper_name": r.scraper_name,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "items_found": r.items_found,
            "error_message": r.error_message,
        }
        for r in runs
    ]


@router.delete("/api/admin/products/stale")
def delete_stale_products(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(hours=48)
    deleted = db.query(Product).filter(Product.last_scraped_at < cutoff).delete()
    db.commit()
    return {"deleted": deleted}
