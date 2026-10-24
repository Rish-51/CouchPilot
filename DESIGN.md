---
name: CouchPilot
description: Autonomous repository housekeeping and review workbench design system
colors:
  primary: "#5B2C6F"
  primary-hover: "#4A235A"
  primary-light: "#F3EEF6"
  secondary: "#1B4F72"
  secondary-hover: "#153E5B"
  secondary-light: "#EBF3F9"
  neutral-bg: "#F7F5F0"
  neutral-surface: "#FFFFFF"
  neutral-surface-subtle: "#FAFAF8"
  neutral-text: "#1F2A33"
  neutral-muted: "#55616B"
  neutral-border: "#E2DCCF"
  status-warning: "#E67E22"
  status-warning-bg: "#FDF2E9"
  status-pending: "#F4D03F"
  status-pending-bg: "#FEF9E7"
  status-danger: "#B83227"
  status-danger-bg: "#FCEBEA"
  diff-add: "#236B3E"
  diff-add-bg: "#EBF5EE"
  diff-del-bg: "#FCEBEA"
typography:
  display:
    fontFamily: "Outfit, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  headline:
    fontFamily: "Outfit, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Outfit, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Outfit, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
    fontSize: "0.85rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "normal"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  "2xl": "48px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.neutral-surface}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.neutral-surface}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-secondary:
    backgroundColor: "{colors.neutral-surface}"
    textColor: "{colors.neutral-text}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-marine:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.neutral-surface}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  chip-filter:
    backgroundColor: "{colors.neutral-bg}"
    textColor: "{colors.neutral-muted}"
    rounded: "{rounded.full}"
    padding: "4px 10px"
  chip-filter-active:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.neutral-surface}"
    rounded: "{rounded.full}"
    padding: "4px 10px"
  status-badge-completed:
    backgroundColor: "{colors.diff-add-bg}"
    textColor: "{colors.diff-add}"
    rounded: "{rounded.sm}"
    padding: "3px 8px"
  status-badge-partial:
    backgroundColor: "{colors.status-warning-bg}"
    textColor: "{colors.neutral-text}"
    rounded: "{rounded.sm}"
    padding: "3px 8px"
  status-badge-pending:
    backgroundColor: "{colors.status-pending-bg}"
    textColor: "{colors.neutral-text}"
    rounded: "{rounded.sm}"
    padding: "3px 8px"
  status-badge-failed:
    backgroundColor: "{colors.status-danger-bg}"
    textColor: "{colors.status-danger}"
    rounded: "{rounded.sm}"
    padding: "3px 8px"
---

# Design System: CouchPilot

## Overview

**Creative North Star: "The Calibrated Avionics Bench"**

CouchPilot is an autonomous repository housekeeping agent with a review workbench engineered for high-trust code verification. The aesthetic philosophy is rooted in the calm, unembellished clarity of a precision laboratory instrument: dense yet immediately scanable, restrained, and completely devoid of decorative marketing tropes such as gradient text, artificial glassmorphism, or ambient neon halos.

Every visual decision reflects the solemnity of automated code modification: maintainers and judges must verify that default branches were protected and that zero functional regressions were introduced. Grounded on an unbleached oat substrate (`#F7F5F0`), deep slate typography (`#1F2A33`), and hairline architectural dividers (`#E2DCCF`), the system directs attention solely toward AST verification guarantees, review branches, and syntax-highlighted diffs.

**Key Characteristics:**
- **Calm, High-Contrast Readability:** Natural oat ground with tinted charcoal body text preserves focus during deep technical diff audits.
- **Strict AST-Equivalence Transparency:** Verification status is treated as an immutable certificate of safety rather than an incidental badge.
- **Semantic Accent Discipline:** Interactive triggers, operational statuses, and diff additions operate under distinct, non-overlapping color roles.
- **Zero Decorative Noise:** Lucide SVG line icons with uniform 2px stroke width; strictly no raw emojis anywhere in the interface.

## Colors

The palette establishes an unambiguous separation between deliberate human command actions, active system states, and code verification outcomes.

### Primary
- **Imperial Plum** (`#5B2C6F`): The primary interactive accent. Reserved strictly for deliberate action triggers (such as the prominent Demo Run button), focused form controls, and active selection rings. Its intentional scarcity reinforces its salience.
- **Plum Hover** (`#4A235A`): Darkened interactive feedback state upon cursor hover.
- **Plum Light Tint** (`#F3EEF6`): Subtle container tint for high-priority command callouts.

### Secondary
- **Deep Marine** (`#1B4F72`): The secondary operational accent. Used for active navigation states, selected run indicators in the history feed, file selector tabs, and running status indicators.
- **Marine Hover** (`#153E5B`): Interactive feedback for secondary tab controls.
- **Marine Light Tint** (`#EBF3F9`): Soft background tint for active run cards and running state pills.

