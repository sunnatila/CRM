import { Check, Clock, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

type Status = "pending" | "confirmed" | "absent";

const CONFIG: Record<Status, { label: string; icon: typeof Check; className: string }> = {
  confirmed: { label: "Mavjud", icon: Check, className: "bg-status-confirmed text-status-confirmed-foreground" },
  absent: { label: "Yo'q", icon: Minus, className: "bg-status-absent text-status-absent-foreground" },
  pending: { label: "Kutilmoqda", icon: Clock, className: "bg-status-pending text-status-pending-foreground" },
};

export function StatusBadge({ status }: { status: Status }) {
  const { label, icon: Icon, className } = CONFIG[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold whitespace-nowrap",
        className,
      )}
    >
      <Icon className="size-3" />
      {label}
    </span>
  );
}
