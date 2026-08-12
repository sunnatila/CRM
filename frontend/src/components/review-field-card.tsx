import { Lock } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";
import type { ReviewField } from "@/lib/types";

const FIELD_LABEL: Record<string, string> = { website: "Website", lms: "LMS" };

interface Props {
  field: ReviewField;
  draft: { available: boolean | null; comment: string };
  onChange: (draft: { available: boolean | null; comment: string }) => void;
  onRequestPermission: () => void;
}

export function ReviewFieldCard({ field, draft, onChange, onRequestPermission }: Props) {
  const label = FIELD_LABEL[field.field] ?? field.field;

  if (field.locked) {
    return (
      <Card className="gap-3 p-5">
        <div className="flex items-center justify-between">
          <h3 className="text-[15px] font-semibold">{label}</h3>
          <StatusBadge status={field.available ? "confirmed" : "absent"} />
        </div>
        <div className="text-muted-foreground flex items-center gap-2 text-[13px]">
          <Lock className="size-4" />
          {field.filled_by ?? "Noma'lum"} tomonidan to'ldirilgan
          {field.filled_at && ` · ${new Date(field.filled_at).toLocaleString("uz-UZ")}`}
        </div>
        {field.comment && <p className="text-muted-foreground text-[13px]">"{field.comment}"</p>}
        <div>
          {field.pending_request ? (
            <Button variant="ghost" size="sm" disabled>
              So'ralgan — kutilmoqda
            </Button>
          ) : (
            <Button variant="outline" size="sm" onClick={onRequestPermission}>
              Ruxsat so'rash
            </Button>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card className="gap-3 p-5">
      <h3 className="text-[15px] font-semibold">{label}</h3>
      <label className="flex items-center gap-2.5 text-[13.5px] font-medium">
        <Checkbox
          checked={draft.available === true}
          onCheckedChange={(checked) => onChange({ ...draft, available: checked === true })}
        />
        Mavjud
      </label>
      <div className="flex flex-col gap-1.5">
        <label className="text-muted-foreground text-xs font-medium">Izoh</label>
        <Textarea
          value={draft.comment}
          onChange={(e) => onChange({ ...draft, comment: e.target.value })}
          placeholder="Qo'ng'iroq/yozishma orqali bilib olingan ma'lumot..."
        />
      </div>
    </Card>
  );
}
