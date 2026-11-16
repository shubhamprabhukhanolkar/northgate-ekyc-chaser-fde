---
name: SME Corporate Banking Theme
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#434655'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#824500'
  on-tertiary: '#ffffff'
  tertiary-container: '#a65900'
  on-tertiary-container: '#ffede1'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#ffdcc3'
  tertiary-fixed-dim: '#ffb77d'
  on-tertiary-fixed: '#2f1500'
  on-tertiary-fixed-variant: '#6e3900'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.03em
  display-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.025em
  headline-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  mono-lg:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.02em
  mono-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: -0.01em
  mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

The design system projects institutional authority, financial precision, and effortless executive clarity. Engineered specifically for high-growth enterprises and mid-market CFOs, the visual language avoids both bureaucratic rigidity and consumer-fintech novelty. Instead, it embodies quiet confidence: immaculate white surfaces, razor-sharp hairline borders, luminous brand accents, and expansive negative space.

The aesthetic fuses **Modern Corporate Realism** with **Swiss Precision**:
- **Purity & Polish**: High-contrast, pristine white planes floating over warm neutral bases eliminate visual friction during complex fiscal workflows (wire transfers, FX hedging, payroll disbursement).
- **Executive Restraint**: Color is applied strictly with semantic intent. The interface relies on deliberate typographic hierarchy and precise spatial cadences rather than decorative flourishes.
- **Micro-tactility**: Interactive elements feature microscopic transitions, subtle interior borders, and diffused ambient shadows that mimic high-grade archival cardstock.

## Colors

The palette is tuned for day-long analytical durability, balancing high legibility against low optical strain.

### Palette Application
- **Canvas Base**: `#F8FAFC` provides a warm, grounded foundation that prevents pure-white eye fatigue while allowing foreground containers to pop cleanly.
- **Card & Sheet Surfaces**: `#FFFFFF` pure white, delineated exclusively by `#E2E8F0` hairline strokes.
- **Primary Accent (Trust Cobalt - `#2563EB`)**: Anchors primary conversion points, active tab rules, and primary state indicators. Pair with `#EFF6FF` for subtle hover washes and active badge fills.
- **Positive / Verified (Teal Emerald - `#0D9488`)**: Denotes cleared transactions, verified KYC/AML statuses, and credit liquidity. Paired with `#ECFDF5`.
- **Warning / Pending (Amber - `#D97706`)**: Reserved for unverified beneficiaries, expiring credit lines, and pending approvals. Paired with `#FFFBEB`.
- **Alert / Overdue (Rose Coral - `#E11D48`)**: Strict semantic indicator for payment rejections, compliance alerts, and overdrawn facilities. Paired with `#FFF1F2`.
- **Text & Structure**: Headlines in Deep Slate (`#0F172A`), body copy in Controlled Slate (`#475569`), secondary metadata in `#64748B`, and disabled text in `#94A3B8`.

## Typography

The typographic hierarchy implements three distinct typefaces to separate editorial authority, scanning comfort, and quantitative data:
1. **Plus Jakarta Sans** governs major headings, module headers, and account balance totals, offering a contemporary geometric personality with humanized terminal apertures.
2. **Inter** handles narrative copy, form controls, and multi-row tables, ensuring maximum legibility at compact scales across diverse viewport resolutions.
3. **JetBrains Mono** is enforced across all financial amounts, SWIFT/IBAN identifiers, timestamps, transfer IDs, and ledger outputs. It preserves character alignment across comparative balance tables.

All numeric monetary entries must use tabular figures (`font-variant-numeric: tabular-nums`) to align decimal points vertically across data grids.

## Layout & Spacing

The interface employs a responsive 12-column fluid grid system bounded by an executive maximum content width of `1600px`. Generous internal padding prevents density-induced errors during rapid corporate transactions.

### Spatial Framework
- **Desktop (1280px+)**: Multi-pane layout consisting of a fixed 280px left rail, a primary 12-column workspace with `1.5rem` (24px) gutters, and a consistent `2rem` (32px) global screen margin.
- **Tablet (768px - 1279px)**: Left rail collapses into an icon-rail (72px) or off-canvas drawer. Grid shifts to 8 columns with `1rem` (16px) gutters and `1.5rem` (24px) margins.
- **Mobile (< 768px)**: Single-column stack with dynamic bottom navigation sheet. Canvas margins tighten to `1rem` (16px). Complex data tables automatically expose card-based views or explicit horizontal scroll views.

Inner card spacing standardizes strictly between `1.5rem` (24px) and `2rem` (32px) to sustain the signature Northgate airiness.

## Elevation & Depth

