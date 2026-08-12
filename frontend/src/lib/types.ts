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

export interface CompanyQueueItem {
  id: number;
  name: string;
  category: string | null;
  address: string | null;
  phone: string | null;
  source: string;
  website_status: "pending" | "confirmed" | "absent";
  lms_status: "pending" | "confirmed" | "absent";
}

export interface ReviewField {
  field: "website" | "lms";
  available: boolean | null;
  comment: string | null;
  filled_by: string | null;
  filled_at: string | null;
  locked: boolean;
  pending_request: boolean;
}

export interface CompanyReviewDetail {
  id: number;
  name: string;
  category: string | null;
  address: string | null;
  phone: string | null;
  email: string | null;
  source: string;
  fields: ReviewField[];
}

export interface PermissionRequestItem {
  id: number;
  review_id: number;
  company_id: number;
  company_name: string;
  field: string;
  requested_by: string;
  reason: string | null;
  status: "pending" | "approved" | "denied";
  created_at: string;
  resolved_at: string | null;
  resolution_note: string | null;
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
  pending_requests: number;
  active_operators: number;
}

export interface Claim {
  id: number;
  company_id: number;
  company_name: string;
  operator_id: number;
  claimed_at: string;
  status: "active" | "deferred" | "completed" | "released";
  deadline_at: string | null;
  deadline_days: number | null;
  overdue: boolean;
}

export interface MyClaims {
  active: Claim | null;
  deferred: Claim[];
}

export interface ClaimRequestItem {
  id: number;
  claim_id: number;
  company_id: number;
  company_name: string;
  operator_id: number;
  operator_name: string;
  action: "extend" | "release";
  requested_days: number | null;
  reason: string | null;
  status: "pending" | "approved" | "denied";
  created_at: string;
  resolved_at: string | null;
  resolution_note: string | null;
}

export interface ClaimBlockError {
  code: "overdue" | "active_claim_exists" | "already_claimed";
  message: string;
  claims?: Claim[];
  active_claim?: Claim;
}
