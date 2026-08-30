import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownWideNarrow, ArrowDownAZ, Check, ChevronsUpDown, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { CategoryOption } from "@/lib/types";

/* The list is virtualised rather than capped.
 *
 * The first version rendered every one of the 3,643 categories on open and
 * froze the tab, so it was cut to the first 60 alphabetically. That fixed the
 * freeze and created a worse problem: you could only reach a category by typing
 * a name you already knew. An operator who wants to *see what is in the
 * database* got "3D печать", "AMR - installation", "ATS - Repair office" and no
 * way forward.
 *
 * So: every category stays reachable, only the ~15 rows on screen are in the
 * DOM, and the default order is by how many companies carry the tag. The 60
 * biggest categories cover 42% of all tags -- opening the list now answers
 * "what is actually in here?" before a single key is pressed. */
const ROW_H = 32;
const VIEW_H = 288;
const OVERSCAN = 6;

export const ALL_CATEGORIES = "__all__";

/** Scraped category strings carry trailing punctuation ("Accountants - Training,")
 *  -- 559 of them do. Cleaned for display only: the value sent to the API must
 *  stay byte-identical, since the filter matches it exactly against the
 *  semicolon-separated tag list in the database (AD-12). */
export function prettyCategory(raw: string): string {
  return raw.replace(/[\s,;]+$/, "");
}

type SortMode = "count" | "alpha";

