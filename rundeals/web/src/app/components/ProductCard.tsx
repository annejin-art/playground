"use client";

import Image from "next/image";
import { useState } from "react";
import { Product } from "../types";

interface ProductCardProps {
  product: Product;
  viewMode: "grid" | "list";
}

const FALLBACK = "https://placehold.co/300x200/e8e8e8/999?text=Shoe";

export default function ProductCard({ product, viewMode }: ProductCardProps) {
  const [imgError, setImgError] = useState(false);
  const imgSrc = imgError || !product.image_url ? FALLBACK : product.image_url;
  const discountLabel = `-${Math.round(product.discount_pct)}%`;

  const handleClick = () => {
    if (product.product_url) {
      window.open(product.product_url, "_blank", "noopener,noreferrer");
    }
  };

  if (viewMode === "list") {
    return (
      <div
        onClick={handleClick}
        className="flex items-center gap-4 bg-white border border-gray-100 rounded-lg p-3 cursor-pointer hover:border-gray-300 hover:shadow-sm transition-all"
      >
        <div className="relative flex-shrink-0 w-24 h-16 bg-gray-50 rounded overflow-hidden">
          <Image
            src={imgSrc}
            alt={product.full_name}
            fill
            className="object-contain"
            unoptimized
            onError={() => setImgError(true)}
          />
          <span className="absolute top-1 left-1 bg-red-500 text-white text-xs font-semibold px-1.5 py-0.5 rounded-full">
            {discountLabel}
          </span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{product.full_name}</p>
          <p className="text-xs text-gray-400 mt-0.5">{product.seller}</p>
        </div>
        <div className="flex-shrink-0 text-right">
          <p className="text-base font-bold text-blue-600">${product.sale_price.toFixed(2)}</p>
          <p className="text-xs text-gray-400 line-through">${product.msrp.toFixed(2)}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={handleClick}
      className="bg-white border border-gray-100 rounded-lg overflow-hidden cursor-pointer hover:border-gray-300 hover:shadow-sm transition-all flex flex-col"
    >
      <div className="relative aspect-[4/3] bg-gray-50">
        <Image
          src={imgSrc}
          alt={product.full_name}
          fill
          className="object-contain"
          unoptimized
        />
        <span className="absolute top-2 left-2 bg-red-500 text-white text-xs font-semibold px-2 py-1 rounded-full">
          {discountLabel}
        </span>
      </div>
      <div className="p-3 flex flex-col flex-1">
        <p className="text-sm font-medium text-gray-900 line-clamp-2 leading-snug">
          {product.full_name}
        </p>
        <p className="text-xs text-gray-400 mt-1">{product.seller}</p>
        <div className="flex items-baseline gap-2 mt-auto pt-2">
          <span className="text-base font-bold text-blue-600">
            ${product.sale_price.toFixed(2)}
          </span>
          <span className="text-xs text-gray-400 line-through">
            ${product.msrp.toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  );
}
