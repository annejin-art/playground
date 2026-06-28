"""
Brooks Running sale scraper.
Uses Playwright because the site is JS-rendered (Salesforce Commerce Cloud / SFCC).
Each product tile exposes analytics data-attributes with name, SKU, price, gender, etc.
"""
from scrapers.base import BaseScraper, extract_colors, is_excluded

BASE = "https://www.brooksrunning.com"
SALE_URL = f"{BASE}/en_us/sale/"


def _gender_from_category(category: str, gender_str: str) -> str:
    combined = (category + " " + gender_str).lower()
    if "female" in combined or "women" in combined:
        return "Women's"
    if "male" in combined or "men" in combined:
        return "Men's"
    return "Unisex"


def _support_type(support_level: str) -> str:
    lvl = support_level.lower()
    if "stability" in lvl or "motion" in lvl or "support" in lvl:
        return "Stability"
    return "Neutral"


class BrooksScraper(BaseScraper):
    scraper_name = "brooks"
    brand = "Brooks"

    def scrape(self):
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup

        results = []
        seen_skus: set[str] = set()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )
            page = ctx.new_page()
            page.goto(SALE_URL, wait_until="networkidle", timeout=60000)
            # Click "Load all" to get all products, then wait for them to render
            try:
                load_all = page.query_selector(".js-load-more-products")
                if load_all:
                    load_all.click()
                    page.wait_for_timeout(5000)
                    page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                pass
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        tiles = soup.select(".js-product-tile-container")

        for tile in tiles:
            analytics = tile.select_one(".js-product-analytics-data")
            if not analytics:
                continue

            name = analytics.get("data-product-name", "").strip()
            if not name or is_excluded(name):
                continue

            sku = analytics.get("data-product-style-id", "").strip()
            if not sku or sku in seen_skus:
                continue
            seen_skus.add(sku)

            category = analytics.get("data-product-category", "")
            # Only keep shoes (skip apparel, bras, etc.)
            if "apparel" in category.lower() or "bra" in category.lower():
                continue

            # Price info
            try:
                sale_price = float(analytics.get("data-product-price", 0) or 0)
            except ValueError:
                continue
            if sale_price <= 0:
                continue

            # Original price
            price_wrapper = tile.select_one(".m-product-tile__price")
            msrp = sale_price
            if price_wrapper:
                orig_el = price_wrapper.select_one(".pricing__base, .js-list-price")
                if orig_el:
                    orig_text = orig_el.get_text(strip=True).replace("$", "").replace(",", "")
                    try:
                        msrp = float(orig_text)
                    except ValueError:
                        pass
            # If no original price different from sale, skip (not actually on sale)
            if msrp <= sale_price:
                continue

            # Image
            img_el = tile.select_one("img[src]")
            image_url = img_el["src"] if img_el else ""

            # URL
            nav_url = analytics.get("data-navigation-url", "")
            product_url = nav_url if nav_url.startswith("http") else f"{BASE}{nav_url}"

            # Color
            color_name = analytics.get("data-product-color-name", "")
            colors = extract_colors(color_name) if color_name else []

            # Size — not available at list level, leave empty
            sizes: list[str] = []

            gender = _gender_from_category(category, analytics.get("data-product-gender", ""))
            support = _support_type(analytics.get("data-product-shoe-support-level", ""))
            width = analytics.get("data-product-width", "Regular") or "Regular"
            if width in ("D", "2E", "4E"):
                width = "Wide"
            elif width in ("B", "2A"):
                width = "Narrow"
            else:
                width = "Regular"

            results.append({
                "seller": "Brooks Running",
                "seller_sku": f"BROOKS-{sku}",
                "brand": "Brooks",
                "model": name,
                "full_name": f"Brooks {name}",
                "msrp": msrp,
                "sale_price": sale_price,
                "image_url": image_url,
                "product_url": product_url,
                "sizes_available": sizes,
                "colors_available": colors,
                "width": width,
                "support_type": support,
                "gender": gender,
            })

        return results
