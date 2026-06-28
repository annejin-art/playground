from scrapers.base import BaseScraper

SALE_URL = "https://www.brooksrunning.com/en_us/sale/"


class BrooksScraper(BaseScraper):
    scraper_name = "brooks"
    brand = "Brooks"

    def scrape(self):
        # JS-heavy site — requires Playwright. Not yet implemented.
        return []
