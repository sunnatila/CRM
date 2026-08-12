---
name: OperatorDesk
status: final
sources: []
updated: 2026-07-28
---

# OperatorDesk — Experience Spine

> Single-surface responsive web, desktop-primary. React + Vite + TypeScript + Tailwind + shadcn/ui SPA against the existing FastAPI backend. Paired with `DESIGN.md`. Fast-path draft — `[ASSUMPTION]` tags mark inferred decisions pending user confirmation.

## Foundation

Single-surface responsive web app, desktop-primary (operators work at a desk, phone in hand or headset on, screen open). One codebase, one login, two role-gated areas: **Operator** and **Admin**. A user's JWT carries their role; the app renders the matching sidebar and redirects away from routes the role can't reach (no "access denied" screen — the nav simply doesn't offer what isn't theirs, and a direct URL hit redirects to the user's home surface). `DESIGN.md` is the visual identity reference; this spine is the experience.

**Scope boundary** `[ASSUMPTION]`: OperatorDesk owns the review workflow (queue, fill form, permission requests, operator stats/profile) and admin operator-management (create operators, approve/deny requests, stats). It does not reimplement raw company scrape management or scrape-trigger controls — those stay in the existing SQLAdmin panel (`/admin`), which continues to exist separately and is not part of this spine.

## Information Architecture

| Surface | Reached from | Role | Purpose |
|---|---|---|---|
| Login | App entry | Both | Username + password → JWT |
| Queue ("To'ldirish ro'yxati") | Sidebar default / post-login | Operator | Unfilled companies, table, row → Fill |
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
| Company row | Queue table | Click anywhere opens Company Review. Status column shows two mini status-badges (Website, LMS) reflecting current state — both `pending` (amber) until filled. |
| Review field (Website / LMS) | Company Review | Three states: **editable** (checkbox "Mavjud" + `Textarea` for izoh, both required before submit — see State Patterns), **locked-mine** (disabled, "Siz to'ldirdingiz" + timestamp, no request-access button), **locked-other** (disabled, "{operator} tomonidan to'ldirilgan" + "Ruxsat so'rash" button). Website and LMS are independent — one can be locked while the other is still editable, if the backend ever allows partial submit (`v1` submits both together — see Key Flows). |
| Submit action | Company Review | Single "Saqlash" button submits both fields together (not per-field) and immediately transitions both to locked. `AlertDialog` confirms: "Saqlagandan so'ng bu yozuvni faqat ruxsat bilan tahrirlash mumkin. Davom etasizmi?" — the lock is a real commitment, the UI treats it as one. |
| Request-permission button | Locked-other review field | Click → `AlertDialog` optional reason field (`[ASSUMPTION]` free-text "Nega qayta tahrirlashni so'rayapsiz?") → submits request, button becomes disabled "So'ralgan — kutilmoqda" (pending amber). Re-clickable only after admin resolves (approve reopens the field; deny re-enables the button, no cooldown `[ASSUMPTION]`). |
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
| Review field, editable, incomplete | Company Review | Checkbox unset AND comment empty → Submit disabled, helper text under the field: "Belgilang va izoh yozing." Both website and LMS must be complete before Submit enables (`[ASSUMPTION]`: can't submit half-done). |
| Review field, locked-mine | Company Review | Muted background, lock icon, no request-access affordance (you don't need permission from yourself — a data-fix in this state goes through the same request flow as anyone, `[ASSUMPTION]` unless product wants a self-serve short-window edit, not specified). |
| Review field, locked-other | Company Review | Muted background, lock icon, filler's name + timestamp, "Ruxsat so'rash" button. |
| Permission requested, pending | Company Review (requester), Notifications | Amber "pending" badge replaces the request button; live-updates on next poll if admin resolves while the page is open. |
| Permission denied | Notifications, Company Review | Notification: "{admin} rad etdi." Field returns to locked-other state, request button re-enabled. |
| Submit in flight | Company Review | Submit button shows spinner, disabled; on success, dialog/sheet transitions to locked view in place (no navigation away). |
| Save/network failure | Any mutation | shadcn `Toast` (destructive): "Saqlab bo'lmadi. Qayta urinib ko'ring." Form data retained, not cleared. |
| Duplicate-submit race | Company Review | Two operators open the same unfilled row; second submitter's request is rejected server-side (already locked) → `Toast`: "Bu yozuvni {operator} allaqachon to'ldirdi." View refreshes to locked-other. |

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
- **Rejected — free-form status (custom tags beyond confirmed/absent/pending):** three states, no more — the whole point is a scannable, unambiguous queue.
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
