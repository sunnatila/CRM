import { useState } from "react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { Claim } from "@/lib/types";

interface Props {
  activeClaim: Claim;
  onCancel: () => void;
  onSubmit: (days: number, reason: string | null) => Promise<void> | void;
}

export function DeferDialog({ activeClaim, onCancel, onSubmit }: Props) {
  const [days, setDays] = useState(1);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await onSubmit(days, reason.trim() || null);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AlertDialog open onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Boshqa ishga o'tish</AlertDialogTitle>
          <AlertDialogDescription>
            Sizda faol ish bor: <strong>{activeClaim.company_name}</strong>. Uni necha kunda tugatasiz? 2 kungacha
            darhol davom etasiz; 3 kun va undan ko'p bo'lsa, admin tasdig'i kerak bo'ladi.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="defer-days">Necha kunda tugatasiz?</Label>
          <Input
            id="defer-days"
            type="number"
            min={1}
            max={30}
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="defer-reason">Izoh (3+ kun uchun tavsiya etiladi)</Label>
          <Textarea id="defer-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel>Bekor qilish</AlertDialogCancel>
          <AlertDialogAction onClick={handleSubmit} disabled={submitting}>
            Davom etish
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
