# Phase D — v0.5.0 Implementation Plan

> **Target:** Polish error UX, PyPI final publish, Homebrew tap, launch messaging, HARD-TO-DISPLAY verification.
> **Effort:** ~1.5 weeks solo, ~1 week with 2 engineers.
> **Prerequisite:** v0.4.0 complete (all 11 primitives, `\substory`, docs site).
> **Binds to:** [`roadmap.md`](roadmap.md) §7.

---

## 1. Phase D scope

| Category | Deliverable | Reference |
|----------|-------------|-----------|
| Error UX | Structured error messages with `E1xxx` codes, source line/column, docs site link | `environments.md` §11, `roadmap.md` §7.2 |
| PyPI final | Publish `scriba 0.5.0` (non-alpha) to PyPI with full changelog | `roadmap.md` §7.2 |
| Homebrew tap | `brew tap ojcloud/tap` + `brew install scriba` formula (arm64 + x86_64) | `roadmap.md` §7.2 |
| Launch messaging | Blog post + community thread drafts (HN, Lobsters, CP Discord) | `roadmap.md` §7.2 |
| HARD-TO-DISPLAY verification | 9 canonical editorials verified, accessibility audit, Problem #3 documented as partial | `roadmap.md` §7.2 |
| Bug fixes | Resolve remaining test failures (6 failing as of Phase C exit) | — |

---

## 2. Priority order

### Tier 1 — Stability (fix before anything else)

| # | Deliverable | Effort | Why first |
|---|-------------|--------|-----------|
| 1 | **Fix remaining test failures** | 0.5 days | 6 tests failing (diagram renderer); must be green before tagging |
| 2 | **Error UX overhaul** | 2 days | Improves DX for all future users; touches parser, renderer, emitter |

### Tier 2 — Packaging + Distribution

| # | Deliverable | Effort | Why |
|---|-------------|--------|-----|
| 3 | **PyPI final publish** | 0.5 days | Version bump 0.1.1a0 → 0.5.0, changelog, `python -m build`, `twine upload` |
| 4 | **Homebrew tap** | 1 day | Formula in `ojcloud/homebrew-tap`, test on arm64 + x86_64 |

### Tier 3 — Verification + Launch

| # | Deliverable | Effort | Why |
|---|-------------|--------|-----|
| 5 | **HARD-TO-DISPLAY verification** | 2 days | Build all 9 editorials, axe-core audit, CLS measurement, coverage report |
| 6 | **Launch blog post + threads** | 1 day | HN, Lobsters, CP Discord drafts |

---

## 3. Deliverable specs

### 3.1 Error UX overhaul

**Goal:** Every error a Scriba author encounters includes:
1. Error code (`E1xxx`)
2. Source file location (line + column)
3. Human-readable explanation
4. Link to docs site error catalog page

**Changes:**

- `scriba/animation/errors.py` — refactor `ScribaError` base class:
  ```python
  class ScribaError(Exception):
      code: str          # "E1042"
      line: int | None
      col: int | None
      message: str
      hint: str | None   # "Did you mean \step instead of \ste?"

      def __str__(self) -> str:
          loc = f" at line {self.line}, col {self.col}" if self.line else ""
          url = f"https://scriba.ojcloud.dev/errors/{self.code}"
          return f"[{self.code}]{loc}: {self.message}\n  → {url}"
  ```

- All existing `raise` sites updated to pass `line=` and `col=` from AST nodes
- Error catalog page auto-generated in docs site from `errors.py` table
- Parser errors include surrounding source context (2 lines before/after)

**Error code ranges (existing):**
- E10xx: parser errors
- E11xx: scene/renderer errors
- E12xx: Starlark worker errors
- E13xx: reserved (formerly `\fastforward`, removed)
- E14xx: primitive errors (plane2d, metricplot, graph-stable)

**Test additions:** ~10 tests verifying error format, line/col accuracy, URL presence.

### 3.2 Fix remaining test failures

6 failing tests in `tests/animation/test_diagram_renderer.py`:
- `KeyError: 'options'` — diagram block metadata missing `options` key
- `test_narrate_raises_validation_error` — grammar parse error instead of validation error
- `test_no_js_assets` — likely interactive mode leaking JS into static

Fix each with minimal diff. No architectural changes.

### 3.3 PyPI final publish

