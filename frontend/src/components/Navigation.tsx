import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutDashboard,
  FileText,
  GitCompare,
  Building2,
  FileSpreadsheet,
  Bell,
  Users,
  ShieldAlert,
  LogOut,
} from "lucide-react";
import { useAuth } from "../auth/useAuth";
import { notificationsApi, relationsApi } from "../api";
import { BureauChip } from "./Badges";

export const TopBar: React.FC = () => {
  const { user, logout } = useAuth();

  // Poll unread notifications every 30s
  const { data: unreadNotifications } = useQuery({
    queryKey: ["unread-notifications"],
    queryFn: () => notificationsApi.list({ is_read: false, page_size: 1 }),
    refetchInterval: 30000,
    enabled: !!user,
  });

  const unreadCount = unreadNotifications?.total || 0;

  return (
    <header className="h-16 bg-brand-900 text-white flex items-center justify-between px-6 shadow-md border-b border-brand-800 z-30">
      <div className="flex items-center gap-4">
        <Link to="/dashboard" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded bg-white p-1 flex items-center justify-center font-bold text-brand-900 text-sm shadow">
            AICTE
          </div>
          <div>
            <div className="font-semibold text-sm tracking-wide text-white group-hover:text-amber-300 transition-colors">
              AICTE Complaint Monitoring System
            </div>
            <div className="text-[11px] text-brand-200">
              Integrated Multi-Bureau Grievance &amp; Coordination Portal
            </div>
          </div>
        </Link>
      </div>

      <div className="flex items-center gap-4">
        {/* Synthetic Data Indicator */}
        <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/20 text-amber-200 border border-amber-400/30">
          Synthetic Data
        </span>

        {/* Notification Bell */}
        <Link
          to="/notifications"
          className="relative p-2 rounded-lg text-brand-100 hover:text-white hover:bg-brand-800 transition-colors"
          title="Notifications"
        >
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center ring-2 ring-brand-900">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Link>

        {/* User Info & Logout */}
        <div className="h-6 w-px bg-brand-700 hidden sm:block" />

        <div className="flex items-center gap-3">
          <div className="text-right hidden sm:block">
            <div className="text-xs font-semibold text-white flex items-center gap-1.5 justify-end">
              <span>{user?.full_name}</span>
              {user?.bureau_code && <BureauChip code={user.bureau_code} />}
            </div>
            <div className="text-[10px] text-brand-200">
              {user?.designation || user?.role}
            </div>
          </div>

          <button
            onClick={() => logout()}
            className="p-2 rounded-lg text-brand-200 hover:text-white hover:bg-brand-800 transition-colors text-xs flex items-center gap-1"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const location = useLocation();

  // Fetch pending relations count for badge
  const { data: pendingRelations } = useQuery({
    queryKey: ["pending-relations-count"],
    queryFn: () => relationsApi.queue({ status: "PENDING_REVIEW", page_size: 1 }),
    enabled: !!user,
    refetchInterval: 60000,
  });

  const pendingCount = pendingRelations?.total || 0;

  const navItems = [
    { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
    { label: "Complaints", to: "/complaints", icon: FileText },
    {
      label: "Relations Queue",
      to: "/relations",
      icon: GitCompare,
      badge: pendingCount > 0 ? pendingCount : null,
    },
    { label: "Institutions", to: "/institutions", icon: Building2 },
    { label: "Reports", to: "/reports", icon: FileSpreadsheet },
    { label: "Notifications", to: "/notifications", icon: Bell },
  ];

  const adminItems = [
    { label: "User Management", to: "/admin/users", icon: Users },
    { label: "Audit Logs", to: "/admin/audit", icon: ShieldAlert },
  ];

  const isActive = (path: string) => {
    if (path === "/dashboard") return location.pathname === "/dashboard";
    return location.pathname.startsWith(path);
  };

  return (
    <aside className="w-64 bg-slate-900 text-slate-200 flex flex-col shrink-0 border-r border-slate-800 select-none">
      <div className="p-4 border-b border-slate-800">
        <div className="text-xs uppercase tracking-wider text-slate-400 font-semibold">
          Navigation
        </div>
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = isActive(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-center justify-between px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                active
                  ? "bg-brand-700 text-white shadow-sm"
                  : "text-slate-300 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${active ? "text-white" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge !== null && (
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-500 text-slate-900">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}

        {/* Administration Section */}
        {user?.role === "SYSTEM_ADMIN" && (
          <>
            <div className="pt-4 pb-1 px-3">
              <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">
                Administration
              </div>
            </div>
            {adminItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.to);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-md text-sm font-medium transition-colors ${
                    active
                      ? "bg-brand-700 text-white shadow-sm"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={`w-4 h-4 ${active ? "text-white" : "text-slate-400"}`} />
                    <span>{item.label}</span>
                  </div>
                </Link>
              );
            })}
          </>
        )}
      </nav>

      {/* Bureau Info footer */}
      <div className="p-4 border-t border-slate-800 text-xs text-slate-400 bg-slate-950/40">
        <div>Role: <span className="text-slate-200 font-medium">{user?.role}</span></div>
        <div>Bureau: <span className="text-slate-200 font-medium">{user?.bureau_code || "All Bureaus"}</span></div>
      </div>
    </aside>
  );
};
