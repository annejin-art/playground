"use client";

interface PaginationProps {
  page: number;
  pages: number;
  onPageChange: (page: number) => void;
}

export default function Pagination({ page, pages, onPageChange }: PaginationProps) {
  if (pages <= 1) return null;

  const getPages = () => {
    const all = Array.from({ length: pages }, (_, i) => i + 1);
    if (pages <= 7) return all;
    if (page <= 4) return [...all.slice(0, 5), "...", pages];
    if (page >= pages - 3) return [1, "...", ...all.slice(pages - 5)];
    return [1, "...", page - 1, page, page + 1, "...", pages];
  };

  return (
    <div className="flex items-center justify-center gap-1 py-4">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page === 1}
        className="px-3 py-1.5 text-sm rounded border border-gray-200 text-gray-600 hover:border-gray-400 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Prev
      </button>
      {getPages().map((p, i) =>
        p === "..." ? (
          <span key={`ellipsis-${i}`} className="px-2 text-gray-400 text-sm">
            …
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(Number(p))}
            className={`px-3 py-1.5 text-sm rounded border transition-colors ${
              p === page
                ? "bg-blue-600 border-blue-600 text-white font-medium"
                : "bg-white border-gray-200 text-gray-600 hover:border-gray-400"
            }`}
          >
            {p}
          </button>
        )
      )}
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page === pages}
        className="px-3 py-1.5 text-sm rounded border border-gray-200 text-gray-600 hover:border-gray-400 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Next
      </button>
    </div>
  );
}
