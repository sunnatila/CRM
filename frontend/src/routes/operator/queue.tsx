import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { ClaimBanner } from "@/components/claim-banner";
import { DeferDialog } from "@/components/defer-dialog";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { formatPhone } from "@/lib/format";
import type { Claim, ClaimBlockError, CompanyQueueItem, MyClaims } from "@/lib/types";

const PAGE_SIZE = 10;
const ALL_CATEGORIES = "__all__";

function errorDetail(err: unknown): ClaimBlockError | null {
  const detail = (err as { response?: { data?: { detail?: ClaimBlockError } } })?.response?.data?.detail;
  return detail ?? null;
}

export function QueuePage() {
  const [tab, setTab] = useState<"unfilled" | "filled">("unfilled");
  const [q, setQ] = useState("");
  const [category, setCategory] = useState(ALL_CATEGORIES);
  const [categories, setCategories] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<CompanyQueueItem[] | null>(null);
  const [total, setTotal] = useState(0);
  const [myClaims, setMyClaims] = useState<MyClaims | null>(null);
  const [deferTarget, setDeferTarget] = useState<{ companyId: number; activeClaim: Claim } | null>(null);
  const navigate = useNavigate();

  async function loadClaims() {
    const res = await api.get<MyClaims>("/claims/me");
    setMyClaims(res.data);
  }

  async function loadCategories() {
    const res = await api.get<string[]>("/reviews/categories");
    setCategories(res.data);
  }

  async function loadQueue() {
    const params = {
      status: tab,
      q: q || undefined,
      category: category === ALL_CATEGORIES ? undefined : category,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    };
    const [itemsRes, countRes] = await Promise.all([
      api.get<CompanyQueueItem[]>("/reviews", { params }),
      api.get<{ total: number }>("/reviews/count", { params }),
    ]);
    setItems(itemsRes.data);
    setTotal(countRes.data.total);
  }

  useEffect(() => {
    loadClaims();
    loadCategories();
  }, []);

  useEffect(() => {
    setItems(null);
    const handle = setTimeout(loadQueue, 200);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, q, category, page]);

  useEffect(() => {
    setPage(1);
  }, [tab, q, category]);

  async function tryClaim(companyId: number) {
    try {
      await api.post(`/claims/${companyId}/claim`);
      navigate(`/review/${companyId}`);
    } catch (err) {
      const detail = errorDetail(err);
      if (detail?.code === "active_claim_exists" && detail.active_claim) {
        setDeferTarget({ companyId, activeClaim: detail.active_claim });
      } else if (detail?.code === "overdue") {
        toast.error("Muddati o'tgan ishlaringiz bor -- avval yuqoridagilarni hal qiling.");
        await loadClaims();
      } else if (detail?.code === "already_claimed") {
        toast.error("Bu kompaniyani boshqa operator band qilib ulgurdi.");
        await loadQueue();
      } else {
        toast.error("Band qilib bo'lmadi.");
      }
    }
  }

  async function handleDeferSubmit(days: number, reason: string | null) {
    if (!deferTarget) return;
    try {
      const res = await api.post<{ auto_approved: boolean }>(`/claims/${deferTarget.activeClaim.id}/defer`, {
        days,
        reason,
      });
      const pendingCompanyId = deferTarget.companyId;
      setDeferTarget(null);
      if (res.data.auto_approved) {
        toast.success("Davom etilmoqda...");
        await loadClaims();
        await tryClaim(pendingCompanyId);
      } else {
        toast.success("So'rov adminga yuborildi. Tasdiqlanguncha kuting.");
        await loadClaims();
      }
    } catch {
      toast.error("So'rovni yuborib bo'lmadi.");
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <AppShell title="To'ldirish ro'yxati">
      {myClaims && (
        <ClaimBanner active={myClaims.active} deferred={myClaims.deferred} onChanged={loadClaims} />
      )}

      <div className="mb-4 flex items-center justify-between gap-4">
        <Tabs value={tab} onValueChange={(v) => setTab(v as "unfilled" | "filled")}>
          <TabsList>
            <TabsTrigger value="unfilled">To'ldirilishi kerak</TabsTrigger>
            <TabsTrigger value="filled">To'ldirilgan</TabsTrigger>
          </TabsList>
        </Tabs>
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
          <Input
            placeholder="Nomi bo'yicha qidirish..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="max-w-64"
          />
        </div>
      </div>

      {items === null && (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      )}

      {items !== null && items.length === 0 && (
        <div className="flex flex-col items-center gap-1 py-16 text-center">
          <p className="text-[20px] font-semibold">
            {tab === "unfilled" ? "Ro'yxat bo'sh — hammasi to'ldirilgan" : "Hali hech narsa to'ldirilmagan"}
          </p>
        </div>
      )}

      {items !== null && items.length > 0 && (
        <>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nomi</TableHead>
                  <TableHead>Manzil</TableHead>
                  <TableHead>Telefon</TableHead>
                  <TableHead>Manba</TableHead>
                  <TableHead>Website</TableHead>
                  <TableHead>LMS</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((c) => (
                  <TableRow
                    key={c.id}
                    className="cursor-pointer"
                    onClick={() => (tab === "unfilled" ? tryClaim(c.id) : navigate(`/review/${c.id}`))}
                  >
                    <TableCell className="max-w-64 truncate font-medium whitespace-nowrap" title={c.name}>
                      {c.name}
                    </TableCell>
                    <TableCell
                      className="text-muted-foreground max-w-48 truncate whitespace-nowrap"
                      title={c.address ?? undefined}
                    >
                      {c.address ?? "—"}
                    </TableCell>
                    <TableCell className="font-mono text-muted-foreground tabular-nums">
                      {formatPhone(c.phone)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">{c.source}</TableCell>
                    <TableCell>
                      <StatusBadge status={c.website_status} />
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={c.lms_status} />
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (tab === "unfilled") tryClaim(c.id);
                          else navigate(`/review/${c.id}`);
                        }}
                      >
                        {tab === "unfilled" ? "To'ldirish" : "Ko'rish"}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="mt-3.5 flex items-center justify-between">
            <p className="text-muted-foreground text-[13px]">
              Jami {total} ta — sahifa {page} / {totalPages}
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

      {deferTarget && (
        <DeferDialog
          activeClaim={deferTarget.activeClaim}
          onCancel={() => setDeferTarget(null)}
          onSubmit={handleDeferSubmit}
        />
      )}
    </AppShell>
  );
}
