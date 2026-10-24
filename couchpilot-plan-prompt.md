# CouchPilot: Architecture and Implementation Plan Request

You are a staff-level full-stack and AI systems architect. Produce a concrete, phased implementation plan for **CouchPilot**, an autonomous repository housekeeping agent with a web review dashboard, built for the Hacktoberfest DEV Challenge.

**Do not write application code yet.** Output the plan, list open questions (maximum 5), then stop and wait for my explicit confirmation before starting Phase 1\.

---

## 1\. Product summary

CouchPilot takes a messy Python repository and:

1. Finds undocumented or unannotated functions, classes and methods using deterministic static analysis (tree-sitter), never the LLM.  
2. Asks an open-weight Gemma model to generate docstrings, type hints and README updates for only those targets.  
3. Verifies every generated change (syntax, Ruff, and an AST-equivalence safety check).  
4. Commits verified changes to an isolated review branch and never touches the default branch.  
5. Publishes a structured audit and diff report to a FastAPI dashboard hosted on Render.

**Primary audience:** hackathon judges (30-second evaluation, must work with zero setup) and open-source maintainers (need to trust the diff).

**Success definition:** a judge opens the Render URL, clicks one button, and sees a real-looking run with a syntax-highlighted diff, metrics and a Sentry trace link, without installing anything.

---

## 2\. Architecture decisions to bake into the plan

These resolve gaps and conflicts in the original brief. Challenge any of them in "Open questions" rather than silently deviating.

### 2.1 Two deployment halves

| Half | Runs where | Contains | Dependencies |
| :---- | :---- | :---- | :---- |
| **Dashboard** | Render (web service) | `app/web/` only | `requirements-web.txt` (fastapi, uvicorn, jinja2, pygments, sentry-sdk, a DB driver) |
| **Engine** | Local machine (CLI and Temporal worker) | `app/core/`, `app/workflows/`, `cli.py` | `requirements-worker.txt` (tree-sitter, tree-sitter-python, GitPython, ruff, openai, temporalio, sentry-sdk) |

- Render must **not** need Temporal, tree-sitter or Git. Keep its build small and fast.  
- The engine pushes finished reports to the dashboard through `POST /api/reports`, authenticated with a shared secret header (`X-CouchPilot-Key`, value from env). Unauthenticated writes are not allowed.  
- Temporal needs a server. Plan for `temporal server start-dev` locally. State clearly that Render does not host Temporal, and say whether Temporal Cloud is worth it (my default: no).

### 2.2 Demo Run must work without Temporal or a live LLM

`POST /api/demo-trigger` has two modes:

- **replay (default):** replays a pre-recorded run against a bundled messy sample repo, with realistic staged progress (scanning, generating, validating, committed). Zero cost, zero failure risk for judges.  
- **live (optional, env-gated):** runs the real pipeline in-process against the bundled sample repo only, with a hard rate limit and token cap. It must never accept an arbitrary repo URL (cost and abuse risk).

Include a fixture `sample_repo/` (messy on purpose: missing docstrings, no type hints, inconsistent formatting) used by tests, the demo and the CLI quick-start.

### 2.3 Persistence on Render

Render's free filesystem is ephemeral and free instances spin down. Choose and justify one: (a) SQLite seeded from fixtures on boot (simplest, demo-safe), or (b) Render Postgres. Whatever is chosen, the dashboard must render a populated, believable state on first boot with an empty database.

### 2.4 Model and provider configuration

- Use the OpenAI Python SDK against an OpenAI-compatible endpoint. Provider, base URL, model ID and API key all come from env vars, with no hardcoded model strings.  
- Provider presets to document: Groq (`https://api.groq.com/openai/v1`), Google AI Studio (`https://generativelanguage.googleapis.com/v1beta/openai/`), local Ollama (`http://localhost:11434/v1`).  
- Model IDs differ per provider (the Ollama tag for Gemma 2 2B is `gemma2:2b`, not `gemma-2-2b-it`) and provider catalogs change. Add a Phase 2 step that verifies the chosen Gemma model ID is currently served before building on it, and list a fallback Gemma variant.

---

## 3\. Tech stack constraints (zero local GPU load)

- **Python 3.11+**, `venv`. Strict `.gitignore`: `venv/`, `__pycache__/`, `*.pyc`, `.env`, `*.egg-info/` (plus the Impeccable block in section 5.4 once installed).  
- **LLM:** OpenAI Python SDK, Gemma open-weight model, toggleable base URL (section 2.4).  
- **AST parsing:** `tree-sitter` \+ `tree-sitter-python` to extract functions, classes and missing docstrings deterministically.  
- **Verification:** `ruff` via subprocess before any commit.  
- **Git:** `GitPython`. Review branches named `couchpilot/tidy-YYYYMMDD`, with a numeric suffix on collision.  
- **Orchestration:** `temporalio` with durable Workflows and Activities, exponential-backoff `RetryPolicy`, resilient to HTTP 429 and laptop sleep.  
- **Observability:** `sentry-sdk` custom spans (`@sentry_sdk.trace` and `sentry_sdk.start_span`). Sentry must be optional: no DSN means a silent no-op, never a crash.  
- **Dashboard:** FastAPI \+ Uvicorn \+ Jinja2 \+ Tailwind CSS, deployed to Render via a `render.yaml` Blueprint.

