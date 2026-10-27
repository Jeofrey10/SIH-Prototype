import React from "react";
import { Info, Tag, Hash } from "lucide-react";
import { cn } from "../lib/utils";

interface MatchExplanationProps {
  score?: number;
  explanation: {
    algorithm_version?: string;
    score?: number;
    confidence?: "HIGH" | "MEDIUM";
    components?: Array<{
      name: string;
      points: number;
      max_points: number;
      detail: string;
    }>;
    rule_points?: Record<string, number>;
    shared_keywords?: string[];
    shared_domain_terms?: string[];
    category_match?: boolean;
    incident_reference_match?: boolean;
    date_gap_days?: number | null;
    candidate_status?: string;
    candidate_primary_bureau?: string;
  };
  className?: string;
}

export const MatchExplanationCard: React.FC<MatchExplanationProps> = ({
  score: explicitScore,
  explanation,
  className,
}) => {
  const score = explicitScore ?? explanation.score ?? 0;
  const confidence =
    explanation.confidence || (score >= 70 ? "HIGH" : "MEDIUM");
  const isHighConfidence = confidence === "HIGH";

  const components =
    explanation.components ||
    (explanation.rule_points
      ? Object.entries(explanation.rule_points).map(([k, v]) => {
          const maxMap: Record<string, number> = {
            category_match: 15,
            text_similarity: 35,
            shared_domain_terms: 25,
            incident_date_proximity: 15,
            incident_ref_exact_match: 40,
          };
          return {
            name: k.replace(/_/g, " "),
            points: v,
            max_points: maxMap[k] || 35,
            detail: `${v} pts from signal analysis`,
          };
        })
      : []);

  const sharedTerms = explanation.shared_domain_terms || [];
  const sharedKeywords = explanation.shared_keywords || [];

  return (
    <div
      className={cn(
        "gov-card border-brand-200 bg-white shadow-xs p-4 rounded-lg",
        className
      )}
    >
      <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-3">
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-brand-700" />
          <h4 className="text-sm font-semibold text-slate-900">
            Why this was flagged
          </h4>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">
            Score: <strong className="text-slate-900">{score}/100</strong>
          </span>
          <span
            className={cn(
              "px-2 py-0.5 rounded text-[11px] font-bold uppercase",
              isHighConfidence
                ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                : "bg-amber-100 text-amber-800 border border-amber-300"
            )}
          >
            {confidence} CONFIDENCE
          </span>
        </div>
      </div>

      {/* Component Breakdown Table */}
      {components.length > 0 && (
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-50 text-slate-500 uppercase font-semibold">
              <tr>
                <th className="py-1.5 px-2">Rule / Signal</th>
                <th className="py-1.5 px-2 text-right">Points</th>
                <th className="py-1.5 px-2">Assessment Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {components.map((comp) => (
                <tr key={comp.name} className="hover:bg-slate-50/50">
                  <td className="py-1.5 px-2 font-medium capitalize">
                    {comp.name}
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono font-semibold">
                    +{comp.points} / {comp.max_points}
                  </td>
                  <td className="py-1.5 px-2 text-slate-600">{comp.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Shared Tokens & Domain Terms Chips */}
      <div className="space-y-2 pt-2 border-t border-slate-100">
        {sharedTerms.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-slate-500 font-medium flex items-center gap-1">
              <Tag className="w-3 h-3 text-brand-600" /> Domain Terms:
            </span>
            {sharedTerms.map((term) => (
              <span
                key={term}
                className="bg-brand-50 text-brand-800 px-2 py-0.5 rounded font-mono text-[11px] border border-brand-200"
              >
                {term}
              </span>
            ))}
          </div>
        )}

        {sharedKeywords.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-slate-500 font-medium flex items-center gap-1">
              <Hash className="w-3 h-3 text-slate-400" /> Shared Keywords:
            </span>
            {sharedKeywords.map((kw) => (
              <span
                key={kw}
                className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded text-[11px]"
              >
                {kw}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
