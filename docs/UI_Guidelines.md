# UI Guidelines

## Visual identity
Dark Industrial + Warm Metallic. SCADA/MES layout density (Siemens WinCC,
Ignition, FactoryTalk as layout inspiration only, not branding) built
around forged steel, brass, and furnace-glow accents rather than a
corporate blue/gray palette.

## Design tokens
Single source of truth: `app/styles/theme.css`. Never hardcode colors,
fonts, or spacing in a page or component — add a token there first.

- Backgrounds: `--bg-primary`, `--bg-panel`, `--bg-panel-raised`, `--bg-inset`
- Accent (interaction only, never status): `--accent-gold`, `--accent-bronze`, `--accent-glow`
- Status (semantic only, never decorative): `--status-running` (green),
  `--status-idle` (amber), `--status-error` (red), `--status-info` (cyan)
- Fonts: Inter (body), Chakra Petch (headings/nav), JetBrains Mono (all numeric readouts)

Gold and status-amber are visually close but never interchangeable — gold
never appears in a status badge, amber never appears on an interactive element.

## Component library
`app/components/`: `kpi_card`, `status_badge`, `machine_tile`,
`stage_progress`, `top_bar`, `coming_soon`. Pages compose these instead
of writing their own markup.

## Charts
Plotly, transparent background, palette matched to the theme tokens
(gold/bronze/green/red/cyan), max 3 series per chart.

## Motion
150-200ms ease-out transitions. The only looping animation is a slow
pulse on `--accent-glow` elements (actively-processing states).
`prefers-reduced-motion` respected.

## Error/empty/loading states
- Errors: `st.error()` with a plain-language message, never a raw
  traceback (enforced globally in `app/main.py`).
- Empty states: `st.info()` explaining what to do next, not just "no data".
- Loading: `st.spinner()` around every DB write and AI inference call.
- Confirmations: `st.dialog()` for destructive/edit actions in Admin.

## Navigation
Auth-gated `st.navigation`, role-filtered. Factory Overview is the
landing page — situational awareness before action.
