import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppShell } from "@/components/app-shell";
import { FieldStatusBadge } from "@/components/field-status-badge";
import { LeadStatusBadge } from "@/components/lead-status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatPhone } from "@/lib/format";
import { fetchLeads } from "@/lib/lead-api";
import { useLeadEvents } from "@/lib/use-lead-events";
import { onReconnect } from "@/lib/ws";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";
import type { LeadList, QueueTab } from "@/lib/types";

const PAGE_SIZE = 20;
const ALL_CATEGORIES = "__all__";
const ALL_OPERATORS = "__all__";

interface TabDef {
  key: QueueTab;
  label: string;
  /** Shown when the tab is empty. Some of these are success states, not errors. */
  empty: string;
}

const OPERATOR_TABS: TabDef[] = [
  { key: "new", label: "Yangi", empty: "Yangi lead qolmadi — hammasi ishga olingan." },
  { key: "mine", label: "Mening ishim", empty: "Hozir sizda ochiq ish yo'q. Yangi tabidan birini oling." },
  { key: "waiting", label: "Kutilmoqda", empty: "Yarim qolgan ish yo'q." },
  { key: "approved", label: "Tasdiqlangan", empty: "Hali hech narsa tasdiqlanmagan." },
  { key: "rejected", label: "Rad etilgan", empty: "Rad etilgan lead yo'q." },
];

// The admin's tab set. No "Mening ishim": an admin never holds a lead, so the
// tab would always read zero and imply they were supposed to.
const ADMIN_TABS: TabDef[] = [
  { key: "new", label: "Yangi", empty: "Yangi lead qolmadi — hammasi ishga olingan." },
  { key: "in_progress", label: "Jarayonda", empty: "Hozir hech kim hech narsa ustida ishlamayapti." },
  { key: "waiting", label: "Kutilmoqda", empty: "Yarim qolgan ish yo'q." },
  { key: "approved", label: "Tasdiqlangan", empty: "Hali hech narsa tasdiqlanmagan." },
  { key: "rejected", label: "Rad etilgan", empty: "Rad etilgan lead yo'q." },
  { key: "all", label: "Barchasi", empty: "Baza bo'sh." },
];

