import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api, getToken, wsUrl } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { NotificationItem, Role } from "@/lib/types";

const RECONNECT_DELAY_MS = 3_000;

function resolveLink(link: string | null, role: Role): string | null {
  if (!link) return null;
  if (link.startsWith("review:")) {
    const [, companyId] = link.split(":");
    return `/review/${companyId}`;
  }
  if (link.startsWith("permission-request:")) {
    return role === "admin" ? "/admin/permission-requests" : "/my-requests?type=permission";
  }
  if (link.startsWith("claim-request:")) {
    return role === "admin" ? "/admin/claim-requests" : "/my-requests?type=claim";
  }
  return null;
}

export function NotificationBell() {
  const { user } = useAuth();
  const [items, setItems] = useState<NotificationItem[]>([]);
  const navigate = useNavigate();
  const socketRef = useRef<WebSocket | null>(null);

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

    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      const token = getToken();
      if (!token || cancelled) return;

      const socket = new WebSocket(wsUrl(`/ws/notifications?token=${encodeURIComponent(token)}`));
      socketRef.current = socket;

      socket.onmessage = (event) => {
        const notification = JSON.parse(event.data) as NotificationItem;
        setItems((prev) => [notification, ...prev]);
      };
      socket.onclose = () => {
        if (!cancelled) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();
    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      socketRef.current?.close();
    };
  }, []);

  const unreadCount = items.filter((n) => !n.read).length;

  async function handleClick(n: NotificationItem) {
    if (!n.read) {
      await api.post(`/notifications/${n.id}/read`);
      setItems((prev) => prev.map((i) => (i.id === n.id ? { ...i, read: true } : i)));
    }
    const target = user && resolveLink(n.link, user.role);
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
