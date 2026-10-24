# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Hackathon Judges:** Rapid 30-second evaluation flow. Evaluates the project with zero local setup via a one-click Demo Run on Render, reviewing realistic metrics, syntax-highlighted diffs, and distributed traces.
- **Open-Source Maintainers:** High trust requirement. Needs transparent, AST-equivalence guaranteed diffs committed only to isolated review branches (`couchpilot/tidy-YYYYMMDD`), never touching the default branch.

## Product Purpose

CouchPilot is an autonomous repository housekeeping agent with a web review dashboard built for the Hacktoberfest DEV Challenge. It automates docstring generation, parameter/return type annotation, and repository housekeeping on Python codebases without risking default-branch corruption or introducing functional regressions.

## Positioning

Unlike conventional code generation tools that rewrite logic, CouchPilot pairs deterministic static analysis (tree-sitter) with open-weight Gemma models strictly for docstrings and type hints. Every modification is verified by an AST-equivalence engine (stripping docs/annotations and asserting identical syntax trees), with changes isolated to review branches and reported to a dedicated dashboard.

## Operating Context

- **Web Review Dashboard (`app/web/`):** Hosted on Render (`requirements-web.txt`, FastAPI, Uvicorn, Jinja2, Pygments). Uses SQLite (`couchpilot.db`) seeded from fixtures on first boot. Accepts report ingestion via `POST /api/reports` authenticated with `X-CouchPilot-Key`. Provides a one-click demo trigger (`POST /api/demo-trigger`) with replay and live modes.
- **Housekeeping Engine (`app/core/`, `app/workflows/`, `cli.py`):** Runs on local environments with Temporal orchestration and CLI (`couchpilot scan`, `couchpilot tidy`). Operates in isolated Git worktrees, uses tree-sitter for target detection, OpenAI-compatible SDK for Gemma generation, and Ruff subprocesses for linting.

## Capabilities and Constraints

- **Deterministic Target Discovery:** Tree-sitter AST parsing finds missing docstrings, missing parameter types, and missing return annotations.
- **Safe Patch Application:** Edits applied bottom-to-top by byte offset to prevent offset drift; indentation is extracted directly from target function/class bodies.
- **AST Equivalence Guarantee:** Stdlib `ast` parses original and patched code, stripping docstrings and type annotations to verify absolute AST identity. Files failing equivalence or Ruff checks are dropped from the commit and logged.
- **Default Branch Protection:** The default branch is never committed to or pushed. Review branches are named `couchpilot/tidy-YYYYMMDD` (with numeric suffixes for collisions). Push is opt-in (`--push`).
- **Telemetry & Tracing:** Sentry integration with distributed traces; missing DSN fails silently without disrupting execution.
- **No Emojis:** Lucide SVG CDN icons only. No raw emojis in UI, templates, logs, CLI output, commit messages, or README.

## Brand Commitments

- **Voice & Tone:** Calm, precise, reliable, transparent. Minimalist developer utility; no decorative gradients, glows, or unfunctional motion.
- **Color Tokens:**
  - Page Background: `--oat` (`#F7F5F0`)
  - Body Text: `--slate` (`#1F2A33`)
  - Secondary Text: `--slate-muted` (`#55616B`)
  - Borders & Dividers: `--line` (`#E2DCCF`)
  - Primary Accent: `--plum` (`#5B2C6F`)
  - Secondary Accent: `--marine` (`#1B4F72`)
  - Warning/Partial Badge: `--tangerine` (`#E67E22`)
  - Pending/Queued Badge: `--butter` (`#F4D03F`)
  - Lint Failure/Deletion Text: `--red` (`#B83227`)
  - Diff Additions: `--diff-add` (`#236B3E`), bg `--diff-add-bg` (`#EBF5EE`)
  - Diff Deletions: bg `--diff-del-bg` (`#FCEBEA`)
- **Contrast & Token Invariants:**
  - White text allowed on `--plum` and `--marine`.
  - Never put white text on `--tangerine`, `--butter`, or `--red`.
  - Do not combine plum and marine in a gradient.
- **Typography:**
  - UI Sans: Outfit (`font-sans`)
  - Code Monospace: JetBrains Mono (`font-mono`)

## Evidence on Hand

- `couchpilot-plan-prompt.md`: Comprehensive product architecture and execution specification.
- `sample_repo/`: Purposely messy Python repository fixture for testing and replay runs.
- `render.yaml`: Infrastructure-as-code Blueprint for deploying the review dashboard.
- `app/web/`: Existing FastAPI dashboard templates and routes.

## Product Principles

1. **Guaranteed AST Equivalence:** Functional code is immutable to AI modifications; generative output is restricted strictly to docstrings and type annotations verified by AST comparison.
2. **Zero-Blast-Radius Isolation:** Default branches are never modified; all agent activities execute in isolated Git worktrees and commit only to review branches.
3. **Deterministic Discovery over Generative Guessing:** Static AST parsing identifies targets and missing slots before the LLM is ever called.
4. **Frictionless Trust & Verification:** Enable judges and maintainers to inspect diffs, verify AST checks, and audit Sentry traces in under 30 seconds with zero setup.

## Accessibility & Inclusion

- Maintain WCAG AA contrast standards across all badges and state indicators, strictly avoiding light text on low-contrast yellow/orange badges.
- Accessible code and diff viewers using semantic HTML elements and clear color plus typography indicators for additions and deletions.
