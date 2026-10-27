import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Building2,
  MapPin,
  Mail,
  FileText,
  AlertTriangle,
  Clock,
  Calendar,
  Layers,
} from "lucide-react";
import { institutionsApi, complaintsApi } from "../api";
import { KpiCard } from "../components/KpiCard";
import { StatusBadge, PriorityBadge, BureauChip } from "../components/Badges";
import { formatDate, formatDateTime } from "../lib/utils";
import { EmptyState, ErrorState } from "../components/EmptyState";

export const InstitutionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<"complaints" | "coordination" | "timeline">("complaints");

  const {
    data: institution,
    isLoading: isInstLoading,
    error: instError,
    refetch,
  } = useQuery({
    queryKey: ["institution", id],
    queryFn: () => institutionsApi.get(id!),
    enabled: !!id,
  });

  const { data: coordinationData } = useQuery({
    queryKey: ["institution-coordination", id],
    queryFn: () => institutionsApi.getCoordination(id!),
    enabled: !!id,
  });

  const { data: timelineData } = useQuery({
    queryKey: ["institution-timeline", id],
    queryFn: () => institutionsApi.getTimeline(id!),
    enabled: !!id,
  });

  const { data: complaintsData } = useQuery({
    queryKey: ["institution-complaints", id],
    queryFn: () => complaintsApi.list({ institution_id: id, page_size: 50 }),
    enabled: !!id,
  });

  if (isInstLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-16">
        <div className="w-8 h-8 border-3 border-brand-200 border-t-brand-700 rounded-full animate-spin" />
        <span className="mt-3 text-sm text-surface-subtle">
          Loading institution details...
        </span>
      </div>
    );
  }

  if (instError || !institution) {
    return (
      <ErrorState
        title="Institution Not Found"
        message={(instError as any)?.message || "Could not retrieve the requested record."}
        retry={() => refetch()}
      />
    );
  }

  const timelineItems: any[] = timelineData?.items || (Array.isArray(timelineData) ? timelineData : []);
  const coordinationBureaus: any[] = coordinationData?.bureaus || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to="/institutions"
          className="inline-flex items-center gap-1.5 text-xs text-surface-subtle hover:text-surface-text mb-2 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Institutions</span>
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs px-2 py-0.5 rounded font-bold bg-brand-100 text-brand-800">
                {institution.aicte_id || institution.code}
              </span>
              <span className="text-xs text-surface-subtle">
                {institution.category || institution.institution_type || "Technical Institute"}
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-surface-text mt-1">
              {institution.name}
            </h1>
            <div className="text-xs text-surface-subtle flex items-center gap-1.5 mt-1">
              <MapPin className="w-3.5 h-3.5" />
              <span>
                {institution.city}, {institution.state}
              </span>
              {institution.email && (
                <>
                  <span>•</span>
                  <Mail className="w-3.5 h-3.5" />
                  <span>{institution.email}</span>
                </>
              )}
            </div>
          </div>

          <Link
            to={`/complaints/new?institution_id=${institution.id}`}
            className="gov-btn-primary text-xs py-2 px-4 shadow-sm self-start sm:self-auto"
          >
            Register Complaint for Institution
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          title="Total Grievances"
          value={institution.total_complaints_count ?? institution.total_complaints ?? 0}
          icon={<FileText className="w-5 h-5" />}
          variant="default"
        />
        <KpiCard
          title="Active Open Cases"
          value={institution.active_complaints_count ?? institution.open_count ?? 0}
          icon={<Clock className="w-5 h-5" />}
          variant={(institution.active_complaints_count ?? institution.open_count ?? 0) > 0 ? "warning" : "default"}
        />
        <KpiCard
          title="Overdue (SLA Breached)"
          value={institution.overdue_complaints_count ?? institution.overdue_count ?? 0}
          icon={<AlertTriangle className="w-5 h-5" />}
          variant={(institution.overdue_complaints_count ?? institution.overdue_count ?? 0) > 0 ? "danger" : "default"}
        />
        <KpiCard
          title="Resolved Complaints"
          value={institution.resolved_complaints_count ?? institution.resolved_count ?? 0}
          icon={<Building2 className="w-5 h-5" />}
          variant="success"
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-surface-border flex gap-4 text-sm font-medium">
        <button
          onClick={() => setActiveTab("complaints")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "complaints"
              ? "border-brand-600 text-brand-600 font-semibold"
              : "border-transparent text-surface-subtle hover:text-surface-text"
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Complaints List ({complaintsData?.total || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab("coordination")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "coordination"
              ? "border-brand-600 text-brand-600 font-semibold"
              : "border-transparent text-surface-subtle hover:text-surface-text"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Cross-Bureau Coordination ({coordinationBureaus.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("timeline")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "timeline"
              ? "border-brand-600 text-brand-600 font-semibold"
              : "border-transparent text-surface-subtle hover:text-surface-text"
          }`}
        >
          <Calendar className="w-4 h-4" />
          <span>Consolidated Timeline ({timelineItems.length})</span>
        </button>
      </div>

      {/* TAB 1: COMPLAINTS */}
      {activeTab === "complaints" && (
        <div className="gov-card divide-y divide-surface-border">
          {(!complaintsData || complaintsData.items.length === 0) ? (
            <EmptyState
              title="No complaints on record"
              description="This institution currently has no complaint filings."
            />
          ) : (
            complaintsData.items.map((c: any) => (
              <Link
                key={c.id}
                to={`/complaints/${c.id}`}
                className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-surface-muted/60 transition-colors"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-brand-700">
                      {c.complaint_number}
                    </span>
                    <StatusBadge status={c.status} />
                    <PriorityBadge priority={c.priority} />
                    <BureauChip code={c.bureau_code} />
                  </div>
                  <div className="text-xs font-medium text-surface-text mt-1">
                    {c.title}
                  </div>
                </div>
                <div className="text-right text-xs text-surface-subtle">
                  <div>Target: {formatDate(c.target_resolution_date)}</div>
                  <div className="text-[10px]">Registered: {formatDate(c.created_at)}</div>
                </div>
              </Link>
            ))
          )}
        </div>
      )}

      {/* TAB 2: COORDINATION */}
      {activeTab === "coordination" && (
        <div className="gov-card p-6 bg-white space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-surface-text">
                Multi-Bureau Coordination Summary
              </h2>
              <p className="text-xs text-surface-subtle">
                Bureaus actively managing complaints for this institution
              </p>
            </div>
            {coordinationData?.multi_bureau_open && (
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
                Multi-Bureau Active
              </span>
            )}
          </div>

          {coordinationBureaus.length === 0 ? (
            <div className="text-center py-8 text-xs text-surface-subtle bg-surface-muted/30 rounded border border-dashed border-surface-border">
              No active bureau coordination assignments recorded for this institution.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {coordinationBureaus.map((b: any) => (
                <div
                  key={b.bureau_code || b.bureau_id}
                  className="p-4 rounded-lg border border-surface-border bg-surface-muted/30 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <BureauChip code={b.bureau_code} isPrimary={b.open_as_primary > 0} />
                      <span className="text-xs font-semibold text-surface-text">
                        {b.bureau_name}
                      </span>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs pt-1 border-t border-surface-border">
                    <div>
                      <span className="text-surface-subtle">Primary Cases: </span>
                      <span className="font-bold text-surface-text">{b.open_as_primary ?? 0}</span>
                    </div>
                    <div>
                      <span className="text-surface-subtle">Participating: </span>
                      <span className="font-bold text-surface-text">{b.open_as_participating ?? 0}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CONSOLIDATED TIMELINE */}
      {activeTab === "timeline" && (
        <div className="gov-card p-6 bg-white space-y-4">
          <h2 className="text-base font-semibold text-surface-text">
            Consolidated Grievance Timeline
          </h2>
          <p className="text-xs text-surface-subtle">
            Unified chronological audit of complaint registrations, status updates, and resolutions across all bureaus
          </p>

          <div className="relative pl-6 border-l-2 border-brand-200 space-y-6 pt-2">
            {timelineItems.length > 0 ? (
              timelineItems.map((event: any, idx: number) => (
                <div key={idx} className="relative">
                  {/* Timeline dot */}
                  <div className="absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full bg-brand-600 ring-4 ring-white" />

                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-semibold text-surface-text">
                        {event.event_type}
                      </span>
                      {event.bureau_code && <BureauChip code={event.bureau_code} />}
                      <span className="text-surface-subtle">
                        {formatDateTime(event.timestamp)}
                      </span>
                    </div>

                    <div className="text-xs text-surface-text">
                      {event.description}
                    </div>

                    {event.complaint_number && (
                      <Link
                        to={`/complaints/${event.complaint_id}`}
                        className="text-[11px] font-mono font-medium text-brand-600 hover:underline inline-block mt-0.5"
                      >
                        Ref: {event.complaint_number}
                      </Link>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-xs text-surface-subtle py-4">
                No events recorded on this institution timeline.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
