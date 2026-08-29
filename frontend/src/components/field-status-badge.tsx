import { Check, Clock, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

/** The field vocabulary: does this company have a website / an LMS?
 *
 *  Three answers, unchanged from v1 apart from the two contrast fixes in
 *  `index.css`. `null` means the operator has not decided yet -- in v2 that is a
 *  real, storable third state rather than a false the form invented. */
type FieldStatus = "pending" | "confirmed" | "absent";

const CONFIG: Record<FieldStatus, { label: string; icon: typeof Check; className: string }> = {
  confirmed: { label: "Mavjud", icon: Check, className: "bg-status-confirmed text-status-confirmed-foreground" },
  absent: { label: "Yo'q", icon: Minus, className: "bg-status-absent text-status-absent-foreground" },
  pending: { label: "Belgilanmagan", icon: Clock, className: "bg-status-pending text-status-pending-foreground" },
};

function fieldStatus(available: boolean | null): FieldStatus {
  if (available === null) return "pending";
  return available ? "confirmed" : "absent";
}

export function FieldStatusBadge({ available }: { available: boolean | null }) {
  const { label, icon: Icon, className } = CONFIG[fieldStatus(available)];
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
