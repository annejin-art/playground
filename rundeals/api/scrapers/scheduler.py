from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import sessionmaker

from scrapers.saucony import SauconyScraper
from scrapers.brooks import BrooksScraper
from scrapers.nike import NikeScraper
from scrapers.adidas import AdidasScraper
from scrapers.asics import AsicsScraper
from scrapers.hoka import HokaScraper
from scrapers.new_balance import NewBalanceScraper
from scrapers.on_running import OnRunningScraper
from scrapers.dicks import DicksScraper
from scrapers.running_warehouse import RunningWarehouseScraper
from scrapers.marathon_sports import MarathonSportsScraper
from scrapers.heartbreak_hill import HeartbreakHillScraper
from scrapers.shoebecca import ShoebeccaScraper

ALL_SCRAPERS = [
    SauconyScraper, BrooksScraper, NikeScraper, AdidasScraper,
    AsicsScraper, HokaScraper, NewBalanceScraper, OnRunningScraper,
    DicksScraper, RunningWarehouseScraper, MarathonSportsScraper,
    HeartbreakHillScraper, ShoebeccaScraper,
]


def run_all_scrapers(session_factory: sessionmaker) -> None:
    db = session_factory()
    try:
        for cls in ALL_SCRAPERS:
            try:
                scraper = cls()
                products = scraper.scrape()
                scraper.upsert_products(db, products)
            except Exception as e:
                print(f"[scheduler] {cls.__name__} failed: {e}")
    finally:
        db.close()


def start_scheduler(session_factory: sessionmaker) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_all_scrapers,
        "interval",
        hours=6,
        args=[session_factory],
        id="scrape_all",
    )
    scheduler.add_job(
        run_all_scrapers,
        "date",
        args=[session_factory],
        id="scrape_all_startup",
        misfire_grace_time=60,
    )
    scheduler.start()
    return scheduler
