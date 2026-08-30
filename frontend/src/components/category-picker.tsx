import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronsUpDown, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

/** How many rows we are willing to put in the DOM at once.
 *
 *  The source has 3,448 categories. A plain `<Select>` rendered every one of
 *  them on open, which locked the tab for seconds -- the freeze the operator
 *  reported. Nobody scrolls 3,448 rows anyway: they type. So the list is capped
 *  and the search does the narrowing, which is both faster and the interaction
 *  people actually want. */
const MAX_RENDERED = 60;

export const ALL_CATEGORIES = "__all__";

/** Scraped category strings carry trailing punctuation ("Accountants - Training,")
 *  -- 559 of the 3,448 do. Cleaned for display only: the value sent to the API
 *  must stay byte-identical, since the filter matches it exactly against the
 *  semicolon-separated tag list in the database (AD-12). */
export function prettyCategory(raw: string): string {
  return raw.replace(/[\s,;]+$/, "");
}

export function CategoryPicker({
  value,
  options,
  onChange,
  loading,
}: {
  value: string;
  options: string[];
  onChange: (next: string) => void;
  loading?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const { shown, total } = useMemo(() => {
    const q = query.trim().toLowerCase();
    const matches = q ? options.filter((o) => o.toLowerCase().includes(q)) : options;
    return { shown: matches.slice(0, MAX_RENDERED), total: matches.length };
  }, [options, query]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setCursor(0);
    const t = setTimeout(() => inputRef.current?.focus(), 30);
    return () => clearTimeout(t);
  }, [open]);

  useEffect(() => setCursor(0), [query]);

  // Keep the highlighted row in view when arrowing through results.
  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${cursor}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  function choose(next: string) {
    onChange(next);
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, shown.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (shown[cursor]) choose(shown[cursor]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

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

      <PopoverContent className="w-96 p-0" align="start" onKeyDown={onKeyDown}>
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

        <div ref={listRef} className="max-h-72 overflow-y-auto p-1">
          <Row
            idx={-1}
            active={cursor === -1}
            selected={value === ALL_CATEGORIES}
            onSelect={() => choose(ALL_CATEGORIES)}
          >
            Barcha kategoriyalar
          </Row>

          {shown.map((opt, i) => (
            <Row
              key={opt}
              idx={i}
              active={i === cursor}
              selected={opt === value}
              onSelect={() => choose(opt)}
            >
              {prettyCategory(opt)}
            </Row>
          ))}

          {total === 0 && (
            <p className="text-muted-foreground px-2 py-6 text-center text-[13px]">
              Hech narsa topilmadi.
            </p>
          )}
        </div>

        {/* Honest about the cap rather than silently truncating. */}
        {total > shown.length && (
          <div className="text-muted-foreground border-t px-3 py-2 text-xs">
            {shown.length} / {total} ta ko'rsatilmoqda — qidiruvni aniqlashtiring
          </div>
        )}
        {total <= shown.length && total > 0 && (
          <div className="text-muted-foreground border-t px-3 py-2 text-xs">{total} ta kategoriya</div>
        )}
      </PopoverContent>
    </Popover>
  );
}

function Row({
  idx,
  active,
  selected,
  onSelect,
  children,
}: {
  idx: number;
  active: boolean;
  selected: boolean;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      data-idx={idx}
      role="option"
      aria-selected={selected}
      onClick={onSelect}
      className={cn(
        "flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-[13.5px]",
        active && "bg-muted",
      )}
    >
      <Check className={cn("size-3.5 shrink-0", selected ? "opacity-100" : "opacity-0")} />
      <span className="truncate">{children}</span>
    </div>
  );
}
