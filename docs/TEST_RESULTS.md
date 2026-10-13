# Test Results

Run date: 2026-10-13. Results below were collected locally on Windows with Python 3.11,
Node 22, Docker Compose, and Chromium. Backend tests used the mock LLM unless stated otherwise.

| Check | Result |
|---|---|
| `python -m ruff check backend tests` | Passed |
| `python -m black --check backend tests` | Passed; 111 files unchanged |
| `python -m pytest` | 146 passed, 7 deselected |
| Real Chroma integration (`-m chroma`) | 3 passed against the Compose Chroma service with real `all-MiniLM-L6-v2` embeddings |
| Frontend Vitest | 22 passed |
| Extension Vitest | 24 passed |
| `npm run typecheck` | Passed |
| `npm run build` | Passed for the dashboard and extension |
| Playwright browser E2E | 1 passed against the isolated Compose stack; upload, review, approve, fill, and no-submit assertions passed |
| Development and test Compose configuration | Both parsed successfully |
| Real-provider LLM tests | Not run; these are opt-in and can incur API charges |

The default backend command deselects the `chroma` and `real_llm` markers. The Chroma suite
was run separately against a temporary Compose service; the test project and its data volumes
were removed afterward. Playwright also ran in the isolated test Compose project and cleaned
up its containers and volumes. The CI workflow runs the same marked Chroma suite and browser
flow on pushes and pull requests.