**Steps:**
1. Bump `version` in `pyproject.toml`: `"0.1.1a0"` → `"0.5.0"`
2. Write `CHANGELOG.md` covering v0.2.0 → v0.5.0 milestones
3. Verify `python -m build` produces clean sdist + wheel
4. `twine check dist/*` passes
5. Tag `v0.5.0` in git
6. `twine upload dist/*` to PyPI

**Pre-publish checklist:**
- [ ] All tests passing (0 failures)
- [ ] `pip install scriba-tex` in a fresh venv works
- [ ] `python -c "import scriba; print(scriba.__version__)"` prints `0.5.0`
- [ ] `Document.versions` returns correct version dict
- [ ] README renders correctly on PyPI

### 3.4 Homebrew tap

**New repo:** `ojcloud/homebrew-tap`

**Formula:** `Formula/scriba.rb`
```ruby
class Scriba < Formula
  desc "LaTeX → animated HTML renderer for competitive programming editorials"
  homepage "https://scriba.ojcloud.dev"
  url "https://files.pythonhosted.org/packages/.../scriba-0.5.0.tar.gz"
  sha256 "..."
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"scriba", "--version"
  end
end
```

**Verification:**
- [ ] `brew tap ojcloud/tap` works
- [ ] `brew install scriba` works on macOS arm64
- [ ] `brew install scriba` works on macOS x86_64 (CI or Rosetta)
- [ ] `scriba --version` prints `0.5.0`

### 3.5 HARD-TO-DISPLAY verification

**Process:** For each of the 9 covered problems:
1. Build the canonical `.tex` editorial via `scriba`
2. Verify HTML output matches `_expected.html` structure
3. Run axe-core accessibility audit on output
4. Measure CLS (must be < 0.1) on filmstrip scroll
5. Verify both light and dark themes render correctly

**Coverage report:** `docs/cookbook/HARD-TO-DISPLAY-COVERAGE.md`

| # | Problem | Primitives | Status | Notes |
|---|---------|-----------|--------|-------|
| 1 | Zuma interval DP | DPTable + Array + `\substory` | Covered | |
| 2 | DP optimization trick | DPTable + NumberLine | Covered | |
| 3 | 4D Knapsack | — | **Partial** | Cognitive limit: 4D state space cannot be meaningfully visualized in 2D static SVG. Documented in architecture decision §Consequences. |
| 4 | FFT butterfly | Plane2D + `@keyframes` | Covered | |
| 5 | MCMF dense graph | Graph layout=stable + Matrix | Covered | |
| 6 | Li Chao / CHT | Plane2D + geometry helpers | Covered | |
| 7 | Splay amortized | Tree + MetricPlot | Covered | |
| 8 | Persistent segtree | Tree (segtree) | Covered | |
| 9 | Simulated Annealing | Graph + MetricPlot + `\compute` + `\step` | Covered | |
| 10 | Heavy-Light Decomposition | Tree + Array | Covered | |

**Accessibility checklist (per editorial):**
- [ ] axe-core: 0 critical/serious violations
- [ ] Keyboard navigation: Tab through all frames
- [ ] Screen reader: meaningful `aria-label` on all interactive elements
- [ ] Reduced motion: `prefers-reduced-motion` disables CSS transitions
- [ ] Color contrast: WCAG AA (4.5:1 text, 3:1 large text)

### 3.6 Launch blog post

**Target venues:**
1. ojcloud blog (primary)
2. Hacker News (Show HN)
3. Lobsters
4. Codeforces blog
5. CP Discord servers

**Blog post outline:**
1. The problem: CP editorials are hard to understand without visualization
2. 10 HARD-TO-DISPLAY problems that motivated Scriba
3. Demo: before/after (raw TeX vs rendered animation)
4. Architecture: compile-time, zero-JS static mode, portable
5. Quick start: `pip install scriba-tex` + minimal example
6. What's next: community contributions, new primitives on demand

**Deliverable:** `docs/blog/launch-0.5.0.md` + community thread templates

---

## 4. Wave plan

### Wave D1 — Stability (sequential, blocks everything)

| Agent | Scope | Effort |
|-------|-------|--------|
| **bug-fix** | Fix 6 failing diagram renderer tests | 0.5 days |

### Wave D2 — 2 agents parallel