Visual hierarchy uses a refined dual-layer depth model composed of crisp physical outlines paired with soft optical diffusion. Skeuomorphic heavy drops are strictly avoided.

### Surface Elevation Levels
- **Level 0 (App Canvas)**: Surface background `#F8FAFC`. Completely flat with zero elevation.
- **Level 1 (Card & Module Layer)**: Pure white `#FFFFFF` surface accompanied by a hairline border (`1px solid #E2E8F0`) and dual-tier micro-shadow: `0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 10px 15px -3px rgba(0, 0, 0, 0.04)`.
- **Level 2 (Dropdowns & Popovers)**: Pure white `#FFFFFF` surface with hairline border (`1px solid #E2E8F0`) and elevated shadow: `0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 20px 25px -5px rgba(0, 0, 0, 0.08)`.
- **Level 3 (Modal Windows & Drawers)**: Pure white `#FFFFFF` surface framed by `#E2E8F0`, floating over an ambient backdrop dimming tint (`rgba(15, 23, 42, 0.40)` with `backdrop-filter: blur(4px)`). Shadow: `0 25px 50px -12px rgba(15, 23, 42, 0.18)`.

## Shapes

The design system maintains a refined balance between architectural solidity and approachable modern software design.

### Corner Radius System
- **Cards & Primary Modules**: Formed with large, generous radii (`20px` to `24px`) to create an inviting, modular organization of institutional widgets.
- **Nested Components & Input Fields**: Scaled down to `8px` (`rounded-md`) to `10px` for structured, crisp form boundaries.
- **Status Badges, Metrics Tags & Micro-Pills**: Fully rounded pill shapes (`9999px`) to immediately set status chips apart from actionable rectangular buttons.

## Components

### Buttons & Interactive Controls
- **Primary Button**: Deep Cobalt (`#2563EB`) background, white (`#FFFFFF`) bold label, 0.5rem (8px) radius, 12px 20px padding. Hover: `#1D4ED8` with subtle transform lift (`translateY(-1px)`). Focus: 2px offset ring in `#93C5FD`.
- **Secondary / Outline Button**: Pure white `#FFFFFF` background, hairline border (`1px solid #E2E8F0`), text in Slate-900 (`#0F172A`). Hover: `#F8FAFC` surface with border `#CBD5E1`.
- **Ghost Action**: Transparent background, text `#475569`, hover: `#F1F5F9` with text `#0F172A`.

### Status Badges & Chips
- Fully pill-shaped (`9999px`) with padding of `4px 12px`. Typographic scale: `mono-sm` or `body-sm` (font weight 600).
- **Verified / Settled**: Mint background `#ECFDF5`, text `#065F46`, paired with an optional 6px circular dot indicator in `#0D9488`.
- **Pending / Action Required**: Amber background `#FFFBEB`, text `#92400E`, with `#D97706` indicator.
- **Rejected / Alert**: Soft rose background `#FFF1F2`, text `#9F1239`, with `#E11D48` indicator.
- **Neutral / Informational**: Slate background `#F1F5F9`, text `#334155`.

### Data Cards & Financial Modules
- Built on pure `#FFFFFF` backdrops with explicit `24px` internal padding, `20px` corner radii, and `#E2E8F0` hairline borders.
- Cards must prioritize data scannability: the top row contains title and metadata actions, the middle showcases large hero metrics in JetBrains Mono or Plus Jakarta Sans Display, and the footer anchors inline micro-charts or comparative percentage tags.

### Inputs & Form Elements
- **Text Inputs**: Height 44px, background `#FFFFFF`, border `1px solid #E2E8F0`, radius `8px`, typography `body-md` in `#0F172A`. Placeholder text in `#94A3B8`. Active focus triggers border `#2563EB` and box-shadow `0 0 0 3px rgba(37, 99, 235, 0.12)`.
- **Monetary Inputs**: Accompanied by fixed prefix currency badges (`USD`, `EUR`, `GBP`) formatted in JetBrains Mono with `#64748B` neutral coloring.

### Selection Controls (Checkboxes & Radios)
- Checkboxes: 18x18px, 4px border radius, `#E2E8F0` border. Selected state transitions to `#2563EB` fill with a crisp white check icon.
- Radios: 18x18px circle, `#E2E8F0` stroke; selected state renders an outer `#2563EB` ring with a 6px centered inner circle.

### Enterprise Data Tables
- Header cells: Uppercase `mono-sm` in `#64748B`, height 44px, background `#F8FAFC`, bottom border `1px solid #E2E8F0`.
- Data rows: Height 56px, background `#FFFFFF`, bottom border `1px solid #F1F5F9`. Hover state shifts row background to `#F8FAFC`. Financial amounts align strictly to the right in `mono-md`.