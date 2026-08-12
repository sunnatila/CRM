import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { Claim } from "@/lib/types";

type OverdueAction = { claim: Claim; kind: "extend" | "release" };

function formatDeadline(deadlineAt: string | null): string {
  if (!deadlineAt) return "";
  return new Date(deadlineAt).toLocaleString("uz-UZ");
}

export function ClaimBanner({
  active,
  deferred,
  onChanged,
}: {
  active: Claim | null;
  deferred: Claim[];
  onChanged: () => void;
}) {
  const navigate = useNavigate();
  const [action, setAction] = useState<OverdueAction | null>(null);
  const [days, setDays] = useState(3);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const overdue = deferred.filter((c) => c.overdue);
  const upcoming = deferred.filter((c) => !c.overdue);

  if (!active && deferred.length === 0) return null;

  async function handleSubmitAction() {
    if (!action) return;
    setSubmitting(true);
    try {
      if (action.kind === "extend") {
        await api.post(`/claims/${action.claim.id}/request-extend`, { days, reason });
        toast.success("Muddat cho'zish so'rovi yuborildi. Admin javobini kuting.");
      } else {
        if (!reason.trim()) {
          toast.error("Sabab kiritish shart.");
          setSubmitting(false);
          return;
        }
        await api.post(`/claims/${action.claim.id}/request-release`, { reason });
        toast.success("Rad etish so'rovi yuborildi. Admin javobini kuting.");
      }
      setAction(null);
      setReason("");
      onChanged();
    } catch {
      toast.error("So'rovni yuborib bo'lmadi.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mb-5 flex flex-col gap-2.5">
      {active && (
        <Card className="flex flex-row items-center justify-between gap-4 p-4">
          <div>
            <p className="text-muted-foreground text-[11.5px] font-semibold tracking-wide uppercase">Faol ish</p>
            <p className="text-[14.5px] font-medium">{active.company_name}</p>
          </div>
          <Button size="sm" onClick={() => navigate(`/review/${active.company_id}`)}>
            Davom etish
          </Button>
        </Card>
      )}

      {overdue.map((c) => (
        <Card key={c.id} className="border-status-pending flex flex-col gap-2 border-2 p-4">
          <p className="text-[13.5px] font-medium">
            <span className="text-status-pending font-semibold">Muddati o'tdi:</span> {c.company_name} uchun siz{" "}
            {c.deadline_days} kun ichida to'ldiraman degan edingiz. Buni hal qilmasangiz boshqa ishga o'ta olmaysiz.
          </p>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => setAction({ claim: c, kind: "extend" })}>
              Muddat cho'zish
            </Button>
            <Button size="sm" variant="outline" onClick={() => setAction({ claim: c, kind: "release" })}>
              Rad etish so'rash
            </Button>
            <Button size="sm" variant="ghost" onClick={() => navigate(`/review/${c.company_id}`)}>
              Ko'rish
            </Button>
          </div>
        </Card>
      ))}

      {upcoming.map((c) => (
        <Card key={c.id} className="flex flex-row items-center justify-between gap-4 p-4">
          <div>
            <p className="text-muted-foreground text-[11.5px] font-semibold tracking-wide uppercase">
              Kechiktirilgan
            </p>
            <p className="text-[14.5px] font-medium">{c.company_name}</p>
            <p className="text-muted-foreground text-xs">Muddat: {formatDeadline(c.deadline_at)}</p>
          </div>
          <Button size="sm" variant="outline" onClick={() => navigate(`/review/${c.company_id}`)}>
            Ko'rish
          </Button>
        </Card>
      ))}

      <AlertDialog open={action !== null} onOpenChange={(open) => !open && setAction(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {action?.kind === "extend" ? "Muddat cho'zish" : "Ishdan voz kechish"} — {action?.claim.company_name}
            </AlertDialogTitle>
            <AlertDialogDescription>
              So'rovingiz adminga yuboriladi va tasdiqlanishi kerak.
            </AlertDialogDescription>
          </AlertDialogHeader>
          {action?.kind === "extend" && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="extend-days">Necha kun kerak?</Label>
              <Input
                id="extend-days"
                type="number"
                min={1}
                max={30}
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
              />
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="action-reason">
              {action?.kind === "release" ? "Sabab (majburiy)" : "Izoh (ixtiyoriy)"}
            </Label>
            <Textarea id="action-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setReason("")}>Bekor qilish</AlertDialogCancel>
            <AlertDialogAction onClick={handleSubmitAction} disabled={submitting}>
              Yuborish
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
