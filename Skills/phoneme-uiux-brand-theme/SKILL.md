---
name: phoneme-uiux-brand-theme
description: Establish a Phoneme product's brand theme (name, tagline, palette, logo lockup rules) and build its UI/UX mockups as a persisted HTML Artifact using the shared browser-chrome mockup system — the single source of truth both other SDLC documents reference for brand and screens.
---

# Phoneme UI/UX & Brand Theme Builder

Stage 3 of Phoneme's Concept-to-Launch SDLC framework, and the single place brand identity gets decided. `phoneme-brd-prd` and `phoneme-techdesign` both defer to whatever this skill has established for a product — brand and visual design are not re-decided inside those document skills.

## Part A — Brand Theme

Before any mockup screen is built, confirm and record:
1. **Product name & tagline** — exactly as the user has finalized them (never invent, never carry over from a previous Phoneme product).
2. **Palette** — primary/accent color + a dark variant + a light tint, an ink/charcoal neutral, a background, a border, text at 2–3 opacity levels, and success/warning/danger/info pairs. Get hex values from the user's brand sheet/reference image; do not invent colors.
3. **Logo lockup rules** — how the wordmark splits/colors (e.g. a two-part name where each part takes a different palette color), and whether that split treatment holds on both light and dark backgrounds or simplifies to a single solid color on dark surfaces for legibility (a deliberate, documented exception — not an inconsistency).
4. **Legal vs. brand separation** — "Phoneme Solutions Pvt. Ltd." (or the applicable legal entity) appears only as the submitting/legal company in document footers and Settings screens (e.g. sidebar company name), never merged into the product's own brand lockup or tagline.

Record this once per product (e.g. as a short "Brand Theme" note alongside the mockup file) so `phoneme-brd-prd` and `phoneme-techdesign` cover pages, and any future mockup screens, all pull from the same values instead of drifting.

## Part B — UI/UX Mockup System

Build every screen in the confirmed flow as sections in one single-file HTML page, published as a persisted Artifact (load `artifact-design` first for the general page contract; this skill supplies the Phoneme-specific component system on top of it).

**Page structure**: `<title>` + Google Fonts (display font for headings, a body sans, a mono for tags/labels); CSS custom properties on `:root` for the confirmed palette (Part A); an `.intro` block (brand lockup + tagline, page title, and a `.stepnav` of pill-shaped anchor links numbered to match the BRD/PRD's functional modules, e.g. `<span>01</span>JD Creation`, so the mockup stays traceable to the requirements doc); one `.section` per screen with a `.step-tag` (STEP N or STEP N.M for a sub-screen), an `<h2>`, a one-sentence `.section-sub`, then a `.frame` (browser-chrome wrapper: three dots + fake URL bar) holding the actual mockup markup.

**Reusable component classes**: `.card`, `.field` (label+input), `.btn`/`.btn-primary`/`.btn-ghost`/`.btn-dark`, `.tabs`/`.tab`, `.pill` + success/warning/danger/info/neutral variants, `table`/`th`/`td`, `.appshell`/`.sidebar`/`.navitem`/`.topbar`/`.main`/`.content` for authenticated app screens, `.kanban`/`.kcol`/`.kcard` for pipeline/board views, `.toggle-row`/`.tswitch` for settings toggles, `.email-head`/`.email-body` for email mockups, `.upload-box`, `.notebox` for callouts, `.stepper`/`.stepdot` for multi-step user-facing flows.

## Critical layout guardrail (learned the hard way)
`.frame` normally carries `min-width: 1000px` so a single wide screen scrolls horizontally within its own `.frame-scroll` wrapper without dragging the whole page sideways. **The moment two or more `.frame` elements sit side by side in a `.grid2`/`.grid3` row** (e.g. an email next to a scheduling form, or three emails in a row), that min-width multiplies and blows the row past the page — content visibly shifts right or gets clipped, including in PDF export. Fix: scope an override — `.grid2 > .frame, .grid3 > .frame { min-width: 0 }` — for any frame placed inside a multi-column grid instead of a `.frame-scroll` single-column wrapper. Also always set `body { overflow-x: hidden }` as a page-wide safety net so nothing can force horizontal scroll of the whole page — only vertical scroll should ever be possible.

## Workflow
1. Confirm/record the Brand Theme (Part A) before writing any HTML — check project memory or the repo for an existing brand sheet first.
2. Build the page section by section, reusing the component classes above rather than inventing ad hoc styles per screen, and numbering sections to match the BRD/PRD.
3. Publish via the Artifact tool, republishing to the same URL on later revisions for the same product rather than creating a duplicate.
4. If asked for a PDF export: render with headless Chromium (Playwright) at a viewport/page width comfortably wider than the widest `.frame` (e.g. 1400–1450px), `printBackground: true`; verify page count and spot-check pages as PNG before delivering — specifically any page with a multi-column grid section, for the overflow bug above.
5. Deliver via SendUserFile and, if a connected repo has a `UI-UX/` folder, commit the mockup/PDF there.
