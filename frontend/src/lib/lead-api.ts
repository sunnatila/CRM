import { api } from "@/lib/api";
import type { LeadDetail, LeadError, LeadList, LeadStatus, QueueTab } from "@/lib/types";

/** Pulls the server's `{code, message, ...}` envelope out of an axios failure.
 *
 *  Every /leads route answers in this one shape, so callers can switch on `code`
 *  and show `message` verbatim -- there is no second table of Uzbek strings on
 *  the client that could drift from the server's. */
export function leadError(err: unknown): LeadError | null {
  const detail = (err as { response?: { data?: { detail?: LeadError } } })?.response?.data?.detail;
  return detail && typeof detail === "object" && "code" in detail ? detail : null;
}

export async function fetchLeads(params: {
  status: QueueTab;
  q?: string;
  category?: string;
  /** "me", or an operator id (admins only) -- who last acted on the lead. */
  actor?: string;
  limit: number;
  offset: number;
}): Promise<LeadList> {
  const { data } = await api.get<LeadList>("/leads", {
    params: {
      ...params,
      q: params.q || undefined,
      category: params.category || undefined,
      actor: params.actor || undefined,
    },
  });
  return data;
}

export async function fetchLead(companyId: number | string): Promise<LeadDetail> {
  const { data } = await api.get<LeadDetail>(`/leads/${companyId}`);
  return data;
}

export const startLead = (id: number) => api.post<LeadDetail>(`/leads/${id}/start`).then((r) => r.data);

/** Hand off the current lead and pick up the new one in one server-side
 *  transaction -- the operator can never end up having dropped one and gained
 *  nothing. */
export const switchLead = (toId: number, fromId: number, note: string) =>
  api.post<LeadDetail>(`/leads/${toId}/switch`, { from_company_id: fromId, note }).then((r) => r.data);

export const pauseLead = (id: number, note: string) =>
  api.post<LeadDetail>(`/leads/${id}/pause`, { note }).then((r) => r.data);

export const finishLead = (id: number, result: "approved" | "rejected", note?: string) =>
  api.post<LeadDetail>(`/leads/${id}/finish`, { result, note: note ?? null }).then((r) => r.data);

export const reopenLead = (id: number, note: string) =>
  api.post<LeadDetail>(`/leads/${id}/reopen`, { note }).then((r) => r.data);

export const commentLead = (id: number, note: string) =>
  api.post<LeadDetail>(`/leads/${id}/comment`, { note }).then((r) => r.data);

export const saveDraft = (id: number | string, body: Record<string, { available: boolean | null; comment: string | null }>) =>
  api.patch(`/leads/${id}/draft`, body);

export const releaseLead = (id: number, note: string) =>
  api.post<LeadDetail>(`/leads/${id}/release`, { note }).then((r) => r.data);

export const assignLead = (id: number, operatorId: number, note: string) =>
  api.post<LeadDetail>(`/leads/${id}/assign`, { operator_id: operatorId, note }).then((r) => r.data);

/** Statuses a click should try to claim. Finished leads open read-only instead;
 *  reopening one is a deliberate, note-bearing action taken on the lead page. */
export const CLAIMABLE: LeadStatus[] = ["new", "waiting"];

/** The category list is 3,448 entries / ~200 KB and changes only when a scrape
 *  adds a new one. It was refetched on every mount of the queue, so navigating
 *  back and forth re-downloaded it every time. Cached for the session; a reload
 *  is what refreshes it, which is the right cadence for data this static. */
let categoriesCache: Promise<string[]> | null = null;

export function fetchCategories(): Promise<string[]> {
  if (!categoriesCache) {
    categoriesCache = api
      .get<string[]>("/leads/categories")
      .then((r) => r.data)
      .catch((err) => {
        categoriesCache = null; // a failed fetch must not be cached forever
        throw err;
      });
  }
  return categoriesCache;
}
