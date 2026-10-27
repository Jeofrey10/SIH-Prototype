/**
 * Typed API client for AICTE Grievance Portal.
 */
import { apiClient, downloadCsv } from "./client";

export type { User, LoginResponse, ComplaintDetail, ComplaintItem, InstitutionItem } from "./types";
import type { User, LoginResponse, ComplaintDetail, ComplaintItem, InstitutionItem } from "./types";

// --- Auth API ---
export const authApi = {
  login: (data: { username: string; password: string }) =>
    apiClient<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getMe: () => apiClient<User>("/auth/me"),
  changePassword: (data: { old_password: string; new_password: string }) =>
    apiClient<{ message: string }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// --- Complaints API ---
export const complaintsApi = {
  list: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        if (typeof v === "boolean") {
          query.set(k, v ? "true" : "false");
        } else {
          query.set(k, String(v));
        }
      }
    });
    return apiClient<{ items: ComplaintItem[]; total: number; page: number; page_size: number }>(
      `/complaints?${query.toString()}`
    );
  },
  get: (id: string) => apiClient<ComplaintDetail>(`/complaints/${id}`),
  getById: (id: string) => apiClient<ComplaintDetail>(`/complaints/${id}`),
  create: (data: any) =>
    apiClient<ComplaintDetail & { related_candidates: any[] }>("/complaints", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: any) =>
    apiClient<ComplaintDetail>(`/complaints/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  updateStatus: (id: string, data: any) =>
    apiClient<ComplaintDetail>(`/complaints/${id}/status`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  changeStatus: (id: string, data: any) =>
    apiClient<ComplaintDetail>(`/complaints/${id}/status`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  escalate: (id: string, data?: any) =>
    apiClient<ComplaintDetail>(`/complaints/${id}/escalate`, {
      method: "POST",
      body: JSON.stringify(typeof data === "string" ? { reason: data } : data || {}),
    }),
  clearEscalation: (id: string, note: string) =>
    apiClient<ComplaintDetail>(`/complaints/${id}/clear-escalation`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  getNotes: (id: string) => apiClient<any[]>(`/complaints/${id}/notes`),
  addNote: (id: string, data: { content?: string; body?: string; note_type?: string }) =>
    apiClient<any>(`/complaints/${id}/notes`, {
      method: "POST",
      body: JSON.stringify({
        content: data.content || data.body || "",
        note_type: data.note_type || "INTERNAL",
      }),
    }),
  addParticipant: (id: string, data: { bureau_code?: string; bureau_id?: string; reason?: string }) =>
    apiClient<{ message: string }>(`/complaints/${id}/participants`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  removeParticipant: (id: string, bureau_id: string) =>
    apiClient<{ message: string }>(`/complaints/${id}/participants/${bureau_id}`, {
      method: "DELETE",
    }),
  transferPrimary: (id: string, data: { new_bureau_code?: string; bureau_id?: string; reason?: string }) =>
    apiClient<ComplaintDetail>(`/complaints/${id}/transfer-primary`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getRelations: (id: string) => apiClient<any[]>(`/relations/complaint/${id}`),
};

// --- Institutions API ---
export const institutionsApi = {
  list: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        query.set(k, String(v));
      }
    });
    return apiClient<{ items: InstitutionItem[]; total: number; page: number; page_size: number }>(
      `/institutions?${query.toString()}`
    );
  },
  get: (id: string) => apiClient<any>(`/institutions/${id}`),
  getById: (id: string) => apiClient<any>(`/institutions/${id}`),
  create: (data: any) =>
    apiClient<any>("/institutions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: any) =>
    apiClient<any>(`/institutions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deactivate: (id: string) =>
    apiClient<{ message: string }>(`/institutions/${id}/deactivate`, { method: "POST" }),
  activate: (id: string) =>
    apiClient<{ message: string }>(`/institutions/${id}/activate`, { method: "POST" }),
  getTimeline: (id: string, page = 1, pageSize = 20) =>
    apiClient<{ items: any[]; total: number }>(`/institutions/${id}/timeline?page=${page}&page_size=${pageSize}`),
  getCoordination: (id: string) =>
    apiClient<any>(`/institutions/${id}/coordination`),
};

