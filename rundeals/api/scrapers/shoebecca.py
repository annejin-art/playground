from scrapers.base import BaseScraper


class ShoebeccaScraper(BaseScraper):
    scraper_name = "shoebecca"
    brand = "multiple"

    def scrape(self):
        # Site is no longer operational (redirects to parked domain).
        return []
