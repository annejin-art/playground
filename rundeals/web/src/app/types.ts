export interface Product {
  id: number;
  seller: string;
  seller_sku: string;
  brand: string;
  model: string;
  full_name: string;
  msrp: number;
  sale_price: number;
  discount_pct: number;
  image_url: string | null;
  product_url: string | null;
  sizes_available: string[] | null;
  colors_available: string[] | null;
  width: string | null;
  support_type: string | null;
  gender: string | null;
  is_active: boolean;
  last_scraped_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DealsResponse {
  items: Product[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface FiltersResponse {
  brands: string[];
  models: string[];
  sellers: string[];
  sizes: string[];
  colors: string[];
  widths: string[];
  support_types: string[];
  genders: string[];
}

export interface ActiveFilters {
  brands: string[];
  models: string[];
  sellers: string[];
  min_price: string;
  max_price: string;
  min_discount: string;
  sizes: string[];
  colors: string[];
  widths: string[];
  support_types: string[];
  genders: string[];
  sort: string;
  page: number;
}