### Neutral
- **Warm Oat Ground** (`#F7F5F0`): The canonical page background. A calm, warm neutral canvas that reduces glare and fatigue.
- **Clean Surface** (`#FFFFFF`): Elevated container background for the metrics strip, feed cards, and diff panels.
- **Deep Slate** (`#1F2A33`): Primary text color. Tinted slate rather than harsh pure black (`#000000`).
- **Muted Slate** (`#55616B`): Secondary text for labels, timestamps, commit hashes, and helper copy.
- **Line Divider** (`#E2DCCF`): Crisp 1px hairline dividers separating panes, cards, and table rows.

### Functional / Status
- **Tangerine** (`#E67E22`, bg `#FDF2E9`): Partial run or warning status badge. Text is always rendered in Deep Slate (`#1F2A33`) for contrast compliance.
- **Butter** (`#F4D03F`, bg `#FEF9E7`): Pending or queued status badge. Text is always rendered in Deep Slate (`#1F2A33`).
- **Carmine Red** (`#B83227`, bg `#FCEBEA`): Failed runs, lint syntax errors, and diff deletion rows. Text on oat uses `#B83227`.
- **Diff Add Green** (`#236B3E`, bg `#EBF5EE`): Validated additions text and verified AST equivalence pass indicators.

### Named Rules
**The One Voice Rule.** Imperial Plum is reserved strictly for primary deliberate actions and focus rings, occupying ≤5% of screen surface area. Its rarity guarantees immediate visual hierarchy.

**The Contrast Invariant Rule.** White text is strictly forbidden on Tangerine, Butter, and Red backgrounds. Badges in these states must use Deep Slate (`#1F2A33`) text on pale tinted backgrounds to satisfy WCAG AA contrast ratios.

**The No-Gradient Rule.** Plum and Marine must never be blended into a gradient. Each represents an independent semantic state (Deliberate Action vs Navigational/Operational Focus).

## Typography

**Display & UI Font:** Outfit (with `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` fallback)  
**Code & Metrics Font:** JetBrains Mono (with `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace` fallback)  

**Character:** Outfit delivers clean, geometric sans-serif clarity for navigation and headings, while JetBrains Mono provides unambiguous tabular numbers, code diffs, and cryptographic commit hashes.

### Hierarchy
- **Display / H1** (600 weight, `1.75rem` / 26px, line-height 1.25, letter-spacing `-0.015em`): Surface title and primary workbench header.
- **Headline / H2** (600 weight, `1.25rem` / 19px, line-height 1.35, letter-spacing `-0.015em`): Section headings, modal titles, and panel division headers.
- **Title / H3** (600 weight, `1.05rem` / 16px, line-height 1.4, letter-spacing `-0.01em`): Card titles, feed item identifiers, and certificate headings.
- **Body** (400 weight, `15px` / 1rem, line-height 1.5): Standard paragraphs, descriptions, and audit commentary (measure capped at 65–75ch).
- **Label / Monospace** (500 weight, `0.85rem` / 13px, line-height 1.4, tabular-nums): Commit SHAs, branch names, diff line outputs, and tabular metrics.

### Named Rules
**The Monospace Honesty Rule.** Monospace typography is strictly reserved for code, AST nodes, git commit hashes, file paths, branch names, and tabular execution metrics. It must never be used as a decorative costume for general copy.

**The Tabular Numbers Rule.** All numerical metrics, token counters, and elapsed time durations must declare `font-variant-numeric: tabular-nums` to eliminate layout jitter during live updates.

## Layout

CouchPilot employs a **Unified Workbench** master-detail spatial model. A sticky 64px header anchors global navigation and the primary Demo Run trigger, bounded by a 1440px maximum viewport container.

The primary workspace is divided into an asymmetric two-column grid:
- **Run History Feed (Left Pane):** Fixed 380px sidebar housing real-time filter chips, live search box, and a scrollable card feed of historical housekeeping runs.
- **Active Run Workbench (Right Pane):** Flexible main stage displaying run identity, branch clipboard tools, the AST Equivalence Guarantee certificate card, file selector tabs, and the interactive diff viewer.
- **Spacing Rhythm:** Structured on an 8px base rhythm (`4px` xs, `8px` sm, `16px` md, `24px` lg, `32px` xl, `48px` 2xl).
- **Responsive Behavior:** Below 1024px, the workbench stacks vertically, preserving full horizontal scan width for syntax-highlighted diff hunks.

## Elevation & Depth

Depth is established primarily through **tonal surface layering** and crisp 1px hairline borders (`#E2DCCF`), rather than aggressive drop shadows. Surfaces rest quietly on the warm oat canvas; elevation occurs only when elements physically lift above the document plane.

