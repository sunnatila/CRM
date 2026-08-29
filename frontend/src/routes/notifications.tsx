import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { BellOff, Check } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { onReconnect, subscribe } from "@/lib/ws";
import { cn } from "@/lib/utils";
import type { NotificationItem } from "@/lib/types";

/** Full notification history.
 *
 *  The bell popover holds ~30 items in a cramped 80-unit column and is the only
 *  place any of this was readable -- fine for "what just happened", useless for
 *  "what did I miss yesterday". Admins in particular had no section at all, while
 *  being the role that accumulates the most: every handover and every finish
 *  notifies them.
 */
export function NotificationsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<NotificationItem[] | null>(null);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get<NotificationItem[]>("/notifications", {
        params: { unread_only: unreadOnly, limit: 100 },
      });
      setItems(res.data);
      setError(null);
    } catch {
      setError("Bildirishnomalarni yuklab bo'lmadi.");
    }
  }, [unreadOnly]);

  useEffect(() => {
    load();
  }, [load]);

  // Live: the same shared socket the bell uses, plus a resync after a drop.
  useEffect(() => {
    const off = subscribe((frame) => {
      if (frame.kind === "notification") load();
    });
    const offResync = onReconnect(load);
    return () => {
      off();
      offResync();
    };
  }, [load]);

  async function markAllRead() {
    setBusy(true);
    try {
      await api.post("/notifications/read-all");
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function open(n: NotificationItem) {
    if (!n.read) {
      await api.post(`/notifications/${n.id}/read`).catch(() => {});
      setItems((prev) => prev?.map((i) => (i.id === n.id ? { ...i, read: true } : i)) ?? prev);
    }
    // v2 links are all `lead:{id}`; v1 rows for removed features are left inert
    // rather than sent to a route that no longer exists.
    const [prefix, id] = (n.link ?? "").split(":");
    if ((prefix === "lead" || prefix === "review") && id) navigate(`/lead/${id}`);
  }

  const unread = (items ?? []).filter((n) => !n.read).length;

  return (
    <AppShell title="Bildirishnomalar">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex gap-1.5">
            <Button size="sm" variant={unreadOnly ? "outline" : "default"} onClick={() => setUnreadOnly(false)}>
              Hammasi
            </Button>
            <Button size="sm" variant={unreadOnly ? "default" : "outline"} onClick={() => setUnreadOnly(true)}>
              O'qilmagan{unread > 0 && ` (${unread})`}
            </Button>
          </div>
          {unread > 0 && (
            <Button size="sm" variant="outline" disabled={busy} onClick={markAllRead}>
              <Check className="size-4" /> Hammasini o'qilgan deb belgilash
            </Button>
          )}
        </div>

        {items === null && !error && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        )}

        {error && (
          <div className="flex flex-col items-start gap-3 py-10">
            <p className="text-[15px] font-semibold">{error}</p>
            <Button size="sm" onClick={() => void load()}>
              Qayta urinish
            </Button>
          </div>
        )}

        {items !== null && items.length === 0 && !error && (
          <div className="flex flex-col items-center gap-2 py-16 text-center">
            <BellOff className="text-muted-foreground size-6" />
            <p className="text-[15px] font-semibold">
              {unreadOnly ? "O'qilmagan bildirishnoma yo'q." : "Hali bildirishnoma yo'q."}
            </p>
          </div>
        )}

        {items !== null && items.length > 0 && (
          <div className="flex flex-col gap-2">
            {items.map((n) => (
              <Card
                key={n.id}
                onClick={() => void open(n)}
                className={cn(
                  "hover:bg-muted/50 cursor-pointer gap-1 p-4 transition-colors",
                  !n.read && "border-primary border-l-4",
                )}
              >
                <p className={cn("text-[14px]", !n.read && "font-medium")}>{n.message}</p>
                <p className="text-muted-foreground text-xs">
                  {new Date(n.created_at).toLocaleString("uz-UZ")}
                </p>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
