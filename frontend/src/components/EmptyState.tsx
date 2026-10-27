import React from "react";
import { FolderOpen, AlertTriangle } from "lucide-react";

interface EmptyStateProps {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  icon?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = "No records found",
  description = "There are no items to display matching the current criteria.",
  action,
  icon,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-white rounded-lg border border-surface-border my-4">
      <div className="w-12 h-12 rounded-full bg-surface-muted flex items-center justify-center text-surface-subtle mb-3">
        {icon || <FolderOpen className="w-6 h-6" />}
      </div>
      <h3 className="text-base font-semibold text-surface-text">{title}</h3>
      <p className="text-sm text-surface-subtle max-w-md mt-1 mb-4">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};

interface ErrorStateProps {
  title?: string;
  message?: string;
  retry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Something went wrong",
  message = "Failed to load data from the server. Please try again.",
  retry,
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-red-50/50 rounded-lg border border-red-200 my-4">
      <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center text-red-600 mb-3">
        <AlertTriangle className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-red-900">{title}</h3>
      <p className="text-sm text-red-700 max-w-md mt-1 mb-4">{message}</p>
      {retry && (
        <button
          onClick={retry}
          className="gov-btn-secondary text-sm py-1.5 px-4"
        >
          Retry
        </button>
      )}
    </div>
  );
};
