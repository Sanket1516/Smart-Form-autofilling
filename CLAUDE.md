## Code Intelligence and Memory Workflow

Pick the smallest tool set for the task; do not run every tool on every request.

- **Resumed or follow-up work**: use claude-mem's injected context / `mem-search` for prior decisions and unfinished tasks.
- **Architecture / "how do X and Y relate"**: Graphify (`graphify-out/graph.json`, built `--code-only`). Use `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<symbol>"`. Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review.
- **Callers, dependencies, change impact before refactors**: CodeGraph (`codegraph_explore` MCP tool, or `codegraph callers|impact|affected <symbol>` in the shell).
- **Small isolated fixes**: plain Grep/Read plus tests is fine.
- Graph results can be stale. Verify against current source before editing. Refresh with `graphify update .` after code changes; CodeGraph auto-syncs (`codegraph status` to check).
- If a tool is unavailable or its index is missing, fall back to normal exploration and say so. Never claim a tool was used without its actual output.
- For significant changes, identify affected files and tests first, run the relevant tests after, and report actual results.
- Preserve existing behavior and API contracts. Never put secrets, Aadhaar/PAN numbers, or bank identifiers in logs, summaries, or memory.
