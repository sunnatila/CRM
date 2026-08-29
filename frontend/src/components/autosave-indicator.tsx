import { AlertCircle, Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type SaveState = "idle" | "saving" | "saved" | "error";

const CONFIG: Record<Exclude<SaveState, "idle">, { icon: typeof Check; label: string; className: string }> = {
  saving: { icon: Loader2, label: "Saqlanmoqda…", className: "text-muted-foreground" },
  saved: { icon: Check, label: "Saqlandi", className: "text-lead-approved" },
  // Never silently swallow a failed save: the operator's typing is still on
  // screen and they need to know it has not reached the server yet. The label
  // says what is actually happening -- there IS a backoff retry now, and when
  // it gives up the button beside it is the way back.
  error: { icon: AlertCircle, label: "Saqlanmadi — qayta urinilmoqda", className: "text-destructive" },
};

export function AutosaveIndicator({ state, onRetry }: { state: SaveState; onRetry?: () => void }) {
  if (state === "idle") return null;
  const { icon: Icon, label, className } = CONFIG[state];
  return (
    <span
      aria-live="polite"
      className={cn("inline-flex items-center gap-1.5 text-xs font-medium", className)}
    >
      <Icon className={cn("size-3.5", state === "saving" && "animate-spin")} />
      {label}
      {state === "error" && onRetry && (
        <button type="button" onClick={onRetry} className="underline underline-offset-2">
          Qayta urinish
        </button>
      )}
    </span>
  );
}
