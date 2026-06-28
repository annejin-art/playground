from scrapers.base import BaseScraper

SALE_URL = "https://www.marathonsports.com/collections/sale"


class MarathonSportsScraper(BaseScraper):
    scraper_name = "marathon_sports"
    brand = "multiple"

    def scrape(self):
        # Shopify store but JSON API endpoints are disabled; page requires JS to render.
        return []
