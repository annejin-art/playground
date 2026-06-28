import re
import json
from scrapers.base import BaseScraper, get_soup, is_excluded, extract_model, extract_colors

SALE_URL = "https://www.saucony.com/en/sale/"


class SauconyScraper(BaseScraper):
    scraper_name = "saucony"
    brand = "Saucony"

    def scrape(self):
        soup = get_soup(SALE_URL)
        tiles = soup.select(".product-tile")
        results = []
        for tile in tiles:
            try:
                attrs = json.loads(tile.get("data-product-attributes", "{}"))

                name_el = tile.select_one(".product-name")
                if not name_el:
                    continue
                name = name_el.get_text(strip=True)
                if is_excluded(name):
                    continue

                url_el = tile.select_one('a[href*="/en/"]')
                if not url_el:
                    continue
                product_url = url_el["href"]
                if not product_url.startswith("http"):
                    product_url = "https://www.saucony.com" + product_url

                sale_el = tile.select_one(".product-sales-price")
                orig_el = tile.select_one(".product-standard-price")
                if not sale_el or not orig_el:
                    continue

                sale_price = float(re.sub(r"[^\d.]", "", sale_el.get_text()))
                msrp = float(re.sub(r"[^\d.]", "", orig_el.get_text()))
                if sale_price <= 0 or msrp <= 0 or sale_price >= msrp:
                    continue

                img_el = tile.select_one('img[src*="wolverine"], img[src*="thekit"], img[src*="saucony"]')
                image_url = img_el["src"] if img_el else ""

                sku = tile.get("data-itemid", "")
                classification = attrs.get("classification", "Neutral")
                support_type = "Stability" if "stability" in classification.lower() else "Neutral"

                model = extract_model(name, "Saucony")

                # Determine gender from name
                lower = name.lower()
                gender = "Women's" if "women" in lower or " w " in lower else "Men's"

                colors = extract_colors(attrs.get("genericColor", "") or attrs.get("color", ""))

                results.append({
                    "seller": "Saucony",
                    "seller_sku": sku,
                    "brand": "Saucony",
                    "model": model,
                    "full_name": name,
                    "msrp": msrp,
                    "sale_price": sale_price,
                    "image_url": image_url,
                    "product_url": product_url,
                    "sizes_available": [],
                    "colors_available": colors,
                    "width": "Regular",
                    "support_type": support_type,
                    "gender": gender,
                })
            except Exception:
                continue
        return results
