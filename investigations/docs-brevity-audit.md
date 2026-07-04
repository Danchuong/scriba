# Scriba docs brevity audit — is `SCRIBA-TEX-REFERENCE.md` as lean as it can be?

> Audit only, no repo source modified. Repo @ `eda4f7d` (v0.23.1), venv `.venv/bin/python`.
> Target of audit: `docs/SCRIBA-TEX-REFERENCE.md` (the self-declared "single file for AI agents").
> Cross-checked against `docs/spec/{ruleset,smart-label-ruleset,motion-ruleset,error-codes,primitives,environments}.md`.
> Probes: `scratchpad/db_measure.py`, `db_sections.py` (structural counts, reproducible).
> Grading: **[Confirmed]** = measured/quoted from the file; **[Hypothesized]** = editorial estimate or from-memory.

---

## 1. Hand-off Brief — the direct answer

**No — it is not the briefest, though it does keep more than enough to author everything.** The reference is **2005 lines / 12,235 words** [Confirmed]; roughly **480–560 lines (≈25%) are removable or foldable with zero loss of authoring capability** [Hypothesized] — the file still ships an `Appendix A — Internal / Forward-Compat` that its own text calls "**not needed for authoring**," documents `\ref` **twice** (§5.4 + §5.15), carries a §12 "Common Patterns" section that mostly re-shows snippets already in §5, sprinkles **16 maintainer R-/A-/GEP-card references** and **12 inline "(since X)" version notes** through author-facing prose, and re-teaches the same command/primitive/selector surface that three sibling spec files (`ruleset.md`, `primitives.md`, `environments.md`) also re-teach at three *different* version vintages [Confirmed].

So the owner's two-part test splits cleanly: **"keeps enough to do everything" → yes** (arguably over-complete); **"stripped what users don't need, briefest possible" → no**, and the trim targets are concrete and named below.

---

## 2. Structural measurement [Confirmed unless noted]

### 2.1 Global content mix (`db_measure.py`)

| Content type | Lines | Share | Note |
|---|---:|---:|---|
| Fenced code (76 blocks) | 761 | 38.0% | runnable/illustrative `.tex` + `bash` |
| Tables | 354 | 17.7% | arg tables, selector grid, error grid |
| Prose | 400 | 20.0% | explanation + mechanism |
| Lists | 70 | 3.5% | |
| Headings | 97 | 4.8% | 15 sections + appendix, to H4 |
| Blank | 323 | 16.1% | |
| **Total** | **2005** | 100% | 12,235 words |

Signal ratios: **args-tables 17.7%** and **runnable examples 38%** dominate (good — that is the load-bearing reference mass). The removable mass hides in the **20% prose**, where mechanism/history/duplication live.

### 2.2 Section weight (`db_sections.py`) — four sections are 72% of the file

| Group | Lines | Share |
|---|---:|---:|
| Front-matter + nav (Contents, Index-by-task) | 44 | 2.2% |
| §0–§2 render / structure / LaTeX | 162 | 8.1% |
| §3–§4 environments | 74 | 3.7% |
| **§5 Inner Commands (18)** | **621** | **31.0%** |
| §6 Visual States | 20 | 1.0% |
| **§7 Primitives (15)** | **445** | **22.2%** |
| §8 Selector Quick Reference | 92 | 4.6% |
| **§9 Complete Examples** | **276** | **13.8%** |
| §10–§12 options / colors / patterns | 77 | 3.8% |
| **§13 Gotchas** | **116** | **5.8%** |
| §14 Limits | 21 | 1.0% |
| §15 Error Code Quick Ref | 42 | 2.1% |
| Appendix A — Internal / Forward-Compat | 15 | 0.7% |

### 2.3 "Non-author" footprint counted directly

| Marker | Count | Where (sample) |
|---|---:|---|
| Inline version-history `(since X)` / `Since X` / `Removed in X` | **12** | L357, 455–458, 533, 592, 622, 785, 888, 1395, 1406, 1905, 2000 |
| Maintainer card refs `R-3x/R-4x/A-x/GEP` | **16** | R-32×2, R-36×3, R-38×2, R-39×2, R-40, A-2/3/4/5/8, GEP-20 |
| Distinct E-codes **cited in body** | **64** | — |
| …of which present in §15 quick-table | **33** | → **31 cited but not tabled** (§15 defers rest to spec) |

### 2.4 "Spiritual competitor" comparison — **[Hypothesized]**

