import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import type { ClaimRequestItem, PermissionRequestItem } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = { pending: "Kutilmoqda", approved: "Tasdiqlangan", denied: "Rad etilgan" };
const FIELD_LABEL: Record<string, string> = { website: "Website", lms: "LMS" };
const ACTION_LABEL: Record<string, string> = { extend: "Muddat cho'zish", release: "Ishdan voz kechish" };

type StatusFilter = "all" | "pending" | "approved" | "denied";

function formatDate(value: string): string {
  return new Date(value).toLocaleString("uz-UZ");
}

function PermissionRequestsTable({ status }: { status: StatusFilter }) {
  const [items, setItems] = useState<PermissionRequestItem[] | null>(null);

  useEffect(() => {
    setItems(null);
    const params = status === "all" ? {} : { status };
    api.get<PermissionRequestItem[]>("/permission-requests", { params }).then((res) => setItems(res.data));
  }, [status]);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Kompaniya</TableHead>
          <TableHead>Maydon</TableHead>
          <TableHead>Sabab</TableHead>
          <TableHead>Admin izohi</TableHead>
          <TableHead>Holat</TableHead>
          <TableHead>Yuborilgan</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {(items ?? []).map((r) => (
          <TableRow key={r.id}>
            <TableCell className="max-w-56 truncate font-medium whitespace-nowrap" title={r.company_name}>
              {r.company_name}
            </TableCell>
            <TableCell>{FIELD_LABEL[r.field] ?? r.field}</TableCell>
            <TableCell className="text-muted-foreground max-w-56 truncate" title={r.reason ?? undefined}>
              {r.reason ?? "—"}
            </TableCell>
            <TableCell className="text-muted-foreground max-w-56 truncate" title={r.resolution_note ?? undefined}>
              {r.resolution_note ?? "—"}
            </TableCell>
            <TableCell>
              <Badge variant="secondary">{STATUS_LABEL[r.status] ?? r.status}</Badge>
            </TableCell>
            <TableCell className="text-muted-foreground text-xs whitespace-nowrap">{formatDate(r.created_at)}</TableCell>
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
  );
}

function ClaimRequestsTable({ status }: { status: StatusFilter }) {
  const [items, setItems] = useState<ClaimRequestItem[] | null>(null);

  useEffect(() => {
    setItems(null);
    const params = status === "all" ? {} : { status };
    api.get<ClaimRequestItem[]>("/claim-requests", { params }).then((res) => setItems(res.data));
  }, [status]);

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Kompaniya</TableHead>
          <TableHead>So'rov turi</TableHead>
          <TableHead>Sabab</TableHead>
          <TableHead>Admin izohi</TableHead>
          <TableHead>Holat</TableHead>
          <TableHead>Yuborilgan</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {(items ?? []).map((r) => (
          <TableRow key={r.id}>
            <TableCell className="max-w-56 truncate font-medium whitespace-nowrap" title={r.company_name}>
              {r.company_name}
            </TableCell>
            <TableCell className="whitespace-nowrap">
              {ACTION_LABEL[r.action] ?? r.action}
              {r.action === "extend" && r.requested_days ? ` (${r.requested_days} kun)` : ""}
            </TableCell>
            <TableCell className="text-muted-foreground max-w-56 truncate" title={r.reason ?? undefined}>
              {r.reason ?? "—"}
            </TableCell>
            <TableCell className="text-muted-foreground max-w-56 truncate" title={r.resolution_note ?? undefined}>
              {r.resolution_note ?? "—"}
            </TableCell>
            <TableCell>
              <Badge variant="secondary">{STATUS_LABEL[r.status] ?? r.status}</Badge>
            </TableCell>
            <TableCell className="text-muted-foreground text-xs whitespace-nowrap">{formatDate(r.created_at)}</TableCell>
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
  );
}

export function MyRequestsPage() {
  const [searchParams] = useSearchParams();
  const initialType = searchParams.get("type") === "claim" ? "claim" : "permission";
  const [type, setType] = useState<"permission" | "claim">(initialType);
  const [status, setStatus] = useState<StatusFilter>("all");

  return (
    <AppShell title="Mening so'rovlarim">
      <div className="mb-4 flex items-center justify-between gap-4">
        <Tabs value={type} onValueChange={(v) => setType(v as typeof type)}>
          <TabsList>
            <TabsTrigger value="permission">Ruxsat so'rovlari</TabsTrigger>
            <TabsTrigger value="claim">Ish so'rovlari</TabsTrigger>
          </TabsList>
        </Tabs>
        <Tabs value={status} onValueChange={(v) => setStatus(v as StatusFilter)}>
          <TabsList>
            <TabsTrigger value="all">Hammasi</TabsTrigger>
            <TabsTrigger value="pending">Kutilmoqda</TabsTrigger>
            <TabsTrigger value="approved">Tasdiqlangan</TabsTrigger>
            <TabsTrigger value="denied">Rad etilgan</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      <div className="rounded-lg border">
        {type === "permission" ? <PermissionRequestsTable status={status} /> : <ClaimRequestsTable status={status} />}
      </div>
    </AppShell>
  );
}
