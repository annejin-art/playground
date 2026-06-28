from scrapers.base import BaseScraper

SALE_URL = "https://www.asics.com/us/en-us/sale/"


class AsicsScraper(BaseScraper):
    scraper_name = "asics"
    brand = "ASICS"

    def scrape(self):
        # JS-heavy site — requires Playwright. Not yet implemented.
        return []
