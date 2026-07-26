---
name: variorum-ui-ux
description: Use when designing or styling Variorum UI — dashboard layouts, components, colors, spacing, badges, accessibility, or responsive behavior. Defines the developer-tool visual language (Linear / Vercel / GitHub / Stripe).
---

# Variorum UI/UX design language

Target feel: **Linear · Vercel · GitHub · Stripe Dashboard** — minimal, precise, high-contrast, dark-first, calm. Restraint over decoration.

## Design tokens
- Colors are CSS variables in `frontend/src/app/globals.css` (light + dark), consumed as `hsl(var(--token))` via the Tailwind theme: `--background`, `--foreground`, `--muted(-foreground)`, `--card`, `--border`, `--primary`, `--accent`, `--ring`.
- Never hardcode hex in components — use the semantic tokens so light/dark both work.
- Radius is small/sharp (`--radius: 0.5rem`). Mono font for code, paths, and identifiers.

## Patterns
- **Layout:** centered `max-w-6xl` container, generous padding (`px-6 py-10`), vertical rhythm via `space-y-*`.
- **Cards** (`ui/card.tsx`) group everything: title + description header, content body.
- **Status** is shown with a small colored icon/badge, never color alone: emerald = ok, amber = warning/incomplete, red = error, blue = in-progress, muted = neutral. Always pair with text.
- **Buttons** (`ui/button.tsx`, cva variants: default/outline/ghost; sizes sm/default/lg) with icons from `lucide-react`.

## Accessibility
- Semantic HTML (`<header>`, `<main>`, `<button>`, real `<a>`); label inputs.
- Keyboard: inputs submit on Enter; interactive elements are focusable with visible `focus-visible:ring-2 ring-ring`.
- Sufficient contrast in both themes; don't rely on color as the only signal.

## Responsive
- Mobile-first Tailwind; grids collapse (`grid gap-4 sm:grid-cols-3`); wrap toolbars with `flex-wrap`.
- The page body must never scroll horizontally — put wide content (tables, diffs) in an `overflow-x-auto` container.

## Related built-in skills
- `artifact-design` — for standalone shareable HTML artifacts.
- `dataviz` — before building any chart/graph/dashboard visualization.