Mermaid.js docs are **multi-page**, not a single "read one file" contract; a single diagram-type page (flowchart, sequence) is roughly **500–1500 lines** of markdown. Scriba's 2005-line one-file reference covers **15 primitives + 18 commands + selectors + worked examples** at ≈130 lines/primitive-equivalent — *comparable density per feature*, just consolidated. **Conclusion:** the file is not egregiously bloated relative to peers; the brevity win is trimming the ~25% mechanism/history/duplication, **not** shrinking the core reference mass. Treat this whole subsection as from-memory.

---

## 3. Block classification (sequential, whole file) [Confirmed line refs; saves Hypothesized]

Types: **ESS** = author-essential (keep) · **RESCUE** = only needed on error (fold to `<details>`/appendix) · **LEAK** = internal mechanism → belongs in `docs/spec/*` · **DUP** = duplicated elsewhere in REFERENCE.

| Lines | Block | Type | Recommendation | ~Save |
|---|---|---|---|---:|
| 1–44 | Title, Contents, Index-by-task | ESS | keep (see §6 cheat-sheet idea) | 0 |
| 45–76 | §0 Render, §1 File Structure | ESS | keep | 0 |
| 113–122 | §2.2.2 Legacy Polygon aliases | RESCUE | fold (legacy-source rescue) | 8 |
| 154–164 | §2.5 copy-button `enable_copy_button`/library-mode | LEAK | trim to author-facing | 2 |
| 245–246 | §3.2 "Delta-based — operational definition" | DUP | restates the bullets above; compress | 4 |
| 248–254 | §3.3 Playback (reverse/emphasis) "not something you author" | LEAK | 1 line + motion-ruleset link | 5 |
| 284–285 | §5 header `SCRIBA_NO_EMPHASIS` env note | LEAK | move to appendix | 2 |
| 344–350 | §5.3 emitter HTML-`id`/`data-label`/`:target` internals | LEAK | keep "label enables \hl"; drop emit detail | 3 |
| 385–402 | §5.3 full labeled-`\hl` example | DUP | duplicates §5.14 examples; drop one copy | 10 |
| 413–430 | §5.4 `\ref` full write-up (R-39) | DUP | **duplicates §5.15**; reduce to "supports \ref (§5.15)" | 15 |
| 444–447 | §5.8 "Maintainer note" (pill internals → smart-label) | LEAK | 1-line pointer | 2 |
| 634–667 | §5.12 "why `${i}` is mandatory" + worked wrong/right | DUP | **overlaps §13.2**; consolidate to one home | 12 |
| 848–863 | §5.18 "Desugaring (A-5 — indistinguishable hand-frames)" + differ/emitter prose | LEAK | duplicates motion-ruleset A-5; keep "expands to N real steps" | 12 |
| 879–884 | §5.18 "Note on syntax vs the `{write,cursor}` sketch" | LEAK | design-history; drop | 6 |
| 619–620 | §5.11 "See R-38 / A-4 for the full contract" + card refs | LEAK | strip card tokens; keep behavior | 2 |
| 1049–1076 | §7.4.1 Layout guide + 16-line "best-practices" callout | RESCUE | fold callout to `<details>` | 8 |
| 1058–1059 | §7.4 `stable`+`directed` gotcha | DUP | **duplicates §13.10**; single home | 4 |
| 1395–1412 | §8 blockquotes: `block[..]` + `color="state:X"`+`leader` | DUP | duplicate §5.8/§5.18 params; keep table row, move detail | 12 |
| 1489–1593 | §9.3/9.4/9.5/9.6 examples | RESCUE | echo §5 mini-examples; keep 1, fold rest | 60 |
| 1764–1809 | §12 Common Patterns (cursor/DP-arrow/edge/flow) | DUP | re-shows §5.8/§5.11/§7.4 snippets; replace w/ recipe index | 30 |
| 1839–1871 | §13.2 `${interpolation}` positions | DUP | overlaps §5.12 (counted once above) | — |
| 1904–1909 | §13.8 headroom mechanism (scratch buffer, R-32) | LEAK | duplicates smart-label R-32; keep only the workaround | 5 |
| 1923–1925 | §13.10 tail: forward-compat/env pointer | LEAK | drop (Appendix A already covers) | 2 |
| 1992–2005 | **Appendix A — Internal / Forward-Compat** | LEAK | self-declared "not needed for authoring"; cut to 2-line pointer | 12 |
| (scattered) | 12 inline `(since X)` notes | history | → single CHANGELOG pointer; masthead already states Target version | 8 |
| (scattered) | 16 R-/A-/GEP card tokens | LEAK | delete tokens from author prose | 3 |

