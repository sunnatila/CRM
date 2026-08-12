import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Bell,
  CalendarClock,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  UserRound,
  UserRoundCog,
  UsersRound,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { NotificationBell } from "@/components/notification-bell";
import { useAuth } from "@/lib/auth-context";
import { API_BASE } from "@/lib/api";

interface NavItem {
  to: string;
  label: string;
  icon: typeof ClipboardList;
}

const OPERATOR_NAV: NavItem[] = [
  { to: "/queue", label: "To'ldirish ro'yxati", icon: ClipboardList },
  { to: "/my-requests", label: "Mening so'rovlarim", icon: Bell },
  { to: "/profile", label: "Mening natijalarim", icon: UserRound },
];

const ADMIN_NAV: NavItem[] = [
  { to: "/admin", label: "Boshqaruv paneli", icon: LayoutDashboard },
  { to: "/admin/operators", label: "Operatorlar", icon: UsersRound },
  { to: "/admin/permission-requests", label: "Ruxsat so'rovlari", icon: UserRoundCog },
  { to: "/admin/claim-requests", label: "Ish so'rovlari", icon: CalendarClock },
];

function initials(fullName: string): string {
  return fullName
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function avatarSrc(avatarUrl: string | null): string | undefined {
  if (!avatarUrl) return undefined;
  const backendOrigin = API_BASE.replace(/\/api\/?$/, "");
  return `${backendOrigin}${avatarUrl}`;
}

export function AppShell({ title, children }: { title: string; children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;
  const navItems = user.role === "admin" ? ADMIN_NAV : OPERATOR_NAV;

  return (
    <div className="flex min-h-screen">
      <aside className="bg-card flex w-58 flex-shrink-0 flex-col gap-5 border-r px-3.5 py-5">
        <div className="flex items-center gap-2.5 px-2 text-[15px] font-bold">
          <span className="bg-primary size-2.5 rounded-[3px]" />
          OperatorDesk
        </div>
        <nav className="flex flex-col gap-0.5">
          <div className="text-muted-foreground px-2.5 py-1 text-[11px] font-semibold tracking-wide uppercase">
            {user.role === "admin" ? "Admin" : "Operator"}
          </div>
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/admin"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] font-medium",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              <Icon className="size-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto flex flex-col gap-1">
          <button
            onClick={logout}
            className="text-muted-foreground hover:bg-muted hover:text-foreground flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13.5px] font-medium"
          >
            <LogOut className="size-4" />
            Chiqish
          </button>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="bg-card flex items-center justify-between gap-4 border-b px-7 py-3.5">
          <h1 className="text-[20px] leading-tight font-semibold">{title}</h1>
          <div className="flex items-center gap-3.5">
            <NotificationBell />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="rounded-full">
                  <Avatar className="size-8">
                    <AvatarImage src={avatarSrc(user.avatar_url)} alt={user.full_name} />
                    <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                      {initials(user.full_name)}
                    </AvatarFallback>
                  </Avatar>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel className="font-normal">
                  <p className="text-[13.5px] font-medium">{user.full_name}</p>
                  <p className="text-muted-foreground text-xs">@{user.username}</p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => navigate("/profile")}>
                  <UserRound className="size-4" />
                  Profil
                </DropdownMenuItem>
                <DropdownMenuItem onClick={logout} variant="destructive">
                  <LogOut className="size-4" />
                  Chiqish
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main className="p-7">{children}</main>
      </div>
    </div>
  );
}