---

## 4\. Safety invariants (must be enforced in code, not just documented)

1. Work on a fresh clone or `git worktree`, never in the user's working tree.  
2. Never commit to or push the default branch. Pushing the review branch is opt-in (`--push`); the default is local branch only.  
3. **Docstring-only guarantee:** after applying a patch, parse the file before and after with stdlib `ast`, strip docstrings and annotations from both trees, and require them to be identical. If not, reject that file's patch.  
4. Apply edits bottom-to-top by byte offset so earlier edits don't shift later ones. Docstring indentation is derived from the function body, not guessed.  
5. Per-file validation: `ast.parse` succeeds, `ruff check --select E9,F` clean on touched files, `ruff format --check` clean. A failing file is dropped from the commit and recorded in the report as a lint failure (never silently).  
6. LLM output is treated as untrusted: structured JSON schema, length caps, rejected if it contains code outside the target's docstring or annotation slots.  
7. `--dry-run` mode produces the report and diff without creating a branch.  
8. Secrets never appear in reports, logs or spans.

---

## 5\. Dashboard UI/UX and design system

### 5.1 Aesthetic

Clean, minimalist developer utility. Calm, dense-but-readable, trustworthy. This is a review tool, not a marketing page. No decorative gradients, glows or motion beyond functional transitions.

### 5.2 Color tokens

| Token | Value | Use |
| :---- | :---- | :---- |
| `--oat` | `#F7F5F0` | Page background |
| `--slate` | proposed `#1F2A33` (tinted, not pure black) | Body text |
| `--slate-muted` | proposed `#55616B` | Secondary text |
| `--line` | proposed `#E2DCCF` | Borders and dividers |
| `--plum` | `#5B2C6F` | Primary interactive accent (buttons, links, focus ring) |
| `--marine` | `#1B4F72` | Secondary interactive accent (tabs, selected state, running status) |
| `--tangerine` | `#E67E22` | Status badge: warning, partial, retried |
| `--butter` | `#F4D03F` | Status badge: pending, queued |
| `--red` | `#E74C3C` | Lint failures, deletions |

Contrast rules (the plan must respect these):

- White text is fine on plum and marine. **Never put white text on tangerine, butter or red** (contrast is too low for small text). Use `--slate` text on those badges, or a pale tint of the color as the background with a darker text shade.  
- Red is for icons, borders and tinted deletion rows. For red text on oat, use a darker proposed shade (about `#B83227`).  
- Do not combine plum and marine in a gradient.  
- The palette has no "addition" color for diffs. Propose one muted green used **only** in diff additions, and flag it as a deliberate deviation for my approval.

### 5.3 Rules

- **Icons:** Lucide SVG via CDN only. **No raw emojis anywhere**: UI, templates, logs, CLI output, commit messages, README.  
- Diff syntax highlighting is rendered server-side with Pygments using a custom style that maps to the tokens above (no extra JS highlighter).  
- Choose a deliberate UI typeface and monospace face (not a generic system or default stack) and justify the choice in one line.  
- WCAG AA contrast, visible focus states, keyboard-navigable run list and diff viewer, responsive down to mobile width.  
- Every view has designed empty, loading and error states.

### 5.4 Core views

1. **Overview metrics bar:** repos audited, missing docstrings resolved, tokens used, average latency, latest Sentry trace link.  
2. **Run history feed:** filterable (status, repo, date) list of Temporal workflow executions with branch names and status badges.  
3. **Diff viewer:** unified and side-by-side toggle, per-file collapse, per-file lint status, plus a prominent one-click **Demo Run** button for judges.

### 5.5 Design workflow (Impeccable)

