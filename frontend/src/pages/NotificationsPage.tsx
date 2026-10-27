import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Check, CheckCheck, ExternalLink } from "lucide-react";
import { notificationsApi } from "../api";
import { formatDateTime } from "../lib/utils";
import { EmptyState, ErrorState } from "../components/EmptyState";

export const NotificationsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [filterUnread, setFilterUnread] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["notifications-list", filterUnread, page, pageSize],
    queryFn: () =>
      notificationsApi.list({
        is_read: filterUnread ? false : undefined,
        page,
        page_size: pageSize,
      }),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications-list"] });
      queryClient.invalidateQueries({ queryKey: ["unread-notifications"] });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications-list"] });
      queryClient.invalidateQueries({ queryKey: ["unread-notifications"] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-surface-text">
            Notifications Center
          </h1>
          <p className="text-sm text-surface-subtle mt-0.5">
            SLA warnings, duplicate review alerts, and multi-bureau assignment updates
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => markAllReadMutation.mutate()}
            disabled={markAllReadMutation.isPending}
            className="gov-btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
          >
            <CheckCheck className="w-4 h-4 text-brand-600" />
            <span>Mark All Read</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="gov-card p-3 bg-white flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          <button
            type="button"
            onClick={() => {
              setFilterUnread(false);
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded font-medium transition-colors ${
              !filterUnread
                ? "bg-brand-900 text-white"
                : "text-surface-subtle hover:text-surface-text"
            }`}
          >
            All Notifications
          </button>
          <button
            type="button"
            onClick={() => {
              setFilterUnread(true);
              setPage(1);
            }}
            className={`px-3 py-1.5 rounded font-medium transition-colors ${
              filterUnread
                ? "bg-brand-900 text-white"
                : "text-surface-subtle hover:text-surface-text"
            }`}
          >
            Unread Only
          </button>
        </div>

        <div className="text-xs text-surface-subtle">
          Total: <span className="font-semibold">{data?.total || 0}</span>
        </div>
      </div>

      {/* Notifications List */}
      <div className="gov-card divide-y divide-surface-border bg-white">
        {isLoading ? (
          <div className="p-8 text-center text-xs text-surface-subtle">
            Loading notifications...
          </div>
        ) : error ? (
          <ErrorState
            title="Failed to load notifications"
            message={(error as any)?.message}
            retry={() => refetch()}
          />
        ) : data?.items.length === 0 ? (
          <EmptyState
            title="No notifications"
            description="You are all caught up! No notifications match your filter."
          />
        ) : (
          data?.items.map((n: any) => (
            <div
              key={n.id}
              className={`p-4 flex items-start justify-between gap-4 transition-colors ${
                !n.is_read ? "bg-brand-50/40" : "hover:bg-surface-muted/40"
              }`}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
                    !n.is_read
                      ? "bg-brand-100 text-brand-700"
                      : "bg-surface-muted text-surface-subtle"
                  }`}
                >
                  <Bell className="w-4 h-4" />
                </div>

                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-surface-text">
                      {n.title}
                    </span>
                    {!n.is_read && (
                      <span className="w-2 h-2 rounded-full bg-brand-600 inline-block" />
                    )}
                  </div>
                  <div className="text-xs text-surface-subtle">{n.message}</div>
                  <div className="text-[10px] text-surface-subtle pt-1">
                    {formatDateTime(n.created_at)}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {n.complaint_id && (
                  <Link
                    to={`/complaints/${n.complaint_id}`}
                    className="p-1.5 rounded text-surface-subtle hover:text-brand-700 hover:bg-surface-muted transition-colors"
                    title="View Complaint"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </Link>
                )}

                {!n.is_read && (
                  <button
                    type="button"
                    onClick={() => markReadMutation.mutate(n.id)}
                    className="p-1.5 rounded text-surface-subtle hover:text-emerald-700 hover:bg-surface-muted transition-colors"
                    title="Mark as read"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