function relative(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "hozirgina";
  if (minutes < 60) return `${minutes} daqiqa oldin`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} soat oldin`;
  return `${Math.round(hours / 24)} kun oldin`;
}

export function QueuePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isAdmin = user?.role === "admin";
  const tabs = isAdmin ? ADMIN_TABS : OPERATOR_TABS;

  const [tab, setTab] = useState<QueueTab>("new");
  const [q, setQ] = useState("");
  const [category, setCategory] = useState(ALL_CATEGORIES);
  const [actor, setActor] = useState(ALL_OPERATORS);
  const [operators, setOperators] = useState<{ id: number; full_name: string }[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<LeadList | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const next = await fetchLeads({
        status: tab,
        q,
        category: category === ALL_CATEGORIES ? undefined : category,
        actor: actor === ALL_OPERATORS ? undefined : actor,
        limit: PAGE_SIZE,
        offset: (page - 1) * PAGE_SIZE,
      });
      setData(next);
      setListError(null);
    } catch {
      // A failed load used to throw into nothing, leaving skeletons on screen
      // forever with no error and no way to retry.
      setListError("Ro'yxatni yuklab bo'lmadi — aloqani tekshiring.");
    }
  }, [tab, q, category, actor, page]);

  useEffect(() => {
    api.get<string[]>("/leads/categories").then((r) => setCategories(r.data));
  }, []);

  // Admin-only: the operator list backing the "whose work?" filter.
  useEffect(() => {
    if (!isAdmin) return;
    api
      .get<{ id: number; full_name: string }[]>("/operators")
      .then((r) => setOperators(r.data))
      .catch(() => setOperators([]));
  }, [isAdmin]);

  useEffect(() => {
    // Deliberately NOT `setData(null)` here. Blanking to skeletons on every
    // keystroke, tab click and background refresh is the churn the operator
    // sees as "it keeps refreshing" -- the old rows stay on screen and are
    // replaced when the new ones arrive.
    const handle = setTimeout(load, 200);
    return () => clearTimeout(handle);
  }, [load]);

  useEffect(() => {
    setPage(1);
  }, [tab, q, category, actor]);

  // Somebody else claiming or releasing a lead changes what belongs in this
  // list, so the queue refreshes itself rather than waiting for a click that
  // would then 409 (FR-15).
  useLeadEvents(load);

  // A dropped socket misses frames outright and nothing replays them, so a tab
  // that was briefly offline would sit on pre-outage rows indefinitely.
  useEffect(() => onReconnect(load), [load]);

  function openRow(id: number) {
    // Opening is never claiming. Clicking a row used to call start() for a
    // new/waiting lead, so merely looking at one moved it to in_progress and
    // put the operator on the hook for a handover comment to back out of it.
    // Claiming is now only ever the explicit "Ishni boshlash" button on the
    // lead's own page, where the operator can actually see what they are taking.
    navigate(`/lead/${id}`);
  }

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE));
  const activeTab = tabs.find((t) => t.key === tab)!;
  // The admin's whole job here is seeing who holds what, so the column is
  // always on for them.
  const showsAssignee = isAdmin;

  return (
    <AppShell title={isAdmin ? "Barcha leadlar" : "Leadlar"}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5" role="tablist">
          {tabs.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-1.5 text-[13.5px] font-medium transition-colors",
                tab === t.key
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              {t.label}
              {data && (
                <span
                  className={cn(
                    "rounded-full px-1.5 py-0.5 text-[11px] font-semibold tabular-nums",
                    tab === t.key ? "bg-primary-foreground/20" : "bg-muted",
                  )}
                >
                  {data.counts[t.key] ?? 0}
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Kategoriya" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_CATEGORIES}>Barcha kategoriyalar</SelectItem>
              {categories.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {isAdmin && (
            <Select value={actor} onValueChange={setActor}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Operator" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_OPERATORS}>Barcha operatorlar</SelectItem>
                {operators.map((o) => (
                  <SelectItem key={o.id} value={String(o.id)}>
                    {o.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Input
            placeholder="Nomi bo'yicha qidirish..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="max-w-64"
          />
        </div>
      </div>

      {data === null && listError && (
        <div className="flex flex-col items-start gap-3 py-12">
          <p className="text-[15px] font-semibold">{listError}</p>
          <Button size="sm" onClick={() => void load()}>
            Qayta urinish
          </Button>
        </div>
      )}

      {data === null && !listError && (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {data !== null && data.items.length === 0 && (
        <div className="flex flex-col items-center gap-1 py-16 text-center">
          <p className="text-[18px] font-semibold">{activeTab.empty}</p>
        </div>
      )}

      {data !== null && data.items.length > 0 && (
        <>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nomi</TableHead>
                  <TableHead>Holat</TableHead>
                  {showsAssignee && <TableHead>Kimda</TableHead>}
                  <TableHead>Telefon</TableHead>
                  <TableHead>Website</TableHead>
                  <TableHead>LMS</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((c) => (
                  <TableRow key={c.id} className="cursor-pointer" onClick={() => openRow(c.id)}>
                    <TableCell className="max-w-80 align-top">
                      <div className="truncate font-medium" title={c.name}>
                        {c.name}
                      </div>
                      {/* The handover comment, right in the row: an operator can
                          judge a waiting lead without opening it (FR-12). */}
                      {c.last_note && (
                        <div className="text-muted-foreground mt-0.5 truncate text-xs" title={c.last_note}>
                          {c.last_note_by ?? "Tizim"}
                          {c.last_note_at && `, ${relative(c.last_note_at)}`}: {c.last_note}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="align-top">
                      <LeadStatusBadge status={c.status} />
                    </TableCell>
                    {showsAssignee && (
                      <TableCell className="text-muted-foreground align-top text-[13px]">
                        {c.assignee_name ?? "—"}
                      </TableCell>
                    )}
                    <TableCell className="text-muted-foreground align-top font-mono tabular-nums">
                      {formatPhone(c.phone)}
                    </TableCell>
                    <TableCell className="align-top">
                      <FieldStatusBadge available={c.website_available} />
                    </TableCell>
                    <TableCell className="align-top">
                      <FieldStatusBadge available={c.lms_available} />
                    </TableCell>
                    <TableCell className="align-top">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          openRow(c.id);
                        }}
                      >
                        Ochish
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="mt-3.5 flex items-center justify-between">
            <p className="text-muted-foreground text-[13px]">
              Jami {data.total} ta — sahifa {page} / {totalPages}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Oldingi
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Keyingi
              </Button>
            </div>
          </div>
        </>
      )}

      {/* No handover dialog here any more: the queue never claims, so it can
          never be the thing that forces an operator to hand over what they hold.
          That conversation now happens only on the lead page, at the moment the
          operator actually presses "Ishni boshlash". */}
    </AppShell>
  );
}