Impeccable ([https\://github.com/pbakaus/impeccable](https://github.com/pbakaus/impeccable)) is installed in the repo before Phase 4\. In Phase 4 the plan must schedule these steps in order:

1. `npx impeccable install` (project scope), then `/impeccable init` to write `PRODUCT.md` (audience: judges and maintainers; purpose; voice: calm, precise; constraints: sections 5.1 to 5.3 verbatim).  
2. `/impeccable shape` on the dashboard before any template code is written.  
3. Build `app/web/` templates to the tokens above, then `/impeccable document` to generate `DESIGN.md` from the real code so palette and type decisions are recorded.  
4. Per view (overview, history, diff): `/impeccable critique`, then `/impeccable audit`, then `/impeccable polish`.  
5. Targeted passes: `/impeccable harden` (very large diffs, zero runs, failed runs, long branch names), `/impeccable onboard` (first-load empty state leading to Demo Run), `/impeccable clarify` (status and error copy).  
6. Do **not** run `bolder`, `delight` or `overdrive`; they conflict with the minimalist brief.  
7. Add `npx impeccable detect app/web/templates/` to the final checks. Any waiver for a finding caused by the mandated palette is recorded with a reason (`npx impeccable ignores add-value ... --reason`).

If any Impeccable suggestion conflicts with section 5.2 (the fixed palette), the brief wins.

---

## 6\. Required plan structure

Output the plan in exactly this order.

### 6.1 Repository and file tree

Exact layout: `app/web/` (templates, static, routes), `app/core/` (ast scanner, patcher, validator, git ops, llm client, models), `app/workflows/` (workflow, activities, worker), `cli.py`, `sample_repo/`, `fixtures/`, `tests/`, `render.yaml`, `requirements-web.txt`, `requirements-worker.txt`, `.env.example`, `PRODUCT.md`, `DESIGN.md`, `README.md`. Annotate what each file owns.

### 6.2 Data contracts

Define before the phases, since everything depends on them: the `Target` (node type, qualified name, byte range, signature, existing annotations), `Patch`, `ValidationResult`, and the `Report` JSON schema that the engine posts and the dashboard stores (run id, workflow id, repo, branch, timestamps, status, stats, per-file results, unified diff, sentry trace id).

### 6.3 Phase 1: Static analysis and Git engine

How tree-sitter locates functions, methods, async functions, classes, decorated definitions, nested functions and one-liner bodies; how a missing docstring is detected; how edits are applied; how GitPython creates the branch and extracts the diff; how Ruff and the AST-equivalence check gate commits. Include edge cases: decorators, `__init__`, overloads, property setters, lambdas (skipped), files with syntax errors (skipped and reported).

### 6.4 Phase 2: Gemma client and Sentry tracing

Structured generation schema (one request per file batch, JSON out: docstring, params, return annotation, confidence), prompt design, retries on malformed JSON, token accounting, concurrency limits. Give the **exact Sentry span hierarchy**, for example:

couchpilot.run (transaction)

  scan.repo

    scan.file            (ast parse time, targets found)

  llm.generate           (model, tokens\_in, tokens\_out, latency\_ms, retries)

  validate.file          (ruff\_pass, ast\_equivalent)

  git.commit

  report.publish

Specify which values are span data attributes versus tags, and how the trace id lands in the report for the dashboard link.

### 6.5 Phase 3: Temporal workflow design

Workflow definition and determinism rules (no network, time or randomness in workflow code; Sentry calls only inside activities). Activity boundaries (clone, scan, generate per batch, validate, commit, build report, publish). Per-activity timeouts, heartbeats, and `RetryPolicy` values with reasoning. 429 handling that honors `Retry-After` where the SDK supports it. Non-retryable errors (auth failure, validation rejection, malformed repo). Behavior across laptop sleep and worker restart. Bounded fan-out for LLM calls.

### 6.6 Phase 4: FastAPI dashboard and Render Blueprint

- Endpoints: `POST /api/reports` (auth required), `GET /api/reports` (filters and pagination), `GET /api/reports/{id}`, `POST /api/demo-trigger` (rate limited), `GET /healthz`, plus the HTML routes.  
- UI layout per section 5.4 and the Impeccable workflow in section 5.5.  
- A **complete `render.yaml`**: service type, runtime, region, plan, build and start commands (`uvicorn app.web.main:app --host 0.0.0.0 --port $PORT`), `healthCheckPath`, pinned Python version, and env vars (`COUCHPILOT_API_KEY` generated, `SENTRY_DSN` unsynced, `DEMO_MODE`, DB settings).

### 6.7 Testing and verification

Unit tests for the scanner and patcher against `sample_repo/`; a golden-file test for the diff; a test that the AST-equivalence gate rejects a body-altering patch; an LLM client test with a mocked provider; a dashboard smoke test; a local end-to-end run command.

### 6.8 Schedule, risks and acceptance

- A timeboxed schedule per phase (ask me for my deadline in Open Questions).  
- Top risks with mitigations (rate limits, model availability, Render cold start, Temporal setup friction).  
- Per-phase **acceptance criteria**, each one a command or observable behavior I can check.  
- A cut line: what gets dropped first if time runs out (suggested order: live demo mode, side-by-side diff, README generation).

### 6.9 Submission checklist

Items needed for the DEV post: architecture diagram, screenshots, live Render URL, repo link, a short demo walkthrough, and how Gemma, Temporal and Sentry are each used. Do not assume challenge rules you cannot verify; list them as questions.

---

## 7\. Output rules

- Use Markdown with tables and short code blocks where they clarify. No emojis.  
- Be specific: real package names, CLI commands, file paths, field names. No hand-waving like "handle errors appropriately".  
- Where a decision is mine to make, give your recommendation and the one-line tradeoff.  
- End with **Open questions** (maximum 5), then the line: `Awaiting confirmation to begin Phase 1.`