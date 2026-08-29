import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, API_BASE } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { LeadStatusBadge } from "@/components/lead-status-badge";
import { FieldStatusBadge } from "@/components/field-status-badge";
import type { LeadList, LeadListItem, OperatorStats } from "@/lib/types";

function avatarSrc(avatarUrl: string | null | undefined): string | undefined {
  if (!avatarUrl) return undefined;
  return `${API_BASE.replace(/\/api\/?$/, "")}${avatarUrl}`;
}

export function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const isOperator = user?.role === "operator";
  const [stats, setStats] = useState<OperatorStats | null>(null);
  const [history, setHistory] = useState<LeadListItem[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    if (!isOperator) return;
    // "actor: me" rather than a filled-by lookup: a finished lead is the unit of
    // work now, and the operator who closed it is the one who did it.
    const [statsRes, approved, rejected] = await Promise.all([
      api.get<OperatorStats>("/me/stats"),
      api.get<LeadList>("/leads", { params: { status: "approved", actor: "me", limit: 20 } }),
      api.get<LeadList>("/leads", { params: { status: "rejected", actor: "me", limit: 20 } }),
    ]);
    setStats(statsRes.data);
    setHistory([...approved.data.items, ...rejected.data.items].slice(0, 20));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOperator]);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await api.post("/auth/me/avatar", formData, { headers: { "Content-Type": "multipart/form-data" } });
      await refreshUser();
      toast.success("Rasm yangilandi.");
    } catch {
      toast.error("Rasmni yuklab bo'lmadi.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  if (!user) return null;

  return (
    <AppShell title={isOperator ? "Mening natijalarim" : "Profil"}>
      <div className="flex max-w-2xl flex-col gap-6">
        <Card className="flex flex-row items-center gap-5 p-5">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="group relative"
            disabled={uploading}
            title="Rasmni o'zgartirish"
          >
            <Avatar className="size-16">
              <AvatarImage src={avatarSrc(user.avatar_url)} alt={user.full_name} />
              <AvatarFallback className="bg-primary text-primary-foreground text-lg">
                {user.full_name
                  .split(" ")
                  .map((p) => p[0])
                  .slice(0, 2)
                  .join("")}
              </AvatarFallback>
            </Avatar>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={handleFileChange}
          />
          <div>
            <p className="text-[16px] font-semibold">{user.full_name}</p>
            <p className="text-muted-foreground text-[13px]">
              @{user.username} · {user.role === "admin" ? "Administrator" : "Operator"}
            </p>
            <Button
              variant="link"
              size="sm"
              className="h-auto p-0 text-[12.5px]"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Yuklanmoqda..." : "Rasmni o'zgartirish"}
            </Button>
          </div>
        </Card>

        {isOperator && (
          <>
            <div className="grid grid-cols-3 gap-3.5">
              <Card className="gap-1 p-5">
                <div className="text-[28px] font-bold tabular-nums">{stats?.today_count ?? "—"}</div>
                <div className="text-muted-foreground text-[12.5px]">Bugun</div>
              </Card>
              <Card className="gap-1 p-5">
                <div className="text-[28px] font-bold tabular-nums">{stats?.week_count ?? "—"}</div>
                <div className="text-muted-foreground text-[12.5px]">Bu hafta</div>
              </Card>
              <Card className="gap-1 p-5">
                <div className="text-[28px] font-bold tabular-nums">{stats?.total_count ?? "—"}</div>
                <div className="text-muted-foreground text-[12.5px]">Jami</div>
              </Card>
            </div>

            <div>
              <h3 className="mb-3 text-[16px] font-semibold">So'nggi yakunlanganlar</h3>
              <div className="rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nomi</TableHead>
                      <TableHead>Holat</TableHead>
                      <TableHead>Website</TableHead>
                      <TableHead>LMS</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(history ?? []).map((c) => (
                      <TableRow key={c.id}>
                        <TableCell className="max-w-64 truncate font-medium" title={c.name}>
                          {c.name}
                        </TableCell>
                        <TableCell>
                          <LeadStatusBadge status={c.status} />
                        </TableCell>
                        <TableCell>
                          <FieldStatusBadge available={c.website_available} />
                        </TableCell>
                        <TableCell>
                          <FieldStatusBadge available={c.lms_available} />
                        </TableCell>
                      </TableRow>
                    ))}
                    {history !== null && history.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={4} className="text-muted-foreground text-center">
                          Hali yakunlangan ish yo'q.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
