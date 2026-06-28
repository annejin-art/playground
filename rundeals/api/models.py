from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProductOut(BaseModel):
    id: int
    seller: str
    seller_sku: str
    brand: str
    model: str
    full_name: str
    msrp: float
    sale_price: float
    discount_pct: float
    image_url: Optional[str]
    product_url: Optional[str]
    sizes_available: Optional[list[str]]
    colors_available: Optional[list[str]]
    width: Optional[str]
    support_type: Optional[str]
    gender: Optional[str]
    is_active: bool
    last_scraped_at: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DealsResponse(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    per_page: int
    pages: int


class FiltersResponse(BaseModel):
    brands: list[str]
    models: list[str]
    sellers: list[str]
    sizes: list[str]
    colors: list[str]
    widths: list[str]
    support_types: list[str]
    genders: list[str]
