"""
Nike sale running shoes scraper.
Uses Playwright. Nike's sale page renders product cards as static HTML in the initial
response (React SSR), so we can parse them without JS execution.
Only products with a visibly-reduced price (striked-out original) are included.
"""
import re

from scrapers.base import BaseScraper, extract_colors, extract_model, is_excluded

BASE = "https://www.nike.com"
# Sale + Running Shoes combined category filter
SALE_URL = f"{BASE}/w/sale-running-shoes-37v7jznik1zy7ok"


def _gender(title: str, subtitle: str = "") -> str:
    combined = (title + " " + subtitle).lower()
    if "women" in combined:
        return "Women's"
    if "men" in combined:
        return "Men's"
    return "Unisex"


def _parse_price(text: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", text)
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


class NikeScraper(BaseScraper):
    scraper_name = "nike"
    brand = "Nike"

    def scrape(self):
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup

        results = []
        seen_urls: set[str] = set()

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
            # Scroll repeatedly to trigger infinite-scroll lazy loading
            prev_count = 0
            for _ in range(15):  # up to 15 scroll iterations
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
                count = page.evaluate(
                    "() => document.querySelectorAll('[data-testid=\"product-card\"]').length"
                )
                if count == prev_count:
                    break
                prev_count = count
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select('[data-testid="product-card"]')

        for card in cards:
            # Only include cards with a reduced price (aria-label shows "current price X, original price Y")
            price_wrapper = card.select_one('[data-testid="product-card__price"]')
            if not price_wrapper:
                continue

            reduced_el = price_wrapper.select_one('[data-testid="product-price-reduced"]')
            original_el = price_wrapper.select_one('[data-testid="product-price"]')
            if not reduced_el or not original_el:
                # Not discounted
                continue

            sale_price = _parse_price(reduced_el.get_text(strip=True))
            msrp = _parse_price(original_el.get_text(strip=True))
            if sale_price <= 0 or msrp <= sale_price:
                continue

            # Title
            title_el = card.select_one('[data-testid="product-card__link-overlay"]')
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if is_excluded(title):
                continue

            # Product URL
            link_el = card.select_one('a[href*="nike.com/t/"]')
            if not link_el:
                continue
            href = link_el.get("href", "")
            product_url = href if href.startswith("http") else f"{BASE}{href}"
            if product_url in seen_urls:
                continue
            seen_urls.add(product_url)

            # Sub-title (e.g. "Men's Road Running Shoes")
            subtitle_el = card.select_one('.product-card__subtitle, [data-testid="product-card__subtitle"]')
            subtitle = subtitle_el.get_text(strip=True) if subtitle_el else ""

            # Image
            img_el = card.select_one("img[src*='nike.com']")
            image_url = img_el.get("src", "") if img_el else ""

            # Colors from colorway thumbnails
            color_alts = " ".join(
                a.get("aria-label", "") or a.get("alt", "")
                for a in card.select('[data-testid*="colorway"] img, .colorway img')
            )
            colors = extract_colors(color_alts) if color_alts else []

            gender = _gender(title, subtitle)
            model = extract_model(title, "Nike")

            # Support type heuristic from subtitle
            support = "Neutral"
            if any(k in subtitle.lower() for k in ("stability", "structure", "support")):
                support = "Stability"

            results.append({
                "seller": "Nike",
                "seller_sku": f"NIKE-{product_url.split('/')[-1]}",
                "brand": "Nike",
                "model": model,
                "full_name": f"Nike {title}" if not title.lower().startswith("nike") else title,
                "msrp": msrp,
                "sale_price": sale_price,
                "image_url": image_url,
                "product_url": product_url,
                "sizes_available": [],
                "colors_available": colors,
                "width": "Regular",
                "support_type": support,
                "gender": gender,
            })

        return results
