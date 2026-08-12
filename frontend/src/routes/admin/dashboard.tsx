import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AppShell } from "@/components/app-shell";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import type { OperatorStats, OverviewStats } from "@/lib/types";

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
  const navigate = useNavigate();

  useEffect(() => {
    (async () => {
      const [overviewRes, operatorsRes] = await Promise.all([
        api.get<OverviewStats>("/stats/overview"),
        api.get<OperatorStats[]>("/operators"),
      ]);
      setOverview(overviewRes.data);
      setOperators([...operatorsRes.data].sort((a, b) => b.today_count - a.today_count));
    })();
  }, []);

  return (
    <AppShell title="Boshqaruv paneli">
      <div className="mb-6 grid grid-cols-4 gap-3.5">
        <Card className="gap-1 p-5">
          <div className="text-[28px] font-bold tabular-nums">{overview?.today_filled ?? "—"}</div>
          <div className="text-muted-foreground text-[12.5px]">Bugun to'ldirilgan</div>
        </Card>
        <Card className="gap-1 p-5">
          <div className="text-[28px] font-bold tabular-nums">{overview?.week_filled ?? "—"}</div>
          <div className="text-muted-foreground text-[12.5px]">Bu hafta</div>
        </Card>
        <Card className="gap-1 p-5">
          <div className="text-status-pending text-[28px] font-bold tabular-nums">
            {overview?.pending_requests ?? "—"}
          </div>
          <div className="text-muted-foreground text-[12.5px]">Kutilayotgan so'rovlar</div>
        </Card>
        <Card className="gap-1 p-5">
          <div className="text-[28px] font-bold tabular-nums">{overview?.active_operators ?? "—"}</div>
          <div className="text-muted-foreground text-[12.5px]">Faol operatorlar</div>
        </Card>
      </div>

      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-[20px] font-semibold">Operatorlar bo'yicha natija</h3>
      </div>
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
              <TableRow key={op.id} className="cursor-pointer" onClick={() => navigate(`/admin/operators`)}>
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
