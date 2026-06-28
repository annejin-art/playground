"""
Marathon Sports sale scraper.
Uses Playwright because the Shopify JSON API is disabled for this store.
Products are rendered in .product-partial divs at /shop?sale=1&page=N.
"""
import json
import re

from scrapers.base import BaseScraper, extract_colors, extract_model, is_excluded

BASE = "https://www.marathonsports.com"
SALE_URL = f"{BASE}/shop?sale=1"


def _gender(title: str, alt_text: str = "") -> str:
    combined = (title + " " + alt_text).lower()
    if "women" in combined or "woman" in combined:
        return "Women's"
    if "men" in combined or "man" in combined:
        return "Men's"
    return "Unisex"


class MarathonSportsScraper(BaseScraper):
    scraper_name = "marathon_sports"
    brand = "multiple"

    def scrape(self):
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup

        results = []
        seen_slugs: set[str] = set()

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

            page_num = 1
            while True:
                url = f"{SALE_URL}&page={page_num}"
                page = ctx.new_page()
                page.goto(url, wait_until="networkidle", timeout=60000)
                html = page.content()
                page.close()

                soup = BeautifulSoup(html, "html.parser")
                products = soup.select(".product-partial")
                if not products:
                    break

                for prod in products:
                    # DL item has name, price, brand, variant ID
                    dl_raw = prod.get("dl-item", "{}")
                    try:
                        dl = json.loads(dl_raw)
                    except (json.JSONDecodeError, TypeError):
                        dl = {}

                    title = dl.get("item_name", "").strip()
                    if not title:
                        title_el = prod.select_one(".title a, h2 a")
                        title = title_el.get_text(strip=True) if title_el else ""
                    if not title:
                        continue
                    if is_excluded(title):
                        continue

                    # Slug (unique per product group)
                    link_el = prod.select_one("a[href*='/products/']")
                    if not link_el:
                        continue
                    href = link_el.get("href", "")
                    slug = href.rstrip("/").split("/products/")[-1]
                    if slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)

                    product_url = href if href.startswith("http") else f"{BASE}{href}"

                    # Prices
                    price_el = prod.select_one(".product-price")
                    sale_price = 0.0
                    msrp = 0.0
                    if price_el:
                        current = price_el.select_one(".-price")
                        compare = price_el.select_one(".-compare")
                        if current:
                            try:
                                sale_price = float(
                                    re.sub(r"[^\d.]", "", current.get_text(strip=True))
                                )
                            except ValueError:
                                pass
                        if compare:
                            try:
                                msrp = float(
                                    re.sub(r"[^\d.]", "", compare.get_text(strip=True))
                                )
                            except ValueError:
                                pass

                    if sale_price <= 0:
                        try:
                            sale_price = float(dl.get("price", 0) or 0)
                        except (ValueError, TypeError):
                            pass
                    if msrp <= 0:
                        msrp = sale_price
                    if sale_price <= 0:
                        continue
                    # Only include discounted items
                    if msrp <= sale_price:
                        continue

                    # Image
                    img_el = prod.select_one(".image img")
                    image_url = img_el.get("src", "") if img_el else ""

                    # Brand
                    brand_raw = (dl.get("item_brand") or "").strip()
                    brand = brand_raw.title() if brand_raw else "Unknown"

                    # Colors via thumb alt texts
                    color_texts = " ".join(
                        t.get("alt", "") for t in prod.select(".thumb img")
                    )
                    colors = extract_colors(color_texts)

                    gender = _gender(title, color_texts)
                    model = extract_model(title, brand)

                    results.append({
                        "seller": "Marathon Sports",
                        "seller_sku": f"MS-{slug}",
                        "brand": brand,
                        "model": model,
                        "full_name": title,
                        "msrp": msrp,
                        "sale_price": sale_price,
                        "image_url": image_url,
                        "product_url": product_url,
                        "sizes_available": [],
                        "colors_available": colors,
                        "width": "Regular",
                        "support_type": "Neutral",
                        "gender": gender,
                    })

                # Check for next page
                next_link = soup.select_one("a.next, a[rel='next']")
                if not next_link:
                    break
                page_num += 1
                if page_num > 20:  # safety cap
                    break

            browser.close()

        return results
