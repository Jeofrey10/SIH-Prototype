import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, RefreshCw } from "lucide-react";
import { reportsApi, bureausApi } from "../api";
import { formatDate } from "../lib/utils";
import { StatusBadge, BureauChip } from "../components/Badges";
import { EmptyState } from "../components/EmptyState";

export const ReportsPage: React.FC = () => {
  const [reportType, setReportType] = useState<"overdue" | "complaints">("overdue");
  const [bureauCode, setBureauCode] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [isExporting, setIsExporting] = useState<boolean>(false);

  const { data: bureausData } = useQuery({
    queryKey: ["bureaus-list"],
    queryFn: () => bureausApi.list(),
  });

  const {
    data: previewData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["report-preview", reportType, bureauCode, status],
    queryFn: () => {
      if (reportType === "overdue") {
        return reportsApi.previewOverdue({
          bureau_code: bureauCode || undefined,
          page_size: 50,
        });
      } else {
        return reportsApi.previewComplaints({
          bureau_code: bureauCode || undefined,
          status: status || undefined,
          page_size: 50,
        });
      }
    },
  });

  const handleDownloadCsv = async () => {
    setIsExporting(true);
    try {
      if (reportType === "overdue") {
        await reportsApi.exportOverdueCsv({
          bureau_code: bureauCode || undefined,
        });
      } else {
        await reportsApi.exportComplaintsCsv({
          bureau_code: bureauCode || undefined,
          status: status || undefined,
        });
      }
    } catch (err: any) {
      alert("CSV export failed: " + (err.message || "Unknown error"));
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-surface-text">
            Statutory Reports &amp; CSV Export
          </h1>
          <p className="text-sm text-surface-subtle mt-0.5">
            Download audit-ready grievance datasets sanitized against CSV injection
          </p>
        </div>

        <button
          type="button"
          onClick={handleDownloadCsv}
          disabled={isExporting}
          className="gov-btn-primary text-sm py-2 px-4 shadow-sm flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          <span>{isExporting ? "Generating CSV..." : "Download Report CSV"}</span>
        </button>
      </div>

      {/* Report Configuration & Filters */}
      <div className="gov-card p-5 bg-white space-y-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-surface-subtle">
          Report Parameters
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="gov-label" htmlFor="repType">
              Report Type
            </label>
            <select
              id="repType"
              value={reportType}
              onChange={(e) => setReportType(e.target.value as any)}
              className="gov-input text-xs"
            >
              <option value="overdue">Overdue Complaints SLA Audit</option>
              <option value="complaints">Grievance Master Data Export</option>
            </select>
          </div>

          <div>
            <label className="gov-label" htmlFor="bureauFilter">
              Bureau Filter
            </label>
            <select
              id="bureauFilter"
              value={bureauCode}
              onChange={(e) => setBureauCode(e.target.value)}
              className="gov-input text-xs"
            >
              <option value="">All Bureaus</option>
              {bureausData?.map((b: any) => (
                <option key={b.code} value={b.code}>
                  {b.code} - {b.name}
                </option>
              ))}
            </select>
          </div>

          {reportType === "complaints" && (
            <div>
              <label className="gov-label" htmlFor="statFilter">
                Status Filter
              </label>
              <select
                id="statFilter"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="gov-input text-xs"
              >
                <option value="">All Statuses</option>
                <option value="SUBMITTED">Submitted</option>
                <option value="UNDER_REVIEW">Under Review</option>
                <option value="ASSIGNED">Assigned</option>
                <option value="IN_INVESTIGATION">In Investigation</option>
                <option value="PENDING_INSTITUTION_ACTION">Pending Institution Action</option>
                <option value="RESOLVED">Resolved</option>
                <option value="CLOSED">Closed</option>
              </select>
            </div>
          )}
        </div>
      </div>

      {/* Preview Table */}
      <div className="gov-card overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-border bg-surface-muted flex items-center justify-between">
          <div className="text-xs font-semibold text-surface-text">
            Report Data Preview (First 50 records)
          </div>
          <button
            onClick={() => refetch()}
            className="p-1 rounded text-surface-subtle hover:text-surface-text"
            title="Refresh preview"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="gov-table w-full text-xs">
            <thead>
              <tr>
                <th>Complaint #</th>
                <th>Title</th>
                <th>Institution</th>
                <th>Bureau</th>
                <th>Status</th>
                <th>Target Date</th>
                <th>Days Overdue</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-surface-subtle">
                    Generating preview...
                  </td>
                </tr>
              ) : (!previewData || previewData.items.length === 0) ? (
                <tr>
                  <td colSpan={7} className="p-0 border-none">
                    <EmptyState
                      title="No matching records"
                      description="No complaints meet the selected report criteria."
                    />
                  </td>
                </tr>
              ) : (
                previewData.items.map((r: any) => (
                  <tr key={r.id}>
                    <td className="font-mono font-bold text-brand-700">
                      {r.complaint_number}
                    </td>
                    <td className="font-medium max-w-xs truncate">{r.title}</td>
                    <td>{r.institution_name || r.institution_aicte_id}</td>
                    <td>
                      <BureauChip code={r.bureau_code} />
                    </td>
                    <td>
                      <StatusBadge status={r.status} />
                    </td>
                    <td>{formatDate(r.target_resolution_date)}</td>
                    <td className="font-semibold text-red-600">
                      {r.days_overdue !== undefined && r.days_overdue !== null
                        ? `${r.days_overdue}d`
                        : r.is_overdue
                        ? "Overdue"
                        : "On Track"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
