from scrapers.base import BaseScraper

SALE_URL = "https://www.on-running.com/en-us/outlet"


class OnRunningScraper(BaseScraper):
    scraper_name = "on_running"
    brand = "On"

    def scrape(self):
        # JS-heavy site — requires Playwright. Not yet implemented.
        return []
