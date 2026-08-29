---
name: OperatorDesk
description: Internal lead-verification tool -- operators work scraped companies through a five-status pipeline, confirming whether each has a website and an LMS; admins watch throughput and step in where work has stalled. shadcn/ui on React + Vite + Tailwind; this DESIGN.md specifies the brand-layer delta only. Reworked 2026-08-20 (Lead Workflow v2).
colors:
  # Brand overrides on top of shadcn defaults. All unlisted tokens inherit
  # from shadcn (background, foreground, muted, muted-foreground, popover,
  # popover-foreground, card, card-foreground, border, input, ring, destructive).
  primary: '#1D4ED8'
  primary-foreground: '#FFFFFF'
  accent: '#0EA5E9'
  accent-foreground: '#FFFFFF'
  primary-dark: '#3B82F6'
  primary-foreground-dark: '#0B1220'
  accent-dark: '#38BDF8'
  accent-foreground-dark: '#0B1220'
  # Field vocabulary (Website/LMS answer). confirmed and pending were darkened
  # 2026-08-20: the originals (#16A34A, #D97706) measured 3.3:1 and 3.19:1 on
  # white, below the 4.5:1 AA floor this document claimed to meet.
  status-confirmed: '#15803D'
  status-confirmed-foreground: '#FFFFFF'
  status-absent: '#64748B'
  status-absent-foreground: '#FFFFFF'
  status-pending: '#B45309'
  status-pending-foreground: '#FFFFFF'
  status-confirmed-dark: '#22C55E'
  status-absent-dark: '#94A3B8'
  status-pending-dark: '#F59E0B'
  # Lead vocabulary (workflow state). A second, separate vocabulary added
  # 2026-08-20 -- see Colors below for why it is not a fourth colour in the first.
  lead-new: '#475569'
  lead-progress: '#4F46E5'
  lead-waiting: '#B45309'
  lead-approved: '#15803D'
  lead-rejected: '#B91C1C'
  lead-new-dark: '#CBD5E1'
  lead-progress-dark: '#818CF8'
  lead-waiting-dark: '#F59E0B'
  lead-approved-dark: '#22C55E'
  lead-rejected-dark: '#F87171'
typography:
  # Body, label, and muted inherit from shadcn (Inter). Only display is set explicitly.
  display:
    fontFamily: 'Inter'
    fontSize: 28px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  display-sm:
    fontFamily: 'Inter'
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.25'
  mono:
    fontFamily: 'JetBrains Mono'
    fontSize: 13px
    fontWeight: '400'
rounded:
  # shadcn defaults inherited as-is -- this is a tool, not a brand showcase.
  sm: 6px
  md: 8px
  lg: 10px
spacing:
  # shadcn / Tailwind defaults inherited; no overrides.
components:
  button-primary:
    background: '{colors.primary}'
    foreground: '{colors.primary-foreground}'
    radius: '{rounded.md}'
  status-badge-confirmed:
    background: '{colors.status-confirmed}'
    foreground: '{colors.status-confirmed-foreground}'
    radius: 'full'
  status-badge-absent:
    background: '{colors.status-absent}'
    foreground: '{colors.status-absent-foreground}'
    radius: 'full'
  status-badge-pending:
    background: '{colors.status-pending}'
    foreground: '{colors.status-pending-foreground}'
    radius: 'full'
  sidebar-active-item:
    background: '{colors.primary}'
    foreground: '{colors.primary-foreground}'
    radius: '{rounded.md}'
---

## Brand & Style

OperatorDesk is an internal operations tool: operators call or message companies to confirm whether they have a website and an LMS (learning management system), record what they found, and admins keep the operation running -- creating accounts, watching throughput, unsticking work that has stalled. Nobody outside the company ever sees this screen. The design brief follows from that: **legible, fast, unambiguous** beats decorative. A user scanning a table of 40 companies for the 3 still unverified needs status to read at a glance, not a personality.

The visual language is a restrained SaaS-dashboard: shadcn/ui defaults for nearly everything, one brand blue for primary actions and active navigation, and **two status vocabularies** -- five colours for a lead's workflow state, three for a field's answer -- which together are the single most-repeated visual element in the product. Get those right and the rest of the brand is quiet by design.

`[ASSUMPTION]` No existing brand guidelines were supplied; blue-primary + slate-neutral is chosen as the safe, professional default for an internal business tool. Revisit if the company has an existing brand palette.

## Colors

- **Primary Blue (`#1D4ED8` light / `#3B82F6` dark)** -- primary buttons, active sidebar item, links, focus states, the brand's only "loud" color. Replaces shadcn's default `primary`.
- **Accent Sky (`#0EA5E9` light / `#38BDF8` dark)** -- used sparingly for informational highlights (e.g. the "new" dot on an unread notification, the active tab indicator). Never used for status.
**Two vocabularies, not one (2026-08-20).** The original trio answered "does this company have a website?". The lead workflow introduced an orthogonal question -- "where is this piece of work?" -- and one badge set answering both made queue rows ambiguous. They are now separate components (`LeadStatusBadge`, `FieldStatusBadge`) over separate tokens. The old rule "never invent a fourth status colour" still binds *within* each vocabulary.

