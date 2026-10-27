import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus, Download, RefreshCw } from "lucide-react";
import { complaintsApi, reportsApi } from "../api";
import { DataTable, type Column } from "../components/DataTable";
import {
  StatusBadge,
  PriorityBadge,
  OverdueBadge,
  EscalationBadge,
  BureauChip,
} from "../components/Badges";
import { formatDate } from "../lib/utils";

export const ComplaintsPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // URL-driven filter states
  const page = parseInt(searchParams.get("page") || "1", 10);
  const pageSize = parseInt(searchParams.get("page_size") || "10", 10);
  const status = searchParams.get("status") || "";
  const category = searchParams.get("category") || "";
  const priority = searchParams.get("priority") || "";
  const bureauCode = searchParams.get("bureau_code") || "";
  const isOverdue = searchParams.get("is_overdue") === "true";
  const scope = (searchParams.get("scope") as "bureau" | "all") || "bureau";
  const search = searchParams.get("search") || "";
  const sortBy = searchParams.get("sort_by") || "created_at";
  const sortOrder = (searchParams.get("sort_order") as "asc" | "desc") || "desc";

  const [isExporting, setIsExporting] = useState(false);

  // Helper to update query params cleanly
  const updateParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (value === null || value === "" || value === "false") {
      next.delete(key);
    } else {
      next.set(key, value);
    }
    if (key !== "page") {
      next.set("page", "1");
    }
    setSearchParams(next);
  };

  const {
    data: complaintsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: [
      "complaints",
      page,
      pageSize,
      status,
      category,
      priority,
      bureauCode,
      isOverdue,
      scope,
      search,
      sortBy,
      sortOrder,
    ],
    queryFn: () =>
      complaintsApi.list({
        page,
        page_size: pageSize,
        status: status || undefined,
        category: category || undefined,
        priority: priority || undefined,
        bureau_code: bureauCode || undefined,
        is_overdue: isOverdue ? true : undefined,
        scope,
        search: search || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
  });

  const handleExportCsv = async () => {
    setIsExporting(true);
    try {
      await reportsApi.exportComplaintsCsv({
        bureau_code: bureauCode || undefined,
        status: status || undefined,
        category: category || undefined,
      });
    } catch (err: any) {
      alert("Failed to export CSV: " + (err.message || "Unknown error"));
    } finally {
      setIsExporting(false);
    }
  };

  const columns: Column<any>[] = [
    {
      header: "Complaint #",
      accessorKey: "complaint_number",
      sortable: true,
      className: "w-44 font-mono font-bold text-xs text-brand-700",
      cell: (row) => (
        <div>
          <div>{row.complaint_number}</div>
          <div className="text-[10px] text-surface-subtle font-sans font-normal">
            {formatDate(row.created_at)}
          </div>
        </div>
      ),
    },
    {
      header: "Title & Category",
      accessorKey: "title",
      className: "max-w-xs",
      cell: (row) => (
        <div>
          <div className="font-semibold text-xs text-surface-text line-clamp-1">
            {row.title}
          </div>
          <div className="text-[11px] text-surface-subtle flex items-center gap-1.5 mt-0.5">
            <span className="capitalize">{row.category.replace(/_/g, " ")}</span>
            {row.incident_date && (
              <span>• Inc: {formatDate(row.incident_date)}</span>
            )}
          </div>
        </div>
      ),
    },
    {
      header: "Institution",
      accessorKey: "institution_name",
      className: "max-w-xs text-xs",
      cell: (row) => (
        <div>
          <div className="font-medium text-surface-text truncate">
            {row.institution_name || "—"}
          </div>
          <div className="text-[10px] text-surface-subtle font-mono">
            {row.institution_aicte_id}
          </div>
        </div>
      ),
    },
    {
      header: "Bureau",
      accessorKey: "bureau_code",
      className: "w-28 text-center",
      cell: (row) => (
        <div className="flex flex-col items-center gap-1">
          <BureauChip code={row.bureau_code} />
          {row.participating_bureaus?.length > 0 && (
            <span className="text-[10px] text-surface-subtle">
              +{row.participating_bureaus.join(", ")}
            </span>
          )}
        </div>
      ),
    },
    {
      header: "Priority",
      accessorKey: "priority",
      sortable: true,
      className: "w-24 text-center",
      cell: (row) => <PriorityBadge priority={row.priority} />,
    },
    {
      header: "Status",
      accessorKey: "status",
      sortable: true,
      className: "w-32 text-center",
      cell: (row) => <StatusBadge status={row.status} />,
    },
    {
      header: "SLA Due Date",
      accessorKey: "target_resolution_date",
      sortable: true,
      className: "w-36 text-right",
      cell: (row) => (
        <div className="text-right">
          <div className="text-xs font-medium text-surface-text">
            {formatDate(row.target_resolution_date)}
          </div>
          <div className="flex justify-end gap-1 mt-0.5">
            <OverdueBadge isOverdue={row.is_overdue} />
            <EscalationBadge isEscalated={row.is_escalated} />
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-surface-text">
            Complaints Management
          </h1>
          <p className="text-sm text-surface-subtle mt-0.5">
            Monitor, assign, investigate, and resolve student and faculty grievances
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={isExporting}
            className="gov-btn-secondary text-sm py-2 px-3 flex items-center gap-1.5"
            title="Download CSV report"
          >
            <Download className="w-4 h-4" />
            <span>{isExporting ? "Exporting..." : "Export CSV"}</span>
          </button>

          <Link
            to="/complaints/new"
            className="gov-btn-primary text-sm py-2 px-4 shadow-sm flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>Register Complaint</span>
          </Link>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="gov-card p-4 bg-white space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Scope Toggle */}
          <div className="inline-flex rounded-md shadow-sm border border-surface-border p-0.5 bg-surface-muted text-xs">
            <button
              type="button"
              onClick={() => updateParam("scope", "bureau")}
              className={`px-3 py-1.5 rounded-sm font-medium transition-colors ${
                scope === "bureau"
                  ? "bg-white text-brand-900 shadow-sm"
                  : "text-surface-subtle hover:text-surface-text"
              }`}
            >
              My Bureau Cases
            </button>
            <button
              type="button"
              onClick={() => updateParam("scope", "all")}
              className={`px-3 py-1.5 rounded-sm font-medium transition-colors ${
                scope === "all"
                  ? "bg-white text-brand-900 shadow-sm"
                  : "text-surface-subtle hover:text-surface-text"
              }`}
            >
              All AICTE Cases
            </button>
          </div>

          {/* Status Filter */}
          <select
            value={status}
            onChange={(e) => updateParam("status", e.target.value)}
            className="gov-input text-xs py-1.5 w-auto"
          >
            <option value="">All Statuses</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="ASSIGNED">Assigned</option>
            <option value="IN_INVESTIGATION">In Investigation</option>
            <option value="PENDING_INSTITUTION_ACTION">Pending Inst. Action</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>

          {/* Priority Filter */}
          <select
            value={priority}
            onChange={(e) => updateParam("priority", e.target.value)}
            className="gov-input text-xs py-1.5 w-auto"
          >
            <option value="">All Priorities</option>
            <option value="URGENT">Urgent</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          {/* Bureau Filter */}
          <select
            value={bureauCode}
            onChange={(e) => updateParam("bureau_code", e.target.value)}
            className="gov-input text-xs py-1.5 w-auto"
          >
            <option value="">All Primary Bureaus</option>
            <option value="RB">Bureau RB</option>
            <option value="PGRC">Bureau PGRC</option>
            <option value="HQ">Bureau HQ</option>
          </select>

          {/* Overdue Checkbox Toggle */}
          <label className="flex items-center gap-1.5 text-xs text-surface-text cursor-pointer select-none border border-surface-border px-2.5 py-1.5 rounded bg-surface-muted/50">
            <input
              type="checkbox"
              checked={isOverdue}
              onChange={(e) =>
                updateParam("is_overdue", e.target.checked ? "true" : null)
              }
              className="rounded border-slate-300 text-brand-600 focus:ring-brand-500 h-3.5 w-3.5"
            />
            <span className="font-medium text-red-600">Overdue Only</span>
          </label>

          {/* Reset Filters */}
          {(status || category || priority || bureauCode || isOverdue || search) && (
            <button
              type="button"
              onClick={() => {
                const next = new URLSearchParams();
                next.set("scope", scope);
                setSearchParams(next);
              }}
              className="text-xs text-brand-600 hover:text-brand-800 underline font-medium ml-auto"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Main Table */}
      <DataTable
        columns={columns}
        data={complaintsData?.items || []}
        totalCount={complaintsData?.total || 0}
        page={page}
        pageSize={pageSize}
        sortBy={sortBy}
        sortOrder={sortOrder}
        isLoading={isLoading}
        searchQuery={search}
        searchPlaceholder="Search complaint #, title, description, or complainant..."
        onSearchChange={(val) => updateParam("search", val)}
        onPageChange={(p) => updateParam("page", String(p))}
        onSortChange={(field) => {
          if (sortBy === field) {
            updateParam("sort_order", sortOrder === "asc" ? "desc" : "asc");
          } else {
            updateParam("sort_by", field);
            updateParam("sort_order", "asc");
          }
        }}
        onRowClick={(row) => navigate(`/complaints/${row.id}`)}
        emptyTitle="No complaints found"
        emptyDescription="Try clearing or adjusting your search filters above."
        headerAction={
          <button
            type="button"
            onClick={() => refetch()}
            className="p-1.5 rounded border border-surface-border text-surface-subtle hover:text-surface-text"
            title="Refresh table"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        }
      />
    </div>
  );
};
