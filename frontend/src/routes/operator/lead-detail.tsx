import { useCallback, useEffect, useRef, useState } from "react";
import { useBlocker, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, Copy, CornerUpLeft, PauseCircle, Play, ShieldAlert, X } from "lucide-react";
import { toast } from "sonner";
import { AppShell } from "@/components/app-shell";
import { AutosaveIndicator, type SaveState } from "@/components/autosave-indicator";
import { HandoverNotice } from "@/components/handover-notice";
import { LeadStatusBadge } from "@/components/lead-status-badge";
import { LeadTimeline } from "@/components/lead-timeline";
import { HandoverDialog, NoteDialog } from "@/components/note-dialog";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/lib/auth-context";
import { onReconnect, subscribe } from "@/lib/ws";
import { splitPhones } from "@/lib/format";
import {
  commentLead,
  fetchLead,
  finishLead,
  leadError,
  pauseLead,
  releaseLead,
  reopenLead,
  saveDraft,
} from "@/lib/lead-api";
import { useStartLead } from "@/lib/use-start-lead";
import type { LeadAction, LeadDetail, LeadField } from "@/lib/types";

const AUTOSAVE_DELAY_MS = 900;
const FIELD_LABEL: Record<string, string> = { website: "Website", lms: "LMS" };

type Draft = { available: boolean | null; comment: string };
type DialogKind = "pause" | "reject" | "reopen" | "release" | null;

function draftsFrom(fields: LeadField[]): Record<string, Draft> {
  return Object.fromEntries(
    fields.map((f) => [f.field, { available: f.available, comment: f.comment ?? "" }]),
  );
}

