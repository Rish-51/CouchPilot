# CouchPilot Product Specification

## 1. Product Overview & Purpose
CouchPilot is an autonomous repository housekeeping agent with a web review dashboard built for the Hacktoberfest DEV Challenge. It automates docstring generation, parameter/return type annotation, and repository housekeeping on messy Python repositories without risking default-branch corruption or introducing functional regressions.

## 2. Target Audience
1. **Hackathon Judges:** Rapid 30-second evaluation flow. Must work with zero local setup via one-click Demo Run on Render, displaying realistic metrics, syntax-highlighted diffs, and Sentry distributed traces.
2. **Open-Source Maintainers:** High trust requirement. Need unambiguous, AST-equivalence guaranteed diffs committed only to isolated review branches (`couchpilot/tidy-YYYYMMDD`), never touching the default branch.

## 3. Brand Voice & Aesthetic
- **Voice:** Calm, precise, reliable, transparent.
- **Aesthetic:** Clean, minimalist developer utility. Calm, dense-but-readable, trustworthy. This is a review tool, not a marketing page. No decorative gradients, glows, or motion beyond functional transitions.
- **Tone:** Professional, objective, developer-first.

## 4. Design System Constraints & Palette Tokens (Verbatim)

### Color Tokens
- `--oat`: `#F7F5F0` (Page background)
- `--slate`: `#1F2A33` (Body text, tinted, not pure black)
- `--slate-muted`: `#55616B` (Secondary text)
- `--line`: `#E2DCCF` (Borders and dividers)
- `--plum`: `#5B2C6F` (Primary interactive accent: buttons, links, focus ring)
- `--marine`: `#1B4F72` (Secondary interactive accent: tabs, selected state, running status)
- `--tangerine`: `#E67E22` (Status badge: warning, partial, retried)
- `--butter`: `#F4D03F` (Status badge: pending, queued)
- `--red`: `#B83227` (Lint failures, deletions, text on oat)
- `--diff-add`: `#236B3E` (Diff additions text)
- `--diff-add-bg`: `#EBF5EE` (Diff additions background)
- `--diff-del-bg`: `#FCEBEA` (Diff deletions background)

### Contrast & Typography Rules
- White text is allowed on `--plum` and `--marine`.
- **Never put white text on tangerine, butter or red** (contrast is too low for small text). Use `--slate` text on those badges, or a pale tint of the color as the background with a darker text shade.
- Red is for icons, borders, and tinted deletion rows. For red text on oat, use `#B83227`.
- Do not combine plum and marine in a gradient.
- **Icons:** Lucide SVG via CDN only. **No raw emojis anywhere**: UI, templates, logs, CLI output, commit messages, README.
- **Typography:**
  - UI Face: **Outfit** (`font-sans`)
  - Monospace: **JetBrains Mono** (`font-mono`)
- **Syntax Highlighting:** Server-side rendered with Pygments using a custom style mapping strictly to the tokens above.
