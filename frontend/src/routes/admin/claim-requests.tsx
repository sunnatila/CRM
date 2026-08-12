import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { ClaimRequestItem } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = { pending: "Kutilmoqda", approved: "Tasdiqlangan", denied: "Rad etilgan" };
const ACTION_LABEL: Record<string, string> = { extend: "Muddat cho'zish", release: "Ishdan voz kechish" };

type PendingDecision = { request: ClaimRequestItem; decision: "approve" | "deny" };

export function ClaimRequestsPage() {
  const [status, setStatus] = useState<"pending" | "approved" | "denied">("pending");
  const [items, setItems] = useState<ClaimRequestItem[] | null>(null);
  const [pendingDecision, setPendingDecision] = useState<PendingDecision | null>(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    const res = await api.get<ClaimRequestItem[]>("/claim-requests", { params: { status } });
    setItems(res.data);
  }

  useEffect(() => {
    setItems(null);
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  async function handleConfirm() {
    if (!pendingDecision) return;
    setSubmitting(true);
    try {
      await api.post(`/claim-requests/${pendingDecision.request.id}/${pendingDecision.decision}`, {
        note: note.trim() || null,
      });
      toast.success(pendingDecision.decision === "approve" ? "Tasdiqlandi." : "Rad etildi.");
      setPendingDecision(null);
      setNote("");
      await load();
    } catch {
      toast.error("Amalni bajarib bo'lmadi.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell title="Ish so'rovlari">
      <Tabs value={status} onValueChange={(v) => setStatus(v as typeof status)} className="mb-4">
        <TabsList>
          <TabsTrigger value="pending">Kutilmoqda</TabsTrigger>
          <TabsTrigger value="approved">Tasdiqlangan</TabsTrigger>
          <TabsTrigger value="denied">Rad etilgan</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Operator</TableHead>
              <TableHead>Kompaniya</TableHead>
              <TableHead>So'rov turi</TableHead>
              <TableHead>Sabab</TableHead>
              {status === "pending" ? <TableHead /> : <TableHead>Admin izohi</TableHead>}
              <TableHead>Holat</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(items ?? []).map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-medium whitespace-nowrap">{r.operator_name}</TableCell>
                <TableCell className="max-w-56 truncate whitespace-nowrap" title={r.company_name}>
                  {r.company_name}
                </TableCell>
                <TableCell className="whitespace-nowrap">
                  {ACTION_LABEL[r.action] ?? r.action}
                  {r.action === "extend" && r.requested_days ? ` (${r.requested_days} kun)` : ""}
                </TableCell>
                <TableCell className="text-muted-foreground max-w-56 truncate" title={r.reason ?? undefined}>
                  {r.reason ?? "—"}
                </TableCell>
                {status === "pending" ? (
                  <TableCell className="flex gap-2">
                    <Button size="sm" onClick={() => setPendingDecision({ request: r, decision: "approve" })}>
                      Tasdiqlash
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setPendingDecision({ request: r, decision: "deny" })}
                    >
                      Rad etish
                    </Button>
                  </TableCell>
                ) : (
                  <TableCell className="text-muted-foreground max-w-56 truncate" title={r.resolution_note ?? undefined}>
                    {r.resolution_note ?? "—"}
                  </TableCell>
                )}
                <TableCell>
                  <Badge variant="secondary">{STATUS_LABEL[r.status] ?? r.status}</Badge>
                </TableCell>
              </TableRow>
            ))}
            {items !== null && items.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="text-muted-foreground text-center">
                  Hech narsa yo'q.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      <AlertDialog open={pendingDecision !== null} onOpenChange={(open) => !open && setPendingDecision(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {pendingDecision?.decision === "approve" ? "Tasdiqlash" : "Rad etish"} —{" "}
              {pendingDecision?.request.company_name}
            </AlertDialogTitle>
          </AlertDialogHeader>
          <div className="flex flex-col gap-1.5">
            <label className="text-muted-foreground text-xs font-medium">Izoh (ixtiyoriy)</label>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Operatorga ko'rinadigan izoh..."
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setNote("")}>Bekor qilish</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirm} disabled={submitting}>
              {pendingDecision?.decision === "approve" ? "Tasdiqlash" : "Rad etish"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