export function LeadDetailPage() {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [dialog, setDialog] = useState<DialogKind>(null);
  const [busy, setBusy] = useState(false);
  /** Shown in place (inside the dialog when one is open) rather than as a toast:
   *  an operator mid-call misses a toast that auto-dismisses. */
  const [actionError, setActionError] = useState<string | null>(null);
  /** True when a buffered draft was restored from localStorage after a reload. */
  const [restored, setRestored] = useState(false);
  /** Set when the lead could not be fetched for a reason that is not "gone". */
  const [loadError, setLoadError] = useState<string | null>(null);
  /** Someone else claimed it while we had it open. */
  const [takenByOther, setTakenByOther] = useState(false);
  /** True once the lead has loaded at least once, so a later 404 can be told
   *  apart from a first-load 404. */
  const hadLeadRef = useRef(false);

  // Set while a guarded navigation is being resolved, so the blocker does not
  // re-fire on the programmatic navigate that follows the handover.
  const leavingRef = useRef(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  /** Drafts the debounce has not written yet; null once they are on the server. */
  const unsavedRef = useRef<Record<string, Draft> | null>(null);

  /** Cancel any debounced autosave that has not fired yet.
   *
   *  Anything that gives the lead up (handover, pause, reject, approve) must call
   *  this first. Otherwise a timer armed by the operator's last keystroke fires
   *  ~900ms later against a lead they no longer own, the server correctly refuses
   *  it, and the indicator flips to "Saqlanmadi" -- telling the operator their
   *  work was lost at the exact moment it was in fact saved and handed over.
   */
  const cancelPendingSave = useCallback(() => {
    clearTimeout(saveTimer.current);
    saveTimer.current = undefined;
  }, []);

  const load = useCallback(async () => {
    try {
      const next = await fetchLead(companyId!);
      setLead(next);
      hadLeadRef.current = true;
      setLoadError(null);
      setTakenByOther(false);

      // Prefer a buffered draft over the server copy: it only exists when a
      // save had not landed, so it is strictly newer than what the server holds.
      const server = draftsFrom(next.fields);
      let restoredDraft: Record<string, Draft> | null = null;
      const key = user && companyId ? `operatordesk_draft:${user.id}:${companyId}` : null;
      if (key) {
        try {
          const raw = localStorage.getItem(key);
          if (raw) {
            const parsed = JSON.parse(raw) as Record<string, Draft>;
            if (JSON.stringify(parsed) !== JSON.stringify(server)) restoredDraft = parsed;
            else localStorage.removeItem(key); // server caught up; nothing owed
          }
        } catch {
          /* unreadable buffer is not worth failing the page over */
        }
      }
      if (restoredDraft) {
        setDrafts(restoredDraft);
        unsavedRef.current = restoredDraft;
        setRestored(true);
        setSaveState("error"); // it is genuinely not on the server yet
      } else {
        setDrafts(server);
      }
    } catch (err) {
      const detail = leadError(err);
      // Only a real "this lead is not yours / does not exist" answer should
      // eject. A network blip used to do it too -- and since the same load()
      // runs after every action, one blip after a successful pause told the
      // operator the lead could not be opened, from a page that was fine.
      if (detail?.code === "not_found") {
        // Two operators reading the same lead is normal, and one of them is
        // going to lose. The server answers 404 for someone else's in-progress
        // lead by design (FR-4: no probing for leads you may not see) -- but if
        // we already had it open, that is not "you should not be here", it is
        // "somebody just took it". Teleporting them to the queue mid-read
        // throws away their place for no reason; say what happened instead.
        if (hadLeadRef.current) {
          setTakenByOther(true);
          return;
        }
        toast.error(detail.message ?? "Bu leadni ochib bo'lmadi.");
        navigate("/queue", { replace: true });
        return;
      }
      setLoadError(detail?.message ?? "Aloqa yo'q — sahifani yuklab bo'lmadi.");
    }
  }, [companyId, navigate, user]);

  useEffect(() => {
    setLead(null);
    hadLeadRef.current = false;
    setTakenByOther(false);
    load();
  }, [load]);

  // Live updates for THIS lead. Two operators reading the same lead is the
  // normal case, not an edge case: without this the one who did not click first
  // sits looking at a stale "Ishni boshlash" button and only discovers the lead
  // is gone by pressing it. The claim itself is already race-safe server-side
  // (an atomic conditional upsert; the loser gets 409 held_by_other) -- this is
  // about not letting the screen lie in the seconds before that click.
  useEffect(() => {
    const id = Number(companyId);
    const off = subscribe((frame) => {
      if (frame.kind === "lead" && frame.company_id === id) load();
    });
    const offResync = onReconnect(load);
    return () => {
      off();
      offResync();
    };
  }, [companyId, load]);

  const isMine = lead?.status === "in_progress" && lead.assignee_id === user?.id;
  const can = (action: LeadAction) => lead?.available_actions.includes(action) ?? false;

  // ----------------------------------------------------------------- autosave
  //
  // Everything below exists because this is the only copy of what the operator
  // heard on the phone. Measured failure modes it fixes, in order of severity:
  //   1. an action (approve/handover) proceeding over text that never reached
  //      the server, reporting success and closing the lead with the notes gone
  //   2. a slow PATCH landing after a newer one and reverting the text, while
  //      the indicator read "Saqlandi"
  //   3. no retry at all, so an operator who stops typing to talk leaves their
  //      work stranded until the next keystroke
  //   4. nothing surviving a reload

  /** True while a PATCH is in flight -- at most one, ever. */
  const savingRef = useRef(false);
  /** Set when drafts change mid-flight; the newest snapshot is sent on landing. */
  const dirtyRef = useRef(false);
  const retryTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const retryStep = useRef(0);

  const RETRY_BACKOFF_MS = [1000, 2000, 5000];

  const bufferKey = useCallback(
    () => (user && companyId ? `operatordesk_draft:${user.id}:${companyId}` : null),
    [user, companyId],
  );

  /** Second copy, written synchronously so it survives a reload or a closed tab. */
  const buffer = useCallback(
    (next: Record<string, Draft> | null) => {
      const key = bufferKey();
      if (!key) return;
      try {
        if (next) localStorage.setItem(key, JSON.stringify(next));
        else localStorage.removeItem(key);
      } catch {
        // Private mode / quota. The in-memory copy is unaffected.
      }
    },
    [bufferKey],
  );

  /** Send the newest snapshot. Returns true only when the server took it.
   *
   *  `fetchLead` is deliberately outside the try that decides success: it used
   *  to be inside, so a failed *refetch* after a successful save reported
   *  "Saqlanmadi" while the text was safely stored.
   */
  const pushDraft = useCallback(
    async (next: Record<string, Draft>): Promise<boolean> => {
      if (!companyId) return false;
      setSaveState("saving");
      try {
        await saveDraft(companyId, {
          website: { available: next.website?.available ?? null, comment: next.website?.comment || null },
          lms: { available: next.lms?.available ?? null, comment: next.lms?.comment || null },
        });
      } catch {
        setSaveState("error");
        return false;
      }
      unsavedRef.current = null;
      buffer(null);
      setSaveState("saved");
      try {
        // Only so the action bar learns "Tasdiqlash" is now possible. Its
        // failure says nothing about whether the draft was saved.
        setLead(await fetchLead(companyId));
      } catch {
        /* stale action bar, nothing lost */
      }
      return true;
    },
    [companyId, buffer],
  );

  /** Single-flight driver: one request at a time, newest snapshot always wins. */
  const runSave = useCallback(async () => {
    if (savingRef.current) {
      dirtyRef.current = true; // coalesce into the in-flight request
      return;
    }
    savingRef.current = true;
    try {
      // eslint-disable-next-line no-constant-condition
      while (true) {
        dirtyRef.current = false;
        const snapshot = unsavedRef.current;
        if (!snapshot) break;
        const ok = await pushDraft(snapshot);
        if (ok) {
          retryStep.current = 0;
          if (!dirtyRef.current) break;
          continue; // newer text arrived while we were saving
        }
        // Failed: schedule a backoff retry rather than waiting for a keystroke.
        const delay = RETRY_BACKOFF_MS[Math.min(retryStep.current, RETRY_BACKOFF_MS.length - 1)];
        if (retryStep.current < RETRY_BACKOFF_MS.length) {
          retryStep.current += 1;
          clearTimeout(retryTimer.current);
          retryTimer.current = setTimeout(() => void runSave(), delay);
        }
        break;
      }
    } finally {
      savingRef.current = false;
    }
  }, [pushDraft]);

  function updateDraft(field: string, patch: Partial<Draft>) {
    setDrafts((prev) => {
      const next = { ...prev, [field]: { ...prev[field], ...patch } };
      unsavedRef.current = next;
      buffer(next); // synchronous, so a reload cannot outrun it
      clearTimeout(saveTimer.current);
      retryStep.current = 0;
      saveTimer.current = setTimeout(() => void runSave(), AUTOSAVE_DELAY_MS);
      return next;
    });
  }

  /** Land whatever is still owed, *before* giving the lead up.
   *
   *  Returns false if it could not be saved. Callers must not proceed on false:
   *  approving or handing over across a failed flush is how typed call notes
   *  were being destroyed while the UI reported success.
   */
  const flushBeforeRelease = useCallback(async (): Promise<boolean> => {
    cancelPendingSave();
    clearTimeout(retryTimer.current);
    const pending = unsavedRef.current;
    if (!pending) return true;
    return await pushDraft(pending);
  }, [cancelPendingSave, pushDraft]);

  /** Manual "try again", for when the backoff attempts are used up. */
  const retryNow = useCallback(() => {
    retryStep.current = 0;
    void runSave();
  }, [runSave]);

  useEffect(
    () => () => {
      clearTimeout(saveTimer.current);
      clearTimeout(retryTimer.current);
    },
    [],
  );

  // ------------------------------------------------------------ exit guarding
  // The one rule v2 enforces: you do not walk away from work in progress without
  // saying where you stopped. `useBlocker` needs the data router (see App.tsx) --
  // that is why the router was migrated.
  const blocker = useBlocker(
    useCallback(
      ({ currentLocation, nextLocation }) =>
        !!isMine && !leavingRef.current && currentLocation.pathname !== nextLocation.pathname,
      [isMine],
    ),
  );

  useEffect(() => {
    // A tab close cannot be made to collect a comment; the browser only offers a
    // generic prompt. The 4-hour auto-release covers what slips through here.
    if (!isMine) return;
    const handler = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isMine]);

  async function handleBlockedHandover(note: string) {
    setBusy(true);
    // Where the operator was actually trying to go. Captured now, because
    // handing the lead over destroys the blocker that knows it (see below).
    const target = blocker.location?.pathname ?? "/queue";
    try {
      // Land the operator's last keystrokes while we still own the lead. If it
      // will not land, do NOT hand the lead over: doing so was destroying the
      // notes and reporting success, which is the worst outcome in the product.
      if (!(await flushBeforeRelease())) {
        setBusy(false);
        blocker.reset?.();
        toast.error("Yozganingiz saqlanmadi — internet yo'q. Qayta urinib ko'ring.");
        return;
      }
      await pauseLead(lead!.id, note);
      leavingRef.current = true;
      // This is the whole bug. A successful pause makes `isMine` false, so the
      // blocker's condition stops holding and React Router unblocks it — and
      // calling `proceed()` on a blocker that is no longer blocked *throws*.
      // That throw landed in the catch below and told the operator "Qoldirib
      // bo'lmadi" immediately after the handover had in fact been saved (the
      // POST returned 200), while also stranding them on the lead.
      // Proceeding is therefore best-effort, and leaving is done explicitly.
      try {
        blocker.proceed?.();
      } catch {
        // Already unblocked by the release — nothing to resume.
      }
      navigate(target, { replace: true });
    } catch (err) {
      toast.error(leadError(err)?.message ?? "Qoldirib bo'lmadi.");
      blocker.reset?.();
    } finally {
      setBusy(false);
    }
  }

  // Starting another lead from here goes through the same shared flow the queue
  // uses, so the handover rule has exactly one implementation.
  const startFlow = useStartLead(
    (id) => {
      if (String(id) === companyId) {
        load(); // claimed the lead we are already looking at -- just re-render it
        return;
      }
      leavingRef.current = true;
      navigate(`/lead/${id}`);
    },
    // Lost the race: reload so the page immediately shows who holds it now,
    // instead of leaving a button that will only ever 409 again.
    load,
  );

  // ------------------------------------------------------------------ actions
  async function run(fn: () => Promise<unknown>, successMessage?: string) {
    setBusy(true);
    try {
      // Every action here either ends our ownership (pause/reject/approve) or
      // reloads the lead, and in both cases an in-flight debounce would race it.
      // If the flush fails the action is refused outright: approving over
      // unsaved text closed leads with the call notes silently missing.
      if (!(await flushBeforeRelease())) {
        setActionError("Yozganingiz saqlanmadi — internet yo'q. Qayta urinib ko'ring.");
        return;
      }
      setActionError(null);
      await fn();
      if (successMessage) toast.success(successMessage);
      setDialog(null);
      await load();
    } catch (err) {
      // Two things the old version got wrong: the dialog closed anyway (losing
      // the note the operator had just typed) and the page kept showing stale
      // state, so every follow-up button 409'd. Keep the dialog open with its
      // text, show the error in place, and re-sync so the page stops
      // contradicting the server -- the action may in fact have committed.
      setActionError(leadError(err)?.message ?? "Amalni bajarib bo'lmadi.");
      await load().catch(() => {});
    } finally {
      setBusy(false);
    }
  }

  function leaveToQueue() {
    navigate("/queue");
  }

  // Claimed out from under us. `lead` still holds the copy we were reading, so
  // the company details stay on screen -- the operator keeps their place and is
  // simply told the work is no longer available, instead of being teleported to
  // the queue mid-read by a 404 that only means "not yours any more".
  if (takenByOther) {
    return (
      <AppShell title={lead?.name ?? "Lead"}>
        <div className="mx-auto flex max-w-3xl flex-col items-start gap-3 py-10">
          <p className="text-[15px] font-semibold">Bu leadni boshqa operator oldi.</p>
          <p className="text-muted-foreground text-[13.5px]">
            Siz o'qib turgan paytda kimdir ishni boshladi. Endi u sizga ochiq emas.
          </p>
          <div className="flex gap-2">
            <Button size="sm" onClick={leaveToQueue}>
              Ro'yxatga qaytish
            </Button>
            <Button size="sm" variant="outline" onClick={() => void load()}>
              Qayta tekshirish
            </Button>
          </div>
        </div>
      </AppShell>
    );
  }

  if (!lead) {
    // A failed load used to leave skeletons on screen forever with no way out.
    if (loadError) {
      return (
        <AppShell title="Lead">
          <div className="mx-auto flex max-w-3xl flex-col items-start gap-3 py-10">
            <p className="text-[15px] font-semibold">{loadError}</p>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => void load()}>
                Qayta urinish
              </Button>
              <Button size="sm" variant="outline" onClick={leaveToQueue}>
                Ro'yxatga qaytish
              </Button>
            </div>
          </div>
        </AppShell>
      );
    }
    return (
      <AppShell title="Lead">
        <div className="mx-auto flex max-w-3xl flex-col gap-3.5">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      </AppShell>
    );
  }

  const missingForApprove = lead.fields.filter((f) => drafts[f.field]?.available === null).map((f) => f.field);

  return (
    <AppShell title={lead.name}>
      <div className="mx-auto flex max-w-3xl flex-col gap-5">
        <div className="flex items-center justify-between gap-3">
          <Button variant="ghost" size="sm" className="w-fit" onClick={leaveToQueue}>
            <ArrowLeft className="size-4" /> Ro'yxatga qaytish
          </Button>
          <div className="flex items-center gap-3">
            {isMine && <AutosaveIndicator state={saveState} onRetry={retryNow} />}
            <LeadStatusBadge status={lead.status} size="lg" />
          </div>
        </div>

        {/* A reload with unsaved text used to lose it outright. Say so plainly
            when it is recovered, so the operator knows what they are looking at. */}
        {restored && (
          <Card className="border-lead-waiting flex flex-row items-center justify-between gap-3 border-2 p-3.5">
            <p className="text-[13.5px]">
              Saqlanmagan yozuvingiz tiklandi — u hali serverga yetmagan.
            </p>
            <Button size="sm" onClick={retryNow} disabled={saveState === "saving"}>
              Qayta urinish
            </Button>
          </Card>
        )}

        {/* Errors from an action live here, not in a toast that auto-dismisses
            while the operator is on the phone. */}
        {actionError && !dialog && (
          <Card className="border-destructive flex flex-row items-center justify-between gap-3 border-2 p-3.5">
            <p className="text-destructive text-[13.5px]">{actionError}</p>
            <Button size="sm" variant="outline" onClick={() => setActionError(null)}>
              Yopish
            </Button>
          </Card>
        )}

        {lead.status === "in_progress" && !isMine && (
          <Card className="border-lead-progress flex flex-row items-center gap-2 border-2 p-3.5">
            <ShieldAlert className="text-lead-progress size-4 shrink-0" />
            <p className="text-[13.5px]">
              Bu lead ustida hozir <strong>{lead.assignee_name}</strong> ishlayapti.
            </p>
          </Card>
        )}

        {/* The single most useful thing on the page when picking a lead up, so it
            sits above the fold rather than at the bottom of the timeline. The
            timeline still holds the full history; this is the answer to "where
            did the last person stop?" without making anyone hunt for it. */}
        <HandoverNotice lead={lead} isMine={isMine} />

        <Card className="grid grid-cols-2 gap-x-7 gap-y-3.5 p-5">
          <Meta label="Toifa" value={lead.category} />
          <PhoneMeta phone={lead.phone} />
          <Meta label="Manzil" value={lead.address} className="col-span-2" />
          <Meta label="Manba" value={lead.source} />
          <Meta label="Email" value={lead.email} />
          {/* The scraped site: the operator's job is literally to confirm whether
              one exists, and the API has been sending this all along without the
              page ever showing it. */}
          <WebsiteMeta website={lead.website} />
        </Card>

        {lead.fields.map((f) => (
          <Card key={f.field} className="gap-3 p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-[15px] font-semibold">{FIELD_LABEL[f.field] ?? f.field}</h3>
              {f.filled_by && (
                <span className="text-muted-foreground text-xs">
                  {f.filled_by}
                  {f.filled_at && ` · ${new Date(f.filled_at).toLocaleString("uz-UZ")}`}
                </span>
              )}
            </div>

            {isMine ? (
              <>
                {/* Three states, not two: "belgilanmagan" is what an untouched
                    field genuinely is, and approving requires leaving it. */}
                <div className="flex gap-1.5">
                  <ChoiceButton
                    active={drafts[f.field]?.available === true}
                    onClick={() => updateDraft(f.field, { available: true })}
                  >
                    Mavjud
                  </ChoiceButton>
                  <ChoiceButton
                    active={drafts[f.field]?.available === false}
                    onClick={() => updateDraft(f.field, { available: false })}
                  >
                    Yo'q
                  </ChoiceButton>
                  <ChoiceButton
                    active={drafts[f.field]?.available === null}
                    onClick={() => updateDraft(f.field, { available: null })}
                  >
                    Belgilanmagan
                  </ChoiceButton>
                </div>
                <Textarea
                  value={drafts[f.field]?.comment ?? ""}
                  onChange={(e) => updateDraft(f.field, { comment: e.target.value })}
                  placeholder="Qo'ng'iroq/yozishma orqali bilib olingan ma'lumot..."
                />
              </>
            ) : (
              <div className="flex flex-col gap-1.5">
                <p className="text-[14px] font-medium">
                  {f.available === null ? "Belgilanmagan" : f.available ? "Mavjud" : "Yo'q"}
                </p>
                {f.comment && <p className="text-muted-foreground text-[13px]">{f.comment}</p>}
              </div>
            )}
          </Card>
        ))}

        {/* Whatever the server says is possible -- the client does not second-guess
            the state machine, it renders it. */}
        <div className="flex flex-wrap gap-2">
          {can("start") && (
            <Button disabled={startFlow.busy} onClick={() => startFlow.start(lead.id)}>
              <Play className="size-4" /> Ishni boshlash
            </Button>
          )}
          {can("approve") && (
            <Button disabled={busy} onClick={() => run(() => finishLead(lead.id, "approved"), "Tasdiqlandi.")}>
              <Check className="size-4" /> Tasdiqlash
            </Button>
          )}
          {isMine && !can("approve") && (
            <Button disabled title="Website va LMS belgilanishi kerak">
              <Check className="size-4" /> Tasdiqlash
            </Button>
          )}
          {can("reject") && (
            <Button variant="outline" disabled={busy} onClick={() => setDialog("reject")}>
              <X className="size-4" /> Rad etish
            </Button>
          )}
          {can("pause") && (
            <Button variant="outline" disabled={busy} onClick={() => setDialog("pause")}>
              <PauseCircle className="size-4" /> Qoldirish
            </Button>
          )}
          {can("reopen") && (
            <Button variant="outline" disabled={busy} onClick={() => setDialog("reopen")}>
              <CornerUpLeft className="size-4" /> Qayta ochish
            </Button>
          )}
          {can("admin_release") && (
            <Button variant="outline" disabled={busy} onClick={() => setDialog("release")}>
              <ShieldAlert className="size-4" /> Majburan bo'shatish
            </Button>
          )}
        </div>

        {isMine && missingForApprove.length > 0 && (
          <p className="text-muted-foreground -mt-3 text-[13px]" aria-live="polite">
            Tasdiqlash uchun {missingForApprove.map((f) => FIELD_LABEL[f] ?? f).join(" va ")} belgilanishi kerak.
          </p>
        )}

        <LeadTimeline
          events={lead.events}
          canComment={isMine}
          onComment={(note) => run(() => commentLead(lead.id, note))}
        />
      </div>

      {/* Exit guard: any in-app navigation away from an owned lead lands here. */}
      {blocker.state === "blocked" && (
        <HandoverDialog
          companyName={lead.name}
          submitting={busy}
          error={actionError}
          onCancel={() => {
            setActionError(null);
            blocker.reset?.();
          }}
          onSubmit={handleBlockedHandover}
        />
      )}

      {/* Starting a different lead from this page hits the same rule. */}
      {startFlow.pending && (
        <HandoverDialog
          companyName={startFlow.pending.fromName}
          submitting={startFlow.busy}
          onCancel={startFlow.cancelHandover}
          onSubmit={startFlow.confirmHandover}
        />
      )}

      {dialog === "pause" && (
        <NoteDialog
          title="Ishni qoldirish"
          description={
            <>
              <strong>{lead.name}</strong> — qayerda to'xtadingiz? Keyingi operator shu izohni o'qiydi.
            </>
          }
          placeholder="Masalan: mijoz band, ertalab qayta qo'ng'iroq qilish kerak."
          confirmLabel="Qoldirish"
          submitting={busy}
          error={actionError}
          onCancel={() => {
            setDialog(null);
            setActionError(null);
          }}
          onSubmit={(note) => run(() => pauseLead(lead.id, note), "Ish qoldirildi.")}
        />
      )}

      {dialog === "reject" && (
        <NoteDialog
          title="Leadni rad etish"
          description="Nega rad etilyapti? Sabab tarixda qoladi."
          placeholder="Masalan: raqam ishlamaydi, kompaniya yopilgan."
          confirmLabel="Rad etish"
          submitting={busy}
          error={actionError}
          onCancel={() => {
            setDialog(null);
            setActionError(null);
          }}
          onSubmit={(note) => run(() => finishLead(lead.id, "rejected", note), "Rad etildi.")}
        />
      )}

      {dialog === "reopen" && (
        <NoteDialog
          title="Qayta ochish"
          description="Nega qayta ochilyapti? Ruxsat kerak emas — faqat sabab yozing, u tarixda qoladi."
          placeholder="Masalan: LMS ni xato belgilabman."
          confirmLabel="Qayta ochish"
          submitting={busy}
          error={actionError}
          onCancel={() => {
            setDialog(null);
            setActionError(null);
          }}
          onSubmit={(note) => run(() => reopenLead(lead.id, note), "Qayta ochildi.")}
        />
      )}

      {dialog === "release" && (
        <NoteDialog
          title="Majburan bo'shatish"
          description={
            <>
              <strong>{lead.assignee_name}</strong> ning ishi bo'shatiladi va unga bildirishnoma boradi.
            </>
          }
          confirmLabel="Bo'shatish"
          submitting={busy}
          error={actionError}
          onCancel={() => {
            setDialog(null);
            setActionError(null);
          }}
          onSubmit={(note) => run(() => releaseLead(lead.id, note), "Bo'shatildi.")}
        />
      )}
    </AppShell>
  );
}

