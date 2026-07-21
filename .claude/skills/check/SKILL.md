---
name: check
description: Run a project's lint + test + browser-test suite (Ruff, pytest, Playwright, or their JS/TS equivalents), summarize what failed, and suggest fixes. Use when the user asks to "run checks", "run the checks", "lint and test", "run the full test suite", or similar — in any project, not just one with a scripts/check.py.
user-invocable: true
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
---

# /check — Lint + Test + Browser-Test Runner

Runs a project's quality gate (linter, unit/integration tests, browser/e2e
tests), then reports back in a compact, actionable form: what passed, what
failed, and what to do about it. Never edits code — this skill diagnoses,
it doesn't fix. If the user wants the fixes applied, they'll ask separately.

Arguments passed: `$ARGUMENTS` (optional — e.g. a subdirectory to scope to).

---

## Step 1 — Find out how this project runs its checks

Prefer whatever the project already defines over inventing your own
invocation. Check in this order and use the first match:

1. **A project check script** — look for `scripts/check.py`,
   `scripts/check.sh`, `Makefile` (targets like `check`/`lint`/`test`), or a
   `package.json` `"scripts"` entry named `check`/`test`/`lint`. If one
   exists, run it as-is and skip to Step 3 — trust the project's own
   composition of these tools over reimplementing it.
2. **No script exists** — fall back to detecting the tools directly (Step 2).

Use Glob/Read to check for: `requirements.txt`/`pyproject.toml` (Python
project), `package.json` (Node project), `ruff.toml`/`[tool.ruff]` in
pyproject.toml, `pytest.ini`/`[tool.pytest.ini_options]`/a `tests/` dir,
`playwright.config.*` or `pytest-playwright` in requirements, or
`@playwright/test` in package.json.

## Step 2 — Run each stage that applies (only if no script from Step 1)

Run every applicable stage even if an earlier one fails — you want a full
picture, not just the first failure. Use Bash for each:

- **Lint (Ruff)**: `ruff check .` (Python). If no Ruff config/dependency is
  found, skip this stage rather than forcing it on a non-Ruff project.
- **Unit/integration tests**:
  - Python: `pytest` (exclude any file that looks browser-driven, e.g. named
    `test_ui_*`, `test_e2e_*`, or importing `playwright`/`selenium`, and run
    those separately in the next stage).
  - Node: `npm test` or the project's defined test script.
- **Browser/Playwright tests**:
  - Python (`pytest-playwright`): run just the browser-test files identified
    above, e.g. `pytest tests/test_ui_playwright.py` (or `test_e2e*`).
  - JS/TS (`@playwright/test`): `npx playwright test`.
  - If neither is present, skip this stage — don't install Playwright just
    to satisfy the skill.

Before running browser tests, check whether the app needs something
running first (a dev server, an env var the app requires to start — grep
`app.py`/`main.*`/`server.*` for `os.environ[` / `process.env.` patterns
that look required rather than defaulted). If a required var looks unset in
the current shell, set a throwaway value for the run rather than failing
immediately, and say so in the summary.

## Step 3 — Summarize failures

Don't dump raw tool output. For each stage that failed, extract and report:

- **Ruff**: file:line, rule code, and the one-line message, grouped by rule
  code if there are many of the same kind.
- **pytest**: failing test names (`test_file.py::test_name`) and the
  assertion/exception line — not the full traceback unless it's a bare
  `Error` with no assertion context.
- **Playwright**: failing scenario name and the specific Playwright error
  (timeout on which locator, assertion mismatch with expected vs. actual,
  etc.) — these errors usually name the exact selector or expectation that
  failed, surface that verbatim.

If a stage passed, just say so in one line — don't enumerate passing tests.

## Step 4 — Suggest fixes

Ground suggestions in the actual error, not generic advice:

- **Ruff**: if the rule is autofixable, say so and offer
  `ruff check --fix .` (mention `--unsafe-fixes` only if the rule needs it).
  For non-autofixable rules, name the specific line and what change would
  satisfy the rule.
- **pytest**: read the failing test and the code it exercises (Read/Grep)
  before guessing — state what the test expected, what the code actually
  does, and which side is likely wrong (test out of date vs. real
  regression). Don't just say "fix the bug."
- **Playwright**: common causes worth checking specifically —
  - `TimeoutError` waiting for a locator: check if the selector matches
    more than one element (e.g. a nav/layout element sharing a class or
    role with the intended target — this is a common bug: a generic
    selector like `button[type=submit]` can match unrelated buttons
    elsewhere on the page) or if the element genuinely never appears
    (server didn't start, wrong route, auth redirect).
  - Assertion mismatch: quote expected vs. actual from the error and
    connect it to the specific line of app code that produces the actual
    value.
  - Flakiness (passes on rerun): note that explicitly rather than treating
    it as a deterministic bug — suggest a wait-for-condition instead of a
    fixed sleep if one exists in the test.

## Output shape

End with a short structured summary, e.g.:

```
Ruff:        ✅ passed
pytest:      ❌ 2 failed (test_models.py::test_x, test_routes.py::test_y)
Playwright:  ❌ 1 failed (test_login.py::test_checkout_flow)

Fixes:
- test_models.py::test_x — <specific cause + suggested fix>
- test_routes.py::test_y — <specific cause + suggested fix>
- test_checkout_flow — <specific cause + suggested fix>
```

If everything passed, say so in one line and stop — don't pad the
response.
