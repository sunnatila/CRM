import { useState } from "react";
import {
  ArrowRightLeft,
  Check,
  CornerUpLeft,
  Database,
  MessageSquare,
  Send,
  ShieldAlert,
  Timer,
  UserPlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { LeadEvent } from "@/lib/types";

/** v2's control mechanism, rendered.
 *
 *  The old system prevented mistakes by locking records; this one allows the
 *  edit and shows who made it. That trade only works if the record is actually
 *  legible, so this panel is a first-class part of the lead page, not a footnote. */

const META: Record<LeadEvent["type"], { icon: typeof Check; label: string; tone?: string }> = {
  status_change: { icon: ArrowRightLeft, label: "Holat o'zgardi" },
  handover: { icon: MessageSquare, label: "Ish qoldirildi", tone: "text-lead-waiting" },
  comment: { icon: MessageSquare, label: "Izoh" },
  finish: { icon: Check, label: "Yakunlandi", tone: "text-lead-approved" },
  reopen: { icon: CornerUpLeft, label: "Qayta ochildi", tone: "text-lead-progress" },
  auto_release: { icon: Timer, label: "Avtomatik bo'shatildi", tone: "text-muted-foreground" },
  admin_release: { icon: ShieldAlert, label: "Admin bo'shatdi", tone: "text-destructive" },
  admin_assign: { icon: UserPlus, label: "Admin biriktirdi", tone: "text-lead-progress" },
  migration: { icon: Database, label: "Migratsiya", tone: "text-muted-foreground" },
};

function relative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "hozirgina";
  if (minutes < 60) return `${minutes} daqiqa oldin`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} soat oldin`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} kun oldin`;
  return new Date(iso).toLocaleDateString("uz-UZ");
}

export function LeadTimeline({
  events,
  canComment,
  onComment,
}: {
  events: LeadEvent[];
  canComment: boolean;
  onComment: (note: string) => Promise<void> | void;
}) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);

  async function send() {
    const note = draft.trim();
    if (!note) return;
    setSending(true);
    try {
      await onComment(note);
      setDraft("");
    } finally {
      setSending(false);
    }
  }

  return (
    <Card className="gap-4 p-5">
      <h3 className="text-[15px] font-semibold">Tarix</h3>

      {canComment && (
        <div className="flex flex-col gap-2">
          <Textarea
            rows={2}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Izoh qo'shish — nima aniqlandi, nima qilindi..."
          />
          <Button size="sm" className="w-fit" disabled={!draft.trim() || sending} onClick={send}>
            <Send className="size-3.5" />
            Izohni saqlash
          </Button>
        </div>
      )}

      {events.length === 0 ? (
        <p className="text-muted-foreground text-[13px]">Hali hech qanday harakat bo'lmagan.</p>
      ) : (
        <ol className="flex flex-col gap-3.5">
          {events.map((e) => {
            const { icon: Icon, label, tone } = META[e.type] ?? META.comment;
            return (
              <li key={e.id} className="flex gap-2.5">
                <Icon className={cn("mt-0.5 size-4 shrink-0", tone ?? "text-muted-foreground")} />
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] leading-snug">
                    <span className="font-medium">{e.actor ?? "Tizim"}</span>
                    <span className="text-muted-foreground"> · {label}</span>
                    <span className="text-muted-foreground"> · {relative(e.created_at)}</span>
                  </p>
                  {e.note && <p className="mt-0.5 text-[13.5px] break-words">{e.note}</p>}
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </Card>
  );
}
