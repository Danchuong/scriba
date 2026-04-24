# A4 — LLM Cold-Read Usability Audit

**Scope:** Standalone cold-read of `docs/SCRIBA-TEX-REFERENCE.md` (956 lines) by an LLM with no prior Scriba exposure. Test task: "write a Dijkstra editorial with a graph and a distance array."

**Method:** Agent was restricted to the reference file only — no spec/, no code, no examples.

**Overall rating:** **ACCEPTABLE** (not good, not poor). Core loop well-documented; several high-severity traps cause reliable first-attempt failures on the Dijkstra task.

---

## Executive Summary — Biggest Cold-Read Traps

1. **"selector" never defined as a term.** Appears in §5.8 (`arrow_from=<selector>`) and §8 without formal definition. Cold AI guesses but quoting rules (string vs ident) are implicit.
2. **"delta-based" stated but not operationally defined.** §3.2 says frames are delta-based but never explains initial state before first `\step`.
3. **Graph layout engine choice has zero decision criteria.** §7.4 lists 5 options, no guidance on when to use each. Cold AI defaults to `"force"` for Dijkstra → meaningless layout.
4. **`\compute` outside `\foreach` is silently unreliable.** §13.2 says "may fail" with no explanation of why or what workaround to use.
5. **No render/run instructions exist anywhere.** Cold AI cannot self-verify output.

---

## Section-by-Section Friction Log

### §1 File Structure
- No explicit statement that files are `.tex` / UTF-8.
- "Prelude" concept appears as a comment in example but is never formally named.

### §2 Supported LaTeX Commands
- §2.3: asserts `align`/`cases`/`matrix` work inside `$$...$$` but gives no worked example (non-standard LaTeX).
- §2.5: `lstlisting` — supported language list not given.
- §2.9: omits `\label`, `\ref`, `\cite` from NOT-supported list — cold AI writing editorial may try these reflexively.

### §3 Animation Environment
- "delta-based" (§3.2) no operational definition.
- "Each `\step` should have exactly one `\narrate`" — "should" not "must"; unclear if zero/two is error.
- `\annotate` persistent-by-default only documented in §5.8, not §3.2.
- Substory behavior forward-referenced without pointer to §5.12.

### §4 Diagram Environment
- Whether `\compute` is allowed inside `\begin{diagram}` not stated.
- Whether `\apply` is allowed inside a diagram not stated.

### §5 Inner Commands
- **§5.1** Name regex asymmetric (lowercase leading, mixed-case rest) — not called out.
- **§5.2** `print` builtin behavior unspecified (likely silent no-op).
- **§5.2 vs §9.5 CONTRADICTION:** §3.1 prelude comment implies `\compute` is prelude-only, but §9.5 shows `\compute` **inside a `\step`**.
- **§5.5** `\apply`: "Common: value=, label=, tooltip=" — "common" implies others exist. Complete param list never given.
- **§5.7** `\recolor`: same-cell-twice-in-one-step behavior unspecified.
- **§5.8** `\annotate`: `side` param vs `side_hint` prose conflation — cold AI may try `side_hint=` (wrong).
- **§5.9** `\reannotate`: 1-sentence doc. Unclear if `label=` or `ephemeral=` are modifiable.
- **§5.10** `\cursor`: positional + named params mixed in one brace group — unusual syntax, cold AI may split into two brace groups.
- **§5.11** `\foreach`: `\compute` silently absent from allowed-commands list inside body.
- **§5.12** `\substory`: state persistence across substory boundary completely unspecified.

