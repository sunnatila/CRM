import { MessageSquare, Timer } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { LeadDetail, LeadEvent } from "@/lib/types";

/** Event types that answer "where did the last person stop?".
 *
 *  A plain `status_change` is excluded on purpose: it carries no note and adding
 *  it here would mean showing an empty banner on every lead that has merely been
 *  picked up and put down. */
const HANDOVER_TYPES: LeadEvent["type"][] = ["handover", "comment", "migration"];

function lastMeaningful(events: LeadEvent[]): LeadEvent | null {
  // `events` arrive newest-first from the API.
  return events.find((e) => HANDOVER_TYPES.includes(e.type) && !!e.note?.trim()) ?? null;
}

function wasAutoReleased(events: LeadEvent[]): boolean {
  // Only if nothing an operator deliberately wrote came after it.
  for (const e of events) {
    if (e.type === "auto_release") return true;
    if (HANDOVER_TYPES.includes(e.type) && e.note?.trim()) return false;
  }
  return false;
}

/** Surfaces the previous operator's parting note before work starts.
 *
 *  Without this the note existed but was effectively invisible: it lived only in
 *  the timeline at the very bottom of the page, below the fields and the action
 *  bar, so an operator picking up a waiting lead had to scroll past everything
 *  to find the one thing that tells them what already happened. */
export function HandoverNotice({ lead, isMine }: { lead: LeadDetail; isMine: boolean }) {
  // Once it is yours and you are working it, the history panel is the right
  // place for this -- a banner would just be permanent furniture.
  if (isMine || lead.status === "approved" || lead.status === "rejected") return null;

  const note = lastMeaningful(lead.events);

  if (note) {
    return (
      <Card className="border-lead-waiting flex flex-row gap-2.5 border-2 p-4">
        <MessageSquare className="text-lead-waiting mt-0.5 size-4 shrink-0" />
        <div className="min-w-0">
          <p className="text-muted-foreground text-[11.5px] font-semibold tracking-wide uppercase">
            Oldingi operator qayerda to'xtagan
          </p>
          <p className="mt-1 text-[14px] break-words">{note.note}</p>
          <p className="text-muted-foreground mt-1 text-xs">
            {note.actor ?? "Tizim"} · {new Date(note.created_at).toLocaleString("uz-UZ")}
          </p>
        </div>
      </Card>
    );
  }

  // No note is itself information -- and it is the case the operator is most
  // likely to misread as "nobody has touched this". Say what actually happened.
  if (wasAutoReleased(lead.events)) {
    return (
      <Card className="flex flex-row gap-2.5 border-2 border-dashed p-4">
        <Timer className="text-muted-foreground mt-0.5 size-4 shrink-0" />
        <div className="min-w-0">
          <p className="text-[13.5px]">
            Bu lead <strong>avtomatik bo'shatilgan</strong> — oldingi operator 4 soat davomida ishlamagan va
            izoh qoldirmagan.
          </p>
          <p className="text-muted-foreground mt-0.5 text-xs">
            Ya'ni bu yerda nima qilinganini bilib bo'lmaydi — noldan boshlashga to'g'ri keladi.
          </p>
        </div>
      </Card>
    );
  }

  return null;
}
