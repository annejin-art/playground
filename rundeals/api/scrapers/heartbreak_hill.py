from scrapers.base import BaseScraper, get_json, is_running_shoe, extract_model, extract_colors

BASE = "https://heartbreak.run"


def _support_type(tags: list[str]) -> str:
    lower = [t.lower() for t in tags]
    if any("stability" in t or "motion control" in t for t in lower):
        return "Stability"
    return "Neutral"


def _gender(tags: list[str], title: str) -> str:
    lower = title.lower() + " " + " ".join(t.lower() for t in tags)
    if "women" in lower:
        return "Women's"
    if "men" in lower:
        return "Men's"
    return "Unisex"


def _option_index(options: list[dict], *names: str) -> int:
    """Return 0-based index of the option whose name matches any of the given names."""
    for i, opt in enumerate(options):
        if opt.get("name", "").lower() in {n.lower() for n in names}:
            return i
    return -1


class HeartbreakHillScraper(BaseScraper):
    scraper_name = "heartbreak_hill"
    brand = "multiple"

    def scrape(self):
        results = []
        page = 1
        while True:
            data = get_json(f"{BASE}/collections/sale/products.json?limit=250&page={page}")
            products = data.get("products", [])
            if not products:
                break

            for p in products:
                title = p.get("title", "")
                tags = p.get("tags", [])
                if not is_running_shoe(title, p.get("product_type", ""), tags):
                    continue

                variants = p.get("variants", [])
                options = p.get("options", [])

                # Determine which option position holds size vs color
                size_idx = _option_index(options, "size", "us size")
                color_idx = _option_index(options, "color", "colour", "style", "colorway")
                # Fallback: first numeric-looking option is size
                if size_idx == -1:
                    for i, opt in enumerate(options):
                        vals = opt.get("values", [])
                        if vals and vals[0][:1].isdigit():
                            size_idx = i
                            break
                if color_idx == -1:
                    color_idx = 0 if size_idx != 0 else 1

                opt_keys = ["option1", "option2", "option3"]

                sale_variants = [
                    v for v in variants
                    if v.get("compare_at_price") and float(v["compare_at_price"]) > float(v["price"])
                ]
                if not sale_variants:
                    continue

                sizes = sorted({
                    v.get(opt_keys[size_idx], "")
                    for v in sale_variants
                    if v.get("available") and v.get(opt_keys[size_idx] if size_idx < 3 else "option2", "")
                })
                sizes = [s for s in sizes if s and s[0].isdigit()]

                colorways = {
                    v.get(opt_keys[color_idx], "")
                    for v in sale_variants
                    if color_idx < 3 and v.get(opt_keys[color_idx])
                }
                colors = sorted({c for cw in colorways for c in extract_colors(cw)} )

                v = sale_variants[0]
                sale_price = float(v["price"])
                msrp = float(v["compare_at_price"])
                if sale_price <= 0 or msrp <= 0:
                    continue

                image_url = p["images"][0].get("src", "") if p.get("images") else ""
                handle = p.get("handle", "")
                vendor = p.get("vendor", "")

                results.append({
                    "seller": "Heartbreak Hill RC",
                    "seller_sku": f"HBHRC-{handle}",
                    "brand": vendor,
                    "model": extract_model(title, vendor),
                    "full_name": title,
                    "msrp": msrp,
                    "sale_price": sale_price,
                    "image_url": image_url,
                    "product_url": f"{BASE}/products/{handle}",
                    "sizes_available": sizes,
                    "colors_available": colors,
                    "width": "Regular",
                    "support_type": _support_type(tags),
                    "gender": _gender(tags, title),
                })

            if len(products) < 250:
                break
            page += 1

        return results
