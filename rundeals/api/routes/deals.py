import json
import os
import math
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
import redis as redis_lib

from database import get_db, Product, ScrapeRun
from models import DealsResponse, FiltersResponse, ProductOut

router = APIRouter()

redis_client = redis_lib.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))


def _cache_key(params: dict) -> str:
    return "deals:" + json.dumps(params, sort_keys=True)


@router.get("/api/deals", response_model=DealsResponse)
def get_deals(
    brands: list[str] = Query(default=[]),
    models: list[str] = Query(default=[]),
    sellers: list[str] = Query(default=[]),
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_discount: Optional[float] = None,
    sizes: list[str] = Query(default=[]),
    colors: list[str] = Query(default=[]),
    widths: list[str] = Query(default=[]),
    support_types: list[str] = Query(default=[]),
    genders: list[str] = Query(default=[]),
    sort: str = "name_asc",
    page: int = 1,
    per_page: int = 99,
    db: Session = Depends(get_db),
):
    per_page = min(per_page, 99)
    cache_key = _cache_key({
        "brands": brands, "models": models, "sellers": sellers,
        "min_price": min_price, "max_price": max_price,
        "min_discount": min_discount, "sizes": sizes, "colors": colors, "widths": widths,
        "support_types": support_types, "genders": genders,
        "sort": sort, "page": page, "per_page": per_page,
    })

    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    q = db.query(Product).filter(Product.is_active == True)

    if brands:
        q = q.filter(Product.brand.in_(brands))
    if models:
        q = q.filter(Product.model.in_(models))
    if sellers:
        q = q.filter(Product.seller.in_(sellers))
    if min_price is not None:
        q = q.filter(Product.sale_price >= min_price)
    if max_price is not None:
        q = q.filter(Product.sale_price <= max_price)
    if min_discount is not None:
        q = q.filter(Product.discount_pct >= min_discount)
    if widths:
        q = q.filter(Product.width.in_(widths))
    if support_types:
        q = q.filter(Product.support_type.in_(support_types))
    if genders:
        q = q.filter(Product.gender.in_(genders))
    if sizes:
        filters = [Product.sizes_available.contains([s]) for s in sizes]
        q = q.filter(or_(*filters))
    if colors:
        color_filters = [Product.colors_available.contains([c]) for c in colors]
        q = q.filter(or_(*color_filters))

    sort_map = {
        "name_asc": Product.full_name.asc(),
        "name_desc": Product.full_name.desc(),
        "price_asc": Product.sale_price.asc(),
        "price_desc": Product.sale_price.desc(),
        "discount_desc": Product.discount_pct.desc(),
        "discount_asc": Product.discount_pct.asc(),
    }
    q = q.order_by(sort_map.get(sort, Product.full_name.asc()))

    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    pages = math.ceil(total / per_page) if total else 1

    result = DealsResponse(
        items=[ProductOut.model_validate(p) for p in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
    result_dict = result.model_dump(mode="json")
    redis_client.setex(cache_key, 1800, json.dumps(result_dict))
    return result_dict


@router.get("/api/filters", response_model=FiltersResponse)
def get_filters(db: Session = Depends(get_db)):
    cached = redis_client.get("filters")
    if cached:
        return json.loads(cached)

    brands = [r[0] for r in db.query(Product.brand).filter(Product.is_active == True).distinct().order_by(Product.brand).all() if r[0]]
    models = [r[0] for r in db.query(Product.model).filter(Product.is_active == True).distinct().order_by(Product.model).all() if r[0]]
    sellers = [r[0] for r in db.query(Product.seller).filter(Product.is_active == True).distinct().order_by(Product.seller).all() if r[0]]
    widths = [r[0] for r in db.query(Product.width).filter(Product.is_active == True).distinct().all() if r[0]]
    support_types = [r[0] for r in db.query(Product.support_type).filter(Product.is_active == True).distinct().all() if r[0]]
    genders = [r[0] for r in db.query(Product.gender).filter(Product.is_active == True).distinct().all() if r[0]]

    all_sizes: set[str] = set()
    for (sizes,) in db.query(Product.sizes_available).filter(Product.is_active == True).all():
        if sizes:
            all_sizes.update(sizes)

    all_colors: set[str] = set()
    for (colors_val,) in db.query(Product.colors_available).filter(Product.is_active == True).all():
        if colors_val:
            all_colors.update(colors_val)

    def size_sort_key(s: str):
        try:
            return float(s)
        except ValueError:
            return 999

    result = FiltersResponse(
        brands=brands,
        models=models,
        sellers=sellers,
        sizes=sorted(all_sizes, key=size_sort_key),
        colors=sorted(all_colors),
        widths=sorted(widths),
        support_types=sorted(support_types),
        genders=sorted(genders),
    )
    result_dict = result.model_dump()
    redis_client.setex("filters", 1800, json.dumps(result_dict))
    return result_dict