### §6 Visual States
- Two different "blue"s (`current` #0072B2, `path` #2563eb). No semantic convention guidance (which for "visited," which for "in queue," which for "finalized"?).

### §7 Primitives
- **§7.4 Graph:** layout options with zero decision criteria. `"stable"` node limit only in §14.
- **§7.4 Graph:** `G.node[A]` (unquoted) vs `G.node["A"]` (quoted) — both shown, rule never stated. Segtree uses quoted `st.node["[0,5]"]` (for bracket chars).
- **§7.3 DPTable:** "Selectors: Same as Array/Grid" — implicit cross-reference.
- **§7.15 VariableWatch:** initial display unspecified (blank, "0", "—"?).

### §8 Selector Quick Reference
- Stack `.all` absent from table — unknown if supported.
- VariableWatch names with spaces not addressed.
- "Interpolation: `${var}` inside any index" contradicts §13.2 "may fail outside foreach."

### §9 Examples Coverage
| Topic | Covered? |
|---|---|
| 1D DP | Yes (§9.3) |
| 2D DP | No |
| BFS/DFS | Yes (§9.4, §9.6) |
| Greedy/Dijkstra | **No** |
| Bit manipulation | No |
| Segment tree | Declaration only (§7.5), no animation |
| Sparse segtree | Declaration only, no animation |
| NumberLine/Geometry | No |
| Graph + Array side-by-side | **No** (Dijkstra use case) |

### §10 Environment Options
- `width`/`height` "dimension" type — no format example. Is it `"800"`, `"800px"`, `"800pt"`, `8cm`?

### §11 Annotation Colors
- Pure repeat of §5.8 table — no new info but fine as lookup.

### §12 Common Patterns
- `\cursor{a.cell}{0}` — "family selector" (no subscript) appears only here, never formally explained.
- `\reannotate` + `arrow_from=` — only evidence is §5.9 header signature.

### §13 Gotchas
- §13.2 "may fail" with no technical reason or workaround.
- §13.1 Stack/Queue push-then-recolor — unclear if applies to `sparse_segtree` `add_node`.

### §14 Limits
- Graph `stable` ≤20 nodes only here, not in §7.4 where `"stable"` is introduced.
- What happens on limit breach unspecified (hard error, warning, truncation, silent drop?).

---

## Prioritized Fix List

| Severity | Friction | Cold-Read Scenario | Recommended Fix |
|---|---|---|---|
| HIGH | `\compute` prelude vs in-step contradiction (§3.1 vs §9.5) | Cold AI gets contradictory signals | Clarify explicitly. If §9.5 correct, remove prelude-only implication from §3.1 |
| HIGH | No Graph + Array example | Dijkstra needs both; cold AI composes two unfamiliar patterns blind | Add §9.7 Dijkstra example |
| HIGH | `${var}` outside foreach "unreliable" with no workaround | Cold AI writes dynamic indices, fails silently | Explain technical reason + concrete workaround |
| HIGH | Graph layout no decision criteria | `"force"` default non-deterministic for Dijkstra | Add 1-line decision guide per layout option in §7.4 |
| MEDIUM | "selector" undefined | `arrow_from=<selector>` quoting inconsistent | Add 2-sentence definition at start of §8 |
| MEDIUM | "delta-based" undefined operationally | Cold AI misses that prelude sets initial state | Add one sentence explaining prelude → step-0 semantics |
| MEDIUM | Node ID quoting rule | `G.node[A]` vs `G.node["A"]` — cold AI guesses | Note in §8: quote when ID has special chars |
| MEDIUM | No render/run instructions | Cannot self-verify | Add §0 or appendix with `python render.py file.tex --open` |
| MEDIUM | `\reannotate` params underdocumented | Don't know if `label=` updatable | Expand §5.9 to match §5.8 table format |
| LOW | "should" vs "must" for single `\narrate` | Ambiguous error/warning behavior | Change to "must" + state what happens with 0 or 2 |
| LOW | Two "blue" visual states | Cold AI conflates `current` / `path` | Semantic convention note |
| LOW | `width`/`height` dimension format | May try wrong format | Add example value in §10 |
| LOW | `\compute` `print` behavior | Debug confusion | "Goes to build log, not rendered output" |

---

## Specific Question Answers

| Question | Answer |
|---|---|
| `arrow=true` vs `arrow_from=` clarity? | **Clear.** §5.8 comparison table is one of best-documented parts |
| When to pick `"force"` vs `"stable"` vs `"hierarchical"`? | **Not answerable from doc** |
| Do states persist across `\step`? Across substory? | Across step: yes (§3.2). Across substory: **unspecified** |
| `\annotate` ephemeral=false cross-substory or cross-animation? | **Not addressed** |
| Multi-target `\recolor` with comma? | **Not addressed** |
| `\shape` hex colors? | **Not addressed** (only named states) |
| Nested `\begin{animation}`? | **Not addressed**, not in NOT-supported list |
| Error `E1005` lookup? | Scattered inline (E1004/5/52/1437); **no consolidated index** |
| `UserWarning: selector not found` troubleshooting? | §13.1 mentions once; no general troubleshooting section |
| Assumes LaTeX knowledge? | **Yes, implicit** |
| Assumes Starlark knowledge? | **Yes, implicit** (§5.2 lists forbidden constructs by name) |

---

## Verdict for Dijkstra One-Shot

Document will produce **syntactically valid** output with high probability. Will likely fail on:

1. Choosing right graph layout for weighted directed graph (no guidance).
2. Combining `Graph` + `Array` in same animation (no example).
3. Using `\compute` for distance init referenced outside foreach (silently unreliable).
4. Self-verifying the result (no render instructions).

Gap between "syntactically valid" and "visually correct + pedagogically sensible" is large, and that's where cold-read AI fails.
