from scrapers.base import BaseScraper

SALE_URL = "https://www.adidas.com/us/sale/running"


class AdidasScraper(BaseScraper):
    scraper_name = "adidas"
    brand = "Adidas"

    def scrape(self):
        # JS-heavy site — requires Playwright. Not yet implemented.
        return []
