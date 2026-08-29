import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api } from "@/lib/api";
import { onReconnect, subscribe } from "@/lib/ws";
import type { NotificationItem } from "@/lib/types";

/** v2 links are all `lead:{company_id}`. The v1 prefixes still sit in the
 *  notifications table, so they are mapped where they can be and ignored where
 *  the destination no longer exists -- a historic row must not make a click
 *  throw or land on a dead route. */
function resolveLink(link: string | null): string | null {
  if (!link) return null;
  const [prefix, id] = link.split(":");
  if (prefix === "lead" || prefix === "review") return `/lead/${id}`;
  return null;
}

export function NotificationBell() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const navigate = useNavigate();

  async function load() {
    try {
      const res = await api.get<NotificationItem[]>("/notifications");
      setItems(res.data);
    } catch {
      // silent -- notifications are supplementary, not core-path
    }
  }

  useEffect(() => {
    load();
    // One shared socket for the whole tab (lib/ws.ts). The bell used to open a
    // SECOND one of its own, doubling every connection the server holds and
    // everything it writes per broadcast. It also pushed EVERY frame into the
    // list without checking `kind`, so the {kind:"lead"} status broadcasts --
    // which fire on every action by every operator -- showed up as bogus
    // notifications for everyone.
    const unsubscribe = subscribe((frame) => {
      if (frame.kind !== "notification") return;
      const incoming = frame as unknown as NotificationItem;
      setItems((prev) =>
        // Dedupe by id: sharing the socket means a frame can be delivered more
        // than once across reconnects, and a duplicated bell item is visible.
        prev.some((n) => n.id === incoming.id) ? prev : [incoming, ...prev],
      );
    });
    // A socket that was down missed notifications outright -- re-read on return.
    const unsubscribeResync = onReconnect(load);
    return () => {
      unsubscribe();
      unsubscribeResync();
    };
  }, []);

  const unreadCount = items.filter((n) => !n.read).length;

  async function handleClick(n: NotificationItem) {
    if (!n.read) {
      await api.post(`/notifications/${n.id}/read`);
      setItems((prev) => prev.map((i) => (i.id === n.id ? { ...i, read: true } : i)));
    }
    const target = resolveLink(n.link);
    if (target) navigate(target);
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="size-4.5" />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 size-2 rounded-full bg-accent ring-2 ring-background" />
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="border-b px-4 py-3 text-sm font-semibold">Bildirishnomalar</div>
        <div className="max-h-96 overflow-y-auto">
          {items.length === 0 && (
            <p className="text-muted-foreground px-4 py-6 text-center text-sm">Bildirishnomalar yo'q.</p>
          )}
          {items.map((n) => (
            <button
              key={n.id}
              onClick={() => handleClick(n)}
              className="hover:bg-muted flex w-full flex-col gap-0.5 border-b px-4 py-3 text-left text-sm last:border-b-0"
            >
              <span className={n.read ? "text-muted-foreground" : "font-medium"}>{n.message}</span>
              <span className="text-muted-foreground text-xs">
                {new Date(n.created_at).toLocaleString("uz-UZ")}
              </span>
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