function Meta({
  label,
  value,
  mono,
  className,
}: {
  label: string;
  value: string | null;
  mono?: boolean;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-0.5 ${className ?? ""}`}>
      <span className="text-muted-foreground text-[11.5px] tracking-wide uppercase">{label}</span>
      <span className={`text-[14px] font-medium ${mono ? "font-mono" : ""}`}>{value ?? "—"}</span>
    </div>
  );
}

function ChoiceButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`rounded-md border px-3 py-1.5 text-[13px] font-medium transition-colors ${
        active ? "bg-primary text-primary-foreground border-primary" : "hover:bg-muted text-muted-foreground"
      }`}
    >
      {children}
    </button>
  );
}

/** Phone numbers, one per line, each dialable and copyable.
 *
 *  The operator's whole job starts with placing this call, and the number used
 *  to be plain text they had to read across to a handset by eye. */
function PhoneMeta({ phone }: { phone: string | null }) {
  const numbers = splitPhones(phone);
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-muted-foreground text-[11.5px] tracking-wide uppercase">Telefon</span>
      {numbers.length === 0 ? (
        <span className="text-[14px] font-medium">—</span>
      ) : (
        <div className="flex flex-col gap-1">
          {numbers.map((n, i) => (
            <div key={i} className="flex items-center gap-2">
              {n.dial ? (
                <a href={`tel:${n.dial}`} className="font-mono text-[14px] font-medium underline underline-offset-2">
                  {n.display}
                </a>
              ) : (
                <span className="font-mono text-[14px] font-medium">{n.display}</span>
              )}
              <button
                type="button"
                title="Nusxa olish"
                className="text-muted-foreground hover:text-foreground text-xs"
                onClick={() => navigator.clipboard?.writeText(n.dial ?? n.display)}
              >
                <Copy className="size-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WebsiteMeta({ website }: { website: string | null }) {
  if (!website) return <Meta label="Website (manbadan)" value={null} />;
  const href = /^https?:\/\//.test(website) ? website : `https://${website}`;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-muted-foreground text-[11.5px] tracking-wide uppercase">Website (manbadan)</span>
      <a
        href={href}
        target="_blank"
        rel="noreferrer noopener"
        className="truncate text-[14px] font-medium underline underline-offset-2"
        title={website}
      >
        {website}
      </a>
    </div>
  );
}
