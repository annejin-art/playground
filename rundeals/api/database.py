import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, JSON, ForeignKey, Text, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rundeals:rundeals@postgres:5432/rundeals")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    seller = Column(String, nullable=False)
    seller_sku = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    msrp = Column(Float, nullable=False)
    sale_price = Column(Float, nullable=False)
    discount_pct = Column(Float, nullable=False)
    image_url = Column(String)
    product_url = Column(String)
    sizes_available = Column(JSON)
    colors_available = Column(JSON)
    width = Column(String)
    support_type = Column(String)
    gender = Column(String)
    is_active = Column(Boolean, default=True)
    last_scraped_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    price_history = relationship("PriceHistory", back_populates="product")


class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sale_price = Column(Float, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="price_history")


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True, index=True)
    scraper_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    items_found = Column(Integer)
    error_message = Column(Text)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
    # Add columns that may not exist on older installs
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS colors_available JSON",
        ]:
            conn.execute(text(stmt))
        conn.commit()
