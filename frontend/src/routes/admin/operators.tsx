import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import type { OperatorStats } from "@/lib/types";

function initials(fullName: string): string {
  return fullName
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function OperatorsPage() {
  const [operators, setOperators] = useState<OperatorStats[] | null>(null);
  const [open, setOpen] = useState(false);
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    const res = await api.get<OperatorStats[]>("/operators");
    setOperators(res.data);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/operators", { full_name: fullName, username, password });
      toast.success("Operator qo'shildi.");
      setOpen(false);
      setFullName("");
      setUsername("");
      setPassword("");
      await load();
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Operator qo'shib bo'lmadi.";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell title="Operatorlar">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-muted-foreground text-[13px]">{operators?.length ?? 0} ta operator</p>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm">+ Yangi operator</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Yangi operator qo'shish</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="flex flex-col gap-3.5">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="full_name">To'liq ism</Label>
                <Input id="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="new_username">Login</Label>
                <Input id="new_username" value={username} onChange={(e) => setUsername(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="new_password">Vaqtinchalik parol</Label>
                <Input
                  id="new_password"
                  type="text"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={submitting}>
                  Qo'shish
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Operator</TableHead>
              <TableHead>Login</TableHead>
              <TableHead>Bugun</TableHead>
              <TableHead>Bu hafta</TableHead>
              <TableHead>Jami</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(operators ?? []).map((op) => (
              <TableRow key={op.id}>
                <TableCell className="flex items-center gap-2.5 font-medium">
                  <Avatar className="size-6.5">
                    <AvatarFallback className="bg-primary text-primary-foreground text-[11px]">
                      {initials(op.full_name)}
                    </AvatarFallback>
                  </Avatar>
                  {op.full_name}
                </TableCell>
                <TableCell className="text-muted-foreground">@{op.username}</TableCell>
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
