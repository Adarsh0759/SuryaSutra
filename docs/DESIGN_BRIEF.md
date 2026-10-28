# SuryaSutra — UI/UX Design Brief & Design System

> Version 1.0 · 2026-10-28 · Applies to the landing page and the app. Implement tokens as CSS variables in `web/src/styles/tokens.css` and motion tokens in `web/src/motion/tokens.ts`.

---

## 1. Design direction

**Feel:** a precise control-room instrument — calm, dark, high-contrast, with one electric accent. Confident on the landing page; quiet and fast inside the app.

**Principles**
1. **Safety first, literally.** Safety information is always the first content, never hidden, never delayed by animation.
2. **Show the source.** Every claim has a visible citation.
3. **Honest by default.** Synthetic data is badged; unmeasured numbers say "Not yet measured".
4. **Motion explains, never decorates in the app.** Animation shows what changed or how evidence was chosen.
5. **Field-ready.** Works on a cheap Android phone, in sunlight, with gloves.

## 2. Colour

### 2.1 Brand palette

| Token | Hex | Use |
|---|---|---|
| `--midnight` | `#030407` | Primary background (dark theme), text on lime |
| `--cobalt` | `#1558C9` | Primary interactive (links on light, filled buttons, focus, selected) |
| `--lime` | `#D4FF24` | Signature accent: primary CTA fill, highlights, "selected evidence", key numbers |

### 2.2 Dark theme (default: control room, landing page)

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#030407` | Page |
| `--surface-1` | `#0B0F17` | Cards |
| `--surface-2` | `#121826` | Raised cards, inputs, panels |
| `--border` | `#1F2737` | Dividers, card strokes |
| `--text-1` | `#F2F4F8` | Primary text |
| `--text-2` | `#A7B0C0` | Secondary text |
| `--text-3` | `#6B7486` | Hints only (≥ 24 px or non-essential) |
| `--accent` | `#D4FF24` | Accent; text on it is `--midnight` |
| `--interactive` | `#4C8DFF` | Links/focus on dark (cobalt lightened for contrast) |
| `--danger` | `#FF5A5F` | Safety box border/icon, errors |
| `--warning` | `#FFB020` | Stale past case, over-budget |
| `--success` | `#3DDC97` | "Covered" state (always with ✓ and a word) |

### 2.3 Light theme ("Field mode" for sunlight — toggle, auto on mobile if the OS is light)

| Token | Hex |
|---|---|
| `--bg` | `#F6F7F2` |
| `--surface-1` | `#FFFFFF` |
| `--surface-2` | `#EEF0E8` |
| `--border` | `#D9DCD2` |
| `--text-1` | `#030407` |
| `--text-2` | `#3E4554` |
| `--accent` | `#D4FF24` (fill only, never as text) |
| `--interactive` | `#1558C9` |
| `--danger` | `#C62828` |
| `--warning` | `#9A6100` |
| `--success` | `#1E7F4F` |

### 2.4 Contrast rules (WCAG 2.2 AA)

- Lime `#D4FF24` on midnight: ≈ 17:1 — fine for any text.
- Cobalt `#1558C9` on midnight: ≈ 3.2:1 — **not for body text on dark**; use `--interactive #4C8DFF` for links on dark. Cobalt is fine as a button fill with white or lime text (≈ 6:1).
- Lime is never used as text on light backgrounds.
- Status is never colour-only: every status has an icon **and** a word ("Covered", "Missing", "Stale").

## 3. Typography

| Role | Font | Weights | Notes |
|---|---|---|---|
| Display (landing headlines) | **Instrument Serif** (italic for one emphasised word) | 400 | Editorial contrast to the technical UI, like the reference "Feel Every Moment" |
| UI & body | **Inter** | 400, 500, 600 | Tabular numbers on for metrics |
| Codes, tokens, IDs | **JetBrains Mono** | 500 | Fault codes, chunk ids, token counts |

Self-host with `@fontsource/*`; `font-display: swap`.

**Type scale (px / line-height)**

| Token | Desktop | Mobile | Use |
|---|---|---|---|
| `display` | 88 / 1.0 | 48 / 1.05 | Landing hero only |
| `h1` | 48 / 1.1 | 32 / 1.15 | Page titles |
| `h2` | 32 / 1.2 | 24 / 1.25 | Section titles |
| `h3` | 20 / 1.3 | 18 / 1.3 | Card titles |
| `body` | 16 / 1.5 | 16 / 1.5 | Default |
| `body-lg` | 18 / 1.55 | 17 / 1.5 | Triage steps (readability on site) |
| `caption` | 13 / 1.4 | 13 / 1.4 | Labels, metadata |
| `mono` | 14 / 1.4 | 14 / 1.4 | Codes, tokens |

