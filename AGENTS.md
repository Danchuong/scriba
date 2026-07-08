<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **scriba**. Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/scriba/context` | Codebase overview, check index freshness |
| `gitnexus://repo/scriba/clusters` | All functional areas |
| `gitnexus://repo/scriba/processes` | All execution flows |
| `gitnexus://repo/scriba/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## Release & Publish

Release checklist (established 0.34.0; mirrors prior releases):

1. Feature commit carries the version bump: `scriba/_version.py` (`__version__` + `SCRIBA_VERSION` if rendered bytes changed, with a docstring ledger entry) **and** the pinned ledger test `tests/unit/test_zoom.py::test_scriba_version_unchanged` (append the bump rationale to its comment and update the assert).
2. Release commit `chore(release): X.Y.Z`: CHANGELOG.md entry, README.md status line + "What's new" (fold the previous release into a `<details>` block), `docs/README.md` line 1, `docs/SCRIBA-TEX-REFERENCE.md` "Target:" line.
3. Push to GitHub (`origin main`). No git tags since 0.9.x.
4. PyPI — dist name is **`scriba-tex`** (repo name `scriba` is squatted by an unrelated package): `rm -rf dist/ && uv build`, `uvx twine check dist/*`, then upload with the token from **`key.env`** (gitignored, repo root; var `PYPI`) — e.g. `source key.env && TWINE_USERNAME=__token__ TWINE_PASSWORD="$PYPI" uvx twine upload --non-interactive dist/*`. Never print or commit the token.
5. Verify `https://pypi.org/pypi/scriba-tex/json` reports the new version.

Notes: no `~/.pypirc`/keyring on this machine — `key.env` is the only credential source. Homebrew tap (`homebrew/`) is a stale scaffold (formula still at 0.5.0 placeholders); update its SHA256s only if reviving that channel. RTK's `rg` proxy can return false "0 matches" — use `rtk proxy grep` or the Read tool for release verification greps.
