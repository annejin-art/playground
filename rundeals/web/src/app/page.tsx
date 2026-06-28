"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { ActiveFilters, DealsResponse, FiltersResponse } from "./types";
import FilterSidebar from "./components/FilterSidebar";
import ProductGrid from "./components/ProductGrid";
import Toolbar from "./components/Toolbar";
import Pagination from "./components/Pagination";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DEFAULT_FILTERS: ActiveFilters = {
  brands: [],
  models: [],
  sellers: [],
  min_price: "",
  max_price: "",
  min_discount: "",
  sizes: [],
  colors: [],
  widths: [],
  support_types: [],
  genders: [],
  sort: "discount_desc",
  page: 1,
};

function buildQuery(filters: ActiveFilters): string {
  const params = new URLSearchParams();
  filters.brands.forEach((v) => params.append("brands", v));
  filters.models.forEach((v) => params.append("models", v));
  filters.sellers.forEach((v) => params.append("sellers", v));
  filters.sizes.forEach((v) => params.append("sizes", v));
  filters.colors.forEach((v) => params.append("colors", v));
  filters.widths.forEach((v) => params.append("widths", v));
  filters.support_types.forEach((v) => params.append("support_types", v));
  filters.genders.forEach((v) => params.append("genders", v));
  if (filters.min_price) params.set("min_price", filters.min_price);
  if (filters.max_price) params.set("max_price", filters.max_price);
  if (filters.min_discount) params.set("min_discount", filters.min_discount);
  params.set("sort", filters.sort);
  params.set("page", String(filters.page));
  params.set("per_page", "99");
  return params.toString();
}

export default function HomePage() {
  const [filters, setFilters] = useState<ActiveFilters>(DEFAULT_FILTERS);
  const [deals, setDeals] = useState<DealsResponse | null>(null);
  const [availableFilters, setAvailableFilters] = useState<FiltersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchDeals = useCallback(async (f: ActiveFilters) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/deals?${buildQuery(f)}`);
      if (!res.ok) throw new Error(`API error ${res.status}`);
      const data: DealsResponse = await res.json();
      setDeals(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load deals");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch(`${API}/api/filters`)
      .then((r) => r.json())
      .then((data: FiltersResponse) => setAvailableFilters(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchDeals(filters), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [filters, fetchDeals]);

  const handleFilterChange = (partial: Partial<ActiveFilters>) => {
    setFilters((prev) => ({ ...prev, ...partial }));
  };

  return (
    <div className="flex h-screen overflow-hidden">
      <FilterSidebar
        currentFilters={filters}
        onFilterChange={handleFilterChange}
        availableFilters={availableFilters}
      />
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b border-gray-200 bg-white px-6 py-3 flex items-center gap-3 flex-shrink-0">
          <h1 className="text-lg font-bold text-gray-900 tracking-tight">RunDeals</h1>
          <span className="text-gray-300 text-sm">|</span>
          <span className="text-sm text-gray-500">Running shoe deals, aggregated</span>
          <a
            href="/admin"
            className="ml-auto text-xs text-gray-400 hover:text-gray-600"
          >
            Admin
          </a>
        </header>

        <div className="flex-1 overflow-y-auto px-6">
          {error ? (
            <div className="flex items-center justify-center h-32 text-red-500 text-sm">
              {error} — is the API running?
            </div>
          ) : (
            <>
              <Toolbar
                total={deals?.total ?? 0}
                sort={filters.sort}
                onSortChange={(sort) => handleFilterChange({ sort, page: 1 })}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
              />
              <ProductGrid
                products={deals?.items ?? []}
                viewMode={viewMode}
                loading={loading}
              />
              <Pagination
                page={deals?.page ?? 1}
                pages={deals?.pages ?? 1}
                onPageChange={(page) => handleFilterChange({ page })}
              />
            </>
          )}
        </div>
      </main>
    </div>
  );
}
