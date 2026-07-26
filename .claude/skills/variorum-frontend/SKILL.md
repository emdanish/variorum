---
name: variorum-frontend
description: Use when working on the Variorum frontend — Next.js pages/components, React architecture, strict TypeScript, the API client, or anything under frontend/src. Covers component design, data fetching, and frontend conventions.
---

# Variorum frontend conventions

Stack: **Next.js 15 (App Router) · React 19 · TypeScript (strict) · Tailwind v3 · shadcn-style components**. All free/open-source.

## Structure
- `frontend/src/app/` — App Router routes (`page.tsx`, `layout.tsx`). Dark theme set on `<html class="dark">`.
- `frontend/src/components/` — feature components; `components/ui/` holds primitives (`button.tsx`, `card.tsx`).
- `frontend/src/lib/api.ts` — the single typed API client. `frontend/src/lib/utils.ts` — `cn()` classnames helper.

## TypeScript
- Strict mode is on; **no `any`**. Type every exported function/component prop.
- Mirror backend response shapes as `interface`s in `lib/api.ts` (keep in sync with `backend/app/schemas`).
- Prefer `type`/`interface` over inline object types for anything reused.

## Components
- Server Components by default; add `"use client"` only when you need state/effects/handlers.
- Keep components small and single-purpose; reuse `ui/` primitives; compose with `cn()`.
- Every async view handles four states: **loading, error, empty, ready**.

## Data fetching
- Always go through `lib/api.ts`. It uses `credentials: "include"` (session cookie) and `cache: "no-store"`, and throws `ApiError` with a status code.
- Handle `ApiError` (esp. 401 → signed-out) explicitly. Poll with `setInterval` only while work is in flight (see the dashboard).

## Hard rules
- **Never run `next build` while `next dev` is running** — it clobbers the shared `.next` dir and 500s the dev server. To verify a change: `npx tsc --noEmit` + `npm run lint`, and rely on dev hot-reload.
- Keep the app usable with no backend/AI configured (status cards, graceful fallbacks).

See also the `variorum-ui-ux` skill for the visual design language.
