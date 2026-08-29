import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { LeadStatusBadge } from "@/components/lead-status-badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useLeadEvents } from "@/lib/use-lead-events";
import type { LeadList, LeadListItem } from "@/lib/types";

/** Replaces v1's "Mening so'rovlarim".
 *
 *  That page existed to let an operator watch requests they were waiting on --
 *  and v2 has no waiting. What is actually useful now is the opposite view:
 *  what I am holding, and what I finished. */
export function MyWorkPage() {
  const navigate = useNavigate();
  const [current, setCurrent] = useState<LeadListItem[] | null>(null);
  const [waiting, setWaiting] = useState<LeadListItem[] | null>(null);
  const [done, setDone] = useState<LeadListItem[] | null>(null);

  const load = useCallback(async () => {
    const get = (params: Record<string, unknown>) =>
      api.get<LeadList>("/leads", { params: { limit: 20, offset: 0, ...params } }).then((r) => r.data.items);
    const [mine, mineWaiting, approved, rejected] = await Promise.all([
      get({ status: "mine" }),
      get({ status: "waiting", actor: "me" }),
      get({ status: "approved", actor: "me" }),
      get({ status: "rejected", actor: "me" }),
    ]);
    setCurrent(mine);
    setWaiting(mineWaiting);
    setDone([...approved, ...rejected].slice(0, 20));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useLeadEvents(load);

  return (
    <AppShell title="Mening ishlarim">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        <Section
          title="Hozirgi ish"
          items={current}
          empty="Hozir sizda ochiq ish yo'q."
          onOpen={(id) => navigate(`/lead/${id}`)}
        />
        <Section
          title="Men qoldirganlar"
          items={waiting}
          empty="Siz qoldirgan yarim ish yo'q."
          hint="Bularni istalgan operator olishi mumkin — siz ham qaytib olsangiz bo'ladi."
          onOpen={(id) => navigate(`/lead/${id}`)}
        />
        <Section
          title="Yaqinda yakunlanganlar"
          items={done}
          empty="Hali yakunlangan ish yo'q."
          onOpen={(id) => navigate(`/lead/${id}`)}
        />
      </div>
    </AppShell>
  );
}

function Section({
  title,
  items,
  empty,
  hint,
  onOpen,
}: {
  title: string;
  items: LeadListItem[] | null;
  empty: string;
  hint?: string;
  onOpen: (id: number) => void;
}) {
  return (
    <section className="flex flex-col gap-2.5">
      <div>
        <h2 className="text-[15px] font-semibold">{title}</h2>
        {hint && <p className="text-muted-foreground text-[13px]">{hint}</p>}
      </div>

      {items === null && <Skeleton className="h-16 w-full" />}
      {items !== null && items.length === 0 && <p className="text-muted-foreground text-[13.5px]">{empty}</p>}

      {items?.map((item) => (
        <Card key={item.id} className="flex flex-row items-center justify-between gap-4 p-4">
          <div className="min-w-0">
            <p className="truncate text-[14.5px] font-medium">{item.name}</p>
            {item.last_note && (
              <p className="text-muted-foreground mt-0.5 truncate text-xs" title={item.last_note}>
                {item.last_note}
              </p>
            )}
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <LeadStatusBadge status={item.status} />
            <Button size="sm" variant="outline" onClick={() => onOpen(item.id)}>
              Ochish <ArrowRight className="size-3.5" />
            </Button>
          </div>
        </Card>
      ))}
    </section>
  );
}
