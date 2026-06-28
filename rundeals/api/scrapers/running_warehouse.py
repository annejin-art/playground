import re
from scrapers.base import BaseScraper, get_soup, is_excluded, extract_model, extract_colors

MENS_URL = "https://www.runningwarehouse.com/catpage-SALEMS.html"
WOMENS_URL = "https://www.runningwarehouse.com/catpage-SALEWA.html"


def _parse_price(text: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", text)
    return float(cleaned) if cleaned else 0.0


def _support_type(name: str) -> str:
    lower = name.lower()
    if "stability" in lower or "adrenaline" in lower or "kayano" in lower or "guide" in lower:
        return "Stability"
    if "motion" in lower:
        return "Motion Control"
    return "Neutral"


def _extract_colorway(full_name: str) -> str:
    """Extract colorway from product name after 'Men's/Women's Shoes' suffix."""
    m = re.search(r"(?:Men'?s?|Women'?s?|Unisex)\s+Shoes?\s+(.*)", full_name, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _scrape_page(url: str, gender: str) -> list[dict]:
    soup = get_soup(url)
    results = []

    for cell in soup.select(".cattable-wrap-cell.gtm_impression"):
        try:
            full_name = cell.get("data-gtm_impression_name", "")
            brand = cell.get("data-gtm_impression_brand", "")
            sku = cell.get("data-code", "")
            if not full_name or not brand or not sku:
                continue

            if is_excluded(full_name):
                continue

            sale_price = float(cell.get("data-gtm_impression_price", 0) or 0)
            if sale_price <= 0:
                continue

            msrp_el = cell.select_one(".cattable-wrap-cell-info-price-msrp .is-crossout")
            if not msrp_el:
                continue
            msrp = _parse_price(msrp_el.get_text())
            if msrp <= 0 or sale_price >= msrp:
                continue

            url_el = cell.select_one("a.cattable-wrap-cell-imgwrap-inner")
            product_url = url_el["href"].strip() if url_el else ""
            if product_url and not product_url.startswith("http"):
                product_url = "https://www.runningwarehouse.com" + product_url

            img_el = cell.select_one("img.cattable-wrap-cell-imgwrap-inner-img")
            image_url = img_el.get("src", "") if img_el else ""

            model = extract_model(full_name, brand)
            colorway = _extract_colorway(full_name)
            colors = extract_colors(colorway) if colorway else []

            results.append({
                "seller": "Running Warehouse",
                "seller_sku": sku,
                "brand": brand.title(),
                "model": model,
                "full_name": full_name,
                "msrp": msrp,
                "sale_price": sale_price,
                "image_url": image_url,
                "product_url": product_url,
                "sizes_available": [],
                "colors_available": colors,
                "width": "Regular",
                "support_type": _support_type(full_name),
                "gender": gender,
            })
        except Exception:
            continue

    return results


class RunningWarehouseScraper(BaseScraper):
    scraper_name = "running_warehouse"
    brand = "multiple"

    def scrape(self):
        results = _scrape_page(MENS_URL, "Men's")
        results += _scrape_page(WOMENS_URL, "Women's")
        return results
