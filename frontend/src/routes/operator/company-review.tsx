import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
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
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ReviewFieldCard } from "@/components/review-field-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { formatPhone } from "@/lib/format";
import type { CompanyReviewDetail } from "@/lib/types";

type Draft = { available: boolean | null; comment: string };

export function CompanyReviewPage() {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<CompanyReviewDetail | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [requestingField, setRequestingField] = useState<string | null>(null);
  const [requestReason, setRequestReason] = useState("");

  async function load() {
    const res = await api.get<CompanyReviewDetail>(`/reviews/${companyId}`);
    setDetail(res.data);
    setDrafts((prev) => {
      const next: Record<string, Draft> = {};
      for (const f of res.data.fields) {
        if (!f.locked) {
          // available defaults to false (not null): a checkbox is inherently
          // true/false, so an untouched box must mean a real "yo'q", not a third
          // "undecided" state -- otherwise Submit can never enable without an
          // arbitrary check+uncheck click on fields the operator means to leave unchecked.
          next[f.field] = prev[f.field] ?? { available: f.available ?? false, comment: f.comment ?? "" };
        }
      }
      return next;
    });
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [companyId]);

  if (!detail) {
    return (
      <AppShell title="Ko'rib chiqish">
        <div className="mx-auto flex max-w-2xl flex-col gap-3.5">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </AppShell>
    );
  }

  const editableFields = detail.fields.filter((f) => !f.locked);
  const canSubmit =
    editableFields.length > 0 &&
    editableFields.every((f) => {
      const d = drafts[f.field];
      return d && d.comment.trim() !== "";
    });

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const body: Record<string, { available: boolean; comment: string }> = {};
      for (const f of editableFields) {
        const d = drafts[f.field];
        if (d && d.available !== null) body[f.field] = { available: d.available, comment: d.comment };
      }
      await api.post(`/reviews/${companyId}`, body);
      toast.success("Saqlandi.");
      setConfirmOpen(false);
      await load();
    } catch {
      toast.error("Saqlab bo'lmadi. Qayta urinib ko'ring.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRequestPermission() {
    if (!requestingField) return;
    try {
      await api.post(`/reviews/${companyId}/${requestingField}/request-permission`, {
        reason: requestReason || null,
      });
      toast.success("Ruxsat so'raldi. Admin javobini kuting.");
      setRequestingField(null);
      setRequestReason("");
      await load();
    } catch {
      toast.error("So'rovni yuborib bo'lmadi.");
    }
  }

  return (
    <AppShell title={detail.name}>
      <div className="mx-auto flex max-w-2xl flex-col gap-5">
        <Button variant="ghost" size="sm" className="w-fit" onClick={() => navigate("/queue")}>
          <ArrowLeft className="size-4" /> Ro'yxatga qaytish
        </Button>

        <Card className="grid grid-cols-2 gap-x-7 gap-y-3.5 p-5">
          <div className="flex flex-col gap-0.5">
            <span className="text-muted-foreground text-[11.5px] tracking-wide uppercase">Toifa</span>
            <span className="text-[14px] font-medium">{detail.category ?? "—"}</span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-muted-foreground text-[11.5px] tracking-wide uppercase">Telefon</span>
            <span className="font-mono text-[14px] font-medium">{formatPhone(detail.phone)}</span>
          </div>
          <div className="col-span-2 flex flex-col gap-0.5">
            <span className="text-muted-foreground text-[11.5px] tracking-wide uppercase">Manzil</span>
            <span className="text-[14px] font-medium">{detail.address ?? "—"}</span>
          </div>
        </Card>

        {detail.fields.map((f) => (
          <ReviewFieldCard
            key={f.field}
            field={f}
            draft={drafts[f.field] ?? { available: null, comment: "" }}
            onChange={(d) => setDrafts((prev) => ({ ...prev, [f.field]: d }))}
            onRequestPermission={() => setRequestingField(f.field)}
          />
        ))}

        {editableFields.length > 0 && (
          <Button className="w-full" disabled={!canSubmit || submitting} onClick={() => setConfirmOpen(true)}>
            Saqlash
          </Button>
        )}
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Saqlashni tasdiqlaysizmi?</AlertDialogTitle>
            <AlertDialogDescription>
              Saqlagandan so'ng bu yozuvni faqat ruxsat bilan tahrirlash mumkin. Davom etasizmi?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Bekor qilish</AlertDialogCancel>
            <AlertDialogAction onClick={handleSubmit} disabled={submitting}>
              Saqlash
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={requestingField !== null} onOpenChange={(open) => !open && setRequestingField(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Ruxsat so'rash</AlertDialogTitle>
            <AlertDialogDescription>Nega qayta tahrirlashni so'rayapsiz? (ixtiyoriy)</AlertDialogDescription>
          </AlertDialogHeader>
          <Textarea value={requestReason} onChange={(e) => setRequestReason(e.target.value)} />
          <AlertDialogFooter>
            <AlertDialogCancel>Bekor qilish</AlertDialogCancel>
            <AlertDialogAction onClick={handleRequestPermission}>Yuborish</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
