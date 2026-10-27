import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  AlertTriangle,
  GitCompare,
  MessageSquare,
  FileText,
  History,
  CheckCircle,
  Share2,
  RefreshCw,
} from "lucide-react";
import { complaintsApi, relationsApi, bureausApi } from "../api";
import { useAuth } from "../auth/useAuth";
import {
  StatusBadge,
  PriorityBadge,
  OverdueBadge,
  EscalationBadge,
  BureauChip,
  AccessLevelNotice,
} from "../components/Badges";
import { formatDate, formatDateTime } from "../lib/utils";
import { ConfirmModal } from "../components/ConfirmModal";
import { MatchExplanationCard } from "../components/MatchExplanationCard";
import { EmptyState, ErrorState } from "../components/EmptyState";

export const ComplaintDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [activeTab, setActiveTab] = useState<
    "overview" | "actions" | "coordination" | "relations" | "notes" | "history"
  >("overview");

  // Action modals
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [targetStatus, setTargetStatus] = useState<string>("");
  const [statusReason, setStatusReason] = useState("");
  const [resolutionSummary, setResolutionSummary] = useState("");

  const [addParticipantModalOpen, setAddParticipantModalOpen] = useState(false);
  const [selectedBureau, setSelectedBureau] = useState("");
  const [assignmentReason, setAssignmentReason] = useState("");

  const [transferPrimaryModalOpen, setTransferPrimaryModalOpen] = useState(false);
  const [transferBureau, setTransferBureau] = useState("");
  const [transferReason, setTransferReason] = useState("");

  const [confirmRelationModalOpen, setConfirmRelationModalOpen] = useState(false);
  const [selectedRelationId, setSelectedRelationId] = useState<string>("");
  const [relationType, setRelationType] = useState<"DUPLICATE" | "RELATED_INCIDENT" | "FOLLOW_UP">("RELATED_INCIDENT");
  const [autoParticipate, setAutoParticipate] = useState(true);
  const [relationNotes, setRelationNotes] = useState("");

  const [dismissRelationModalOpen, setDismissRelationModalOpen] = useState(false);
  const [dismissReason, setDismissReason] = useState("");

  const [newNoteContent, setNewNoteContent] = useState("");
  const [isNoteSubmitting, setIsNoteSubmitting] = useState(false);

  // Queries
  const {
    data: complaint,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["complaint", id],
    queryFn: () => complaintsApi.get(id!),
    enabled: !!id,
  });

  const { data: bureausData } = useQuery({
    queryKey: ["bureaus-list"],
    queryFn: () => bureausApi.list(),
  });

  const { data: relationsData, refetch: refetchRelations } = useQuery({
    queryKey: ["complaint-relations", id],
    queryFn: () => relationsApi.getForComplaint(id!),
    enabled: !!id,
  });

  // Mutations
  const statusMutation = useMutation({
    mutationFn: (vars: { status: string; reason: string; resolution_summary?: string }) =>
      complaintsApi.updateStatus(id!, {
        new_status: vars.status,
        reason: vars.reason,
        resolution_summary: vars.resolution_summary,
        version: complaint?.version ?? 1,
      }),
    onSuccess: () => {
      setStatusModalOpen(false);
      setStatusReason("");
      setResolutionSummary("");
      queryClient.invalidateQueries({ queryKey: ["complaint", id] });
      queryClient.invalidateQueries({ queryKey: ["complaints"] });
      queryClient.invalidateQueries({ queryKey: ["analytics-summary"] });
    },
    onError: (err: any) => {
      alert("Status update failed: " + (err.message || "Unknown error"));
    },
  });

  const escalateMutation = useMutation({
    mutationFn: () =>
      complaintsApi.escalate(id!, {
        reason: "Escalated for immediate supervisory review.",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["complaint", id] });
    },
  });

  const addParticipantMutation = useMutation({
    mutationFn: () =>
      complaintsApi.addParticipant(id!, {
        bureau_code: selectedBureau,
        reason: assignmentReason,
      }),
    onSuccess: () => {
      setAddParticipantModalOpen(false);
      setSelectedBureau("");
      setAssignmentReason("");
      queryClient.invalidateQueries({ queryKey: ["complaint", id] });
    },
    onError: (err: any) => {
      alert("Failed to add participant: " + err.message);
    },
  });

  const transferPrimaryMutation = useMutation({
    mutationFn: () =>
      complaintsApi.transferPrimary(id!, {
        new_bureau_code: transferBureau,
        reason: transferReason,
      }),
    onSuccess: () => {
      setTransferPrimaryModalOpen(false);
      setTransferBureau("");
      setTransferReason("");
      queryClient.invalidateQueries({ queryKey: ["complaint", id] });
    },
    onError: (err: any) => {
      alert("Transfer failed: " + err.message);
    },
  });

  const confirmRelationMutation = useMutation({
    mutationFn: () =>
      relationsApi.confirm(selectedRelationId, {
        relation_type: relationType,
        auto_add_participating_bureau: autoParticipate,
        notes: relationNotes,
      }),
    onSuccess: () => {
      setConfirmRelationModalOpen(false);
      setRelationNotes("");
      refetchRelations();
      queryClient.invalidateQueries({ queryKey: ["complaint", id] });
    },
    onError: (err: any) => {
      alert("Failed to confirm relation: " + err.message);
    },
  });

  const dismissRelationMutation = useMutation({
    mutationFn: () =>
      relationsApi.dismiss(selectedRelationId, {
        reason: dismissReason,
      }),
    onSuccess: () => {
      setDismissRelationModalOpen(false);
      setDismissReason("");
      refetchRelations();
    },
    onError: (err: any) => {
      alert("Failed to dismiss relation: " + err.message);
    },
  });

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteContent.trim()) return;
    setIsNoteSubmitting(true);
    try {
      await complaintsApi.addNote(id!, { content: newNoteContent.trim() });
      setNewNoteContent("");
      queryClient.invalidateQueries({ queryKey: ["complaint", id] });
    } catch (err: any) {
      alert("Failed to add note: " + err.message);
    } finally {
      setIsNoteSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-16">
        <div className="w-8 h-8 border-3 border-brand-200 border-t-brand-700 rounded-full animate-spin" />
        <span className="mt-3 text-sm text-surface-subtle">
          Loading complaint details...
        </span>
      </div>
    );
  }

  if (error || !complaint) {
    return (
      <ErrorState
        title="Complaint Not Found"
        message={(error as any)?.message || "Could not retrieve the requested record."}
        retry={() => refetch()}
      />
    );
  }

  const allowedActions: string[] = complaint.allowed_actions || [];
  const assignments: any[] = complaint.assignments || [];
  const primaryAssignment = assignments.find((a) => a.role_in_case === "PRIMARY");
  const notes: any[] = complaint.notes || [];
  const history: any[] = complaint.status_history || [];

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Quick Info Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Link
            to="/complaints"
            className="inline-flex items-center gap-1.5 text-xs text-surface-subtle hover:text-surface-text mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Complaints</span>
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-mono font-bold tracking-tight text-surface-text">
              {complaint.complaint_number}
            </h1>
            <StatusBadge status={complaint.status} />
            <PriorityBadge priority={complaint.priority} />
            <OverdueBadge isOverdue={complaint.is_overdue} />
            <EscalationBadge isEscalated={complaint.is_escalated} />
          </div>
          <p className="text-sm text-surface-subtle mt-1 font-medium">
            {complaint.title}
          </p>
        </div>

        {/* Quick action buttons */}
        <div className="flex items-center gap-2">
          {allowedActions.includes("ESCALATE") && !complaint.is_escalated && (
            <button
              onClick={() => escalateMutation.mutate()}
              disabled={escalateMutation.isPending}
              className="gov-btn-secondary text-xs py-2 px-3 text-red-700 hover:bg-red-50 border-red-200"
            >
              <AlertTriangle className="w-3.5 h-3.5 mr-1" />
              <span>Escalate Case</span>
            </button>
          )}

          <button
            onClick={() => refetch()}
            className="p-2 rounded border border-surface-border text-surface-subtle hover:text-surface-text"
            title="Refresh record"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Access Level Notice if Read-Only */}
      {complaint.user_access_level === "READ_ONLY" && (
        <AccessLevelNotice accessLevel="READ_ONLY" />
      )}

      {/* Detail Tabs */}
      <div className="border-b border-surface-border flex gap-4 text-sm font-medium">
        <button
          onClick={() => setActiveTab("overview")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "overview"
              ? "border-brand-600 text-brand-600 font-semibold"
              : "border-transparent text-surface-subtle hover:text-surface-text"
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Overview</span>
        </button>

        <button
          onClick={() => setActiveTab("actions")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "actions"
              ? "border-brand-600 text-brand-600 font-semibold"
              : "border-transparent text-surface-subtle hover:text-surface-text"
          }`}
        >
          <CheckCircle className="w-4 h-4" />
          <span>Status &amp; Actions ({allowedActions.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("coordination")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "coordination"
              ? "border-brand-600 text-brand-600 font-semibold"
              : "border-transparent text-surface-subtle hover:text-surface-text"
          }`}
        >
          <Share2 className="w-4 h-4" />
          <span>Coordination ({assignments.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("relations")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "relations"
              ? "border-brand-600 text-brand-600 font-semibold"
              : "border-transparent text-surface-subtle hover:text-surface-text"
          }`}
        >
          <GitCompare className="w-4 h-4" />
          <span>Related Grievances ({relationsData?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab("notes")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "notes"
              ? "border-brand-600 text-brand-600 font-semibold"
              : "border-transparent text-surface-subtle hover:text-surface-text"
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Case Notes ({notes.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("history")}
          className={`pb-3 px-1 border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === "history"
              ? "border-brand-600 text-brand-600 font-semibold"
              : "border-transparent text-surface-subtle hover:text-surface-text"
          }`}
        >
          <History className="w-4 h-4" />
          <span>Lifecycle History ({history.length})</span>
        </button>
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="gov-card p-6 bg-white space-y-4">
              <h2 className="text-base font-semibold text-surface-text">
                Complaint Particulars
              </h2>
              <div>
                <div className="text-xs text-surface-subtle">Category</div>
                <div className="text-sm font-semibold capitalize mt-0.5">
                  {complaint.category.replace(/_/g, " ")}
                </div>
              </div>
              <div>
                <div className="text-xs text-surface-subtle">Full Description</div>
                <div className="text-sm text-surface-text mt-1 p-3 bg-surface-muted/50 rounded-md border border-surface-border whitespace-pre-wrap leading-relaxed">
                  {complaint.description}
                </div>
              </div>

              {complaint.resolution_summary && (
                <div className="p-3 bg-emerald-50 rounded-md border border-emerald-200">
                  <div className="text-xs font-bold text-emerald-900">
                    Resolution Summary
                  </div>
                  <div className="text-sm text-emerald-800 mt-1">
                    {complaint.resolution_summary}
                  </div>
                </div>
              )}
            </div>

            <div className="gov-card p-6 bg-white space-y-3">
              <h2 className="text-base font-semibold text-surface-text">
                Institution Under Complaint
              </h2>
              <div className="flex items-start justify-between">
                <div>
                  <Link
                    to={`/institutions/${complaint.institution_id}`}
                    className="text-sm font-bold text-brand-700 hover:underline"
                  >
                    {complaint.institution_name}
                  </Link>
                  <div className="text-xs text-surface-subtle mt-0.5">
                    AICTE ID: {complaint.institution_aicte_id}
                  </div>
                </div>
                <Link
                  to={`/institutions/${complaint.institution_id}`}
                  className="gov-btn-secondary text-xs py-1.5 px-3"
                >
                  View Institution Profile
                </Link>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {/* SLA & Timestamps Card */}
            <div className="gov-card p-6 bg-white space-y-4">
              <h2 className="text-sm font-bold text-surface-text uppercase tracking-wider">
                SLA &amp; Timestamps
              </h2>
              <div className="space-y-3 text-xs">
                <div className="flex justify-between py-1 border-b border-surface-border">
                  <span className="text-surface-subtle">Registered On:</span>
                  <span className="font-medium text-surface-text">
                    {formatDateTime(complaint.created_at)}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border">
                  <span className="text-surface-subtle">Incident Date:</span>
                  <span className="font-medium text-surface-text">
                    {formatDate(complaint.incident_date)}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border">
                  <span className="text-surface-subtle">Target Resolution:</span>
                  <span className="font-semibold text-surface-text">
                    {formatDate(complaint.target_resolution_date)}
                  </span>
                </div>
                <div className="flex justify-between py-1 border-b border-surface-border">
                  <span className="text-surface-subtle">Last Updated:</span>
                  <span className="font-medium text-surface-text">
                    {formatDateTime(complaint.updated_at)}
                  </span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-surface-subtle">Optimistic Lock (Ver):</span>
                  <span className="font-mono text-surface-text">
                    v{complaint.version}
                  </span>
                </div>
              </div>
            </div>

            {/* Complainant Card */}
            <div className="gov-card p-6 bg-white space-y-3">
              <h2 className="text-sm font-bold text-surface-text uppercase tracking-wider">
                Complainant Info
              </h2>
              <div className="space-y-2 text-xs">
                <div>
                  <span className="text-surface-subtle">Name:</span>
                  <div className="font-medium text-surface-text">
                    {complaint.complainant_name || "Anonymous / Confidential"}
                  </div>
                </div>
                <div>
                  <span className="text-surface-subtle">Email:</span>
                  <div className="font-medium text-surface-text">
                    {complaint.complainant_email || "Not provided"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: STATUS & ACTIONS */}
      {activeTab === "actions" && (
        <div className="gov-card p-6 bg-white space-y-6">
          <div>
            <h2 className="text-base font-semibold text-surface-text">
              Status Lifecycle Actions
            </h2>
            <p className="text-xs text-surface-subtle mt-0.5">
              Available actions governed by strict RBAC and participant matrix
            </p>
          </div>

          <div className="p-4 bg-surface-muted rounded-md border border-surface-border flex items-center justify-between">
            <div>
              <div className="text-xs text-surface-subtle">Current Status</div>
              <div className="mt-1">
                <StatusBadge status={complaint.status} />
              </div>
            </div>
            <div>
              <div className="text-xs text-surface-subtle">Assigned Bureau</div>
              <div className="mt-1">
                <BureauChip code={primaryAssignment?.bureau_code || "—"} />
              </div>
            </div>
          </div>

          {/* Action buttons list based on backend allowed_actions */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-surface-subtle">
              Allowed Status Transitions
            </h3>

            {allowedActions.length === 0 ? (
              <div className="text-xs text-surface-subtle italic p-4 bg-slate-50 rounded border border-slate-200">
                No status transitions are currently permitted for your role / participation level.
              </div>
            ) : (
              <div className="flex flex-wrap gap-3">
                {allowedActions.map((action) => {
                  // Map action to next status
                  const actionMap: Record<string, { status: string; label: string; variant: string }> = {
                    REVIEW: { status: "UNDER_REVIEW", label: "Mark Under Review", variant: "gov-btn-secondary" },
                    ASSIGN: { status: "ASSIGNED", label: "Assign Bureau Official", variant: "gov-btn-secondary" },
                    INVESTIGATE: { status: "IN_INVESTIGATION", label: "Commence Investigation", variant: "gov-btn-primary" },
                    REQUEST_INFO: { status: "PENDING_INSTITUTION_ACTION", label: "Request Institution Info", variant: "gov-btn-secondary" },
                    RESOLVE: { status: "RESOLVED", label: "Mark as Resolved", variant: "gov-btn-primary" },
                    CLOSE: { status: "CLOSED", label: "Formal Closure (Supervisor)", variant: "gov-btn-primary" },
                    REOPEN: { status: "UNDER_REVIEW", label: "Reopen Case", variant: "gov-btn-secondary" },
                  };

                  const cfg = actionMap[action];
                  if (!cfg) return null;

                  return (
                    <button
                      key={action}
                      onClick={() => {
                        setTargetStatus(cfg.status);
                        setStatusModalOpen(true);
                      }}
                      className={`${cfg.variant} text-xs py-2 px-4 shadow-sm`}
                    >
                      {cfg.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: COORDINATION */}
      {activeTab === "coordination" && (
        <div className="space-y-6">
          <div className="gov-card p-6 bg-white">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-surface-text">
                  Multi-Bureau Case Assignments
                </h2>
                <p className="text-xs text-surface-subtle">
                  Participating bureaus have full collaboration visibility
                </p>
              </div>

              {(user?.role === "SUPERVISOR" || user?.role === "SYSTEM_ADMIN") && (
                <div className="flex gap-2">
                  <button
                    onClick={() => setAddParticipantModalOpen(true)}
                    className="gov-btn-secondary text-xs py-1.5 px-3"
                  >
                    + Add Participating Bureau
                  </button>
                  <button
                    onClick={() => setTransferPrimaryModalOpen(true)}
                    className="gov-btn-secondary text-xs py-1.5 px-3"
                  >
                    Transfer Primary Bureau
                  </button>
                </div>
              )}
            </div>

            <div className="divide-y divide-surface-border">
              {assignments.map((asgn: any) => (
                <div
                  key={asgn.id}
                  className="py-3 flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-3">
                    <BureauChip code={asgn.bureau_code} />
                    <div>
                      <div className="font-semibold text-surface-text">
                        Bureau {asgn.bureau_code}
                      </div>
                      <div className="text-surface-subtle">
                        {asgn.assigned_official_name
                          ? `Official: ${asgn.assigned_official_name}`
                          : "No individual official assigned yet"}
                      </div>
                      {asgn.reason && (
                        <div className="text-[11px] text-surface-subtle italic mt-0.5">
                          "{asgn.reason}"
                        </div>
                      )}
                    </div>
                  </div>

                  <div>
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        asgn.role_in_case === "PRIMARY"
                          ? "bg-brand-100 text-brand-800 border border-brand-300"
                          : "bg-surface-muted text-surface-subtle border border-surface-border"
                      }`}
                    >
                      {asgn.role_in_case}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: RELATIONS */}
      {activeTab === "relations" && (
        <div className="space-y-6">
          <div className="gov-card p-6 bg-white">
            <h2 className="text-base font-semibold text-surface-text mb-1">
              Duplicate &amp; Related Grievance Records
            </h2>
            <p className="text-xs text-surface-subtle mb-4">
              Flagged by Algorithm v1.0 based on text similarity, incident references, and domain terminology
            </p>

            {(!relationsData || relationsData.length === 0) ? (
              <EmptyState
                title="No related complaints flagged"
                description="The algorithm detected no overlapping complaints for this institution."
              />
            ) : (
              <div className="space-y-6">
                {relationsData.map((rel: any) => {
                  const otherComplaintId =
                    rel.complaint_a_id === id ? rel.complaint_b_id : rel.complaint_a_id;
                  const otherComplaintNumber =
                    rel.complaint_a_id === id
                      ? rel.complaint_b_number
                      : rel.complaint_a_number;

                  return (
                    <div
                      key={rel.id}
                      className="border border-surface-border rounded-lg p-4 space-y-4 bg-white shadow-xs"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
                        <div className="flex items-center gap-3">
                          <Link
                            to={`/complaints/${otherComplaintId}`}
                            className="font-mono text-sm font-bold text-brand-700 hover:underline"
                          >
                            {otherComplaintNumber || "Related Complaint"}
                          </Link>
                          <span className="text-xs px-2 py-0.5 rounded font-semibold bg-surface-muted text-surface-text border border-surface-border">
                            {rel.status}
                          </span>
                          {rel.relation_type && (
                            <span className="text-xs px-2 py-0.5 rounded font-semibold bg-blue-100 text-blue-800">
                              {rel.relation_type}
                            </span>
                          )}
                        </div>

                        {/* Review Action Buttons */}
                        {rel.status === "PENDING_REVIEW" && (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => {
                                setSelectedRelationId(rel.id);
                                setConfirmRelationModalOpen(true);
                              }}
                              className="gov-btn-primary text-xs py-1.5 px-3"
                            >
                              Confirm Relation
                            </button>
                            <button
                              onClick={() => {
                                setSelectedRelationId(rel.id);
                                setDismissRelationModalOpen(true);
                              }}
                              className="gov-btn-secondary text-xs py-1.5 px-3 text-red-600 hover:bg-red-50 border-red-200"
                            >
                              Dismiss
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Explanation Card */}
                      <MatchExplanationCard
                        score={rel.score}
                        explanation={rel.explanation}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: CASE NOTES */}
      {activeTab === "notes" && (
        <div className="gov-card p-6 bg-white space-y-6">
          <h2 className="text-base font-semibold text-surface-text">
            Investigation &amp; Case Notes
          </h2>

          {/* Add note input */}
          <form onSubmit={handleAddNote} className="space-y-3">
            <textarea
              rows={3}
              value={newNoteContent}
              onChange={(e) => setNewNoteContent(e.target.value)}
              placeholder="Record investigation findings, meeting minutes, or coordination updates..."
              className="gov-input text-xs"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isNoteSubmitting || !newNoteContent.trim()}
                className="gov-btn-primary text-xs py-1.5 px-4 disabled:opacity-50"
              >
                {isNoteSubmitting ? "Posting..." : "Add Case Note"}
              </button>
            </div>
          </form>

          {/* Notes list */}
          <div className="divide-y divide-surface-border pt-4">
            {notes.length === 0 ? (
              <div className="text-center py-8 text-xs text-surface-subtle">
                No case notes have been recorded yet.
              </div>
            ) : (
              notes.map((note: any) => (
                <div key={note.id} className="py-4 space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-surface-text">
                        {note.author_name}
                      </span>
                      {note.author_bureau && (
                        <BureauChip code={note.author_bureau} />
                      )}
                    </div>
                    <span className="text-surface-subtle">
                      {formatDateTime(note.created_at)}
                    </span>
                  </div>
                  <div className="text-xs text-surface-text whitespace-pre-wrap leading-relaxed mt-1">
                    {note.content}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 6: STATUS HISTORY */}
      {activeTab === "history" && (
        <div className="gov-card p-6 bg-white space-y-4">
          <h2 className="text-base font-semibold text-surface-text">
            Complaint Lifecycle History
          </h2>
          <div className="divide-y divide-surface-border">
            {history.map((hist: any) => (
              <div
                key={hist.id}
                className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-surface-subtle">
                      {hist.from_status || "START"}
                    </span>
                    <span>→</span>
                    <StatusBadge status={hist.to_status} />
                  </div>
                  {hist.reason && (
                    <div className="text-[11px] text-surface-subtle mt-1 italic">
                      "{hist.reason}"
                    </div>
                  )}
                </div>
                <div className="text-right text-surface-subtle">
                  <div>Changed by: {hist.changed_by_name || "System"}</div>
                  <div className="text-[10px]">{formatDateTime(hist.created_at)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STATUS TRANSITION MODAL */}
      <ConfirmModal
        isOpen={statusModalOpen}
        title={`Transition Status to ${targetStatus}`}
        confirmLabel="Update Status"
        isLoading={statusMutation.isPending}
        onConfirm={() =>
          statusMutation.mutate({
            status: targetStatus,
            reason: statusReason,
            resolution_summary: resolutionSummary || undefined,
          })
        }
        onClose={() => setStatusModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="gov-label" htmlFor="statusReason">
              Transition Reason / Comments <span className="text-red-500">*</span>
            </label>
            <textarea
              id="statusReason"
              required
              rows={3}
              value={statusReason}
              onChange={(e) => setStatusReason(e.target.value)}
              placeholder="State the reason or justification for this status change..."
              className="gov-input text-xs"
            />
          </div>

          {(targetStatus === "RESOLVED" || targetStatus === "CLOSED") && (
            <div>
              <label className="gov-label" htmlFor="resolutionSummary">
                Resolution Summary
              </label>
              <textarea
                id="resolutionSummary"
                rows={3}
                value={resolutionSummary}
                onChange={(e) => setResolutionSummary(e.target.value)}
                placeholder="Final summary of actions taken and remedial measures..."
                className="gov-input text-xs"
              />
            </div>
          )}
        </div>
      </ConfirmModal>

      {/* ADD PARTICIPANT MODAL */}
      <ConfirmModal
        isOpen={addParticipantModalOpen}
        title="Add Participating Bureau"
        confirmLabel="Add Bureau"
        isLoading={addParticipantMutation.isPending}
        onConfirm={() => addParticipantMutation.mutate()}
        onClose={() => setAddParticipantModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="gov-label" htmlFor="partBureau">
              Select Bureau
            </label>
            <select
              id="partBureau"
              value={selectedBureau}
              onChange={(e) => setSelectedBureau(e.target.value)}
              className="gov-input text-xs"
            >
              <option value="">Select...</option>
              {bureausData?.map((b: any) => (
                <option key={b.code} value={b.code}>
                  {b.code} - {b.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="gov-label" htmlFor="partReason">
              Reason for Collaboration
            </label>
            <input
              id="partReason"
              type="text"
              value={assignmentReason}
              onChange={(e) => setAssignmentReason(e.target.value)}
              placeholder="e.g. Cross-bureau jurisdictional concern"
              className="gov-input text-xs"
            />
          </div>
        </div>
      </ConfirmModal>

      {/* TRANSFER PRIMARY BUREAU MODAL */}
      <ConfirmModal
        isOpen={transferPrimaryModalOpen}
        title="Transfer Primary Bureau"
        variant="warning"
        confirmLabel="Transfer Jurisdiction"
        isLoading={transferPrimaryMutation.isPending}
        onConfirm={() => transferPrimaryMutation.mutate()}
        onClose={() => setTransferPrimaryModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="gov-label" htmlFor="transBureau">
              New Primary Bureau
            </label>
            <select
              id="transBureau"
              value={transferBureau}
              onChange={(e) => setTransferBureau(e.target.value)}
              className="gov-input text-xs"
            >
              <option value="">Select...</option>
              {bureausData?.map((b: any) => (
                <option key={b.code} value={b.code}>
                  {b.code} - {b.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="gov-label" htmlFor="transReason">
              Transfer Justification
            </label>
            <input
              id="transReason"
              type="text"
              value={transferReason}
              onChange={(e) => setTransferReason(e.target.value)}
              placeholder="e.g. Primary scope pertains to Approval Bureau"
              className="gov-input text-xs"
            />
          </div>
        </div>
      </ConfirmModal>

      {/* CONFIRM RELATION MODAL */}
      <ConfirmModal
        isOpen={confirmRelationModalOpen}
        title="Confirm Grievance Relation"
        confirmLabel="Confirm Relation"
        isLoading={confirmRelationMutation.isPending}
        onConfirm={() => confirmRelationMutation.mutate()}
        onClose={() => setConfirmRelationModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="gov-label" htmlFor="relType">
              Relation Classification
            </label>
            <select
              id="relType"
              value={relationType}
              onChange={(e) => setRelationType(e.target.value as any)}
              className="gov-input text-xs"
            >
              <option value="RELATED_INCIDENT">Related Incident (Shared matter)</option>
              <option value="DUPLICATE">Duplicate Complaint</option>
              <option value="FOLLOW_UP">Follow-up Communication</option>
            </select>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoParticipate}
              onChange={(e) => setAutoParticipate(e.target.checked)}
              className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-surface-text font-medium">
              Automatically add participating bureaus to each other's cases
            </span>
          </label>

          <div>
            <label className="gov-label" htmlFor="relNotes">
              Reviewer Notes
            </label>
            <textarea
              id="relNotes"
              rows={2}
              value={relationNotes}
              onChange={(e) => setRelationNotes(e.target.value)}
              placeholder="Notes on why this relation was confirmed..."
              className="gov-input text-xs"
            />
          </div>
        </div>
      </ConfirmModal>

      {/* DISMISS RELATION MODAL */}
      <ConfirmModal
        isOpen={dismissRelationModalOpen}
        title="Dismiss Grievance Relation"
        variant="danger"
        confirmLabel="Dismiss Flag"
        isLoading={dismissRelationMutation.isPending}
        onConfirm={() => dismissRelationMutation.mutate()}
        onClose={() => setDismissRelationModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="gov-label" htmlFor="dismReason">
              Dismissal Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              id="dismReason"
              required
              rows={3}
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              placeholder="Explain why this candidate is not related (e.g. Distinct student cohorts)..."
              className="gov-input text-xs"
            />
          </div>
        </div>
      </ConfirmModal>
    </div>
  );
};
