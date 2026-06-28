from scrapers.base import BaseScraper

SALE_URL = "https://www.hoka.com/en-us/sale/"


class HokaScraper(BaseScraper):
    scraper_name = "hoka"
    brand = "Hoka"

    def scrape(self):
        # JS-heavy site — requires Playwright. Not yet implemented.
        return []
