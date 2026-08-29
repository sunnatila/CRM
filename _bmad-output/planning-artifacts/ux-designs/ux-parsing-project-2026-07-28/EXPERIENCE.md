---
name: OperatorDesk
status: final
sources: []
updated: 2026-08-20
---

# OperatorDesk — Experience Spine

> **Reworked 2026-08-20 (Lead Workflow v2 — see `prds/prd-parsing-project-2026-08-20/prd.md`).** The queue, the review form, the lock-on-submit pattern and both request flows described below were replaced by a five-status lead pipeline. Sections superseded by that change are marked inline; everything unmarked still holds.

> Single-surface responsive web, desktop-primary. React + Vite + TypeScript + Tailwind + shadcn/ui SPA against the existing FastAPI backend. Paired with `DESIGN.md`. Fast-path draft — `[ASSUMPTION]` tags mark inferred decisions pending user confirmation.

## Foundation

Single-surface responsive web app, desktop-primary (operators work at a desk, phone in hand or headset on, screen open). One codebase, one login, two role-gated areas: **Operator** and **Admin**. A user's JWT carries their role; the app renders the matching sidebar and redirects away from routes the role can't reach (no "access denied" screen — the nav simply doesn't offer what isn't theirs, and a direct URL hit redirects to the user's home surface). `DESIGN.md` is the visual identity reference; this spine is the experience.

**Scope boundary** `[ASSUMPTION]`: OperatorDesk owns the review workflow (queue, fill form, permission requests, operator stats/profile) and admin operator-management (create operators, approve/deny requests, stats). It does not reimplement raw company scrape management or scrape-trigger controls — those stay in the existing SQLAdmin panel (`/admin`), which continues to exist separately and is not part of this spine.

## Information Architecture

| Surface | Reached from | Role | Purpose |
|---|---|---|---|
| Login | App entry | Both | Username + password → JWT |
| Leadlar | Sidebar default / post-login | Operator | Five status tabs; row click claims and opens |
| Barcha leadlar | Sidebar | Admin | The same table, observation-only: owner column always on, no claiming |
| Company Review | Queue row click, or "Fill" button | Operator | Company info + Website/LMS review form; locked view + Request-permission after submit |
| My Stats & Profile | Sidebar / avatar menu | Operator | Own daily/total counts, filled-record history, avatar upload |
| Notifications panel | Bell icon, top bar | Both | Permission-request lifecycle events |
| Admin Dashboard | Sidebar default / post-login (admin) | Admin | Org-wide + per-operator stats (today, this week, all-time) |
| Operators | Sidebar | Admin | Roster, create operator (username/password/full name), per-operator drill-in to their stats |
| Permission Requests | Sidebar (badge count) | Admin | Pending requests queue, Approve/Deny, history |

Sidebar collapses to an icon rail at `md`; content areas cap at `max-w-7xl` (tables) or `max-w-2xl` (the review form). Modal stacks one level deep (e.g. a confirmation `AlertDialog` may open on top of the Company Review sheet, never on top of another dialog).

→ Composition reference: `mockups/login.html`, `mockups/company-review.html`, `mockups/admin-dashboard.html`. Spine wins on conflict.

## Voice and Tone

Microcopy. Brand posture lives in `DESIGN.md.Brand & Style` — plain, operational, no exclamation marks.

| Do | Don't |
|---|---|
| "24 ta kompaniya to'ldirilishi kerak" | "Vay! 24 ta ish kutyapti 🎉" |
| "Bugun: 20 ta to'ldirdingiz" | "Ajoyib natija!" |
| "Ro'yxat bo'sh — hammasi to'ldirilgan" | "Hech narsa yo'q :(" |
| "Ruxsat so'raldi. Admin javobini kuting." | "So'rovingiz yuborildi!!!" |
| Same tone to operator and admin — status and counts, not encouragement | Different voice per audience |

## Component Patterns

Behavioral. Visual specs live in `DESIGN.md.Components`.

| Component | Use | Behavioral rules |
|---|---|---|
| Lead row | Queue table | Click anywhere **claims** the lead and opens it — for `Yangi` and `Kutilmoqda` there is no separate confirm step. Finished leads open read-only. Columns: lead status badge, the two field badges, and — for `Kutilmoqda` — the last handover comment inline, so an operator can judge the lead without opening it. |
| Review field (Website / LMS) | Lead page | **Superseded 2026-08-20.** No lock states. While the lead is yours: a three-way choice (Mavjud / Yo'q / Belgilanmagan) plus a free-text izoh, both autosaved, neither required. Otherwise: read-only text. "Belgilanmagan" is a real stored state — the old form had no way to say it and wrote `false` instead. |
| Save | Lead page | **Superseded 2026-08-20.** There is no Saqlash button and no confirm dialog. Field edits autosave ~1s after typing stops; the indicator next to the status badge says so. Finishing is a separate, deliberate act: **Tasdiqlash** (disabled until both fields are decided, with the reason shown beneath) or **Rad etish** (always available, reason required). |
| Admin lead view | Lead page, admin | **Added 2026-08-20.** An admin sees every field and the full timeline but no work controls -- `available_actions` returns only "Majburan bo'shatish" or "Operatorga biriktirish". Their queue row click opens the lead; it never claims. The admin's tab set has no "Mening ishim", because an admin never holds one. |
| Action bar | Lead page | Renders exactly the actions the server returned in `available_actions`. The client never derives "can I approve this yet?" itself — one state machine, server-side. |
| Handover dialog | Any exit from an owned lead | The one guarded moment in the product. Reached from the back button, the sidebar, a click on another lead, or the explicit "Qoldirish" button — all funnel through one component. The confirm button stays disabled while the comment is empty; the validation message is `aria-live`. Cancel is worded "Ishda qolish", not "Bekor qilish": the operator is choosing to stay, not aborting something. |
| Timeline | Lead page | Newest first. Every status change, comment, handover, finish, reopen, auto-release and admin action, with actor and relative time. This is what replaced the lock as the accountability mechanism, so it is a primary panel, not a footnote. |
| ~~Request-permission button~~ | — | **Removed 2026-08-20.** Replaced by "Qayta ochish": any operator reopens any finished lead immediately, giving a reason that lands in the timeline. No admin, no waiting. |
| Notification bell | Top bar, both roles | Unread count badge (accent sky dot, not a full badge — quiet by design per `DESIGN.md`). Click opens `Popover` list, newest first. Operator sees "Ruxsatingiz tasdiqlandi: {company}" / "rad etildi". Admin sees "{operator} ruxsat so'radi: {company}". Item click deep-links: operator → Company Review (now unlocked); admin → Permission Requests row. |
| Stat tile | Admin Dashboard | See `DESIGN.md.Components.stat-tile`. Grid of 3–4: "Bugun to'ldirilgan", "Bu hafta", "Kutilayotgan so'rovlar", "Faol operatorlar". |
| Operator leaderboard table | Admin Dashboard | Operator name + avatar, today's count, this-week count, all-time count, sortable by any column. Row click → operator's own stats/history (admin viewing operator's page — read-only, no edit). |
| Create-operator form | Operators surface | `Dialog`: full name, username, temporary password (admin sets it directly — `[ASSUMPTION]` no email/invite flow in v1, admin hands credentials to the operator directly). Submits, closes, new row appears in roster. |
| Avatar upload | My Stats & Profile | Click avatar → file picker → immediate upload + optimistic preview; `Toast` confirms or reverts on failure. |

## State Patterns

| State | Surface | Treatment |
|---|---|---|
| Cold load | Queue, Dashboard, Operators | shadcn `Skeleton` rows (5–8) matching final layout. |
| Empty queue | Queue | `display-sm`: "Ro'yxat bo'sh — hammasi to'ldirilgan." No action button (nothing to do); this is the success state, not an error. |
| Lead, partially filled | Lead page | **Superseded 2026-08-20.** Nothing is required to leave a lead half-done — that is the normal case, and the handover comment is what carries it forward. Only **Tasdiqlash** requires both fields decided, and it says which one is missing. |
| Lead held by someone else | Lead page (admin only) | Operators never reach this state: the lead is absent from their queue and the URL 404s. Admins see a banner naming the holder, plus "Majburan bo'shatish". |
| Lead auto-released | Timeline | After 4 hours with no activity the hold lapses; the lead reappears in `Kutilmoqda` and the timeline shows "Avtomatik bo'shatildi — 4 soat harakatsizlik" attributed to Tizim. Draft data is kept. |
| Empty queue tab | Queue | One message per tab, and several are success states rather than errors: "Yangi lead qolmadi — hammasi ishga olingan." |
| Save failure | Lead page | The autosave indicator turns to "Saqlanmadi — qayta urinilmoqda" and **the typed content stays on screen**. What the operator wrote is the only copy until it lands. |
| Save/network failure | Any mutation | shadcn `Toast` (destructive): "Saqlab bo'lmadi. Qayta urinib ko'ring." Form data retained, not cleared. |
| Claim race | Queue | Two operators click the same row at once; the database picks one. The loser gets "Bu leadni boshqa operator band qilib ulgurdi." and the queue refreshes. In practice this is rare, because a claim broadcasts over the WebSocket and removes the row from everyone else's list within a second. |

## Interaction Primitives

Mouse/touch-first (call-center operators, not power-keyboard users) — no command palette, no vim-style nav, `[ASSUMPTION]` diverging from a keyboard-first pattern that wouldn't fit this audience.

- Click row → open detail (Queue, Operators, Permission Requests all follow this)
- `Esc` closes the open dialog/sheet
- Sortable table headers (click to sort, click again to reverse) on Queue, Operators, Permission Requests
- Notification `Popover` closes on outside click or `Esc`
- Pagination, not infinite scroll, on every table (operators may reference "row 12" over the phone — stable positions matter)

**Banned:** infinite scroll, drag-and-drop, autosave-without-confirmation on the review form (the lock is consequential enough to require an explicit Submit).

## Accessibility Floor

Behavioral. Visual contrast lives in `DESIGN.md` (shadcn WCAG AA defaults; status colors verified against both light/dark backgrounds).

- WCAG 2.2 AA across the app.
- Status is never color-only: badge = icon + color + text label, always.
- Every table row is a real interactive element (button/link semantics), reachable and activatable by keyboard even though the primary audience is mouse-first.
- Form validation errors are announced (`aria-live`) and associated to their field, not just color-highlighted.
- Focus rings inherit shadcn's `ring` token; visible on every interactive element, including table rows and status badges that act as buttons.
- Locked fields are marked `aria-disabled` with the reason in an accessible description, not conveyed by icon alone.

## Responsive & Platform

| Breakpoint | Behavior |
|---|---|
| `≥ lg` (1024px+) | Sidebar visible (expanded). Queue/Operators tables show full column set. |
| `md` (768–1023px) | Sidebar collapses to icon rail. Tables drop secondary columns (e.g. source, address) behind a row-expand affordance. |
| `< md` (`sm`) | `[ASSUMPTION]` Not a primary target — operators work at a desk. App remains usable (sidebar → `Sheet`, tables scroll horizontally) but no bespoke mobile layout in v1. |

## Inspiration & Anti-patterns

- **Lifted from Linear/shadcn admin templates:** dense sortable tables as the primary content pattern, quiet status badges, restrained color use.
- **Lifted from support/ticketing tools (e.g. Zendesk queue views):** the "queue → detail → resolve → back to queue" loop for the operator's core task.
- **Rejected — gamification (streaks, confetti, badges-for-badges):** this is a data-quality tool; the admin dashboard reports counts, it doesn't reward them. A sortable table beats a leaderboard widget with medals.
- **Rejected — free-form status (operator-defined tags):** the five lead states and three field states are fixed. The point is a scannable, unambiguous queue; a configurable pipeline would mean a different workflow per operator.
- **Rejected — approval gates on operator actions (2026-08-20):** v1 routed re-edits and deadline changes through an admin. It made the admin a bottleneck and left operators idle. v2 permits the action and records it; the admin watches flow instead of authorising it.
- **Rejected — real-time WebSocket notifications for v1:** polling is simpler, no new infra, "prompt enough" for an internal tool; noted as upgradable, not as a compromise to hide.

## Key Flows

### Flow 1 — Malika verifies a company (operator, mid-shift)

1. Malika logs in, lands on Queue: "24 ta kompaniya to'ldirilishi kerak."
2. She clicks the top row — "IPOTEKA BANK" — opens Company Review: name, address, phone, category shown read-only at the top; two review fields below, both editable, both empty.
3. She calls the number on file. The receptionist confirms they have a website but no LMS.
4. She checks "Mavjud" under Website, types "ipotekabank.uz, operator tasdiqladi" in the comment. Under LMS she leaves the checkbox unset and types "Yo'q, operator bilan tasdiqlandi."
5. Submit enables (both fields complete). She clicks "Saqlash," confirms the lock dialog.
6. **Climax:** the dialog transitions in place — both fields now show locked state, green "Mavjud" badge on Website, gray "Yo'q" badge on LMS, her name and the timestamp under each. No navigation, no page reload; she's already looking at what she'll see if she (or anyone) revisits this row. She closes the sheet; Queue count drops to 23.

Failure: the call drops before she finishes typing. She saves nothing (Submit was never enabled — no partial state persisted), closes the sheet, and the row stays in the queue exactly as before. She tries again later.

### Flow 2 — A locked record needs a fix (Malika + Admin)

1. Two days later Malika notices the LMS comment she wrote has a typo that changes the meaning ("bor" vs "yo'q" — she mis-typed under time pressure).
2. She reopens the company from a search/filter `[ASSUMPTION: reachable via Queue's "hammasi" tab or a search box, not detailed further]`, sees the LMS field locked-other (system attributes locks generically, even to the original filler, per Component Patterns) with "Ruxsat so'rash."
3. She clicks it, types a reason: "Xato kiritdim, LMS mavjud emas emas — mavjud ekan," submits. Button becomes "So'ralgan — kutilmoqda."
4. Within the poll interval, an admin's Notifications bell picks up a new unread dot: "Malika ruxsat so'radi: IPOTEKA BANK — LMS."
5. Admin opens Permission Requests, reads Malika's reason, clicks Approve.
6. **Climax:** Malika's Notifications bell picks up the approval on its next poll — she doesn't have to ask anyone. She reopens the row; the LMS field is now editable again, her previous (wrong) answer pre-filled for reference. She fixes it, submits, it locks again.

Failure: Admin instead clicks Deny (reason optional). Malika's notification reads "rad etildi"; the field stays locked-other, the request button re-enables immediately for a fresh attempt if she wants to explain better.

### Flow 3 — Admin sets up a new operator and checks throughput

1. Admin opens Operators, clicks "Yangi operator qo'shish."
2. Fills full name, chooses a username, sets a temporary password, saves. New row appears in the roster with zero counts.
3. Admin hands the credentials to the new hire directly (no invite email in v1).
4. End of day, Admin opens Dashboard: stat tiles show "Bugun to'ldirilgan: 87," "Faol operatorlar: 5." The operator table, sorted by today's count descending, shows the new hire already at 6 — onboarding worked.
5. **Climax:** Admin clicks the new operator's row to confirm nothing looks off (no unusually fast, suspiciously identical comments — a light manual quality check the dashboard makes possible just by existing), sees a normal-looking list of 6 filled companies with varied comments, and moves on. The dashboard's job was to make that two-second check possible without pulling a database query.
