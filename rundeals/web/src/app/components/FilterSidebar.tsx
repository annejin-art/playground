"use client";

import { ActiveFilters, FiltersResponse } from "../types";

interface FilterSidebarProps {
  currentFilters: ActiveFilters;
  onFilterChange: (filters: Partial<ActiveFilters>) => void;
  availableFilters: FiltersResponse | null;
}

const DISCOUNT_OPTIONS = [
  { label: "10%+", value: "10" },
  { label: "25%+", value: "25" },
  { label: "40%+", value: "40" },
  { label: "50%+", value: "50" },
];

const WIDTH_OPTIONS = ["Narrow", "Regular", "Wide", "X-Wide"];
const SUPPORT_OPTIONS = ["Neutral", "Stability", "Motion Control"];
const GENDER_OPTIONS = ["Men's", "Women's", "Unisex"];

function ScrollableList({
  options,
  selected,
  onToggle,
}: {
  options: string[];
  selected: string[];
  onToggle: (val: string) => void;
}) {
  if (!options.length) return <p className="text-xs text-gray-400">No options</p>;
  return (
    <div className="max-h-36 overflow-y-auto border border-gray-200 rounded bg-white">
      {options.map((opt) => {
        const active = selected.includes(opt);
        return (
          <button
            key={opt}
            onClick={() => onToggle(opt)}
            className={`w-full text-left px-2.5 py-1.5 text-xs flex items-center gap-2 hover:bg-gray-50 transition-colors ${
              active ? "bg-blue-50 text-blue-700" : "text-gray-600"
            }`}
          >
            <span
              className={`w-3 h-3 rounded border flex-shrink-0 ${
                active ? "bg-blue-500 border-blue-500" : "border-gray-300"
              }`}
            />
            <span className="break-words min-w-0">{opt}</span>
          </button>
        );
      })}
    </div>
  );
}