// --- Relations API ---
export const relationsApi = {
  list: (params: { status?: string; institution_id?: string; page?: number; page_size?: number } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return apiClient<{ items: any[]; total: number; page: number; page_size: number }>(
      `/relations/queue?${query.toString()}`
    );
  },
  queue: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        query.set(k, String(v));
      }
    });
    return apiClient<{ items: any[]; total: number; page: number; page_size: number }>(
      `/relations/queue?${query.toString()}`
    );
  },
  preview: (data: any) =>
    apiClient<{ candidates: any[] }>("/relations/related-preview", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  previewRelated: (data: any) =>
    apiClient<{ candidates: any[] }>("/relations/related-preview", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getForComplaint: (id: string) => apiClient<any[]>(`/relations/complaint/${id}`),
  confirm: (id: string, data: { relation_type: string; notes?: string; note?: string; auto_add_participating_bureau?: boolean; add_participating_bureaus?: boolean }) =>
    apiClient<any>(`/relations/${id}/confirm`, {
      method: "POST",
      body: JSON.stringify({
        relation_type: data.relation_type,
        note: data.note || data.notes || "",
        auto_add_participating_bureau: data.auto_add_participating_bureau ?? data.add_participating_bureaus ?? true,
      }),
    }),
  dismiss: (id: string, data: { reason?: string; note?: string }) =>
    apiClient<any>(`/relations/${id}/dismiss`, {
      method: "POST",
      body: JSON.stringify({
        reason: data.reason || data.note || "",
      }),
    }),
  revert: (id: string, data: { reason?: string; note?: string; status?: string }) =>
    apiClient<any>(`/relations/${id}/revert`, {
      method: "POST",
      body: JSON.stringify({
        reason: data.reason || data.note || "",
      }),
    }),
};

// --- Notifications API ---
export const notificationsApi = {
  list: (params: { is_read?: boolean; unread?: boolean; type?: string; page?: number; page_size?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.unread !== undefined) {
      query.set("unread", params.unread ? "true" : "false");
    } else if (params.is_read !== undefined) {
      query.set("unread", params.is_read ? "false" : "true");
    }
    if (params.type) query.set("type", params.type);
    if (params.page) query.set("page", String(params.page));
    if (params.page_size) query.set("page_size", String(params.page_size));
    return apiClient<{ items: any[]; total: number }>(`/notifications?${query.toString()}`);
  },
  getUnreadCount: () =>
    apiClient<{ count?: number; unread_count?: number }>("/notifications/unread-count"),
  markRead: (id: string) => apiClient<{ message: string }>(`/notifications/${id}/read`, { method: "POST" }),
  markAllRead: () => apiClient<{ updated_count: number }>("/notifications/read-all", { method: "POST" }),
};

// --- Analytics API ---
export const analyticsApi = {
  summary: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return apiClient<any>(`/analytics/summary?${query.toString()}`);
  },
  getSummary: (params: Record<string, any> = {}) => analyticsApi.summary(params),
  statusDistribution: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return apiClient<any[]>(`/analytics/status-distribution?${query.toString()}`);
  },
  getStatusDistribution: (params: Record<string, any> = {}) => analyticsApi.statusDistribution(params),
  bureauWorkload: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return apiClient<any[]>(`/analytics/bureau-workload?${query.toString()}`);
  },
  getBureauWorkload: (params: Record<string, any> = {}) => analyticsApi.bureauWorkload(params),
  agingBuckets: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return apiClient<any[]>(`/analytics/aging-buckets?${query.toString()}`);
  },
  getAgingBuckets: (params: Record<string, any> = {}) => analyticsApi.agingBuckets(params),
  trend: (days = 30) => apiClient<any[]>(`/analytics/trend?days=${days}`),
  getTrend: (days = 30) => analyticsApi.trend(days),
  topInstitutions: (limit = 5) => apiClient<any[]>(`/analytics/top-institutions?limit=${limit}`),
  getTopInstitutions: (limit = 5) => analyticsApi.topInstitutions(limit),
};

// --- Reports API ---
export const reportsApi = {
  previewOverdue: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return apiClient<any>(`/reports/overdue?${query.toString()}`);
  },
  getOverdue: (params: Record<string, any> = {}) => reportsApi.previewOverdue(params),
  exportOverdueCsv: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return downloadCsv(`/reports/overdue/csv?${query.toString()}`, "overdue_complaints.csv");
  },
  downloadOverdueCsv: (params: Record<string, any> = {}) => reportsApi.exportOverdueCsv(params),
  previewComplaints: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return apiClient<any>(`/reports/complaints?${query.toString()}`);
  },
  getComplaints: (params: Record<string, any> = {}) => reportsApi.previewComplaints(params),
  exportComplaintsCsv: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return downloadCsv(`/reports/complaints/csv?${query.toString()}`, "complaints_report.csv");
  },
  downloadComplaintsCsv: (params: Record<string, any> = {}) => reportsApi.exportComplaintsCsv(params),
};

// --- Users Admin API ---
export const usersApi = {
  list: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) query.set(k, String(v));
    });
    return apiClient<{ items: User[]; total: number }>(`/users?${query.toString()}`);
  },
  getAssignable: (bureau_id?: string) => {
    const query = bureau_id ? `?bureau_id=${bureau_id}` : "";
    return apiClient<Array<{ id: string; full_name: string; bureau_id: string | null }>>(
      `/users/assignable${query}`
    );
  },
  create: (data: any) =>
    apiClient<User>("/users", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getById: (id: string) => apiClient<User>(`/users/${id}`),
  update: (id: string, data: any) =>
    apiClient<User>(`/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  activate: (id: string) =>
    apiClient<User>(`/users/${id}/activate`, { method: "POST" }),
  deactivate: (id: string) =>
    apiClient<User>(`/users/${id}/deactivate`, { method: "POST" }),
  resetPassword: (id: string, data?: { new_password?: string }) =>
    apiClient<{ temporary_password?: string; message?: string }>(`/users/${id}/reset-password`, {
      method: "POST",
      body: JSON.stringify(data || {}),
    }),
};

// --- Bureaus API ---
export const bureausApi = {
  list: () => apiClient<Array<{ id: string; code: string; name: string }>>("/bureaus"),
};

// --- Audit Logs API ---
export const auditApi = {
  list: (params: Record<string, any> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.set(k, String(v));
    });
    return apiClient<{ items: any[]; total: number; page: number; page_size: number }>(
      `/audit?${query.toString()}`
    );
  },
};

// --- System API ---
export const systemApi = {
  triggerOverdueScan: () =>
    apiClient<any>("/system/jobs/overdue-scan", { method: "POST" }),
};
