import { AlertCircle, AlertTriangle, Clock } from "lucide-react";
import { cn } from "../lib/utils";

// --- Status Badge ---
interface StatusBadgeProps {
  status: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className }) => {
  const getBadgeClass = (s: string) => {
    switch (s.toUpperCase()) {
      case "REGISTERED":
        return "badge-registered";
      case "UNDER_REVIEW":
        return "badge-under-review";
      case "ACTION_INITIATED":
        return "badge-action-initiated";
      case "PENDING_INFORMATION":
        return "badge-pending-info";
      case "RESOLVED":
        return "badge-resolved";
      case "CLOSED":
        return "badge-closed";
      case "REOPENED":
        return "badge-reopened";
      default:
        return "bg-slate-100 text-slate-800 border border-slate-200";
    }
  };

  const getLabel = (s: string) => {
    return s.replace(/_/g, " ");
  };

  return (
    <span className={cn("badge", getBadgeClass(status), className)}>
      <span className="h-1.5 w-1.5 rounded-full bg-current"></span>
      {getLabel(status)}
    </span>
  );
};

// --- Priority Badge ---
interface PriorityBadgeProps {
  priority: string;
  className?: string;
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority, className }) => {
  const getBadgeClass = (p: string) => {
    switch (p.toUpperCase()) {
      case "CRITICAL":
        return "badge-prio-critical";
      case "HIGH":
        return "badge-prio-high";
      case "MEDIUM":
        return "badge-prio-medium";
      case "LOW":
        return "badge-prio-low";
      default:
        return "bg-slate-100 text-slate-700";
    }
  };

  return (
    <span className={cn("badge", getBadgeClass(priority), className)}>
      {priority.toUpperCase()}
    </span>
  );
};

// --- Overdue Badge ---
interface OverdueBadgeProps {
  isOverdue: boolean;
  daysOverdue?: number;
  className?: string;
}

export const OverdueBadge: React.FC<OverdueBadgeProps> = ({
  isOverdue,
  daysOverdue = 0,
  className,
}) => {
  if (!isOverdue) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200",
        className
      )}
      title={`${daysOverdue} days overdue`}
    >
      <Clock className="w-3 h-3 text-rose-600" />
      {daysOverdue > 0 ? `${daysOverdue}d Overdue` : "Overdue"}
    </span>
  );
};

interface EscalationBadgeProps {
  isEscalated?: boolean;
  level?: number;
  className?: string;
}

export const EscalationBadge: React.FC<EscalationBadgeProps> = ({
  isEscalated,
  level,
  className,
}) => {
  const active = isEscalated ?? ((level ?? 0) > 0);
  if (!active) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold bg-amber-500 text-white shadow-xs",
        className
      )}
      title="Escalated to Supervisor"
    >
      <AlertTriangle className="w-3 h-3 text-white" />
      ESCALATED
    </span>
  );
};

// --- Bureau Chip ---
interface BureauChipProps {
  code: string;
  isPrimary?: boolean;
  className?: string;
}

export const BureauChip: React.FC<BureauChipProps> = ({ code, isPrimary = false, className }) => {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold",
        isPrimary
          ? "bg-brand-100 text-brand-900 border border-brand-300 font-bold"
          : "bg-slate-100 text-slate-700 border border-slate-200",
        className
      )}
      title={isPrimary ? "Primary Bureau" : "Participating Bureau"}
    >
      {code}
      {isPrimary && <span className="ml-1 text-[10px] text-brand-700">(Primary)</span>}
    </span>
  );
};

// --- Access Level Notice ---
export const AccessLevelNotice: React.FC<{
  accessLevel?: string;
  message?: string;
  className?: string;
}> = ({
  accessLevel,
  message = "Summary view - your bureau does not participate in this case. Sensitive details are redacted.",
  className = "",
}) => {
  return (
    <div className={`bg-amber-50 border-l-4 border-amber-500 p-3 rounded-r-md flex items-center gap-2 mb-4 ${className}`}>
      <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0" />
      <span className="text-sm text-amber-900 font-medium">
        {accessLevel === "READ_ONLY"
          ? "Read-only view - your bureau has observation permissions. Modifications are disabled."
          : message}
      </span>
    </div>
  );
};
