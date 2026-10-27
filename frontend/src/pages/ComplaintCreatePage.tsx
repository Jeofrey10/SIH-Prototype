import React, { useState, useEffect } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  Sparkles,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";
import { complaintsApi, institutionsApi, relationsApi, bureausApi } from "../api";
import { useAuth } from "../auth/useAuth";
import { MatchExplanationCard } from "../components/MatchExplanationCard";

export const ComplaintCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user } = useAuth();

  // Form state
  const [institutionId, setInstitutionId] = useState(
    searchParams.get("institution_id") || ""
  );
  const [category, setCategory] = useState("INFRASTRUCTURE");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [sourceChannel, setSourceChannel] = useState("PORTAL");
  const [complainantType, setComplainantType] = useState("STUDENT");
  const [complainantName, setComplainantName] = useState("");
  const [complainantContact, setComplainantContact] = useState("");
  const [incidentReference, setIncidentReference] = useState("");
  const [incidentDate, setIncidentDate] = useState("");
  const [targetResolutionDate, setTargetResolutionDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split("T")[0];
  });
  const [assignedBureauCode, setAssignedBureauCode] = useState(
    user?.bureau_code || "RB"
  );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Live preview state
  const [previewCandidates, setPreviewCandidates] = useState<any[]>([]);
  const [isPreviewLoading, setIsPreviewLoading] = useState(false);

  // Query institutions and bureaus
  const { data: institutionsData } = useQuery({
    queryKey: ["institutions-list"],
    queryFn: () => institutionsApi.list({ page_size: 100 }),
  });

  const { data: bureausData } = useQuery({
    queryKey: ["bureaus-list"],
    queryFn: () => bureausApi.list(),
  });

  // Debounced live duplicate/related candidate preview
  useEffect(() => {
    if (!institutionId || title.trim().length < 5 || description.trim().length < 10) {
      const resetTimer = setTimeout(() => setPreviewCandidates([]), 0);
      return () => clearTimeout(resetTimer);
    }

    const timer = setTimeout(async () => {
      setIsPreviewLoading(true);
      try {
        const res = await relationsApi.preview({
          institution_id: institutionId,
          category,
          title,
          description,
          incident_date: incidentDate || undefined,
        });
        setPreviewCandidates(res.candidates || []);
      } catch (err) {
        console.warn("Live preview failed:", err);
      } finally {
        setIsPreviewLoading(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [institutionId, category, title, description, incidentDate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!institutionId) {
      setError("Please select an institution");
      return;
    }
    if (title.trim().length < 5) {
      setError("Title must be at least 5 characters");
      return;
    }
    if (description.trim().length < 20) {
      setError("Description must be at least 20 characters");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      const created = await complaintsApi.create({
        institution_id: institutionId,
        category,
        title: title.trim(),
        description: description.trim(),
        priority,
        source_channel: sourceChannel,
        complainant_type: complainantType,
        complainant_name: complainantName || undefined,
        complainant_contact: complainantContact || undefined,
        incident_reference: incidentReference || undefined,
        incident_date: incidentDate || undefined,
        target_resolution_date: targetResolutionDate || undefined,
        assigned_bureau_code: assignedBureauCode,
      });

      navigate(`/complaints/${created.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to register complaint");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Back button & Page header */}
      <div>
        <Link
          to="/complaints"
          className="inline-flex items-center gap-1.5 text-xs text-surface-subtle hover:text-surface-text mb-2 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Complaints</span>
        </Link>
        <h1 className="text-2xl font-bold tracking-tight text-surface-text">
          Register New Complaint
        </h1>
        <p className="text-sm text-surface-subtle">
          Record student or faculty grievance and trigger automated relation analysis
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2.5 text-sm text-red-800">
          <AlertCircle className="w-5 h-5 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 2-Column Layout: Form on Left, Live Related Candidates on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left Form: 2 cols */}
        <div className="lg:col-span-2 gov-card p-6 bg-white">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="border-b border-surface-border pb-4">
              <h2 className="text-base font-semibold text-surface-text">
                Institution &amp; Classification
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                <div>
                  <label className="gov-label" htmlFor="institution">
                    Institution <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="institution"
                    required
                    value={institutionId}
                    onChange={(e) => setInstitutionId(e.target.value)}
                    className="gov-input text-sm"
                  >
                    <option value="">Select an institution...</option>
                    {institutionsData?.items?.map((inst: any) => (
                      <option key={inst.id} value={inst.id}>
                        {inst.aicte_id || inst.code} - {inst.name} ({inst.city}, {inst.state})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="gov-label" htmlFor="category">
                    Grievance Category <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="category"
                    required
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="gov-input text-sm"
                  >
                    <option value="INFRASTRUCTURE">Infrastructure &amp; Facilities</option>
                    <option value="FACULTY">Faculty &amp; Academics</option>
                    <option value="FEE_DISPUTE">Fee Dispute / Refund</option>
                    <option value="HARASSMENT">Ragging &amp; Harassment</option>
                    <option value="ADMISSION">Admission Irregularities</option>
                    <option value="EXAM">Examination / Evaluation</option>
                    <option value="OTHER">Other Administrative Matters</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="gov-label" htmlFor="sourceChannel">
                    Source Channel <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="sourceChannel"
                    required
                    value={sourceChannel}
                    onChange={(e) => setSourceChannel(e.target.value)}
                    className="gov-input text-sm"
                  >
                    <option value="PORTAL">Online Portal</option>
                    <option value="EMAIL">Official Email</option>
                    <option value="LETTER">Physical Letter / Post</option>
                    <option value="PHONE">Phone / Helpline</option>
                    <option value="OTHER">Other Source</option>
                  </select>
                </div>

                <div>
                  <label className="gov-label" htmlFor="complainantType">
                    Complainant Type <span className="text-red-500">*</span>
                  </label>
                  <select
                    id="complainantType"
                    required
                    value={complainantType}
                    onChange={(e) => setComplainantType(e.target.value)}
                    className="gov-input text-sm"
                  >
                    <option value="STUDENT">Student</option>
                    <option value="FACULTY">Faculty Member</option>
                    <option value="PARENT">Parent / Guardian</option>
                    <option value="STAKEHOLDER">Institutional Stakeholder</option>
                    <option value="ANONYMOUS">Anonymous</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="border-b border-surface-border pb-4">
              <h2 className="text-base font-semibold text-surface-text">
                Complaint Particulars
              </h2>
              <div className="space-y-4 mt-3">
                <div>
                  <label className="gov-label" htmlFor="title">
                    Complaint Title <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="title"
                    type="text"
                    required
                    minLength={5}
                    maxLength={200}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Brief summary of the issue (min 5 characters)"
                    className="gov-input text-sm"
                  />
                </div>

                <div>
                  <label className="gov-label" htmlFor="description">
                    Full Description <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    id="description"
                    rows={5}
                    required
                    minLength={20}
                    maxLength={5000}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Detailed explanation including dates, department, fee receipts, or references (min 20 characters)..."
                    className="gov-input text-sm"
                  />
                  <p className="text-xs text-surface-subtle mt-1">
                    Include specific reference numbers or keywords for automated duplicate detection.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="gov-label" htmlFor="incRef">
                      Incident Ref / Order # (Optional)
                    </label>
                    <input
                      id="incRef"
                      type="text"
                      value={incidentReference}
                      onChange={(e) => setIncidentReference(e.target.value)}
                      placeholder="e.g. REC/2026/049"
                      className="gov-input text-sm"
                    />
                  </div>

                  <div>
                    <label className="gov-label" htmlFor="incidentDate">
                      Incident Date (Optional)
                    </label>
                    <input
                      id="incidentDate"
                      type="date"
                      value={incidentDate}
                      onChange={(e) => setIncidentDate(e.target.value)}
                      className="gov-input text-sm"
                    />
                  </div>

                  <div>
                    <label className="gov-label" htmlFor="targetDate">
                      Target Resolution Date (SLA)
                    </label>
                    <input
                      id="targetDate"
                      type="date"
                      value={targetResolutionDate}
                      onChange={(e) => setTargetResolutionDate(e.target.value)}
                      className="gov-input text-sm"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div className="border-b border-surface-border pb-4">
              <h2 className="text-base font-semibold text-surface-text">
                Assignment &amp; Complainant Details
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                <div>
                  <label className="gov-label" htmlFor="priority">
                    Priority Level
                  </label>
                  <select
                    id="priority"
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="gov-input text-sm"
                  >
                    <option value="URGENT">Urgent (Immediate attention)</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>

                <div>
                  <label className="gov-label" htmlFor="assignedBureau">
                    Initial Assigned Primary Bureau
                  </label>
                  <select
                    id="assignedBureau"
                    value={assignedBureauCode}
                    onChange={(e) => setAssignedBureauCode(e.target.value)}
                    className="gov-input text-sm"
                  >
                    {bureausData?.map((b: any) => (
                      <option key={b.code} value={b.code}>
                        {b.code} - {b.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="gov-label" htmlFor="cName">
                    Complainant Name (Optional)
                  </label>
                  <input
                    id="cName"
                    type="text"
                    value={complainantName}
                    onChange={(e) => setComplainantName(e.target.value)}
                    placeholder="Student or Faculty name"
                    className="gov-input text-sm"
                  />
                </div>

                <div>
                  <label className="gov-label" htmlFor="cContact">
                    Contact / Email (Optional)
                  </label>
                  <input
                    id="cContact"
                    type="text"
                    value={complainantContact}
                    onChange={(e) => setComplainantContact(e.target.value)}
                    placeholder="student@example.com or phone"
                    className="gov-input text-sm"
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <Link
                to="/complaints"
                className="gov-btn-secondary text-sm py-2 px-4"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={isSubmitting}
                className="gov-btn-primary text-sm py-2.5 px-6 shadow-sm flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Registering...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Submit Complaint</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Right Sidebar: Live Duplicate / Related Preview */}
        <div className="gov-card p-5 bg-surface-muted/40 border-surface-border">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-amber-600" />
              <h2 className="text-sm font-bold text-surface-text">
                Live Relation Detection
              </h2>
            </div>
            {isPreviewLoading && (
              <span className="text-[11px] text-brand-600 animate-pulse">
                Analyzing...
              </span>
            )}
          </div>

          <p className="text-xs text-surface-subtle mb-4">
            Algorithm v1.0 automatically scans other complaints at this institution
            for duplicates, overlapping keywords, and shared incident references.
          </p>

          {!institutionId ? (
            <div className="text-center py-8 text-xs text-surface-subtle border border-dashed border-surface-border rounded-md bg-white p-4">
              Select an institution to enable live candidate matching.
            </div>
          ) : previewCandidates.length === 0 ? (
            <div className="text-center py-8 text-xs text-surface-subtle border border-dashed border-surface-border rounded-md bg-white p-4">
              {title.trim().length >= 5
                ? "No matching historical complaints found (Score < 35)."
                : "Type at least 5 characters in title to preview candidates."}
            </div>
          ) : (
            <div className="space-y-4">
              <div className="text-xs font-semibold text-amber-800 bg-amber-50 border border-amber-200 px-3 py-2 rounded">
                Found {previewCandidates.length} potential related complaint(s)
              </div>

              {previewCandidates.map((cand: any) => (
                <div key={cand.complaint_id} className="space-y-2">
                  <div className="p-3 bg-white rounded border border-surface-border shadow-xs">
                    <div className="flex items-center justify-between text-xs font-mono font-bold text-brand-700 mb-1">
                      <span>{cand.complaint_number}</span>
                      <span className="px-1.5 py-0.5 rounded bg-surface-muted font-sans font-medium text-[11px] text-surface-text">
                        {cand.status}
                      </span>
                    </div>
                    <div className="text-xs font-medium text-surface-text line-clamp-2">
                      {cand.title}
                    </div>
                  </div>

                  <MatchExplanationCard
                    score={cand.score}
                    explanation={cand.explanation}
                  />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
