---
name: SpectraSense
description: "Carbon-based system for a technical assessment tool: Cool Gray canvas, white layers, charcoal ink, one blue accent, flat square geometry, IBM Plex. The visible spectrum is the single decorative element."
basis: "Adapted from the IBM / Carbon DESIGN.md in VoltAgent/awesome-design-md (Carbon Design System, Apache-2.0)."
tokens: src/app/globals.css
---

# SpectraSense design system

SpectraSense drafts first technical assessments that an Art Fiber Systems expert reviews and sends to a customer.
The interface has to read as careful and engineered, not as marketing. Carbon gives exactly that: flat square
geometry, hairline borders, light-weight display type and one accent colour.

## Tokens (source of truth: `src/app/globals.css`)

| Role | Light | Dark | Use |
|---|---|---|---|
| `bg` | #f2f4f8 (Cool Gray 10) | #121619 | Page canvas: a cool, slightly blue-tinted gray, not white |
| `panel` | #ffffff | #21272a | Layer 1: cards, tiles, the conversation panel lift off the canvas |
| `panel-2` | #e4e8ee | #343a3f | Layer 2: table heads, badges |
| `line` | #dde1e6 | #343a3f | 1px hairlines |
| `line-strong` | #878d96 | #878d96 | Input and control borders (3:1) |
| `ink` / `ink-2` / `ink-3` | #121619 / #4d5358 / #575e66 | #f2f4f8 / #c1c7cd / #a2a9b0 | Text: primary, secondary, muted |
| `accent` | #0f62fe | #0f62fe | Primary buttons, links, focus, active nav |
| `ok` / `warn` / `bad` | #0e6027 / #684e00 / #a2191f | #42be65 / #f1c21b / #ff8389 | Status text and icons (Carbon 70-grade in light, for 6:1+) |
| `violet` | #6929c4 | #be95ff | Organiser reference material only |
| `hero*` | #121619, #f2f4f8, #c1c7cd | same | The dark hero stage the intro footage plays on |
| `inverse*` | #121619, #ffffff, #c1c7cd | same | Footer |

Every text colour is measured at 4.5:1 or better on every surface it sits on; control borders at 3:1.
Status is never shown by colour alone: it always has an icon or a word.

## Typography

- IBM Plex Sans for UI (300 display, 400 body, 600 emphasis), body tracking 0.16px.
- IBM Plex Serif for the report's running text (long-form reading), IBM Plex Mono for step numbers and code.
- Display headlines use weight 300 (`font-light`); never bold a display headline.
- Minimum text size 12px; captions 12px, body 14–16px, lead 18px.

## Geometry and depth

- Corners are 0px everywhere (Tailwind radius tokens are set to 0). Pills and status dots keep `rounded-full`.
- Depth comes from surface change and 1px hairlines, never drop shadows. Functional overlays (tooltips) may use a shadow.
- No gradients, glows or blur, except the spectrum rule (`.spectrum-line`): the single decorative element, because it is what the product measures.

## Components

- Primary button: `bg-accent text-white px-4 py-3 text-sm`, square, arrow icon right. Secondary: 1px accent border, accent text.
- Inputs: `border-line-strong`, focus = 2px accent outline (global `:focus-visible`).
- Cards and grids: hairline grid (`border-line`), no shadow; evidence numbers in `font-light` 48px.
- Hero: full-screen (viewport height below the header). The intro footage is the background, cropped to cover, played at the display refresh rate with continuous cross-fades between frames; a left-to-right scrim (solid under the text, clear by 62% width) and a bottom fade keep text readable while the probe stays bright. First frame doubles as a CSS poster; reduced motion shows a still frame.
- Navigation: solid canvas bar, 1px bottom hairline, 2px accent underline on the current page.
- Footer: `bg-inverse`, wordmark, product links, "© year SpectraSense. All rights reserved." and the expert-review disclaimer.
- Motion: short fade/rise reveals and the number count-up; both respect `prefers-reduced-motion`. Server-rendered values are final values.

## Component libraries

- **shadcn/ui Button** (`src/components/ui/button.tsx`): all action buttons. Variants are mapped onto the tokens above:
  `default` (primary), `secondary` (charcoal), `outline` (tertiary), `ghost`, `link`, `inverse` (on accent bands); sizes 32 / 40 / 48 px.
  Links styled as buttons use `asChild`.
- **motion-primitives** (MIT, `src/components/motion-primitives/`, pinned to commit 120f64f): only functional motion —
  `AnimatedBackground` (nav hover, report-version tabs), `Disclosure` (trace steps), `TextShimmer` + `BorderTrail` (the
  pending assessment), `AnimatedNumber` (score count-up), `ScrollProgress` (report reading progress). Glow, tilt, spotlight
  and morphing effects are not used: they contradict the flat system.
- `MotionProvider` sets `reducedMotion="user"`; shimmer and trail render static when motion is reduced.

## Copy

- Sentence case, plain and specific: say what the assessment does (facts, unknowns, cited methods, premise checks, first experiment).
- No unsupported claims: numbers on the site come from the last saved evaluation run, never written by hand.
- Each page has a unique title and description (`metadata`), one `h1`, and sequential headings.
