import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Eye } from "lucide-react";
import { auditApi } from "../api";
import { DataTable, type Column } from "../components/DataTable";
import { formatDateTime } from "../lib/utils";
import { ConfirmModal } from "../components/ConfirmModal";

export const AuditLogsAdminPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const pageSize = 20;

  const [inspectModalOpen, setInspectModalOpen] = useState(false);
  const [inspectedLog, setInspectedLog] = useState<any>(null);

  const { data: auditData, isLoading } = useQuery({
    queryKey: ["admin-audit-logs", page, pageSize, actionFilter, entityFilter],
    queryFn: () =>
      auditApi.list({
        page,
        page_size: pageSize,
        action: actionFilter || undefined,
        entity_type: entityFilter || undefined,
      }),
  });

  const columns: Column<any>[] = [
    {
      header: "Timestamp",
      accessorKey: "occurred_at",
      className: "w-44 font-mono text-xs text-surface-subtle",
      cell: (row) => formatDateTime(row.occurred_at),
    },
    {
      header: "Action",
      accessorKey: "action",
      className: "w-44",
      cell: (row) => (
        <span
          className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
            row.action.includes("DENIED")
              ? "bg-red-100 text-red-800 border border-red-300"
              : row.action.includes("CONFIRM") || row.action.includes("RESOLVE")
              ? "bg-emerald-100 text-emerald-800"
              : "bg-surface-muted text-surface-text border border-surface-border"
          }`}
        >
          {row.action}
        </span>
      ),
    },
    {
      header: "Target Entity",
      className: "text-xs font-mono",
      cell: (row) => (
        <div>
          <span className="font-semibold text-surface-text">
            {row.entity_type}
          </span>
          <span className="text-surface-subtle ml-1">
            ({row.entity_id ? row.entity_id.slice(0, 8) + "..." : "System"})
          </span>
        </div>
      ),
    },
    {
      header: "Actor",
      accessorKey: "actor_name",
      className: "text-xs font-medium text-surface-text",
      cell: (row) => row.actor_name || "System",
    },
    {
      header: "IP Address",
      accessorKey: "ip_address",
      className: "w-32 font-mono text-xs text-surface-subtle",
    },
    {
      header: "Inspect",
      className: "w-20 text-center",
      cell: (row) => (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setInspectedLog(row);
            setInspectModalOpen(true);
          }}
          className="p-1 rounded text-surface-subtle hover:text-brand-600 hover:bg-surface-muted"
          title="Inspect state payload"
        >
          <Eye className="w-4 h-4" />
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-surface-text">
          Append-Only System Audit Trail
        </h1>
        <p className="text-sm text-surface-subtle mt-0.5">
          Tamper-evident logs of all grievances, status updates, relation decisions, and access denials
        </p>
      </div>

      {/* Filter toolbar */}
      <div className="gov-card p-4 bg-white flex flex-wrap items-center gap-3">
        <select
          value={actionFilter}
          onChange={(e) => {
            setActionFilter(e.target.value);
            setPage(1);
          }}
          className="gov-input text-xs py-1.5 w-auto"
        >
          <option value="">All Actions</option>
          <option value="LOGIN">LOGIN</option>
          <option value="COMPLAINT_REGISTERED">COMPLAINT_REGISTERED</option>
          <option value="STATUS_CHANGED">STATUS_CHANGED</option>
          <option value="RELATION_CONFIRMED">RELATION_CONFIRMED</option>
          <option value="RELATION_DISMISSED">RELATION_DISMISSED</option>
          <option value="ACCESS_DENIED">ACCESS_DENIED</option>
          <option value="REPORT_EXPORTED">REPORT_EXPORTED</option>
        </select>

        <select
          value={entityFilter}
          onChange={(e) => {
            setEntityFilter(e.target.value);
            setPage(1);
          }}
          className="gov-input text-xs py-1.5 w-auto"
        >
          <option value="">All Entity Types</option>
          <option value="COMPLAINT">COMPLAINT</option>
          <option value="RELATION">RELATION</option>
          <option value="USER">USER</option>
          <option value="REPORT">REPORT</option>
          <option value="AUTH">AUTH</option>
        </select>

        <div className="text-xs text-surface-subtle ml-auto">
          Total Logs:{" "}
          <span className="font-semibold text-surface-text">
            {auditData?.total || 0}
          </span>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={auditData?.items || []}
        totalCount={auditData?.total || 0}
        page={page}
        pageSize={pageSize}
        isLoading={isLoading}
        onPageChange={(p) => setPage(p)}
      />

      {/* INSPECT STATE MODAL */}
      <ConfirmModal
        isOpen={inspectModalOpen}
        title={`Audit Payload: ${inspectedLog?.action}`}
        confirmLabel="Close"
        onConfirm={() => setInspectModalOpen(false)}
        onClose={() => setInspectModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <div className="font-semibold text-surface-subtle mb-1">
              Before State Payload:
            </div>
            <pre className="p-3 bg-slate-900 text-slate-100 rounded text-[11px] overflow-x-auto max-h-48">
              {inspectedLog?.before_data
                ? JSON.stringify(inspectedLog.before_data, null, 2)
                : "null"}
            </pre>
          </div>

          <div>
            <div className="font-semibold text-surface-subtle mb-1">
              After State Payload:
            </div>
            <pre className="p-3 bg-slate-900 text-slate-100 rounded text-[11px] overflow-x-auto max-h-48">
              {inspectedLog?.after_data
                ? JSON.stringify(inspectedLog.after_data, null, 2)
                : "null"}
            </pre>
          </div>
        </div>
      </ConfirmModal>
    </div>
  );
};