**Rough removable/foldable total ≈ 227 hard-trim + ~250 fold (§9, §13, callouts) ≈ 480–560 lines** [Hypothesized]. Everything above is either mechanism the file *itself* flags as non-authoring, a second copy of something, or history — **no author capability is lost.**

---

## 4. REFERENCE ↔ spec duplication & role inversion [Confirmed]

Intended split (owner's principle): **REFERENCE = how to USE; spec = mechanism + maintenance.** It is muddied both directions.

### 4.1 REFERENCE leaks *spec mechanism* into author text (move → spec)

| REFERENCE | Duplicates spec | Verdict |
|---|---|---|
| §5.18 desugaring "byte-for-byte / differ / emitter" (L848–863) | `motion-ruleset.md` **A-5** (L131–150, cites `_grammar_playeach.py`, `test_playeach.py`) | Move mechanism to spec; author needs one sentence |
| §5.4 + §5.15 `\ref` (R-39, R-36 palette) | `smart-label-ruleset.md` **R-39** (L600–605) | Specced once; REFERENCE duplicates it **twice internally** |
| §13.8 headroom scratch-buffer + **R-32** | `smart-label-ruleset.md` R-32 note (L1318) + stable-layout | Move mechanism; keep `ephemeral=true` workaround |
| §3.3 reverse/emphasis playback | `motion-ruleset.md` **A-2/A-3/A-8** | Condensed already; still author-irrelevant detail |
| §5.11 binding-caret "full contract" | `smart-label` **R-38** + `motion` **A-4** | Keep usage table; drop card citations |

### 4.2 Spec is used as *user docs* (reverse — the deeper smell)

`ruleset.md`, `primitives.md`, `environments.md` re-teach the **same authoring surface** REFERENCE owns, at **inconsistent versions** [Confirmed]:

| File | Self-titled version | Overlapping user-facing content |
|---|---|---|
| `SCRIBA-TEX-REFERENCE.md` | **Target v0.23.1**, "§5 Inner Commands (**18** total)" | canonical |
| `spec/ruleset.md` | "**v0.5.0** — Complete Ruleset Reference", "§2 Inner Commands (**14** total)" | full command table, selector syntax, primitive catalog, authoring NOTE on manual-unroll |
| `spec/environments.md` | "**04** — … Spec" ("base 8 commands from **v0.3**") | §3 per-command Signature/Cardinality/**Example**, §12 "**Complete worked examples**" (L770–913) = §9 turf |
| `spec/primitives.md` | "**06** — Primitive Catalog (**Base**)" | Array/Grid/DPTable/Graph/Tree/NumberLine + §10 "selector quick reference" = §8 turf |

**Command-count drift is live and checkable**: REFERENCE says **18**, `ruleset.md` says **14** [Confirmed L282 vs ruleset L74]. Four files teaching one surface at four vintages is the real maintenance tax — but note it is **outside** REFERENCE's own line count, so it does not change the §1 headline; it is a docs-set governance finding.

### 4.3 Correct divisions (leave alone)

`error-codes.md` (full catalog; §15 is a proper subset), and `smart-label`/`motion` **as mechanism sinks** are the right shape — REFERENCE correctly *delegates* internals there. The fix is to make the delegation total (stop re-explaining), not to add more.

---

## 5. "One file is enough" contract check [Confirmed]

Masthead promises (L3): *"Read this one file to write valid Scriba `.tex` sources."* **No hard breach for authoring** — every outward pointer is "for more / exact values / install," never "you cannot write this without opening X." Four soft pointers, all LOW severity:

| Loc | Pointer | Missing at the spot? | Severity |
|---|---|---|---|
| L917 §6 | "exact CSS fill/stroke/text token values → `scriba-scene-primitives.css`" | only exact hex; state **names** are inline & sufficient to author | LOW |
| L619–620 §5.11 | "See R-38 / A-4 for the **full contract**" | wording overpromises; table + soft-drop behavior is enough to use the caret | LOW |
| L331 §5.2 | "See `test_reference_dptable.tex` for the **full** 2D DP animation" | pattern is shown; the file is a bonus | LOW |
| L1988 §15 | "Codes cited elsewhere … are in `spec/error-codes.md`" | **31 of 64** cited codes aren't in the §15 table; meaning is usually inline at citation | LOW–MED |

**Verdict:** contract holds for the stated task. Tighten only the §5.11 "full contract" phrasing (implies something is withheld) and consider marking §15 as "top codes only (33 of the 64 cited here)."

---

## 6. Proposed lean REFERENCE — outline, cheat-sheet, durable rules

### 6.1 Target shape — **≈1400 lines (−30%)**, no capability lost [Hypothesized]

| Part | Now | Lean | Change |
|---|---:|---:|---|
| **Cheat-sheet (1 screen)** — NEW | 0 | 40 | skeleton + 18-cmd one-liners + 15-primitive one-liners + selector grammar + top-5 footguns |
| §0–§1 render/structure | 32 | 30 | keep |
| §2 LaTeX commands | 130 | 95 | fold legacy aliases + copy-button |
| §3–§4 environments | 74 | 45 | cut playback mechanism → motion-ruleset |
| §5 Inner Commands (18) | 621 | 430 | one home per command; kill 2nd `\ref`, desugaring, emit detail |
| §6 Visual States | 20 | 18 | keep |
| §7 Primitives (15) | 445 | 370 | fold rescue callouts to `<details>` |
| §8 Selector table | 92 | 55 | move blockquote param detail to §5 |
| §9 Examples | 276 | 130 | keep Hello + Dijkstra; fold 9.3–9.6 |
| §10–§11 options/colors | 31 | 27 | keep |
| §12 Patterns | 46 | 8 | recipe **index** (pointers), not re-examples |
| §13 Gotchas | 116 | 70 | `<details>` appendix; drop mechanism |
| §14 Limits | 21 | 21 | keep |
| §15 Error quick-ref | 42 | 42 | keep; label "top codes only" |
| Appendix A | 15 | 0 | delete → 2-line pointer folded into §13 |
| **Total** | **2005** | **≈1381** | **−31%** |

### 6.2 Durable editing rules (put at top of the file as a maintenance contract)

1. **One home per fact.** A command/primitive/selector is fully documented **once** (in §5/§7/§8). Every other mention is a `§`-link, never a re-explanation. (Kills the §5.4/§5.15, §12, §13.2, §8-blockquote duplicates.)
2. **Per command: ≤1 args table + ≤2 examples + one "gotchas:" bullet line.** More than that → the overflow is mechanism or history and moves out.
3. **No mechanism vocabulary in the body.** Ban `differ / emitter / prescan / extent / scratch buffer / byte-for-byte / R-xx / A-x / GEP-xx` from author prose. If a mechanism must be named: **one sentence + one spec link.**
4. **No inline version history.** Delete every `(since X)` / `Removed in X`; the masthead states one **Target version** and the author assumes the whole doc is true at that version. History lives in `CHANGELOG.md`.
5. **"Not needed for authoring" is a delete signal.** If the doc says it about a block (Appendix A, §3.3, §13.8 mechanism), that block belongs in spec/appendix, not the body.
6. **Examples are canonical and reused.** Ship exactly **one minimal** + **one full worked** example; the pattern index (§12) links to them instead of re-pasting snippets.

### 6.3 Cheat-sheet — **worth it [Hypothesized].** For the stated AI-agent reader, a ~40-line "1 screen" (empty animation/diagram skeleton, the 18 commands as one-liners, the 15 primitives as one-liners, the `shape.family[index]` selector grammar, and the 5 highest-frequency footguns — bare-`i`-in-selector, `True` vs `true`, 1-based CodePanel, `$$$`≡`$$`, no `\[...\]`) lets an agent emit correct `.tex` without scrolling 2000 lines, and turns §7/§8 into lookup rather than read-through. It replaces nothing; it front-loads the 80% path.

---

## 7. Open questions (≤5)

1. **Is the spec-set version drift (18 vs 14 commands; v0.23.1 / v0.5.0 / v0.3 titles) known and intended**, or are `ruleset.md`/`environments.md`/`primitives.md` stale parallel user-docs slated for demotion to pure mechanism? This decides whether §4.2 is "trim" or "delete."
2. **Who is the primary reader — an AI agent or a human author?** An agent tolerates (even prefers) a front cheat-sheet + terse lookup; a human may want the current narrative callouts. The 30% target assumes agent-first, matching the masthead.
3. **Fold vs delete for §9 and §13** — keep them in-file inside `<details>` (line count stays, scan cost drops) or move to a companion `cookbook.md`? Affects whether "one file" stays literally true.
4. **May history be centralized?** Removing 12 `(since X)` notes assumes a maintained `CHANGELOG.md`; confirm one exists and is authoritative before stripping.
5. **Is exact-CSS-token access (L917) ever an authoring need** (e.g. custom theming through `.tex`), or purely maintainer? If purely maintainer, that pointer can also go.