export function CategoryPicker({
  value,
  options,
  onChange,
  loading,
}: {
  value: string;
  options: CategoryOption[];
  onChange: (next: string) => void;
  loading?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(-1);
  const [sort, setSort] = useState<SortMode>("count");
  const [scrollTop, setScrollTop] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // The server already returns them biggest-first, so "count" is a pass-through
  // and only the alphabetical view pays for a sort.
  const ordered = useMemo(
    () =>
      sort === "count"
        ? options
        : [...options].sort((a, b) => a.name.localeCompare(b.name, "ru")),
    [options, sort],
  );

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return ordered;
    return ordered.filter((o) => o.name.toLowerCase().includes(q));
  }, [ordered, query]);

  const selected = useMemo(
    () => (value === ALL_CATEGORIES ? null : options.find((o) => o.name === value) ?? null),
    [options, value],
  );

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setCursor(-1);
    setScrollTop(0);
    if (listRef.current) listRef.current.scrollTop = 0;
    const t = setTimeout(() => inputRef.current?.focus(), 30);
    return () => clearTimeout(t);
  }, [open]);

  useEffect(() => {
    setCursor(-1);
    setScrollTop(0);
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [query, sort]);

  // Arrowing past the window edge has to move the scroll container itself --
  // the row the cursor is on may not be mounted at all.
  const revealRow = useCallback((idx: number) => {
    const el = listRef.current;
    if (!el || idx < 0) return;
    const top = idx * ROW_H;
    if (top < el.scrollTop) el.scrollTop = top;
    else if (top + ROW_H > el.scrollTop + VIEW_H) el.scrollTop = top + ROW_H - VIEW_H;
  }, []);

  function choose(next: string) {
    onChange(next);
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => {
        const n = Math.min(c + 1, matches.length - 1);
        revealRow(n);
        return n;
      });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => {
        const n = Math.max(c - 1, -1);
        revealRow(n);
        return n;
      });
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (cursor === -1) choose(ALL_CATEGORIES);
      else if (matches[cursor]) choose(matches[cursor].name);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const first = Math.max(0, Math.floor(scrollTop / ROW_H) - OVERSCAN);
  const last = Math.min(matches.length, Math.ceil((scrollTop + VIEW_H) / ROW_H) + OVERSCAN);
  const window = matches.slice(first, last);

  const label = value === ALL_CATEGORIES ? "Barcha kategoriyalar" : prettyCategory(value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-64 justify-between font-normal"
          title={label}
        >
          <span className={cn("truncate", value === ALL_CATEGORIES && "text-muted-foreground")}>
            {loading ? "Yuklanmoqda…" : label}
          </span>
          <div className="flex shrink-0 items-center gap-1">
            {selected && (
              <span className="text-muted-foreground text-[11px] tabular-nums">{selected.count}</span>
            )}
            {value !== ALL_CATEGORIES && (
              <span
                role="button"
                tabIndex={-1}
                aria-label="Tozalash"
                className="hover:bg-muted rounded p-0.5"
                onClick={(e) => {
                  e.stopPropagation();
                  onChange(ALL_CATEGORIES);
                }}
              >
                <X className="size-3.5" />
              </span>
            )}
            <ChevronsUpDown className="size-3.5 opacity-50" />
          </div>
        </Button>
      </PopoverTrigger>

      <PopoverContent className="w-[26rem] p-0" align="start" onKeyDown={onKeyDown}>
        <div className="relative border-b">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-3.5 -translate-y-1/2" />
          <Input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Kategoriya qidirish…"
            className="border-0 pl-9 shadow-none focus-visible:ring-0"
          />
        </div>

        {/* Two orders, because they answer different questions: "what is big in
            here?" when you are exploring, "where is X?" when you half-remember
            a name. */}
        <div className="flex items-center gap-1 border-b px-1.5 py-1.5">
          <SortTab active={sort === "count"} onClick={() => setSort("count")} icon={<ArrowDownWideNarrow className="size-3.5" />}>
            Ko'p uchraydigan
          </SortTab>
          <SortTab active={sort === "alpha"} onClick={() => setSort("alpha")} icon={<ArrowDownAZ className="size-3.5" />}>
            Alifbo
          </SortTab>
        </div>

        <div className="p-1 pb-0">
          <Row active={cursor === -1} selected={value === ALL_CATEGORIES} onSelect={() => choose(ALL_CATEGORIES)}>
            <span className="truncate">Barcha kategoriyalar</span>
          </Row>
        </div>

        <div
          ref={listRef}
          onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
          style={{ height: VIEW_H }}
          className="overflow-y-auto p-1"
        >
          {matches.length === 0 ? (
            <p className="text-muted-foreground px-2 py-6 text-center text-[13px]">Hech narsa topilmadi.</p>
          ) : (
            <div style={{ height: matches.length * ROW_H, position: "relative" }}>
              {window.map((opt, i) => {
                const idx = first + i;
                return (
                  <div
                    key={opt.name}
                    style={{ position: "absolute", top: idx * ROW_H, height: ROW_H, left: 0, right: 0 }}
                  >
                    <Row
                      active={idx === cursor}
                      selected={opt.name === value}
                      onSelect={() => choose(opt.name)}
                    >
                      <span className="truncate" title={prettyCategory(opt.name)}>
                        {prettyCategory(opt.name)}
                      </span>
                      <span className="text-muted-foreground ml-auto shrink-0 pl-2 text-[11.5px] tabular-nums">
                        {opt.count}
                      </span>
                    </Row>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="text-muted-foreground border-t px-3 py-2 text-xs">
          {query.trim()
            ? `${matches.length} ta mos keldi — jami ${options.length} ta`
            : `${options.length} ta kategoriya — hammasini aylantirib ko'rish mumkin`}
        </div>
      </PopoverContent>
    </Popover>
  );
}

function SortTab({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-2 py-1 text-[12.5px] font-medium transition-colors",
        active ? "bg-muted text-foreground" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {icon}
      {children}
    </button>
  );
}

function Row({
  active,
  selected,
  onSelect,
  children,
}: {
  active: boolean;
  selected: boolean;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      role="option"
      aria-selected={selected}
      onClick={onSelect}
      style={{ height: ROW_H }}
      className={cn(
        "flex cursor-pointer items-center gap-2 rounded-sm px-2 text-[13.5px]",
        active && "bg-muted",
      )}
    >
      <Check className={cn("size-3.5 shrink-0", selected ? "opacity-100" : "opacity-0")} />
      {children}
    </div>
  );
}
