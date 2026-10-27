import React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  FileText,
  AlertTriangle,
  GitCompare,
  Users2,
  Clock,
  ArrowRight,
  Building,
} from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  LineChart,
  Line,
  CartesianGrid,
} from "recharts";
import { analyticsApi, complaintsApi } from "../api";
import { KpiCard } from "../components/KpiCard";
import { StatusBadge, PriorityBadge } from "../components/Badges";
import { formatDate } from "../lib/utils";
import { ErrorState } from "../components/EmptyState";

export const DashboardPage: React.FC = () => {
  const {
    data: summary,
    error: summaryError,
    refetch: refetchSummary,
  } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: () => analyticsApi.summary(),
  });

  const { data: statusDist } = useQuery({
    queryKey: ["analytics-status-distribution"],
    queryFn: () => analyticsApi.statusDistribution(),
  });

  const { data: workload } = useQuery({
    queryKey: ["analytics-bureau-workload"],
    queryFn: () => analyticsApi.bureauWorkload(),
  });

  const { data: aging } = useQuery({
    queryKey: ["analytics-aging-buckets"],
    queryFn: () => analyticsApi.agingBuckets(),
  });

  const { data: trend } = useQuery({
    queryKey: ["analytics-trend"],
    queryFn: () => analyticsApi.trend(30),
  });

  const { data: topInstitutions } = useQuery({
    queryKey: ["analytics-top-institutions"],
    queryFn: () => analyticsApi.topInstitutions(5),
  });

  const { data: overdueComplaints } = useQuery({
    queryKey: ["dashboard-overdue-complaints"],
    queryFn: () =>
      complaintsApi.list({
        is_overdue: true,
        page_size: 5,
        sort_by: "target_resolution_date",
        sort_order: "asc",
      }),
  });

  if (summaryError) {
    return (
      <ErrorState
        title="Failed to load dashboard metrics"
        message={(summaryError as any).message}
        retry={() => refetchSummary()}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Title & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-surface-text">
            Complaint Monitoring Dashboard
          </h1>
          <p className="text-sm text-surface-subtle mt-0.5">
            Real-time multi-bureau overview, SLA tracking, and relation insights
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/complaints/new"
            className="gov-btn-primary text-sm py-2 px-4 shadow-sm"
          >
            Register Complaint
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard
          title="Active Complaints"
          value={summary?.active_complaints ?? 0}
          icon={<FileText className="w-5 h-5" />}
          variant="primary"
          subtitle="Non-closed / resolved cases"
        />
        <KpiCard
          title="Overdue (SLA Breached)"
          value={summary?.overdue_complaints ?? 0}
          icon={<AlertTriangle className="w-5 h-5" />}
          variant={
            (summary?.overdue_complaints ?? 0) > 0 ? "danger" : "default"
          }
          subtitle="Past target resolution date"
        />
        <KpiCard
          title="Pending Relations"
          value={summary?.pending_duplicate_reviews ?? 0}
          icon={<GitCompare className="w-5 h-5" />}
          variant={
            (summary?.pending_duplicate_reviews ?? 0) > 0
              ? "warning"
              : "default"
          }
          subtitle="Requires officer review"
        />
        <KpiCard
          title="Multi-Bureau Cases"
          value={summary?.multi_bureau_cases ?? 0}
          icon={<Users2 className="w-5 h-5" />}
          variant="default"
          subtitle="Cross-bureau collaboration"
        />
        <KpiCard
          title="Avg Resolution Days"
          value={
            summary?.avg_resolution_days !== null &&
            summary?.avg_resolution_days !== undefined
              ? summary.avg_resolution_days.toFixed(1)
              : "—"
          }
          icon={<Clock className="w-5 h-5" />}
          variant="success"
          subtitle="For resolved complaints"
        />
      </div>

      {/* Charts Section: Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <div className="gov-card p-5">
          <h2 className="text-base font-semibold text-surface-text mb-1">
            Complaints by Lifecycle Status
          </h2>
          <p className="text-xs text-surface-subtle mb-4">
            Live counts across all 7 grievance lifecycle stages
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={statusDist || []}
                margin={{ top: 10, right: 10, left: -20, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="status"
                  angle={-30}
                  textAnchor="end"
                  tick={{ fontSize: 11 }}
                  interval={0}
                />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(value: any) => [value, "Complaints"]}
                  contentStyle={{
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "12px",
                  }}
                />
                <Bar dataKey="count" fill="#1e3a8a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bureau Workload */}
        <div className="gov-card p-5">
          <h2 className="text-base font-semibold text-surface-text mb-1">
            Workload by Bureau
          </h2>
          <p className="text-xs text-surface-subtle mb-4">
            Active vs Overdue distribution across AICTE Bureaus
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={workload || []}
                margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bureau_code" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "12px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
                <Bar
                  dataKey="active_count"
                  name="Active"
                  fill="#2563eb"
                  radius={[4, 4, 0, 0]}
                />
                <Bar
                  dataKey="overdue_count"
                  name="Overdue"
                  fill="#ef4444"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Section: Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Aging Buckets */}
        <div className="gov-card p-5">
          <h2 className="text-base font-semibold text-surface-text mb-1">
            Active Case Aging Buckets
          </h2>
          <p className="text-xs text-surface-subtle mb-4">
            Days elapsed since registration for open complaints
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={aging || []}
                margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bucket" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "12px",
                  }}
                />
                <Bar
                  dataKey="count"
                  fill="#d97706"
                  radius={[4, 4, 0, 0]}
                  name="Complaints"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 30-Day Registration & Resolution Trend */}
        <div className="gov-card p-5">
          <h2 className="text-base font-semibold text-surface-text mb-1">
            30-Day Intake &amp; Resolution Trend
          </h2>
          <p className="text-xs text-surface-subtle mb-4">
            Daily complaint intake vs closed / resolved volume
          </p>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={trend || []}
                margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(val) => val.slice(5)}
                />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    fontSize: "12px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
                <Line
                  type="monotone"
                  dataKey="registered"
                  stroke="#2563eb"
                  strokeWidth={2}
                  name="Registered"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="resolved"
                  stroke="#16a34a"
                  strokeWidth={2}
                  name="Resolved"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 3: Top Institutions & Urgent Overdue Cases */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Institutions by Complaints */}
        <div className="gov-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-surface-text">
                Top Institutions by Active Cases
              </h2>
              <p className="text-xs text-surface-subtle">
                Technical institutions requiring supervisory attention
              </p>
            </div>
            <Link
              to="/institutions"
              className="text-xs text-brand-600 hover:text-brand-800 font-semibold flex items-center gap-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="divide-y divide-surface-border">
            {topInstitutions && topInstitutions.length > 0 ? (
              topInstitutions.map((inst: any) => (
                <Link
                  key={inst.institution_id}
                  to={`/institutions/${inst.institution_id}`}
                  className="py-3 flex items-center justify-between hover:bg-surface-muted/60 px-2 rounded transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-surface-muted flex items-center justify-center text-surface-subtle">
                      <Building className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-surface-text group-hover:text-brand-600 transition-colors">
                        {inst.institution_name}
                      </div>
                      <div className="text-xs text-surface-subtle">
                        {inst.aicte_id} • {inst.state}
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800">
                      {inst.active_count} active
                    </span>
                  </div>
                </Link>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-surface-subtle">
                No institution complaint records available.
              </div>
            )}
          </div>
        </div>

        {/* Overdue Complaints Quick List */}
        <div className="gov-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-surface-text">
                Urgent: Overdue Complaints
              </h2>
              <p className="text-xs text-surface-subtle">
                Cases that have exceeded their target SLA resolution date
              </p>
            </div>
            <Link
              to="/complaints?is_overdue=true"
              className="text-xs text-brand-600 hover:text-brand-800 font-semibold flex items-center gap-1"
            >
              <span>View All Overdue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="divide-y divide-surface-border">
            {overdueComplaints && overdueComplaints.items.length > 0 ? (
              overdueComplaints.items.map((c: any) => (
                <Link
                  key={c.id}
                  to={`/complaints/${c.id}`}
                  className="py-3 flex items-center justify-between hover:bg-surface-muted/60 px-2 rounded transition-colors group"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-surface-text group-hover:text-brand-600 transition-colors">
                        {c.complaint_number}
                      </span>
                      <StatusBadge status={c.status} />
                      <PriorityBadge priority={c.priority} />
                    </div>
                    <div className="text-xs text-surface-subtle truncate max-w-sm mt-0.5">
                      {c.title}
                    </div>
                  </div>
                  <div className="text-right text-xs">
                    <span className="text-red-600 font-semibold">
                      Due: {formatDate(c.target_resolution_date)}
                    </span>
                  </div>
                </Link>
              ))
            ) : (
              <div className="py-8 text-center text-xs text-surface-subtle">
                No complaints are currently overdue.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
