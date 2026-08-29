import { useEffect, useRef, useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  title: string;
  description: React.ReactNode;
  label?: string;
  placeholder?: string;
  helpText?: string;
  errorText?: string;
  confirmLabel: string;
  cancelLabel?: string;
  /** false only for the free-form comment box, where an empty note is simply a no-op. */
  required?: boolean;
  submitting?: boolean;
  /** Rendered inside the dialog. Shown instead of a toast so the operator does
   *  not lose the message -- and the dialog keeps their text for a retry. */
  error?: string | null;
  onCancel: () => void;
  onSubmit: (note: string) => void;
}

/** Every place v2 asks for a reason funnels through here.
 *
 *  Handover, rejection, reopening, an admin taking a lead away -- all of them
 *  need a note, and all of them need the same validation. One component means
 *  there is no route out of a lead that quietly forgets to ask. */
export function NoteDialog({
  title,
  description,
  label = "Izoh",
  placeholder,
  helpText,
  errorText = "Izoh yozilishi shart.",
  confirmLabel,
  cancelLabel = "Bekor qilish",
  required = true,
  submitting,
  error,
  onCancel,
  onSubmit,
}: Props) {
  const [note, setNote] = useState("");
  const [touched, setTouched] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // The note is the whole point of the dialog -- put the caret in it.
    const handle = setTimeout(() => ref.current?.focus(), 50);
    return () => clearTimeout(handle);
  }, []);

  const invalid = required && note.trim() === "";

  function handleSubmit(event: React.MouseEvent) {
    // Always prevent Radix's built-in close. It used to fire on click, before
    // the request resolved, so a failed action destroyed the note the operator
    // had just typed and they had to write it again from memory. The parent
    // unmounts this dialog when the action succeeds; on failure it stays open
    // with the text intact and `error` filled in.
    event.preventDefault();
    if (invalid) {
      setTouched(true);
      ref.current?.focus();
      return;
    }
    onSubmit(note.trim());
  }

  const showError = touched && invalid;

  return (
    <AlertDialog open onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="note-dialog-input">{label}</Label>
          <Textarea
            id="note-dialog-input"
            ref={ref}
            rows={4}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={() => setTouched(true)}
            aria-invalid={showError}
            aria-describedby="note-dialog-help"
            placeholder={placeholder}
          />
          {/* aria-live so the validation failure is announced, not only coloured. */}
          <p
            id="note-dialog-help"
            aria-live="polite"
            className={showError ? "text-destructive text-xs" : "text-muted-foreground text-xs"}
          >
            {showError ? errorText : helpText}
          </p>
        </div>

        {error && (
          <p role="alert" className="text-destructive text-[13px]">
            {error}
          </p>
        )}

        <AlertDialogFooter>
          <AlertDialogCancel>{cancelLabel}</AlertDialogCancel>
          <AlertDialogAction onClick={handleSubmit} disabled={invalid || submitting}>
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

/** The exit guard, preset. Reached from the sidebar, the back button, a click on
 *  another lead -- one wording, one validation path. */
export function HandoverDialog({
  companyName,
  submitting,
  error,
  onCancel,
  onSubmit,
}: {
  companyName: string;
  submitting?: boolean;
  error?: string | null;
  onCancel: () => void;
  onSubmit: (note: string) => void;
}) {
  return (
    <NoteDialog
      title="Bu ishni qoldiryapsiz"
      description={
        <>
          <strong>{companyName}</strong> — qayerda to'xtadingiz? Bu izohni sizdan keyin bu ishni oladigan operator
          birinchi bo'lib o'qiydi.
        </>
      }
      placeholder="Masalan: 3 marta qo'ng'iroq qildim, javob yo'q. Ertalab 9–10 orasida urinib ko'rish kerak."
      helpText="Qisqa bo'lsa ham bo'ladi — nima qilinganini yozing."
      confirmLabel="Qoldirib davom etish"
      cancelLabel="Ishda qolish"
      submitting={submitting}
      error={error}
      onCancel={onCancel}
      onSubmit={onSubmit}
    />
  );
}
