export type Role = "SYSTEM_ADMIN" | "SUPERVISOR" | "RB_OFFICIAL" | "PGRC_OFFICIAL";

export interface Bureau {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  is_active?: boolean;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  bureau_id?: string | null;
  bureau?: Bureau | null;
  bureau_code?: string | null;
  designation?: string | null;
  is_active: boolean;
  last_login_at?: string | null;
  created_at?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface DelayExplanation {
  sentence: string;
  tone: "muted" | "success" | "warning" | "danger" | "info";
  stage: string;
  key_factor: string;
}

export interface LimboFlag {
  type: string;
  description: string;
  severity: "low" | "medium" | "high";
  duration_days?: number;
}

export interface WaitingOnSummary {
  active_waits_count: number;
  oldest_wait_days: number;
  primary_party?: string;
  items?: any[];
}

export interface PendingHandover {
  id: string;
  from_bureau?: { id: string; code: string; name: string } | null;
  to_bureau?: { id: string; code: string; name: string } | null;
  initiated_by?: { id: string; full_name: string } | null;
  initiated_at: string;
  context_summary?: string;
  key_findings?: string;
}

export interface ComplaintItem {
  id: string;
  reference_number: string;
  complaint_number?: string;
  title?: string | null;
  category: string;
  priority: string;
  status: string;
  incident_date?: string | null;
  received_date?: string;
  created_at?: string;
  target_date?: string;
  target_resolution_date?: string;
  is_overdue: boolean;
  days_overdue?: number;
  escalation_level?: number;
  is_escalated?: boolean;
  access_level?: string;
  user_access_level?: string;
  institution_id?: string;
  institution_name?: string;
  institution_aicte_id?: string;
  institution?: {
    id: string;
    code: string;
    name: string;
  } | null;
  primary_bureau?: {
    id: string;
    code: string;
    name: string;
  } | null;
  bureau_code?: string;
  participating_bureaus?: any[];
  owner?: {
    id: string;
    full_name: string;
  } | null;
  handover_status?: string | null;
  delay_explanation?: DelayExplanation | null;
  limbo_flags?: LimboFlag[];
  waiting_on_summary?: WaitingOnSummary | null;
}

export interface ComplaintDetail extends ComplaintItem {
  description?: string;
  incident_reference?: string | null;
  complainant_type?: string | null;
  complainant_name?: string | null;
  complainant_contact?: string | null;
  complainant_email?: string | null;
  complainant_phone?: string | null;
  source_channel?: string | null;
  resolution_summary?: string | null;
  resolved_at?: string | null;
  closed_at?: string | null;
  reopened_count?: number;
  version: number;
  created_at?: string;
  updated_at?: string;
  allowed_actions?: string[] | any;
  assignments?: any[];
  status_history?: any[];
  notes?: any[];
  relations?: any[];
  pending_handover?: PendingHandover | null;
}

export interface InstitutionItem {
  id: string;
  code: string;
  aicte_id?: string;
  name: string;
  institution_type: string;
  category?: string;
  state: string;
  district?: string | null;
  city?: string | null;
  address?: string | null;
  email?: string | null;
  phone?: string | null;
  is_active: boolean;
  open_count?: number;
  active_complaints_count?: number;
  overdue_count?: number;
  active_bureau_codes?: string[];
  created_at?: string;
  updated_at?: string;
}
