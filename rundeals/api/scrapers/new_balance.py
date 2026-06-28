from scrapers.base import BaseScraper

SALE_URL = "https://www.newbalance.com/on/sale/"


class NewBalanceScraper(BaseScraper):
    scraper_name = "new_balance"
    brand = "New Balance"

    def scrape(self):
        # JS-heavy site — requires Playwright. Not yet implemented.
        return []
