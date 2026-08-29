import { useState } from "react";
import { toast } from "sonner";
import { leadError, startLead, switchLead } from "@/lib/lead-api";

interface Pending {
  toId: number;
  fromId: number;
  fromName: string;
}

/** The "take this lead" flow, including the one case that needs a comment.
 *
 *  The server refuses a second simultaneous claim with `handover_required` and
 *  tells us which lead is in the way; we surface the dialog, then replay the
 *  action as an atomic switch. Keeping this in one hook means the queue and the
 *  lead page cannot drift into two different versions of the rule.
 */
export function useStartLead(onDone: (companyId: number) => void, onConflict?: () => void) {
  const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState(false);

  async function start(companyId: number) {
    setBusy(true);
    try {
      await startLead(companyId);
      onDone(companyId);
    } catch (err) {
      const detail = leadError(err);
      if (detail?.code === "handover_required" && detail.active_company_id) {
        setPending({
          toId: companyId,
          fromId: detail.active_company_id,
          fromName: detail.active_company_name ?? "",
        });
      } else if (detail?.code === "held_by_other") {
        toast.error(detail.message);
        onConflict?.();
      } else {
        toast.error(detail?.message ?? "Ishni boshlab bo'lmadi.");
      }
    } finally {
      setBusy(false);
    }
  }

  async function confirmHandover(note: string) {
    if (!pending) return;
    setBusy(true);
    try {
      await switchLead(pending.toId, pending.fromId, note);
      const target = pending.toId;
      setPending(null);
      onDone(target);
    } catch (err) {
      const detail = leadError(err);
      toast.error(detail?.message ?? "O'tib bo'lmadi.");
      // The switch is atomic server-side, so a failure here means the operator
      // still holds their original lead -- nothing to roll back on the client.
      setPending(null);
      onConflict?.();
    } finally {
      setBusy(false);
    }
  }

  return { start, pending, confirmHandover, cancelHandover: () => setPending(null), busy };
}
