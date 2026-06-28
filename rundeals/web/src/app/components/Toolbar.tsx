"use client";

import { LayoutGrid, List } from "lucide-react";

type SortOption = string;

interface ToolbarProps {
  total: number;
  sort: SortOption;
  onSortChange: (sort: SortOption) => void;
  viewMode: "grid" | "list";
  onViewModeChange: (mode: "grid" | "list") => void;
}

const SORT_BUTTONS: { label: string; asc: string; desc: string }[] = [
  { label: "Price", asc: "price_asc", desc: "price_desc" },
  { label: "Discount", asc: "discount_asc", desc: "discount_desc" },
  { label: "Name", asc: "name_asc", desc: "name_desc" },
];

export default function Toolbar({
  total,
  sort,
  onSortChange,
  viewMode,
  onViewModeChange,
}: ToolbarProps) {
  const handleSortClick = (asc: string, desc: string) => {
    if (sort === asc) onSortChange(desc);
    else if (sort === desc) onSortChange(asc);
    else onSortChange(asc);
  };

  const getSortArrow = (asc: string, desc: string) => {
    if (sort === asc) return " ↑";
    if (sort === desc) return " ↓";
    return "";
  };

  return (
    <div className="flex items-center justify-between py-3 px-1">
      <span className="text-sm text-gray-500">
        <span className="font-semibold text-gray-800">{total}</span> deals found
      </span>
      <div className="flex items-center gap-1">
        {SORT_BUTTONS.map(({ label, asc, desc }) => {
          const active = sort === asc || sort === desc;
          return (
            <button
              key={label}
              onClick={() => handleSortClick(asc, desc)}
              className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                active
                  ? "bg-blue-50 border-blue-300 text-blue-700 font-medium"
                  : "bg-white border-gray-200 text-gray-600 hover:border-gray-400"
              }`}
            >
              {label}
              {getSortArrow(asc, desc)}
            </button>
          );
        })}
        <div className="w-px h-5 bg-gray-200 mx-1" />
        <button
          onClick={() => onViewModeChange("grid")}
          className={`p-1.5 rounded border transition-colors ${
            viewMode === "grid"
              ? "bg-blue-50 border-blue-300 text-blue-700"
              : "bg-white border-gray-200 text-gray-400 hover:border-gray-400"
          }`}
          aria-label="Grid view"
        >
          <LayoutGrid size={15} />
        </button>
        <button
          onClick={() => onViewModeChange("list")}
          className={`p-1.5 rounded border transition-colors ${
            viewMode === "list"
              ? "bg-blue-50 border-blue-300 text-blue-700"
              : "bg-white border-gray-200 text-gray-400 hover:border-gray-400"
          }`}
          aria-label="List view"
        >
          <List size={15} />
        </button>
      </div>
    </div>
  );
}
