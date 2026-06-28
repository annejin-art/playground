from scrapers.base import BaseScraper

SALE_URL = "https://www.nike.com/w/sale-running-shoes-3yaepznik1zy7ok"


class NikeScraper(BaseScraper):
    scraper_name = "nike"
    brand = "Nike"

    def scrape(self):
        # JS-heavy site — requires Playwright. Not yet implemented.
        return []
