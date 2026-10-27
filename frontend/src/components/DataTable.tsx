import React from "react";
import { ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { EmptyState } from "./EmptyState";

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  totalCount?: number;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  isLoading?: boolean;
  searchQuery?: string;
  searchPlaceholder?: string;
  onSearchChange?: (val: string) => void;
  onPageChange?: (page: number) => void;
  onSortChange?: (field: string) => void;
  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  emptyDescription?: string;
  headerAction?: React.ReactNode;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  totalCount = 0,
  page = 1,
  pageSize = 10,
  sortBy,
  sortOrder = "asc",
  isLoading = false,
  searchQuery,
  searchPlaceholder = "Search...",
  onSearchChange,
  onPageChange,
  onSortChange,
  onRowClick,
  emptyTitle,
  emptyDescription,
  headerAction,
}: DataTableProps<T>) {
  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  return (
    <div className="gov-card overflow-hidden">
      {/* Header filter & actions */}
      {(onSearchChange || headerAction) && (
        <div className="p-4 border-b border-surface-border flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-white">
          {onSearchChange && (
            <div className="relative flex-1 max-w-sm">
              <Search className="w-4 h-4 text-surface-subtle absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchQuery || ""}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder={searchPlaceholder}
                className="gov-input pl-9 text-sm"
              />
            </div>
          )}
          {headerAction && <div className="flex items-center gap-2">{headerAction}</div>}
        </div>
      )}

      {/* Table view */}
      <div className="overflow-x-auto">
        <table className="gov-table w-full">
          <thead>
            <tr>
              {columns.map((col, idx) => {
                const isSorted = sortBy === col.accessorKey;
                return (
                  <th
                    key={idx}
                    className={`${col.className || ""} ${
                      col.sortable ? "cursor-pointer select-none hover:bg-surface-border/50" : ""
                    }`}
                    onClick={() => {
                      if (col.sortable && col.accessorKey && onSortChange) {
                        onSortChange(String(col.accessorKey));
                      }
                    }}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>{col.header}</span>
                      {col.sortable && (
                        <span className="text-surface-subtle">
                          {isSorted ? (
                            sortOrder === "asc" ? (
                              <ChevronUp className="w-3.5 h-3.5 text-brand-600" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 text-brand-600" />
                            )
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 opacity-30" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              // Skeleton rows
              Array.from({ length: pageSize }).map((_, rIdx) => (
                <tr key={rIdx}>
                  {columns.map((_, cIdx) => (
                    <td key={cIdx}>
                      <div className="h-4 bg-surface-muted rounded animate-pulse w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="p-0 border-none">
                  <EmptyState
                    title={emptyTitle}
                    description={emptyDescription}
                  />
                </td>
              </tr>
            ) : (
              data.map((row, rIdx) => (
                <tr
                  key={row.id || rIdx}
                  onClick={() => onRowClick && onRowClick(row)}
                  className={onRowClick ? "cursor-pointer hover:bg-surface-muted/70 transition-colors" : ""}
                >
                  {columns.map((col, cIdx) => (
                    <td key={cIdx} className={col.className}>
                      {col.cell
                        ? col.cell(row)
                        : col.accessorKey
                        ? String(row[col.accessorKey] ?? "—")
                        : null}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {totalCount > 0 && onPageChange && (
        <div className="px-4 py-3 border-t border-surface-border bg-surface-muted flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-surface-subtle">
          <div>
            Showing{" "}
            <span className="font-semibold text-surface-text">
              {(page - 1) * pageSize + 1}
            </span>{" "}
            to{" "}
            <span className="font-semibold text-surface-text">
              {Math.min(page * pageSize, totalCount)}
            </span>{" "}
            of{" "}
            <span className="font-semibold text-surface-text">{totalCount}</span>{" "}
            entries
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={page <= 1 || isLoading}
              onClick={() => onPageChange(page - 1)}
              className="p-1.5 rounded border border-surface-border bg-white text-surface-text hover:bg-surface-muted disabled:opacity-40 disabled:cursor-not-allowed"
              title="Previous Page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2">
              Page <span className="font-semibold text-surface-text">{page}</span> of{" "}
              <span className="font-semibold text-surface-text">{totalPages}</span>
            </span>
            <button
              type="button"
              disabled={page >= totalPages || isLoading}
              onClick={() => onPageChange(page + 1)}
              className="p-1.5 rounded border border-surface-border bg-white text-surface-text hover:bg-surface-muted disabled:opacity-40 disabled:cursor-not-allowed"
              title="Next Page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