- **Lead vocabulary** (five states, the queue's primary scan target):
  - **Yangi -- Slate (`#475569` / `#CBD5E1` dark)** -- nothing has happened yet; deliberately the quietest of the five.
  - **Jarayonda -- Indigo (`#4F46E5` / `#818CF8` dark)** -- pointedly *not* the `#1D4ED8` brand blue: an active lead must not read as a button.
  - **Kutilmoqda -- Amber (`#B45309` / `#F59E0B` dark)** -- shares the field vocabulary's amber, and means the same thing in both: waiting on something.
  - **Tasdiqlangan -- Green (`#15803D` / `#22C55E` dark)**.
  - **Rad etilgan -- Red (`#B91C1C` / `#F87171` dark)** -- the one genuinely new colour. Red is right *here* (a rejected lead is a terminal negative outcome) and still wrong for the field vocabulary's "yo'q" (an absent website is a normal finding). That the same colour is correct in one vocabulary and forbidden in the other is precisely why they are separate.

- **Field vocabulary** (the original trio, unchanged in meaning; two values darkened for contrast):
  - **Confirmed Green (`#15803D` / `#22C55E` dark)** -- "bor" (has website / has LMS).
  - **Absent Slate (`#64748B` / `#94A3B8` dark)** -- "yo'q" (confirmed absent). Deliberately gray, not red -- absence is a normal, valid finding, not an error.
  - **Belgilanmagan Amber (`#B45309` / `#F59E0B` dark)** -- the operator has not decided yet. In v1 this state could not be stored and the form wrote `false` instead; v2 keeps it as a real value.

**Contrast correction (2026-08-20).** This document previously claimed its status colours were "verified against both light/dark backgrounds". They were not: `#16A34A` and `#D97706` with white text measure **3.3:1** and **3.19:1**, under the 4.5:1 WCAG AA floor for text this size. Both were darkened one step (`#15803D`, `#B45309`), now 5.02:1. Every pair in both vocabularies has been recomputed and clears 4.5:1 against its own foreground.
- **All other tokens** (`background`, `foreground`, `muted`, `muted-foreground`, `border`, `input`, `ring`, `card`, `popover`, `destructive`) inherit shadcn defaults. `destructive` (shadcn default red) is reserved for real errors and the "Deny" action -- never reused for "absent."

Avoid: red for "no website" (that reads as an error, not a finding), more than the two brand colors, decorative gradients, illustration.

## Typography

Inter throughout (body, label, `display`) -- no separate display face. This is a dashboard meant to be scanned quickly across long sessions; introducing a second typeface would add friction, not character. `display` (28px/600) marks page titles ("Sizga tayinlangan ro'yxat", "Operatorlar"); `display-sm` (20px/600) marks card/section headers and dialog titles. `mono` (JetBrains Mono, 13px) is reserved for phone numbers and source IDs in tables -- fixed-width digits scan faster in a list.

## Layout & Spacing

shadcn / Tailwind spacing scale inherited as-is (4, 8, 12, 16, 20, 24, 32, 40, 48, 64). Standard app shell: fixed left sidebar (`w-64`, collapses to icon rail at `md`) + top bar (search/breadcrumb left, notification bell + avatar menu right) + main content area, `max-w-7xl` for table-heavy surfaces (queue, operators list), `max-w-3xl` for the lead page (wider than v1's `max-w-2xl` since the timeline panel sits below the fields).

Tables are the dominant content pattern (lead queue, operator roster) — dense, no card-grid alternative.

## Elevation & Depth

Inherited from shadcn: flat surfaces by default, subtle shadow only on floating elements (dialogs, popovers, the notification panel, dropdown menus). No elevation on static cards -- a border (`{colors.border}`) separates card from background, not a shadow. Consistent with "tool, not showcase."

## Shapes

shadcn defaults: `rounded/sm` (6px) inputs and checkboxes, `rounded/md` (8px) buttons and cards, `rounded/lg` (10px) dialogs. Status badges are the one `rounded/full` (pill) element in the product — deliberately distinct from every other rectangular surface so status reads as *status*, not as another button.

## Components

Used as-is from shadcn, unmodified: `Button`, `Card`, `Dialog`, `Sheet`, `Table`, `DropdownMenu`, `Popover`, `Toast`, `Tabs`, `Avatar`, `Checkbox`, `Textarea`, `Input`, `Skeleton`, `Badge` (as the base for status badges), `AlertDialog` (the base for every note-collecting dialog: handover, reject, reopen, admin release).

Brand-layer components:

- **Status badge** (confirmed / absent / pending) — the product's signature element. Pill shape, solid fill from the status-color trio above, white text, small icon (check / dash / clock) before the label. Always paired with text, never color-only (accessibility).
- **Sidebar active item** — `{colors.primary}` fill, white text, `{rounded.md}`. Only one active at a time; matches current route.
- **Stat tile** (admin dashboard) — `Card` with a large number (`display` size, tabular-nums), a label below, and an optional trend/comparison line in `muted-foreground`. No sparkline in v1 — a bare number set is more legible for "20 ta bugun" than a chart nobody asked for.
- ~~**Locked-field indicator**~~ — **removed 2026-08-20.** Fields no longer lock; correcting a finished lead is a first-class action (reopen with a reason). Replaced by:
- **Lead status badge** — pill, solid fill from the five-colour lead vocabulary, icon + label, two sizes (queue row / lead header).
- **Autosave indicator** — three states next to the lead header: "Saqlanmoqda…", "Saqlandi", "Saqlanmadi — qayta urinilmoqda". Text, not a spinner alone; a failed save is information the operator must not miss.
- **Timeline entry** — icon (by event type) + actor + relative time + note. Actor renders "Tizim" when the system acted.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Keep the two vocabularies separate — `LeadStatusBadge` for workflow state, `FieldStatusBadge` for the Website/LMS answer | Answer both questions with one badge, or add a sixth lead state / fourth field state |
| Use red for a rejected *lead* | Use red for an absent website — absence is a finding, not an error |
| Keep tables dense and scannable; mono digits for phone/IDs | Switch to card-grid layouts for list surfaces |
| One brand blue for actions/navigation, used consistently | Introduce a second accent or brand color |
| Pair every status badge with a text label | Rely on color alone to convey status |
| Flat cards with border, shadow only on floating elements | Add shadow/elevation to static dashboard cards |
