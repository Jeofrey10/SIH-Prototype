import React from "react";
import { cn } from "../lib/utils";

interface KpiCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  icon?: React.ReactNode;
  variant?: "default" | "warning" | "danger" | "success" | "brand" | "primary";
  onClick?: () => void;
  className?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  variant = "default",
  onClick,
  className,
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case "danger":
        return "border-l-4 border-l-rose-500 text-rose-700";
      case "warning":
        return "border-l-4 border-l-amber-500 text-amber-700";
      case "success":
        return "border-l-4 border-l-emerald-500 text-emerald-700";
      case "brand":
      case "primary":
        return "border-l-4 border-l-brand-700 text-brand-900";
      default:
        return "border-l-4 border-l-slate-400 text-slate-800";
    }
  };

  return (
    <div
      onClick={onClick}
      className={cn(
        "gov-card p-5 transition-all",
        getVariantStyles(),
        onClick && "cursor-pointer hover:shadow-md hover:bg-slate-50/50",
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">{value}</p>
          {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
        </div>
        {icon && (
          <div className="p-2.5 rounded-lg bg-slate-100 text-slate-600">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
};
