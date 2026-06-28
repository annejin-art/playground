from scrapers.base import BaseScraper

SALE_URL = "https://www.dickssportinggoods.com/f/running-shoes?priceTo=150"


class DicksScraper(BaseScraper):
    scraper_name = "dicks"
    brand = "multiple"

    def scrape(self):
        # JS-heavy site — requires Playwright. Not yet implemented.
        return []
