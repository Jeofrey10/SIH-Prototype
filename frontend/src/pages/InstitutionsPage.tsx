import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { MapPin } from "lucide-react";
import { institutionsApi } from "../api";
import { DataTable, type Column } from "../components/DataTable";

export const InstitutionsPage: React.FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const pageSize = 10;

  const { data, isLoading } = useQuery({
    queryKey: ["institutions", page, pageSize, search],
    queryFn: () =>
      institutionsApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
      }),
  });

  const columns: Column<any>[] = [
    {
      header: "AICTE ID",
      accessorKey: "aicte_id",
      sortable: true,
      className: "w-36 font-mono font-bold text-xs text-brand-700",
    },
    {
      header: "Institution Name",
      accessorKey: "name",
      className: "font-semibold text-xs text-surface-text",
      cell: (row) => (
        <div>
          <div>{row.name}</div>
          <div className="text-[11px] text-surface-subtle font-normal flex items-center gap-1 mt-0.5">
            <MapPin className="w-3 h-3 text-surface-subtle" />
            <span>
              {row.city}, {row.state}
            </span>
          </div>
        </div>
      ),
    },
    {
      header: "Category",
      accessorKey: "category",
      className: "w-32 text-xs text-surface-subtle",
    },
    {
      header: "Active Cases",
      accessorKey: "active_complaints_count",
      sortable: true,
      className: "w-28 text-center",
      cell: (row) => (
        <span
          className={`px-2 py-0.5 rounded text-xs font-semibold ${
            (row.active_complaints_count || 0) > 0
              ? "bg-amber-100 text-amber-800"
              : "bg-surface-muted text-surface-subtle"
          }`}
        >
          {row.active_complaints_count ?? 0}
        </span>
      ),
    },
    {
      header: "Total Cases",
      accessorKey: "total_complaints_count",
      sortable: true,
      className: "w-28 text-center text-xs font-medium text-surface-text",
      cell: (row) => row.total_complaints_count ?? 0,
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-surface-text">
            Technical Institutions Directory
          </h1>
          <p className="text-sm text-surface-subtle mt-0.5">
            AICTE-approved institutions with consolidated complaint histories
          </p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={data?.items || []}
        totalCount={data?.total || 0}
        page={page}
        pageSize={pageSize}
        isLoading={isLoading}
        searchQuery={search}
        searchPlaceholder="Search by AICTE ID, Name, City, or State..."
        onSearchChange={(val) => {
          setSearch(val);
          setPage(1);
        }}
        onPageChange={(p) => setPage(p)}
        onRowClick={(row) => navigate(`/institutions/${row.id}`)}
        emptyTitle="No institutions found"
        emptyDescription="Try searching for another keyword or AICTE identifier."
      />
    </div>
  );
};
