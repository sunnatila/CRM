import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRightLeft, Timer } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { LeadStatusBadge } from "@/components/lead-status-badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { useLeadEvents } from "@/lib/use-lead-events";
import type { LeadAttentionItem, LeadList, OperatorStats, OverviewStats } from "@/lib/types";

function initials(fullName: string): string {
  return fullName
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function AdminDashboardPage() {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [operators, setOperators] = useState<OperatorStats[] | null>(null);
  const [attention, setAttention] = useState<LeadAttentionItem[] | null>(null);
  const [counts, setCounts] = useState<Record<string, number> | null>(null);
  const navigate = useNavigate();

  async function load() {
    const [overviewRes, operatorsRes, attentionRes, listRes] = await Promise.all([
      api.get<OverviewStats>("/stats/overview"),
      api.get<OperatorStats[]>("/operators"),
      api.get<LeadAttentionItem[]>("/leads/attention"),
      api.get<LeadList>("/leads", { params: { status: "all", limit: 1 } }),
    ]);
    setOverview(overviewRes.data);
    setOperators([...operatorsRes.data].sort((a, b) => b.today_count - a.today_count));
    setAttention(attentionRes.data);
    setCounts(listRes.data.counts);
  }

  useEffect(() => {
    load();
  }, []);

  useLeadEvents(load);

  const stale = attention?.filter((a) => a.reason === "stale") ?? [];
  const passedAround = attention?.filter((a) => a.reason === "handoffs") ?? [];

  return (
    <AppShell title="Boshqaruv paneli">
      <div className="mb-6 grid grid-cols-4 gap-3.5">
        <Stat value={overview?.today_filled} label="Bugun yakunlangan" />
        <Stat value={overview?.week_filled} label="Bu hafta" />
        {/* NOT another "Kutilmoqda": the distribution row below owns that number.
            This answers what that row cannot -- how far through the catalog the
            team actually is. */}
        <Stat
          value={overview ? overview.finished_leads : undefined}
          label={overview ? `Yakunlangan (${overview.total_companies} tadan)` : "Yakunlangan"}
          tone="text-lead-approved"
        />
        <Stat value={overview?.active_operators} label="Faol operatorlar" />
      </div>

      {/* Status distribution: the fastest read of where the whole pipeline stands. */}
      <div className="mb-6 grid grid-cols-5 gap-3.5">
        {(["new", "in_progress", "waiting", "approved", "rejected"] as const).map((s) => (
          <Card
            key={s}
            className="cursor-pointer gap-2 p-4"
            onClick={() => navigate("/admin/leads")}
          >
            <LeadStatusBadge status={s} />
            <div className="text-[22px] font-bold tabular-nums">{counts?.[s] ?? "—"}</div>
          </Card>
        ))}
      </div>

      {/* Nobody is blocked any more, so the only way an admin learns something is
          stuck is by being shown it (FR-16). */}
      <div className="mb-6 grid grid-cols-2 gap-3.5">
        <AttentionCard
          icon={Timer}
          title="Uzoq turgan ishlar"
          hint="2 kundan beri qimirlamagan"
          items={attention === null ? null : stale}
          empty="Uzoq turgan ish yo'q."
          // "9 kun -- Jasurda qolgan" and "9 kun" call for different
          // responses: one is a conversation, the other is just unclaimed work.
          describe={(a) =>
            a.last_holder ? `${a.waiting_days ?? 0} kun · ${a.last_holder}da` : `${a.waiting_days ?? 0} kun`
          }
          onOpen={(id) => navigate(`/lead/${id}`)}
        />
        <AttentionCard
          icon={ArrowRightLeft}
          title="Ko'p qo'l almashgan"
          hint="3 martadan ko'p operatordan operatorga o'tgan"
          items={attention === null ? null : passedAround}
          empty="Ko'p qo'l almashgan lead yo'q."
          describe={(a) => `${a.handoff_count ?? 0} marta`}
          onOpen={(id) => navigate(`/lead/${id}`)}
        />
      </div>

      <h3 className="mb-3 text-[20px] font-semibold">Operatorlar bo'yicha natija</h3>
      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Operator</TableHead>
              <TableHead>Bugun</TableHead>
              <TableHead>Bu hafta</TableHead>
              <TableHead>Jami</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(operators ?? []).map((op) => (
              <TableRow key={op.id} className="cursor-pointer" onClick={() => navigate("/admin/operators")}>
                <TableCell className="flex items-center gap-2.5 font-medium">
                  <Avatar className="size-6.5">
                    <AvatarFallback className="bg-primary text-primary-foreground text-[11px]">
                      {initials(op.full_name)}
                    </AvatarFallback>
                  </Avatar>
                  {op.full_name}
                </TableCell>
                <TableCell className="font-mono tabular-nums">{op.today_count}</TableCell>
                <TableCell className="font-mono tabular-nums">{op.week_count}</TableCell>
                <TableCell className="font-mono tabular-nums">{op.total_count}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </AppShell>
  );
}

function Stat({ value, label, tone }: { value: number | undefined; label: string; tone?: string }) {
  return (
    <Card className="gap-1 p-5">
      <div className={`text-[28px] font-bold tabular-nums ${tone ?? ""}`}>{value ?? "—"}</div>
      <div className="text-muted-foreground text-[12.5px]">{label}</div>
    </Card>
  );
}

function AttentionCard({
  icon: Icon,
  title,
  hint,
  items,
  empty,
  describe,
  onOpen,
}: {
  icon: typeof Timer;
  title: string;
  hint: string;
  items: LeadAttentionItem[] | null;
  empty: string;
  describe: (a: LeadAttentionItem) => string;
  onOpen: (id: number) => void;
}) {
  return (
    <Card className="gap-3 p-5">
      <div className="flex items-center gap-2">
        <Icon className="text-muted-foreground size-4" />
        <div>
          <h3 className="text-[15px] font-semibold">{title}</h3>
          <p className="text-muted-foreground text-xs">{hint}</p>
        </div>
      </div>

      {items === null && <Skeleton className="h-20 w-full" />}
      {items !== null && items.length === 0 && <p className="text-muted-foreground text-[13px]">{empty}</p>}

      {items !== null && items.length > 0 && (
        <ul className="flex flex-col divide-y">
          {items.slice(0, 6).map((a) => (
            <li key={a.id}>
              <button
                onClick={() => onOpen(a.id)}
                className="hover:bg-muted flex w-full items-center justify-between gap-3 rounded-md px-1.5 py-2 text-left"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[13.5px] font-medium">{a.name}</span>
                  {a.last_note && (
                    <span className="text-muted-foreground block truncate text-xs">{a.last_note}</span>
                  )}
                </span>
                <span className="text-muted-foreground shrink-0 text-xs tabular-nums">{describe(a)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
