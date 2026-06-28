from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
import re as _re
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from database import Product, PriceHistory, ScrapeRun


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def get_json(url: str) -> Any:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


_COMMON_COLORS = {
    "black", "white", "blue", "red", "green", "yellow", "orange", "purple",
    "pink", "grey", "gray", "silver", "gold", "brown", "navy", "teal",
    "coral", "cream", "beige", "tan", "mint", "violet", "indigo", "rose",
    "carbon", "bone", "fog", "stone", "sage", "lime", "aqua", "cyan",
    "maroon", "olive", "smoke", "slate", "iron", "ash", "sand", "rust",
    "cobalt", "copper", "platinum", "crimson", "ivory", "khaki", "lavender",
}
_COLOR_NORMALIZE = {"grey": "Gray", "gray": "Gray", "navy": "Navy Blue"}


def extract_colors(colorway: str) -> list[str]:
    """Return sorted list of recognized basic colors from a colorway string."""
    found = set()
    for word in _re.findall(r"[a-zA-Z]+", colorway):
        w = word.lower()
        if w in _COMMON_COLORS:
            found.add(_COLOR_NORMALIZE.get(w, w.capitalize()))
    return sorted(found)


_APPAREL = {
    # Tops
    "tights", "tight", "shirt", "tee", "t-shirt", "top", "jacket", "vest",
    "bra", "hoodie", "fleece", "polo", "legging", "singlet", "tank",
    "sleeve", "thermal", "turtleneck", "windbreaker", "pullover", "sweatshirt",
    "half zip", "quarter zip", "full zip", "mock neck", " zip",
    # Bottoms
    "shorts", "short", "pants", "pant",
    # Accessories / headwear
    "sock", "socks", "hat", "cap", "glove", "bag", "insole", "lace",
    "mask", "headwear", "balaclava", "buff", "gaiter", "beanie", "headband", "visor", "strapback",
    # Non-running footwear
    "sandal", "flip flop", "slipper", "clog", "slide",
    # Electronics / gadgets
    "watch", "smartwatch", "headphone", "earbud", "earphone",
    # Misc non-shoe products
    "freshener", "deodorizer", "nutrition",
    # Known non-shoe brands carried by multi-brand running stores
    "shokz", "shoks", "garmin", "oofos", "vuori", "huggle", "zensah", "smellwell", "rabbit",
}
_SPIKES  = {"spike", "spikes", "cleat", "cleats", "xc shoe", "cross country shoe"}
_SHOE    = {"shoe", "shoes", "sneaker", "trainer", "boot", "footwear"}
_RUNNING = {"running", "road", "trail", "marathon", "run"}


def is_excluded(title: str) -> bool:
    """True if the product is clearly not a running shoe (apparel, spikes, accessories)."""
    lower = title.lower()
    return any(t in lower for t in _APPAREL) or any(t in lower for t in _SPIKES)


def is_running_shoe(title: str, product_type: str = "", tags: list[str] | None = None) -> bool:
    """Full check: must be a shoe AND running-related AND not excluded.
    Use for general-purpose stores (Heartbreak Hill) that sell apparel alongside shoes."""
    combined = (title + " " + product_type + " " + " ".join(tags or [])).lower()
    if any(t in combined for t in _APPAREL):
        return False
    if any(t in combined for t in _SPIKES):
        return False
    return any(t in combined for t in _SHOE) and any(t in combined for t in _RUNNING)


def extract_model(title: str, brand: str) -> str:
    m = title.strip()
    if m.lower().startswith(brand.lower()):
        m = m[len(brand):].strip()
    # Strip leading gender prefix (e.g. "Men's Hurricane 25" → "Hurricane 25")
    m = _re.sub(r"^(Men'?s?|Women'?s?|Unisex|Men|Women)\s+", "", m, flags=_re.IGNORECASE).strip()
    # Strip trailing gender/color suffix
    m = _re.sub(r"\s+(Men'?s?|Women'?s?|Unisex|Men|Women)\b.*$", "", m, flags=_re.IGNORECASE).strip()
    m = _re.sub(r"\s+Shoes?$", "", m, flags=_re.IGNORECASE).strip()
    return m


def get_playwright_page(url: str) -> str:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        content = page.content()
        browser.close()
        return content


class BaseScraper(ABC):
    @property
    @abstractmethod
    def scraper_name(self) -> str:
        ...

    @property
    @abstractmethod
    def brand(self) -> str:
        ...

    @abstractmethod
    def scrape(self) -> list[dict[str, Any]]:
        ...

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        msrp = float(raw.get("msrp", 0) or 0)
        sale_price = float(raw.get("sale_price", 0) or 0)
        if msrp > 0:
            discount_pct = round((msrp - sale_price) / msrp * 100, 1)
        else:
            discount_pct = 0.0
        return {**raw, "discount_pct": discount_pct}

    def upsert_products(self, db: Session, products: list[dict[str, Any]]) -> None:
        run = ScrapeRun(
            scraper_name=self.scraper_name,
            status="running",
            started_at=datetime.utcnow(),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            # Deactivate all existing products from sellers in this scrape run,
            # so any product not seen this time gets marked inactive.
            sellers_in_run = {p["seller"] for p in products if p.get("seller")}
            if sellers_in_run:
                db.query(Product).filter(
                    Product.seller.in_(sellers_in_run)
                ).update({"is_active": False}, synchronize_session=False)
                db.commit()

            count = 0
            for raw in products:
                data = self.normalize(raw)
                existing = (
                    db.query(Product)
                    .filter(
                        Product.seller == data["seller"],
                        Product.seller_sku == data["seller_sku"],
                    )
                    .first()
                )
                now = datetime.utcnow()
                if existing:
                    if existing.sale_price != data["sale_price"]:
                        db.add(PriceHistory(
                            product_id=existing.id,
                            sale_price=data["sale_price"],
                            scraped_at=now,
                        ))
                    for k, v in data.items():
                        if hasattr(existing, k):
                            setattr(existing, k, v)
                    existing.last_scraped_at = now
                    existing.updated_at = now
                    existing.is_active = True
                else:
                    product = Product(**data, last_scraped_at=now, created_at=now, updated_at=now)
                    db.add(product)
                count += 1

            db.commit()
            run.status = "success"
            run.items_found = count
            run.finished_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            db.rollback()
            run.status = "error"
            run.error_message = str(e)
            run.finished_at = datetime.utcnow()
            db.commit()
            raise