## 4. Spacing, layout, shape

- 4 px base grid: `4, 8, 12, 16, 24, 32, 48, 64, 96`.
- App: 12-column grid, max width 1440 px, gutters 24 px; sidebar 248 px.
- Landing: max width 1200 px; sections 96–160 px vertical spacing.
- Radius: `--r-sm 8px` (chips, inputs), `--r-md 12px` (cards), `--r-lg 20px` (panels, hero media), `--r-pill 999px` (CTAs, status chips).
- Elevation on dark = lighter surface + 1 px border, not heavy shadows. One shadow token for overlays: `0 12px 40px rgba(0,0,0,0.45)`.
- Background texture (landing only): faint 48 px grid lines at 4% opacity, echoing the blueprint look in the references.

## 5. Components

| Component | Spec |
|---|---|
| **Button** | Primary: lime fill, midnight text, pill, 44 px min height. Secondary: transparent, 1 px border `--border`, `--text-1`. Danger: `--danger` outline. Hover: brightness +6%, translateY(-1px). Press: scale 0.97. Disabled: 40% opacity, no motion. |
| **SafetyBox** | `--surface-2`, 2 px `--danger` left border + top label "SAFETY FIRST" with warning icon; items numbered; each with citation chip. Never collapsible, never animated in later than the alarm header. |
| **CitationChip** | Mono, `[doc · p.12]`, `--surface-2`, 1 px border; hover/focus underline; opens source viewer. |
| **StatusChip** | Icon + word + colour: New · In progress · Answered · Insufficient · Closed. |
| **SyntheticBadge** | Small outlined chip "Synthetic data" in `--warning`. |
| **TokenBudgetBar** | Horizontal bar = budget B. Segments per selected chunk, width ∝ tokens. Mandatory segments: lime with lock icon. Fill segments: cobalt. Past cases: striped cobalt. Dropped chunks listed below in `--text-3` with reason. Label: "812 / 1,000 tokens". |
| **RequirementChecklist** | Rows: requirement name, ✓ Covered / ✕ Missing (word + icon + colour), source chip. |
| **PastFixCard** | Date, inverter, root cause, actions, outcome; "Stale" or "Recurred" warning chips. |
| **KPI tile** | Label (caption), value (h1, tabular), source line ("from 42 logged runs"); "Not yet measured" state. |
| **Skeleton** | Same shape as final content; shimmer (see motion), no layout shift. |
| **Bottom sheet** (mobile) | Drag handle, snap points 50% / 90%, Esc / swipe down closes. |

## 6. Iconography & illustration

- Lucide icons, 1.75 px stroke, 20/24 px.
- Landing illustrations are SVG line drawings in `--text-2` with lime highlights (alarm bell, bridge arc, checklist, inverter). No stock photos of people.

## 7. Motion system

### 7.1 Tokens (`web/src/motion/tokens.ts`)

| Token | Value | Use |
|---|---|---|
| `dur.instant` | 80 ms | Press feedback |
| `dur.fast` | 150 ms | Hover, chips, toggles |
| `dur.base` | 220 ms | Panels, cards, list items |
| `dur.slow` | 360 ms | Page transitions, sheets |
| `dur.story` | 600–1200 ms | Landing hero and scroll stories only |
| `ease.standard` | `cubic-bezier(0.2, 0, 0, 1)` | Most transitions |
| `ease.exit` | `cubic-bezier(0.4, 0, 1, 1)` | Leaving elements |
| `ease.emphasized` | `cubic-bezier(0.3, 0, 0, 1)` | Hero, key reveals |
| `spring.snappy` | `{ type: "spring", stiffness: 420, damping: 32 }` | Token segments locking in |
| `spring.soft` | `{ type: "spring", stiffness: 220, damping: 26 }` | Sheets, cards |
| `stagger.list` | 40 ms per item, max 8 items staggered | Lists |

### 7.2 Rules

