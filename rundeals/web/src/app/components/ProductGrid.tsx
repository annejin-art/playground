"use client";

import { Product } from "../types";
import ProductCard from "./ProductCard";

interface ProductGridProps {
  products: Product[];
  viewMode: "grid" | "list";
  loading: boolean;
}

function SkeletonCard({ viewMode }: { viewMode: "grid" | "list" }) {
  if (viewMode === "list") {
    return (
      <div className="flex items-center gap-4 bg-white border border-gray-100 rounded-lg p-3">
        <div className="flex-shrink-0 w-24 h-16 bg-gray-200 rounded animate-pulse" />
        <div className="flex-1">
          <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4 mb-2" />
          <div className="h-3 bg-gray-200 rounded animate-pulse w-1/3" />
        </div>
        <div className="flex-shrink-0 w-16">
          <div className="h-5 bg-gray-200 rounded animate-pulse mb-1" />
          <div className="h-3 bg-gray-200 rounded animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-100 rounded-lg overflow-hidden">
      <div className="aspect-[4/3] bg-gray-200 animate-pulse" />
      <div className="p-3">
        <div className="h-4 bg-gray-200 rounded animate-pulse mb-2" />
        <div className="h-3 bg-gray-200 rounded animate-pulse w-1/2 mb-3" />
        <div className="h-5 bg-gray-200 rounded animate-pulse w-1/3" />
      </div>
    </div>
  );
}

export default function ProductGrid({ products, viewMode, loading }: ProductGridProps) {
  if (loading) {
    const skeletons = Array.from({ length: 9 });
    return (
      <div
        className={
          viewMode === "grid"
            ? "grid grid-cols-3 gap-3"
            : "flex flex-col gap-2"
        }
      >
        {skeletons.map((_, i) => (
          <SkeletonCard key={i} viewMode={viewMode} />
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <p className="text-lg font-medium">No deals found</p>
        <p className="text-sm mt-1">Try adjusting your filters</p>
      </div>
    );
  }

  return (
    <div
      className={
        viewMode === "grid"
          ? "grid grid-cols-3 gap-3"
          : "flex flex-col gap-2"
      }
    >
      {products.map((product) => (
        <ProductCard key={product.id} product={product} viewMode={viewMode} />
      ))}
    </div>
  );
}