### Shadow Vocabulary
- **Resting Card** (`box-shadow: 0 1px 3px rgba(31, 42, 51, 0.05), 0 1px 2px rgba(31, 42, 51, 0.03)`): Applied to white surface containers (metrics strip, feed cards, diff boxes).
- **Interactive Lift** (`box-shadow: 0 4px 12px rgba(31, 42, 51, 0.07), 0 2px 4px rgba(31, 42, 51, 0.04)`): Applied upon button hover or card focus.
- **Modal Overlay** (`box-shadow: 0 12px 28px rgba(31, 42, 51, 0.12), 0 4px 8px rgba(31, 42, 51, 0.06)`): Applied to the four-stage Demo Run progress modal over an ambient 3px backdrop blur.

### Named Rules
**The Zero-Halo Rule.** Soft colored glows and zero-blur hard block drop shadows are strictly prohibited. Shadows exist only to establish spatial elevation above the ground plane.

**The Hairline Discipline Rule.** Container borders must never exceed 1px. Thick decorative side-tab borders on list cards are strictly banned.

## Shapes

- **Radius Scale:**
  - Micro (`4px` / `--radius-sm`): Status badges, code tags, and commit pills.
  - Standard (`6px` / `--radius-md`): Buttons, search inputs, file tabs, and certificate cards.
  - Macro (`8px` / `--radius-lg`): Master workbench panels, metrics bar, and diff containers.
  - Full Pill (`9999px` / `--radius-full`): Filter chips and live service health indicators.
- **Form Language:** Clean rectilinear geometry softened by calibrated corners; interfaces feel engineered and robust rather than toy-like or rounded.

## Components

### Buttons
- **Shape:** Gently rounded rectangle (6px radius).
- **Primary (.btn-primary):** Background Imperial Plum (`#5B2C6F`), text white (`#FFFFFF`), padding `8px 16px`. Active state translates `1px` downward.
- **Secondary (.btn-secondary):** Background white (`#FFFFFF`), text Deep Slate (`#1F2A33`), border `1px solid #E2DCCF`. Hover applies `#F7F5F0`.
- **Marine Action (.btn-marine):** Background Deep Marine (`#1B4F72`), text white (`#FFFFFF`).

### Filter Chips
- **Shape:** Full pill (9999px radius).
- **Unselected:** Background `#F7F5F0`, text Muted Slate (`#55616B`), border `1px solid #E2DCCF`, padding `4px 10px`.
- **Active:** Background Deep Marine (`#1B4F72`), text white (`#FFFFFF`).

### Status Badges
- **Shape:** Compact pill (4px radius, padding `3px 8px`, uppercase, `0.75rem`).
- **Completed:** Background `#EBF5EE`, text `#236B3E`, inline check SVG icon.
- **Partial / Warning:** Background `#FDF2E9`, text `#1F2A33` (contrast invariant).
- **Pending / Queued:** Background `#FEF9E7`, text `#1F2A33` (contrast invariant).
- **Failed:** Background `#FCEBEA`, text `#B83227`, inline cross SVG icon.
- **Running:** Background `#EBF3F9`, text `#1B4F72`, pulsing status dot.

### AST Equivalence Guarantee Certificate
- **Shape:** 6px radius, background `#FAFAF7`, border `1px solid #E2DCCF`, padding `16px`.
- **Anatomy:** Verified shield icon (36px circular badge), invariant certification title, stripped AST equivalence explanation, and 4-point verification checklist.

### File Selector Tabs
- **Shape:** Borderless top tabs with a 2px active bottom border in Deep Marine (`#1B4F72`). Includes target count badge (`patched/detected`).

### Interactive Diff Viewer
- **Container:** White surface, 1px border (`#E2DCCF`), 6px radius, Pygments syntax highlighting matching CouchPilot tokens.
- **Additions:** Color `#236B3E`, background `#EBF5EE`.
- **Deletions:** Color `#B83227`, background `#FCEBEA`.
- **Hunk Headers:** Color `#1B4F72`, subtle tint background.

### Demo Run Stepper Modal
- **Container:** Max-width 540px, 8px radius, white surface, elevated shadow.
- **Pipeline Stages:** Four sequential steps with visual pulse on active state and green checkmark on completion.

## Do's and Don'ts

### Do:
- **Do** use Outfit for UI interface copy and JetBrains Mono for commit hashes, paths, and diffs.
- **Do** enforce WCAG AA contrast standards by using Deep Slate text on low-contrast status backgrounds (Tangerine and Butter).
- **Do** render icons using Lucide SVG line icons with a consistent 2px stroke width.
- **Do** format diff additions in `#236B3E` with `#EBF5EE` background, and deletions in `#B83227` with `#FCEBEA` background.
- **Do** display the AST Equivalence Guarantee prominently on all diff inspection views.

### Don't:
- **Don't** use raw emojis anywhere in the UI, templates, logs, CLI output, or commit messages.
- **Don't** combine Imperial Plum and Deep Marine into a gradient.
- **Don't** use colored border-left accents thicker than 1px on list cards or table rows.
- **Don't** put white text on yellow, orange, or red badges.
- **Don't** add decorative blur, glow halos, or animations beyond functional state transitions.