function PillGroup({
  options,
  selected,
  onToggle,
}: {
  options: string[];
  selected: string[];
  onToggle: (val: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const active = selected.includes(opt);
        return (
          <button
            key={opt}
            onClick={() => onToggle(opt)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
              active
                ? "bg-blue-100 text-blue-700 border-blue-300"
                : "bg-white border-gray-200 text-gray-600 hover:border-gray-400"
            }`}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function toggle(arr: string[], val: string): string[] {
  return arr.includes(val) ? arr.filter((v) => v !== val) : [...arr, val];
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold tracking-widest uppercase text-gray-400 mb-2">
      {children}
    </p>
  );
}

function Divider() {
  return <div className="border-t border-gray-100 my-3" />;
}

export default function FilterSidebar({
  currentFilters,
  onFilterChange,
  availableFilters,
}: FilterSidebarProps) {
  const hasAnyFilter =
    currentFilters.brands.length > 0 ||
    currentFilters.models.length > 0 ||
    currentFilters.sellers.length > 0 ||
    currentFilters.sizes.length > 0 ||
    currentFilters.colors.length > 0 ||
    currentFilters.widths.length > 0 ||
    currentFilters.support_types.length > 0 ||
    currentFilters.genders.length > 0 ||
    currentFilters.min_price !== "" ||
    currentFilters.max_price !== "" ||
    currentFilters.min_discount !== "";

  const clearAll = () =>
    onFilterChange({
      brands: [],
      models: [],
      sellers: [],
      sizes: [],
      colors: [],
      widths: [],
      support_types: [],
      genders: [],
      min_price: "",
      max_price: "",
      min_discount: "",
      page: 1,
    });

  return (
    <aside className="w-[250px] flex-shrink-0 h-full overflow-y-auto bg-gray-50 border-r border-gray-200 px-4 py-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-gray-700">Filters</span>
        {hasAnyFilter && (
          <button
            onClick={clearAll}
            className="text-xs text-blue-600 hover:underline"
          >
            Clear all
          </button>
        )}
      </div>

      <SectionLabel>Brand</SectionLabel>
      <ScrollableList
        options={availableFilters?.brands ?? []}
        selected={currentFilters.brands}
        onToggle={(v) =>
          onFilterChange({ brands: toggle(currentFilters.brands, v), page: 1 })
        }
      />

      <Divider />

      <SectionLabel>Gender</SectionLabel>
      <PillGroup
        options={GENDER_OPTIONS}
        selected={currentFilters.genders}
        onToggle={(v) =>
          onFilterChange({
            genders: toggle(currentFilters.genders, v),
            page: 1,
          })
        }
      />

      <Divider />

      <SectionLabel>Model</SectionLabel>
      <ScrollableList
        options={availableFilters?.models ?? []}
        selected={currentFilters.models}
        onToggle={(v) =>
          onFilterChange({ models: toggle(currentFilters.models, v), page: 1 })
        }
      />

      <Divider />

      <SectionLabel>Price Range</SectionLabel>
      <div className="flex gap-2">
        <div className="flex-1">
          <label className="text-xs text-gray-400 block mb-1">Min</label>
          <input
            type="number"
            min={0}
            max={400}
            placeholder="$0"
            value={currentFilters.min_price}
            onChange={(e) =>
              onFilterChange({ min_price: e.target.value, page: 1 })
            }
            className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded bg-white focus:outline-none focus:border-blue-400"
          />
        </div>
        <div className="flex-1">
          <label className="text-xs text-gray-400 block mb-1">Max</label>
          <input
            type="number"
            min={0}
            max={400}
            placeholder="$400"
            value={currentFilters.max_price}
            onChange={(e) =>
              onFilterChange({ max_price: e.target.value, page: 1 })
            }
            className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded bg-white focus:outline-none focus:border-blue-400"
          />
        </div>
      </div>

      <Divider />

      <SectionLabel>Discount</SectionLabel>
      <PillGroup
        options={DISCOUNT_OPTIONS.map((d) => d.label)}
        selected={
          currentFilters.min_discount
            ? [
                DISCOUNT_OPTIONS.find(
                  (d) => d.value === currentFilters.min_discount
                )?.label ?? "",
              ].filter(Boolean)
            : []
        }
        onToggle={(label) => {
          const opt = DISCOUNT_OPTIONS.find((d) => d.label === label);
          if (!opt) return;
          onFilterChange({
            min_discount:
              currentFilters.min_discount === opt.value ? "" : opt.value,
            page: 1,
          });
        }}
      />

      <Divider />

      <SectionLabel>Seller</SectionLabel>
      <ScrollableList
        options={availableFilters?.sellers ?? []}
        selected={currentFilters.sellers}
        onToggle={(v) =>
          onFilterChange({
            sellers: toggle(currentFilters.sellers, v),
            page: 1,
          })
        }
      />

      <Divider />

      <SectionLabel>Color</SectionLabel>
      <ScrollableList
        options={availableFilters?.colors ?? []}
        selected={currentFilters.colors}
        onToggle={(v) =>
          onFilterChange({ colors: toggle(currentFilters.colors, v), page: 1 })
        }
      />

      <Divider />

      <SectionLabel>Size</SectionLabel>
      <PillGroup
        options={availableFilters?.sizes ?? []}
        selected={currentFilters.sizes}
        onToggle={(v) =>
          onFilterChange({ sizes: toggle(currentFilters.sizes, v), page: 1 })
        }
      />

      <Divider />

      <SectionLabel>Width</SectionLabel>
      <PillGroup
        options={WIDTH_OPTIONS}
        selected={currentFilters.widths}
        onToggle={(v) =>
          onFilterChange({ widths: toggle(currentFilters.widths, v), page: 1 })
        }
      />

      <Divider />

      <SectionLabel>Support Type</SectionLabel>
      <PillGroup
        options={SUPPORT_OPTIONS}
        selected={currentFilters.support_types}
        onToggle={(v) =>
          onFilterChange({
            support_types: toggle(currentFilters.support_types, v),
            page: 1,
          })
        }
      />
    </aside>
  );
}
