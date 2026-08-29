import { Check, Circle, CircleDot, Clock, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LeadStatus } from "@/lib/types";

/** The lead workflow vocabulary. Deliberately separate from the field vocabulary
 *  in `field-status-badge.tsx`: "is this lead done?" and "does this company have
 *  a website?" are different questions, and one badge answering both would be
 *  read wrong on a dense queue row.
 *
 *  Every pair is icon + colour + text (never colour alone) and every fill/text
 *  combination clears 4.5:1 -- see the token block in `index.css`. */
const CONFIG: Record<LeadStatus, { label: string; icon: typeof Check; className: string }> = {
  new: { label: "Yangi", icon: Circle, className: "bg-lead-new text-lead-new-foreground" },
  in_progress: {
    label: "Jarayonda",
    icon: CircleDot,
    className: "bg-lead-progress text-lead-progress-foreground",
  },
  waiting: { label: "Kutilmoqda", icon: Clock, className: "bg-lead-waiting text-lead-waiting-foreground" },
  approved: { label: "Tasdiqlangan", icon: Check, className: "bg-lead-approved text-lead-approved-foreground" },
  rejected: { label: "Rad etilgan", icon: X, className: "bg-lead-rejected text-lead-rejected-foreground" },
};

export function LeadStatusBadge({ status, size = "sm" }: { status: LeadStatus; size?: "sm" | "lg" }) {
  const { label, icon: Icon, className } = CONFIG[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-semibold whitespace-nowrap",
        size === "lg" ? "px-3 py-1.5 text-[13px]" : "px-2.5 py-1 text-xs",
        className,
      )}
    >
      <Icon className={size === "lg" ? "size-3.5" : "size-3"} />
      {label}
    </span>
  );
}
