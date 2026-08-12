---
name: OperatorDesk
description: Internal review/data-entry tool -- operators verify whether scraped companies have a website and an LMS, admins manage operators and approve edit requests. shadcn/ui on React + Vite + Tailwind; this DESIGN.md specifies the brand-layer delta only.
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
  status-confirmed: '#16A34A'
  status-confirmed-foreground: '#FFFFFF'
  status-absent: '#64748B'
  status-absent-foreground: '#FFFFFF'
  status-pending: '#D97706'
  status-pending-foreground: '#FFFFFF'
  status-confirmed-dark: '#22C55E'
  status-absent-dark: '#94A3B8'
  status-pending-dark: '#F59E0B'
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

OperatorDesk is an internal operations tool: operators call or message companies to confirm whether they have a website and an LMS (learning management system), record what they found, and admins keep the operation running -- creating accounts, approving edit requests, watching throughput. Nobody outside the company ever sees this screen. The design brief follows from that: **legible, fast, unambiguous** beats decorative. A user scanning a table of 40 companies for the 3 still unverified needs status to read at a glance, not a personality.

The visual language is a restrained SaaS-dashboard: shadcn/ui defaults for nearly everything, one brand blue for primary actions and active navigation, and a dedicated **three-color status vocabulary** (confirmed / absent / pending) that is the single most-repeated visual element in the product -- it appears on every company row, every stat tile, every badge. Get that vocabulary right and the rest of the brand is quiet by design.

`[ASSUMPTION]` No existing brand guidelines were supplied; blue-primary + slate-neutral is chosen as the safe, professional default for an internal business tool. Revisit if the company has an existing brand palette.

## Colors

- **Primary Blue (`#1D4ED8` light / `#3B82F6` dark)** -- primary buttons, active sidebar item, links, focus states, the brand's only "loud" color. Replaces shadcn's default `primary`.
- **Accent Sky (`#0EA5E9` light / `#38BDF8` dark)** -- used sparingly for informational highlights (e.g. the "new" dot on an unread notification, the active tab indicator). Never used for status.
- **Status vocabulary** (the product's real visual backbone, independent of brand primary):
  - **Confirmed Green (`#16A34A` / `#22C55E` dark)** -- "bor" (has website / has LMS). Checkbox checked + saved.
  - **Absent Slate (`#64748B` / `#94A3B8` dark)** -- "yo'q" (confirmed absent). Deliberately gray, not red -- absence is a normal, valid finding, not an error.
  - **Pending Amber (`#D97706` / `#F59E0B` dark)** -- awaiting something: unfilled row, a permission request awaiting admin decision, a locked field the operator just asked to reopen.
- **All other tokens** (`background`, `foreground`, `muted`, `muted-foreground`, `border`, `input`, `ring`, `card`, `popover`, `destructive`) inherit shadcn defaults. `destructive` (shadcn default red) is reserved for real errors and the "Deny" action -- never reused for "absent."

Avoid: red for "no website" (that reads as an error, not a finding), more than the two brand colors, decorative gradients, illustration.

## Typography

Inter throughout (body, label, `display`) -- no separate display face. This is a dashboard meant to be scanned quickly across long sessions; introducing a second typeface would add friction, not character. `display` (28px/600) marks page titles ("Sizga tayinlangan ro'yxat", "Operatorlar"); `display-sm` (20px/600) marks card/section headers and dialog titles. `mono` (JetBrains Mono, 13px) is reserved for phone numbers and source IDs in tables -- fixed-width digits scan faster in a list.

## Layout & Spacing

shadcn / Tailwind spacing scale inherited as-is (4, 8, 12, 16, 20, 24, 32, 40, 48, 64). Standard app shell: fixed left sidebar (`w-64`, collapses to icon rail at `md`) + top bar (search/breadcrumb left, notification bell + avatar menu right) + main content area, `max-w-7xl` for table-heavy surfaces (queue, operators list), `max-w-2xl` for the fill form (a form this consequential — it locks on submit — should not sprawl edge-to-edge).

Tables are the dominant content pattern (company queue, operator roster, permission requests) — dense, sortable, no card-grid alternative in v1.

## Elevation & Depth

Inherited from shadcn: flat surfaces by default, subtle shadow only on floating elements (dialogs, popovers, the notification panel, dropdown menus). No elevation on static cards -- a border (`{colors.border}`) separates card from background, not a shadow. Consistent with "tool, not showcase."

## Shapes

shadcn defaults: `rounded/sm` (6px) inputs and checkboxes, `rounded/md` (8px) buttons and cards, `rounded/lg` (10px) dialogs. Status badges are the one `rounded/full` (pill) element in the product — deliberately distinct from every other rectangular surface so status reads as *status*, not as another button.

## Components

Used as-is from shadcn, unmodified: `Button`, `Card`, `Dialog`, `Sheet`, `Table`, `DropdownMenu`, `Popover`, `Toast`, `Tabs`, `Avatar`, `Checkbox`, `Textarea`, `Input`, `Skeleton`, `Badge` (as the base for status badges), `AlertDialog` (confirmations: submit-locks, deny request).

Brand-layer components:

- **Status badge** (confirmed / absent / pending) — the product's signature element. Pill shape, solid fill from the status-color trio above, white text, small icon (check / dash / clock) before the label. Always paired with text, never color-only (accessibility).
- **Sidebar active item** — `{colors.primary}` fill, white text, `{rounded.md}`. Only one active at a time; matches current route.
- **Stat tile** (admin dashboard) — `Card` with a large number (`display` size, tabular-nums), a label below, and an optional trend/comparison line in `muted-foreground`. No sparkline in v1 — a bare number set is more legible for "20 ta bugun" than a chart nobody asked for.
- **Locked-field indicator** — once a review field (website or LMS) is submitted, its form controls render disabled with a small lock icon and "{operator_name} tomonidan to'ldirilgan" caption, replacing the editable checkbox+textarea. Not a separate component so much as a state of the review-field component (see EXPERIENCE.md Component Patterns).

## Do's and Don'ts

| Do | Don't |
|---|---|
| Use the status trio (green/gray/amber) exactly as defined — confirmed/absent/pending, nothing else | Invent a fourth status color, or use red for "absent" |
| Keep tables dense and scannable; mono digits for phone/IDs | Switch to card-grid layouts for list surfaces |
| One brand blue for actions/navigation, used consistently | Introduce a second accent or brand color |
| Pair every status badge with a text label | Rely on color alone to convey status |
| Flat cards with border, shadow only on floating elements | Add shadow/elevation to static dashboard cards |
