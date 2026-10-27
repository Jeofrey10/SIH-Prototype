import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { GitCompare, CheckCircle2, XCircle, RotateCcw } from "lucide-react";
import { relationsApi } from "../api";
import { useAuth } from "../auth/useAuth";
import { MatchExplanationCard } from "../components/MatchExplanationCard";
import { ConfirmModal } from "../components/ConfirmModal";
import { EmptyState, ErrorState } from "../components/EmptyState";
import { formatDate } from "../lib/utils";

export const RelationsQueuePage: React.FC = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [statusFilter, setStatusFilter] = useState<string>("PENDING_REVIEW");
  const [minScore, setMinScore] = useState<number>(35);
  const [page, setPage] = useState<number>(1);
  const pageSize = 10;

  // Review Modals State
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [dismissModalOpen, setDismissModalOpen] = useState(false);
  const [revertModalOpen, setRevertModalOpen] = useState(false);
  const [activeRelationId, setActiveRelationId] = useState<string>("");

  const [relationType, setRelationType] = useState<"DUPLICATE" | "RELATED_INCIDENT" | "FOLLOW_UP">("RELATED_INCIDENT");
  const [autoParticipate, setAutoParticipate] = useState(true);
  const [confirmNotes, setConfirmNotes] = useState("");
  const [dismissReason, setDismissReason] = useState("");
  const [revertReason, setRevertReason] = useState("");

  const {
    data: queueData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["relations-queue", statusFilter, minScore, page, pageSize],
    queryFn: () =>
      relationsApi.queue({
        status: statusFilter || undefined,
        min_score: minScore,
        page,
        page_size: pageSize,
      }),
  });

  const confirmMutation = useMutation({
    mutationFn: () =>
      relationsApi.confirm(activeRelationId, {
        relation_type: relationType,
        auto_add_participating_bureau: autoParticipate,
        notes: confirmNotes,
      }),
    onSuccess: () => {
      setConfirmModalOpen(false);
      setConfirmNotes("");
      queryClient.invalidateQueries({ queryKey: ["relations-queue"] });
      queryClient.invalidateQueries({ queryKey: ["pending-relations-count"] });
    },
    onError: (err: any) => {
      alert("Failed to confirm relation: " + err.message);
    },
  });

  const dismissMutation = useMutation({
    mutationFn: () =>
      relationsApi.dismiss(activeRelationId, {
        reason: dismissReason,
      }),
    onSuccess: () => {
      setDismissModalOpen(false);
      setDismissReason("");
      queryClient.invalidateQueries({ queryKey: ["relations-queue"] });
      queryClient.invalidateQueries({ queryKey: ["pending-relations-count"] });
    },
    onError: (err: any) => {
      alert("Failed to dismiss relation: " + err.message);
    },
  });

  const revertMutation = useMutation({
    mutationFn: () =>
      relationsApi.revert(activeRelationId, {
        reason: revertReason,
      }),
    onSuccess: () => {
      setRevertModalOpen(false);
      setRevertReason("");
      queryClient.invalidateQueries({ queryKey: ["relations-queue"] });
      queryClient.invalidateQueries({ queryKey: ["pending-relations-count"] });
    },
    onError: (err: any) => {
      alert("Failed to revert relation: " + err.message);
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-surface-text">
            Duplicate &amp; Related Grievance Queue
          </h1>
          <p className="text-sm text-surface-subtle mt-0.5">
            Algorithm v1.0 automated relationship review pipeline (Score ≥ 35)
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="gov-card p-4 bg-white flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <label className="font-medium text-surface-subtle">Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="gov-input text-xs py-1.5 w-auto"
          >
            <option value="PENDING_REVIEW">Pending Review</option>
            <option value="CONFIRMED">Confirmed</option>
            <option value="DISMISSED">Dismissed</option>
            <option value="">All Statuses</option>
          </select>

          <label className="font-medium text-surface-subtle ml-2">Min Score:</label>
          <select
            value={minScore}
            onChange={(e) => {
              setMinScore(parseInt(e.target.value, 10));
              setPage(1);
            }}
            className="gov-input text-xs py-1.5 w-auto"
          >
            <option value="35">35+ (All Matches)</option>
            <option value="50">50+ (Moderate)</option>
            <option value="70">70+ (High Similarity)</option>
            <option value="85">85+ (Potential Duplicates)</option>
          </select>
        </div>

        <div className="text-xs text-surface-subtle">
          Total Flagged:{" "}
          <span className="font-semibold text-surface-text">
            {queueData?.total || 0}
          </span>
        </div>
      </div>

      {/* Relations Cards List */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center p-16">
          <div className="w-8 h-8 border-3 border-brand-200 border-t-brand-700 rounded-full animate-spin" />
          <span className="mt-3 text-sm text-surface-subtle">
            Loading relations queue...
          </span>
        </div>
      ) : error ? (
        <ErrorState
          title="Failed to load relations queue"
          message={(error as any)?.message}
          retry={() => refetch()}
        />
      ) : queueData?.items.length === 0 ? (
        <EmptyState
          title="No candidates in queue"
          description={`No complaints found matching status '${statusFilter || "any"}' with score ≥ ${minScore}.`}
        />
      ) : (
        <div className="space-y-6">
          {queueData?.items.map((rel: any) => (
            <div
              key={rel.id}
              className="gov-card p-6 bg-white border-surface-border shadow-xs space-y-4"
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-surface-border gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-brand-50 flex items-center justify-center text-brand-700">
                    <GitCompare className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-xs text-surface-subtle">
                      Flagged on {formatDate(rel.created_at)}
                    </div>
                    <div className="text-sm font-semibold text-surface-text">
                      Institution: {rel.institution_name || "Technical Institute"}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded text-xs font-bold ${
                      rel.status === "PENDING_REVIEW"
                        ? "bg-amber-100 text-amber-800 border border-amber-300"
                        : rel.status === "CONFIRMED"
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        : "bg-slate-100 text-slate-700 border border-slate-300"
                    }`}
                  >
                    {rel.status}
                  </span>

                  {rel.relation_type && (
                    <span className="px-2 py-1 rounded text-xs font-semibold bg-blue-100 text-blue-800">
                      {rel.relation_type}
                    </span>
                  )}
                </div>
              </div>

              {/* Side-by-Side Comparison of Complaint A & Complaint B */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-surface-muted/30 p-4 rounded-lg border border-surface-border">
                {/* Complaint A */}
                <div className="space-y-2">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-surface-subtle">
                    Source Grievance
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/complaints/${rel.complaint_a_id}`}
                      className="font-mono text-sm font-bold text-brand-700 hover:underline"
                    >
                      {rel.complaint_a_number}
                    </Link>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-white border border-surface-border">
                      {rel.complaint_a_status}
                    </span>
                  </div>
                  <div className="text-xs font-medium text-surface-text">
                    {rel.complaint_a_title}
                  </div>
                </div>

                {/* Complaint B */}
                <div className="space-y-2 md:border-l md:border-surface-border md:pl-4">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-surface-subtle">
                    Candidate Grievance
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/complaints/${rel.complaint_b_id}`}
                      className="font-mono text-sm font-bold text-brand-700 hover:underline"
                    >
                      {rel.complaint_b_number}
                    </Link>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-white border border-surface-border">
                      {rel.complaint_b_status}
                    </span>
                  </div>
                  <div className="text-xs font-medium text-surface-text">
                    {rel.complaint_b_title}
                  </div>
                </div>
              </div>

              {/* Match Explanation Breakdown */}
              <MatchExplanationCard
                score={rel.score}
                explanation={rel.explanation}
              />

              {/* Reviewer / Decision Details if already reviewed */}
              {rel.reviewed_by_name && (
                <div className="p-3 bg-surface-muted rounded text-xs text-surface-subtle flex flex-col sm:flex-row justify-between gap-1">
                  <div>
                    Reviewed by:{" "}
                    <span className="font-semibold text-surface-text">
                      {rel.reviewed_by_name}
                    </span>
                    {rel.notes && ` • Notes: "${rel.notes}"`}
                  </div>
                  <div>Reviewed at: {formatDate(rel.reviewed_at)}</div>
                </div>
              )}

              {/* Actions Footer */}
              <div className="flex items-center justify-end gap-3 pt-2">
                {rel.status === "PENDING_REVIEW" && (
                  <>
                    <button
                      type="button"
                      onClick={() => {
                        setActiveRelationId(rel.id);
                        setDismissModalOpen(true);
                      }}
                      className="gov-btn-secondary text-xs py-2 px-3 text-red-600 hover:bg-red-50 border-red-200 flex items-center gap-1.5"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Dismiss Match</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        setActiveRelationId(rel.id);
                        setConfirmModalOpen(true);
                      }}
                      className="gov-btn-primary text-xs py-2 px-4 shadow-sm flex items-center gap-1.5"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Confirm Relation</span>
                    </button>
                  </>
                )}

                {/* Supervisor Revert Action */}
                {rel.status !== "PENDING_REVIEW" &&
                  (user?.role === "SUPERVISOR" || user?.role === "SYSTEM_ADMIN") && (
                    <button
                      type="button"
                      onClick={() => {
                        setActiveRelationId(rel.id);
                        setRevertModalOpen(true);
                      }}
                      className="gov-btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5 text-amber-700 hover:bg-amber-50"
                      title="Reopen review decision"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Revert Decision (Supervisor)</span>
                    </button>
                  )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CONFIRM MODAL */}
      <ConfirmModal
        isOpen={confirmModalOpen}
        title="Confirm Grievance Relation"
        confirmLabel="Confirm"
        isLoading={confirmMutation.isPending}
        onConfirm={() => confirmMutation.mutate()}
        onClose={() => setConfirmModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="gov-label" htmlFor="qRelType">
              Relation Classification
            </label>
            <select
              id="qRelType"
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
            <label className="gov-label" htmlFor="qNotes">
              Confirmation Notes
            </label>
            <textarea
              id="qNotes"
              rows={2}
              value={confirmNotes}
              onChange={(e) => setConfirmNotes(e.target.value)}
              placeholder="Why these cases are related..."
              className="gov-input text-xs"
            />
          </div>
        </div>
      </ConfirmModal>

      {/* DISMISS MODAL */}
      <ConfirmModal
        isOpen={dismissModalOpen}
        title="Dismiss Grievance Relation"
        variant="danger"
        confirmLabel="Dismiss"
        isLoading={dismissMutation.isPending}
        onConfirm={() => dismissMutation.mutate()}
        onClose={() => setDismissModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="gov-label" htmlFor="qDismissReason">
              Dismissal Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              id="qDismissReason"
              required
              rows={3}
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              placeholder="Explain why this candidate is not related..."
              className="gov-input text-xs"
            />
          </div>
        </div>
      </ConfirmModal>

      {/* REVERT MODAL (SUPERVISOR ONLY) */}
      <ConfirmModal
        isOpen={revertModalOpen}
        title="Revert Relation Decision"
        variant="warning"
        confirmLabel="Revert to Pending"
        isLoading={revertMutation.isPending}
        onConfirm={() => revertMutation.mutate()}
        onClose={() => setRevertModalOpen(false)}
      >
        <div className="space-y-4 text-xs">
          <p className="text-surface-subtle">
            This will return the relation to <strong>PENDING_REVIEW</strong> status
            for re-evaluation.
          </p>
          <div>
            <label className="gov-label" htmlFor="qRevertReason">
              Reversal Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              id="qRevertReason"
              required
              rows={3}
              value={revertReason}
              onChange={(e) => setRevertReason(e.target.value)}
              placeholder="Justification for reopening review..."
              className="gov-input text-xs"
            />
          </div>
        </div>
      </ConfirmModal>
    </div>
  );
};