| Agent | Scope | Effort |
|-------|-------|--------|
| **error-ux** | Error UX overhaul: structured errors, line/col, docs links, tests | 2 days |
| **htd-verify** | HARD-TO-DISPLAY verification: build all 9, axe-core, CLS, coverage report | 2 days |

### Wave D3 — 2 agents parallel

| Agent | Scope | Effort |
|-------|-------|--------|
| **pypi-publish** | Version bump, CHANGELOG.md, build, test install, tag | 0.5 days |
| **homebrew-tap** | Create ojcloud/homebrew-tap repo, formula, test on arm64/x86_64 | 1 day |

### Wave D4 — Launch messaging

| Agent | Scope | Effort |
|-------|-------|--------|
| **launch** | Blog post, HN/Lobsters/Discord drafts | 1 day |

---

## 5. Exit criteria

- [ ] `scriba 0.5.0` published on PyPI with full changelog
- [ ] `brew install ojcloud/tap/scriba` works on macOS arm64 and x86_64
- [ ] All tests passing (0 failures, 0 errors)
- [ ] All error messages include `E1xxx` code, source location, docs URL
- [ ] 9/10 HARD-TO-DISPLAY editorials build and pass axe-core
- [ ] Problem #3 (4D Knapsack) documented as partial with rationale
- [ ] CLS < 0.1 on all filmstrip scroll tests
- [ ] Launch blog post published
- [ ] At least one external CP community thread posted
- [ ] No CRITICAL or HIGH issues open

---

## 6. Test budget

| Category | Count | Location |
|----------|-------|----------|
| Error format tests | ~10 | `tests/unit/test_error_format.py` |
| Diagram renderer fixes | ~6 | `tests/animation/test_diagram_renderer.py` (fix existing) |
| HARD-TO-DISPLAY E2E | ~9 | `tests/integration/test_htd_coverage.py` |
| Homebrew install smoke | ~2 | CI workflow |
| **Total new** | **~21** | |
| **Total existing (passing)** | **905** | |
| **Grand total** | **~926** | |

---

## 7. Version changes

| Field | Before (v0.4.0) | After (v0.5.0) |
|-------|-----------------|----------------|
| `__version__` | `"0.4.0"` | `"0.5.0"` |
| `pyproject.toml version` | `"0.1.1a0"` | `"0.5.0"` |
| `SCRIBA_VERSION` | `2` | `2` (unchanged) |
| `AnimationRenderer.version` | `1` | `1` (unchanged) |
| PyPI status | alpha | **final** |
| Homebrew | — | `ojcloud/tap/scriba` |

---

## 8. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| PyPI name `scriba` already taken | Medium | Check `pip index versions scriba`; if taken, use `scriba-cp` or `ojcloud-scriba` |
| Homebrew formula review delay | Low | Use tap (no review needed for taps, only core formulae) |
| axe-core failures on existing editorials | Medium | Fix a11y issues in Phase D; budget 0.5 extra days |
| Community reception lukewarm | Low | Focus on CP-specific communities (Codeforces, USACO forum) where pain is acute |
| 6 failing tests harder to fix than expected | Low | Diagram renderer is well-understood; failures are metadata/option parsing issues |

---

## 9. Post-launch (v0.6+)

After v0.5.0 GA, Scriba enters maintenance + on-demand mode:

| Feature | Trigger | Status |
|---------|---------|--------|
| Lit 3 interactive runtime | Sustained demand from JS-only consumers | Deferred |
| New primitives (Heap, SegTree, UnitCircle, Tensor) | Specific editorial PRDs | On demand |
| 4D Tensor primitive | Multidimensional DP editorial demand | Deferred |
| 1.0 API freeze | 2 consecutive minors with no HTML shape change + 1 external OJ | Not scheduled |

---

## 10. Cross-references

| Document | Relationship |
|----------|--------------|
| [`roadmap.md`](roadmap.md) §7 | Phase D milestone |
| [`PHASE-A-PLAN.md`](phase-a.md) | Phase A (predecessor) |
| [`PHASE-B-PLAN.md`](phase-b.md) | Phase B (predecessor) |
| [`PHASE-C-PLAN.md`](phase-c.md) | Phase C (predecessor) |
| [`cookbook/HARD-TO-DISPLAY.md`](../cookbook/HARD-TO-DISPLAY.md) | 10-problem stress test |
| [`00-ARCHITECTURE-DECISION-2026-04-09.md`](architecture-decision.md) | Pivot #2 rationale |