1. Animate only `transform`, `opacity`, and SVG `pathLength`. No animating width/height/top/left (use Motion `layout`).
2. **Safety is never delayed.** The SafetyBox renders with the alarm header, at full opacity, with at most a 150 ms fade. No stagger, no typewriter effect.
3. App interactions finish within 360 ms. Longer motion only on the landing page and the optional run-trace replay.
4. Every animation has a reduced-motion version: `useReducedMotion()` → replace movement with an opacity change ≤ 100 ms, or none. Scroll-triggered reveals show content immediately.
5. No auto-playing motion longer than 5 s without a pause control (WCAG 2.2.2). Hero loop has a pause button.
6. No motion that flashes more than 3 times per second.
7. Animations are driven by real data. The evidence-packing animation replays the actual run trace from `/runs/{id}`; it never shows an invented outcome.

### 7.3 Landing page animations

| Section | Animation |
|---|---|
| Page load | Grid background fades in (600 ms); headline words rise 16 px + fade with 60 ms stagger; one italic serif word slides in last in lime |
| Hero illustration | SVG line draw (`pathLength 0→1`, 1.2 s): alarm bell → bridge arc → checklist; checklist ticks pop in with `spring.snappy`; loops slowly with a pause button |
| CTA | Lime pill with subtle shine sweep on hover (gradient translateX), arrow nudges 4 px |
| Problem cards | `whileInView` fade + rise 24 px, 80 ms stagger, once |
| How it works | 7 steps connected by a line that draws as you scroll (`useScroll` → `pathLength`); active step highlights in lime |
| Safety guarantee | Scroll-pinned demo: budget bar empty → mandatory blocks drop in and lock (lock icon flips) → optional blocks fill → an extra block bounces off with "doesn't fit" label. Uses a recorded real run trace |
| Results | Numbers count up only if they exist in `summary.md`; otherwise static "Not yet measured" |
| Section transitions | Soft parallax on illustrations only (max 40 px), never on text |

### 7.4 App animations

| Where | Animation |
|---|---|
| Route change | Fade + 8 px rise, 220 ms (`AnimatePresence`, `mode="wait"`) |
| Alarm queue | New alarm row slides in from top (layout animation) with a 1.2 s lime left-edge pulse, once |
| Triage loading | Skeleton shimmer (1.4 s linear loop, opacity 0.5→0.8); stage label updates: "Retrieving → Selecting evidence → Writing answer" |
| Answer reveal | Header + SafetyBox appear together; causes and steps fade/rise with 40 ms stagger |
| Citation open | Desktop panel slides in from right (`spring.soft`); mobile bottom sheet with drag; highlighted passage gets a 600 ms lime underline sweep |
| Token budget bar | Segments grow from left in selection order (`spring.snappy`, 60 ms apart); mandatory segments show lock icon on settle |
| Compare mode | Both bars animate in sync; a missing safety requirement row shakes once (4 px, 300 ms) and shows "Missing" — only if truly missing |
| Insufficient state | Calm entrance (fade 220 ms); missing items list staggers; no error shake |
| Buttons/chips | Hover lift 1 px, press scale 0.97 |
| Feedback submitted | Check icon draws (`pathLength`, 300 ms) + toast slides up |
| KPI tiles | Count-up 600 ms on first view (real values only) |

## 8. Accessibility

- WCAG 2.2 AA throughout; tested with axe and keyboard-only.
- Focus ring: 2 px `--interactive` + 2 px offset, never removed.
- Tap targets ≥ 44 × 44 px; spacing between targets ≥ 8 px (gloves).
- Live region announces triage stage changes and result status.
- All charts have a data table alternative.
- Reduced-motion and Field mode (light theme) available from settings and respected from OS preferences.

## 9. Responsive behaviour

| Breakpoint | Layout |
|---|---|
| < 640 px | Single column, bottom tab bar, bottom-sheet citations, steps at `body-lg` |
| 640–1024 px | Two columns where useful; sheet citations |
| > 1024 px | Sidebar + content + optional source panel |

## 10. Voice & content

- Plain, direct, imperative for steps: "Isolate the DC side. Wait 5 minutes for capacitors to discharge." (wait time only if the cited source says so).
- Never "AI-powered magic". Say what it does.
- Empty and error states explain what to do next.
- Numbers always carry their source.

## 11. Do / Don't

| Do | Don't |
|---|---|
| Put safety first and keep it visible | Collapse, fade late, or "typewriter" safety text |
| Use lime sparingly — one accent per view | Use lime for large text blocks or on light backgrounds |
| Label synthetic data | Show demo numbers as real results |
| Respect reduced motion | Add motion that can't be turned off |
| Animate real run traces | Animate a fabricated "win" for our method |
