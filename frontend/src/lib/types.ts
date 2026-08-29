export type Role = "operator" | "admin";

export interface User {
  id: number;
  username: string;
  full_name: string;
  role: Role;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface NotificationItem {
  id: number;
  message: string;
  link: string | null;
  read: boolean;
  created_at: string;
}

export interface OperatorStats {
  id: number;
  username: string;
  full_name: string;
  avatar_url: string | null;
  today_count: number;
  week_count: number;
  total_count: number;
}

export interface OverviewStats {
  today_filled: number;
  week_filled: number;
  total_companies: number;
  finished_leads: number;
  active_operators: number;
}

/* ---------------------------------------------------------------------------
 * Lead Workflow v2
 * ------------------------------------------------------------------------ */

/** The five workflow states. "mine" and "all" are queue tabs, not statuses. */
export type LeadStatus = "new" | "in_progress" | "waiting" | "approved" | "rejected";
export type QueueTab = LeadStatus | "mine" | "all";

/** What the server says this user may do right now. The client renders this
 *  list rather than re-deriving the state machine. */
export type LeadAction =
  | "start"
  | "pause"
  | "comment"
  | "approve"
  | "reject"
  | "reopen"
  | "admin_release"
  | "admin_assign";

export interface LeadField {
  field: "website" | "lms";
  /** null = belgilanmagan -- a real third state, not a missing false. */
  available: boolean | null;
  comment: string | null;
  filled_by: string | null;
  filled_at: string | null;
}

export interface LeadEvent {
  id: number;
  type:
    | "status_change"
    | "handover"
    | "comment"
    | "finish"
    | "reopen"
    | "auto_release"
    | "admin_release"
    | "admin_assign"
    | "migration";
  /** null renders as "Tizim". */
  actor: string | null;
  from_status: LeadStatus | null;
  to_status: LeadStatus | null;
  note: string | null;
  created_at: string;
}

export interface LeadListItem {
  id: number;
  name: string;
  category: string | null;
  address: string | null;
  phone: string | null;
  source: string;
  status: LeadStatus;
  assignee_id: number | null;
  assignee_name: string | null;
  website_available: boolean | null;
  lms_available: boolean | null;
  last_note: string | null;
  last_note_by: string | null;
  last_note_at: string | null;
}

export interface LeadList {
  items: LeadListItem[];
  total: number;
  /** Every tab badge in one payload, keyed by tab name. */
  counts: Record<string, number>;
}

export interface LeadDetail {
  id: number;
  name: string;
  category: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  source: string;
  source_url: string | null;
  status: LeadStatus;
  assignee_id: number | null;
  assignee_name: string | null;
  assigned_at: string | null;
  last_activity_at: string | null;
  fields: LeadField[];
  events: LeadEvent[];
  available_actions: LeadAction[];
}

export interface LeadAttentionItem {
  id: number;
  name: string;
  status: LeadStatus;
  reason: "stale" | "handoffs";
  waiting_days: number | null;
  handoff_count: number | null;
  last_note: string | null;
  /** Who was holding it when it went quiet, if anyone. */
  last_holder: string | null;
}

/** Every /leads error answers in this shape (one server-side handler). */
export interface LeadError {
  code:
    | "not_found"
    | "held_by_other"
    | "handover_required"
    | "invalid_transition"
    | "not_in_progress"
    | "note_required"
    | "fields_incomplete"
    | "unknown_operator";
  /** Already operator-facing Uzbek -- show it verbatim. */
  message: string;
  active_company_id?: number;
  active_company_name?: string;
  missing?: string[];
}
