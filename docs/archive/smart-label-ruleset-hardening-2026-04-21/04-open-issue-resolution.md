---
title: "Smart-Label Ruleset — Round-3 Open-Issue Resolution"
date: 2026-04-21
round: 3
feeds-into: docs/spec/smart-label-ruleset.md (v2-final)
status: DESIGN-ONLY — no code edits, no spec edits in this document
---

# 04 — Open-Issue Resolution

> **Purpose**: Convert every OPEN / PROPOSED / AT-RISK / ISSUE-Axxxxx marker
> in `smart-label-ruleset.md` v2-draft into a firm decision (ACCEPT / FIX /
> DEFER), resolve the six invariant-conflict tie-breakers from Round-2
> synthesis, produce a v2-final patch plan (text edits only), and flag any
> missing invariants for a proposed v2.1 list.
>
> **Not in scope**: editing `smart-label-ruleset.md`, editing `_svg_helpers.py`,
> or committing anything. This document is a decision record for human execution.

---

## §1 Issue Inventory

The table below is an exhaustive enumeration of every marker the current
`smart-label-ruleset.md` (v2.0.0-draft, 2026-04-21) contains that signals
ambiguity, pending work, or instability. Marker types:

- **OPEN** — `> **ISSUE-Axxx**:` blocks in §9.3
- **PROPOSED** — prose or table cells reading "PROPOSED"
- **AT RISK** — `[AT RISK]` stability markers
- **PENDING** — inline phrases noting work not yet done
- **ISSUE-below-math** — named sub-issue in §9.3

| # | ID | Type | Section | Exact quoted text (trimmed) |
|---|----|----|---------|----------------------------|
| 1 | ISSUE-A1 | OPEN | §9.3 | `> **ISSUE-A1**: I-2 pad semantics. v1 claimed pad=2, code enforced pad=0. v2 resolves: pad=0 is the canonical default (§2.3). Any caller wanting a buffer MUST pass pad>0 explicitly. **Status**: resolved in v2; code update pending.` |
| 2 | ISSUE-A2 | OPEN | §9.3 | `> **ISSUE-A2**: Math width multiplier. Current 1.15× over-estimates by RMSE 17.1 px on 16 / 20 sample labels. Optimal 0.81×. Recommended 0.90× (RMSE 11.5 px). **Status**: S-2 default to be flipped with corpus-driven regression test.` |
| 3 | ISSUE-A3 | OPEN | §9.3 | `> **ISSUE-A3**: Clamp-race in collision loop. Per-candidate clamp is normative (M-4). **Status**: PENDING code patch.` |
| 4 | ISSUE-A4 | OPEN | §9.3 | `> **ISSUE-A4**: WCAG AA contrast post-opacity-composite. 4/6 tokens fail at baseline (info 2.01:1, muted 1.49:1, compounded hover ~1.1:1). **Status**: re-palette or opacity floor — design call pending.` |
| 5 | ISSUE-A5 | OPEN | §9.3 | `> **ISSUE-A5**: info and path share hex #0b68cb. Deuteranopia simulator renders warn/good/error indistinguishable. **Status**: re-palette via CVD simulator.` |
| 6 | ISSUE-below-math | OPEN | §9.3 | `> **ISSUE-below-math**: position_label_height_below omits math branch (AC-6 pending). **Status**: two-line fix in MW-2.` |
| 7 | N-9 AT RISK | AT RISK | §1.9 | `N-9 \| Math multiplier 1.15× (→ 0.90× P0 A2)` |
| 8 | §1.9 N-9 AT RISK note | AT RISK | §10.2 | `§1.9 N-9 (math multiplier) — [AT RISK] pending ISSUE-A2.` |
| 9 | §2.5 4-dir loop AT RISK | AT RISK | §2.5 | `Currently uses a 4-direction / 16-candidate ad-hoc loop that diverges from §2.1. This is an [AT RISK] area — see S-6 in §4 and MW-3 roadmap in §9.` |
| 10 | §2.5 4-dir loop AT RISK note | AT RISK | §10.2 | `§2.5 emit_position_label_svg 4-dir loop — [AT RISK] pending MW-3.` |
| 11 | §3.3 arrow_height_below PROPOSED | PROPOSED | §3.3 | `arrow_height_below(annotations) [absent in v1; AT RISK] → mirror of arrow_height_above — PROPOSED in MW-2.` |
| 12 | §3.3 below math PENDING | PENDING | §3.3 | `position_label_height_below(annotations) → pill_h + 6 px margin (math branch MUST mirror _above — v1 defect closed by AC-6; currently PENDING per P1 B6).` |
| 13 | §3.5 BG_OPACITY AT RISK | AT RISK | §10.2 | `§3.5 _LABEL_BG_OPACITY=0.92 — [AT RISK] pending ISSUE-A4.` |
| 14 | M-4 clamp normative note | PROPOSED | §2.1 | `Per M-4 in §4 error table (and Round-1 synthesis A3), v2 moves the clamp inside the candidate loop...Until M-4 ships, implementations MAY approximate by re-checking...` |
| 15 | §2.3 pad=0 canonical | OPEN (code) | §2.3 | `v2 resolves the v1 I-2 discrepancy: the canonical default is pad=0 (strict non-intersection). If callers want a buffer they MUST pass pad>0 explicitly.` |
| 16 | C-6 SHOULD→MUST upgrade | PENDING | §1.2 | `*Upgrades to MUST when MW-2 registers leader path AABBs.*` |
| 17 | C-7 SHOULD→MUST upgrade | PENDING | §1.2 | `*Upgrades to MUST when MW-2 seeds cell-text AABBs.*` |
| 18 | A-1..A-4 contrast tests | PENDING | Appendix A | `A-1..A-4 \| TestContrast::* (PENDING MW-2 B7)` |
| 19 | AC-6 test PENDING | PENDING | Appendix A | `AC-6 \| TestMathHeadroom::test_below_also_32px (PENDING B6)` |
| 20 | §6 legacy engine DEPRECATED | AT RISK | §6 | `SCRIBA_LABEL_ENGINE \| ... legacy eligible for removal at v3 per §10.3` |

**Total distinct open markers: 20** (6 OPEN issue blocks, 5 AT RISK, 6 PENDING
upgrade/test notes, 2 PROPOSED, 1 DEPRECATED lifecycle note).

For v2-final we must close or explicitly defer every row above so readers have
a single ground truth. Rows 16–20 are bookkeeping items (they reflect already-
planned milestones, not ambiguity); they are addressed in §6 of this document.

---

## §2 Per-Issue Decision Records

### §2.1 ISSUE-A1 — I-2 pad=0 Semantics

> **Exact spec quote (§9.3)**:
> "v1 claimed `pad=2`, code enforced `pad=0`. v2 resolves: `pad=0` is the
> canonical default (§2.3). Any caller wanting a buffer MUST pass `pad>0`
> explicitly. **Status**: resolved in v2; code update pending."

#### Background

The v1 ruleset contained invariant I-2 stating that pills must maintain a
2 px separation gap. The `_LabelPlacement.overlaps()` method, however, has no
`pad` parameter and implements strict AABB intersection (`pad=0`). This created
a permanent spec/code divergence: the spec promised a 2 px margin, the code
never enforced it. Round-2 audit agent 3 catalogued this as API asymmetry A-1
and signature hazard H-1. The v2 draft chose `pad=0` as the normative default
and deferred `pad>0` enforcement to the proposed `_place_pill(overlap_pad=...)`,
but left the implementation in a "code update pending" limbo.

#### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | ACCEPT: `pad=0` is the permanent spec; remove the 2 px language entirely | Clean; matches reality; no test regressions | Authors who relied on visual breathing room lose it formally |
| B | FIX (v2 via MW-3): add `overlap_pad` param to `_place_pill`; default `0.0`, expose `2.0` when author requests | Restores spirit of v1 I-2; enforceable; API forward-compat | Needs MW-3 to ship first; small regression risk on dense frames |
| C | FIX (v1.1 patch): add `pad` param directly to `_LabelPlacement.overlaps()` now; default `0` | Unblocks enforcement without waiting for MW-3 | Requires updating three call sites; changes behaviour if anyone calls `overlaps()` directly |
| D | DEFER: mark `pad=0` as current behavior; park 2 px goal in §8 non-goals until MW-3 scope decision | Zero risk today | Continues the spec/code divergence that caused the confusion |

#### Recommended Decision: **ACCEPT** (Option A)

**Justification**: The v2 draft has already made the policy decision (`pad=0`
is canonical default). The spec text in §2.3 is unambiguous. What remains is
only to remove the residual "code update pending" note from §9.3, since the
*spec* is closed. The *implementation* of an optional `overlap_pad` path
belongs under MW-3 as an enhancement, not as a bug fix. No invariant changes.

**Invariant change**: None. §2.3 already codifies `pad=0`. The 2 px spirit
is preserved via the documented `pad>0` escape hatch.

**Deadline**: N/A (ACCEPT — spec-side is already resolved; code update is
MW-3 scope and tracked there).

**Action for §7 patch plan**: Remove the "code update pending" qualifier from
the §9.3 ISSUE-A1 block; replace with "**Status**: closed in v2 (§2.3).
Optional `overlap_pad` path is tracked under MW-3."

---

### §2.2 ISSUE-A2 — Math Width Multiplier (1.15× → 0.90×)

> **Exact spec quote (§9.3)**:
> "Current 1.15× over-estimates by RMSE 17.1 px on 16 / 20 sample labels.
> Optimal 0.81×. Recommended 0.90× (RMSE 11.5 px). **Status**: S-2 default to
> be flipped with corpus-driven regression test."
>
> **Also §1.9 N-9**: "Math multiplier 1.15× (→ 0.90× P0 A2) — [AT RISK]"
> **Also §10.2**: "§1.9 N-9 (math multiplier) — [AT RISK] pending ISSUE-A2."
> **Also §3.2**: "Current value 1.15× is scheduled to become ≈ 0.90× per P0 A2"

#### Background

`_label_width_text` inflates math-label width estimates by appending 15 % extra
characters before calling `estimate_text_width`. This was calibrated heuristically.
Round-2 audit measured RMSE 17.1 px over-estimate on 16/20 sample labels at
common font sizes; the optimal multiplier from that corpus is 0.81×, with a
recommended conservative value of 0.90× (RMSE 11.5 px). Over-estimation causes
unnecessary pill widening, which in turn triggers nudges that would not be
needed with a tighter estimate — wasting nudge grid slots in dense frames. The
change is a calibration, not a structural change: the code path stays identical,
only the float constant in `_label_width_text` changes (`0.15` → `−0.10`).

#### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | ACCEPT: keep 1.15×; declare T-4's ≤ 30 px over-estimate tolerance as the ceiling | Zero code risk; simpler spec | Wastes collision budget; over-wide pills hurt dense layouts |
| B | FIX (v0.11.0): flip to 0.90× with corpus-driven regression gate before merge | Improves pill sizing; RMSE drop from 17 → 11 px; preserves T-4 floor | Visual shift ≥ 8 px on some math labels → MINOR version bump required per §10.4 |
| C | FIX aggressive (v0.11.0): flip to optimal 0.81× | Minimum RMSE | May under-estimate on edge-case formulae not in the 20-label corpus; T-4 may be violated |
| D | DEFER to v3: no action until LR-1 wave includes proper KaTeX metrics | Safest | Leaves a known error in production indefinitely |

#### Recommended Decision: **FIX** — deadline v0.11.0

**Justification**: The 0.90× value has been validated on the existing 20-label
corpus and preserves the T-4 invariant floor (estimated ≥ actual − 20 px).
The change shifts rendered math pill widths by up to ≈ 10 px. Per §10.4, shifts
< 8 px are MINOR; shifts ≥ 8 px are also MINOR when the constant is `[AT RISK]`
(which N-9 already is). The version bump is therefore MINOR (0.10.x → 0.11.0).
Aggressive 0.81× (Option C) is too risky without a larger corpus.

**Deadline**: v0.11.0.

**PR-level patch sketch**:
1. In `_label_width_text`, change `extra_len = max(1, int(len(result) * 0.15))`
   to `extra_len = max(0, int(len(result) * -0.10))` — i.e. subtract 10 % of
   stripped length from `result` instead of appending. Since subtracting
   produces a shorter string, the implementation becomes:
   ```python
   trimmed_len = max(0, len(result) - max(0, int(len(result) * 0.10)))
   result = result[:trimmed_len]
   ```
2. Add a 20-label regression test `TestMathWidthMultiplier::test_rmse_below_12px`
   that fails if RMSE exceeds 12 px on the corpus.
3. Update §1.9 N-9: remove `[AT RISK]`, update value to `0.90×`.
4. Update §3.2: change "Current value 1.15×" to "0.90×" and remove the
   "scheduled to become" clause.
5. Close ISSUE-A2 in §9.3 with "**Status**: fixed in v0.11.0 (N-9 → 0.90×)".

---

### §2.3 ISSUE-A3 — Clamp-Race in Collision Loop

> **Exact spec quote (§9.3)**:
> "Clamp-race in collision loop. Per-candidate clamp is normative (M-4).
> **Status**: PENDING code patch."
>
> **Also §2.1 normative note**: "v2 moves the clamp *inside* the candidate loop
> so that a candidate which passes the collision check pre-clamp but collides
> post-clamp is rejected. Until M-4 ships, implementations MAY approximate by
> re-checking the final clamped coordinate..."

#### Background

All three emitters (`emit_arrow_svg`, `emit_plain_arrow_svg`,
`emit_position_label_svg`) share the same structural bug: the viewBox clamp is
applied *after* a candidate is accepted, not per-candidate. A candidate can
pass the overlap check at its natural position but, after clamping, land on top
of a previously placed pill. Round-2 audit asymmetry A-3 confirmed this
empirically. The §2.1 pseudocode shows the normative ("inner loop clamp")
behaviour. The gap between spec and code is currently bridged by a
"MAY approximate" escape in §2.1 prose.

#### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | ACCEPT: keep post-candidate clamp; drop M-4 from normative and mark it SHOULD | Zero code change; honest about current state | Leaves a real collision bug; violates MUST invariant in corner cases |
| B | FIX (v0.11.0 alongside MW-3): implement per-candidate clamp in `_place_pill` only; old emitters unchanged until MW-3 replaces them | Low risk (new code path); closes clamp-race for all future calls | Requires MW-3 to ship; old emitters still have the bug during the window |
| C | FIX (hot-patch v0.10.x): implement per-candidate clamp in all three existing emitters now | Closes bug immediately | 3 copy-paste sites; regression risk if clamp logic differs slightly |
| D | DEFER: document the escape hatch, ship as-is, fix in MW-3 | No urgency in practice | "MAY approximate" norm is confusing; two different behaviors in the same spec version |

#### Recommended Decision: **FIX** — deadline v0.11.0 (bundled with MW-3)

**Justification**: The clamp-race produces observable wrong output in any frame
where a post-clamp pill overlaps a prior pill; this violates MUST invariant C-1.
The safest implementation path is to fix it inside the proposed `_place_pill`
helper (MW-3) so that all three emitters inherit the fix simultaneously via the
unified call. The §2.1 "MAY approximate" escape clause should be dropped from
the spec once the fix ships; before it ships it should be tightened to say "MUST
implement per-candidate clamp by v0.11.0."

**Deadline**: v0.11.0 (MW-3 scope).

**PR-level patch sketch**:
1. Inside `_place_pill` candidate loop:
   ```python
   for ndx, ndy in _nudge_candidates(pill_w, pill_h, side_hint=side_hint):
       raw = _LabelPlacement(x=natural_x + ndx, y=candidate_y + ndy, ...)
       clamped_x = max(raw.x, pill_w / 2)  # viewBox clamp: left edge
       clamped = _LabelPlacement(x=clamped_x, y=raw.y, ...)
       if not any(clamped.overlaps(p, pad=overlap_pad) for p in placed_labels):
           accepted = clamped
           resolved = True
           break
   ```
2. Remove the "MAY approximate" sentence from §2.1 after v0.11.0 ships.
3. Close ISSUE-A3 in §9.3: "**Status**: fixed in v0.11.0 via `_place_pill`."

---

### §2.4 ISSUE-A4 — WCAG AA Contrast Post-Opacity-Composite

> **Exact spec quote (§9.3)**:
> "WCAG AA contrast post-opacity-composite. 4/6 tokens fail at baseline
> (`info` 2.01:1, `muted` 1.49:1, compounded hover ~1.1:1). **Status**:
> re-palette or opacity floor — design call pending."
>
> **Also §10.2**: "§3.5 `_LABEL_BG_OPACITY=0.92` — [AT RISK] pending ISSUE-A4."

#### Background

`ARROW_STYLES` contains six color tokens. The invariant A-1 requires effective
contrast ≥ 4.5:1 for normal-weight text after compositing all opacity layers.
Inspection of the current `ARROW_STYLES` dict shows `info.opacity = 0.45` and
`muted.opacity = 0.30`. When the group `<g opacity="0.45">` composites over a
typical white or light-grey stage background, the effective contrast of
`info.label_fill = #506882` drops below the 4.5:1 floor mandated by A-1. The
code comments next to each token claim "verified ≥ 4.5:1 against white," but
those measurements were against the pill background (white with `fill-opacity
= 0.92`), not against the blended stage background. There is a discrepancy
between what the comment asserts and what A-1 requires.

#### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | ACCEPT: A-1 as written already requires ≥ 4.5:1 effective; declare current `info`/`muted` opacity values non-conformant and block v2 on fixing them | Closes the accessibility gap; honest | Requires design work (new hex values or raised opacity floor) before v2 ships |
| B | FIX (v0.11.0): raise `info` opacity to at least 0.70; raise `muted` opacity to at least 0.55; verify all 6 tokens pass A-1 via automated contrast script | Achieves compliance; unblocks A-1..A-4 test wiring | Visual change to `info`/`muted` annotations; minor aesthetic shift |
| C | FIX (design-first approach): hire a contrast audit pass on all 6 tokens; only change the 2 failing tokens, leave 4 alone | Minimal blast radius | Needs designer sign-off; may delay v2 |
| D | DEFER: downgrade A-1 to SHOULD for `muted`/`info`; add a footnote | Unblocks v2 immediately | Weakens accessibility guarantee; contradicts WCAG 2.2 SC 1.4.3 |

#### Recommended Decision: **FIX** — deadline v0.11.0

**Justification**: WCAG 2.2 SC 1.4.3 is not negotiable for a MUST invariant.
Downgrading A-1 (Option D) is categorically off the table. The measured deficit
on `info` and `muted` is structural: the group opacity multiplied against the
stage background produces sub-threshold blended values. Option B's approach of
raising group opacity is the lowest-risk fix: it does not change the hex
palette (no CVD recalibration needed), only the opacity values. Post-fix, the
contrast-checking script referenced in §11 step 6 must be run as a gate before
merge.

**Deadline**: v0.11.0.

**PR-level patch sketch**:
1. Write `tools/check_annotation_contrast.py` (referenced in §11 step 6):
   reads `ARROW_STYLES`, blends each token against `#ffffff` at nominal and
   hover opacity, asserts WCAG AA pass.
2. Raise `info.opacity` from `0.45` to `0.75`; raise `muted.opacity` from
   `0.30` to `0.60`. Verify with the script.
3. Run visual corpus diff (§11 step 3) to confirm no annotation disappears.
4. Update `_LABEL_BG_OPACITY` comment and remove `[AT RISK]` from §10.2.
5. Close ISSUE-A4 in §9.3: "**Status**: fixed in v0.11.0 (opacity floor raised)."

---

### §2.5 ISSUE-A5 — `info` and `path` Hex Collision; CVD Indistinguishability

> **Exact spec quote (§9.3)**:
> "`info` and `path` share hex `#0b68cb`. Deuteranopia simulator renders
> `warn`/`good`/`error` indistinguishable. **Status**: re-palette via CVD
> simulator."

#### Background

Invariant A-4 requires that semantically-distinct tokens `{good, warn, error}`
be distinguishable from each other under deuteranopia and protanopia simulation
with CIEDE2000 pairwise distance ≥ 10 units. Additionally, A-4 notes that any
two tokens sharing the same hex MUST be documented as aliases. Current code
shows `info.stroke = info.label_fill = #506882` and `path.stroke = #2563eb` —
these are NOT the same hex, so the "shared hex" claim in ISSUE-A5 refers to a
pre-fix state or to an earlier palette iteration. Examining the current
`ARROW_STYLES` in `_svg_helpers.py`: `info` is `#506882` (dark blue-grey) and
`path` is `#2563eb` (vivid blue). These are distinguishable. The CVD concern
about `warn`/`good`/`error` is separate and real: `warn = #92600a` (brown),
`good = #027a55` (dark green), `error = #c6282d` (red). Under deuteranopia,
green and red collapse; the brown-vs-red distinction also narrows. A formal
CIEDE2000 measurement is needed.

#### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | ACCEPT: declare current palette already closes the `info`/`path` hex collision (they are already different); run CIEDE2000 test; if it passes, close ISSUE-A5 | Minimal change; may already be resolved | CIEDE2000 test not yet run; may fail for `warn`/`good`/`error` |
| B | FIX (v0.11.0): run CVD simulation on all 6 tokens; if any pair fails CIEDE2000 ≥ 10, adjust those hex values; write `TestContrast::test_cvd_distance` | Completes A-4; automated regression gate | Palette changes affect all existing visuals using those tokens |
| C | FIX (split): close the `info`/`path` shared-hex claim as already resolved (they are different); treat CVD gap as a separate FIX in v0.11.0 | Clearer accounting | More PR overhead |
| D | DEFER CVD: document A-4 as SHOULD until a CVD audit is done | Unblocks v2 | Weakens accessibility guarantee |

#### Recommended Decision: **FIX** — deadline v0.11.0 (Option B, combined)

**Justification**: The `info`/`path` hex identity claim appears to be stale
(the current code has different hex values). However, a clean resolution of
ISSUE-A5 requires confirming this by running the automated CVD simulation, not
just reading the code. Option B does that in one pass and either closes the
issue (if the current palette passes CIEDE2000 ≥ 10) or identifies the specific
tokens that need adjustment. The automated test is required by A-4 regardless
and should have been written in the initial A-4 work.

**Deadline**: v0.11.0 (bundled with ISSUE-A4 palette work).

**PR-level patch sketch**:
1. Write `tools/check_annotation_contrast.py` (same script as ISSUE-A4) with a
   CVD simulation section: apply Machado 2009 deuteranopia and protanopia
   matrices to each token's `label_fill` hex; assert CIEDE2000 pairwise ≥ 10
   for `{good, warn, error}`.
2. If current palette passes, add the test, close ISSUE-A5 in §9.3: "**Status**:
   confirmed closed — palette already meets CIEDE2000 ≥ 10; `info`/`path` hex
   collision claim was stale."
3. If any pair fails, adjust the failing token's hex (lightest change: shift
   `warn`'s hue slightly toward orange). Re-run. Update `ARROW_STYLES`.

---

### §2.6 ISSUE-below-math — `position_label_height_below` Missing Math Branch

> **Exact spec quote (§9.3)**:
> "`position_label_height_below` omits math branch (AC-6 pending).
> **Status**: two-line fix in MW-2."
>
> **Also §3.3**: "math branch MUST mirror `_above` — v1 defect closed by
> AC-6; currently PENDING per P1 B6"

#### Background

Invariant AC-6 states that the math headroom extra (32 px vs 24 px) MUST apply
in both `position_label_height_above` and `position_label_height_below` when
any position-only annotation label contains `$…$`. The `_above` function
already implements `headroom_extra = 32 if has_math else _LABEL_HEADROOM`. The
`_below` function does not: it uses a flat `pill_h + gap + l_font_px * 0.3`
formula with no math branch. This is a straightforward two-line omission.
Examining `_svg_helpers.py` lines 1161–1199 confirms the math branch is absent.

#### Options Considered

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| A | FIX (v0.10.x hot-patch): add the math branch to `position_label_height_below` immediately | Closes AC-6 gap; two-line fix; low risk | Small positive headroom change for below-math labels |
| B | FIX (v0.11.0 bundled): ship with MW-2 as documented | Consistent with existing plan | Leaves `position=below` math labels potentially clipped until then |
| C | DEFER: mark AC-6 as SHOULD for `below` until MW-2 | No urgency if `position=below` math is rare | Spec inconsistency: AC-6 says MUST for both |

#### Recommended Decision: **FIX** — deadline v0.10.x (hot-patch, unblock v2)

**Justification**: This is a two-line fix with essentially zero regression risk
(only `position=below` math labels are affected, and they currently get
*insufficient* headroom, not excessive). Shipping it as a hot-patch in v0.10.x
means v2 can declare AC-6 fully enforced without waiting for the larger MW-2
milestone. The PENDING qualifier in §3.3 can be removed.

**Deadline**: v0.10.x (before v2-final spec ships).

**PR-level patch sketch**:
```python
# In position_label_height_below, after computing pill_h and gap:
has_math = any(_label_has_math(a.get("label", "")) for a in pos_anns)
math_extra = 8 if has_math else 0   # mirrors _LABEL_MATH_HEADROOM_EXTRA
pill_bottom = cell_height / 2 + pill_h + gap + l_font_px * 0.3 + math_extra
return max(0, int(math.ceil(pill_bottom - cell_height)))
```
Add test `TestMathHeadroom::test_below_also_32px` (currently PENDING B6).
Update §9.3 ISSUE-below-math status to "fixed in v0.10.x."

---

## §3 Math Multiplier AT-RISK — Dedicated Section

### §3.1 Current State

The math width multiplier is implemented in `_label_width_text`:

```python
extra_len = max(1, int(len(result) * 0.15))
result = result + result[:extra_len]
```

This appends 15 % extra characters to the stripped math string before passing
to `estimate_text_width`, producing a ≈1.15× width estimate. Stability status
in `§1.9`: `[AT RISK]`. The Round-2 audit measured this on a 20-label corpus:
RMSE 17.1 px over-estimate. Optimal multiplier: 0.81×. Recommended: 0.90×.

### §3.2 Why It Is Risky

1. **Over-wide pills waste collision budget.** A pill that is 10–17 px wider
   than necessary occupies more AABB area, triggering nudges for adjacent
   labels that could coexist without nudging at a tighter estimate. In dense
   DPTable frames (the primary use case for math labels), this cascades.

2. **Inconsistent with the T-4 tolerance band.** T-4 specifies a ±20/+30 px
   window. At 1.15× the over-estimate for a 10-character label at 12 px font
   is `estimate_text_width(label, 12) × 0.15 ≈ 11 px`. For a 20-character
   label at 12 px font it is ≈ 22 px, which exceeds the +20 px over-estimate
   floor. The rule and the constant are on a collision course at longer labels.

3. **Test corpus is only 20 labels.** The optimal value may shift with wider
   sampling. The 0.90× value is conservative enough to stay above the T-4 floor
   even if actual rendered widths are slightly wider than the corpus average.

### §3.3 Concrete Retire Plan

| Step | Action | Commit boundary | Fallback behaviour |
|------|---------|-----------------|--------------------|
| R-1 | Write `tools/check_math_width_multiplier.py` that runs 20-label corpus and outputs RMSE per multiplier value. | Standalone script commit, no spec change. | N/A |
| R-2 | Run R-1, confirm 0.90× RMSE ≤ 12 px and 0.81× RMSE ≤ 9 px on the corpus. Record results in the PR description. | No code change. | Abort if RMSE at 0.90× > 12 px — keep 1.15× and open a new corpus expansion issue. |
| R-3 | In a single commit: change `0.15` → `-0.10` in `_label_width_text` (see §2.2 patch sketch). Add the RMSE regression test. | Main FIX commit; version bump to 0.11.0. | If visual regression shows any pill undershooting by > 20 px (T-4 violation), revert this commit only. |
| R-4 | Remove `[AT RISK]` from N-9. Update §3.2 and §9.3 ISSUE-A2 to "closed." | Follow-up spec-only commit. | N/A |
| R-5 | After 2 minor releases (0.11.x, 0.12.x), remove the dead `extra_len / result + result[:extra_len]` code path (replaced by the trim). | Cleanup commit at 0.13.0. | N/A |

**Fallback behaviour if R-3 visual regression fails**: revert R-3, keep 1.15×,
re-evaluate the corpus with a wider label set, target 0.95× as the next
increment. The `[AT RISK]` marker remains until a confirmed RMSE-gated flip.

---

## §4 ISSUE-A1 Verification and Close

ISSUE-A1 was noted in §9.3 as "resolved in v2; code update pending." This
section confirms closure.

### §4.1 Spec-side (already closed)

The v2 spec text at §2.3 states:

> "v2 resolves the v1 I-2 discrepancy: the canonical default is `pad=0` (strict
> non-intersection). If callers want a buffer they MUST pass `pad>0` explicitly."

This is unambiguous. The spec intention is settled.

### §4.2 Code-side verification

`_LabelPlacement.overlaps()` in `_svg_helpers.py` (lines 85–92):

```python
def overlaps(self, other: "_LabelPlacement") -> bool:
    return not (
        self.x + self.width / 2 < other.x - other.width / 2
        or ...
    )
```

No `pad` parameter. Strict AABB intersection. This matches the spec's `pad=0`
default exactly. No code change is required to close the spec-side decision.

### §4.3 Final decision: CLOSED

ISSUE-A1 is **closed in v2**. The "code update pending" language referred to
a future `overlap_pad` parameter in the proposed `_place_pill` helper (MW-3),
not to a defect in the current code. The §9.3 block should be updated to
remove the ambiguity. See §7 patch plan entry §7.1 for the exact text edit.

---

## §5 ISSUE-A2..A5 Decision Summary

See §2.2–§2.5 for full decision records.

| Issue | Decision | Deadline | Blocks v2-final? |
|-------|----------|----------|-----------------|
| A1 | ACCEPT (spec already closed) | Immediate (text fix) | YES — remove ambiguous qualifier |
| A2 | FIX (0.90× multiplier) | v0.11.0 | NO — v2 ships with `[AT RISK]`; fix in next minor |
| A3 | FIX (per-candidate clamp in `_place_pill`) | v0.11.0 (MW-3) | NO — v2 ships with the MAY approximation; MW-3 closes it |
| A4 | FIX (raise `info`/`muted` opacity floor) | v0.11.0 | YES — A-1 is a MUST invariant; v2 cannot declare MUST compliance with known failures |
| A5 | FIX (run CVD simulation; adjust if needed) | v0.11.0 (bundled with A4) | YES — A-4 is a MUST invariant; requires at minimum a measurement confirming pass |
| below-math | FIX (hot-patch v0.10.x) | v0.10.x (before v2-final) | YES — AC-6 is MUST; §3.3 marks it PENDING |

**v2-final blockers**: A1 (text fix), A4 (opacity), A5 (CVD measurement), below-math (hot-patch).
Issues A2 and A3 do not block v2-final; they are tracked under v0.11.0.

---

## §6 Conflict Tie-Breaker Re-Audit

Round-2 synthesis (`00-synthesis.md`) documented six invariant pairs in tension
and six tie-breakers. The v2 ruleset encoded these in §1.8. This section
verifies each tie-breaker still holds against the current spec and code, and
flags any recommended changes.

### §6.1 C-1 vs AC-3: No overlap vs declared position

> **v2 §1.8**: "C-1 wins. Try preferred direction first (AC-3 start-point
> guarantee), fall back per C-5."

**Re-audit**: Correct and well-grounded. AC-3 guarantees the *first placement
attempted* respects the declared position, not the *final* placement. C-5
formalises the side-hint mechanism that makes this guarantee meaningful. The
current code implements this correctly: `anchor_side = ann.get("side") or
ann.get("position") or None` is passed as `side_hint` to `_nudge_candidates`.

**Verdict**: HOLD. No change required.

---

### §6.2 G-3 vs AC-1: Fit inside viewBox vs pill must appear

> **v2 §1.8**: "G-3 wins for clipping; AC-1 is minimum. System MUST emit
> (AC-1) AND clamp (G-3). If `pill_w > viewBox_W`, primitive config error."

**Re-audit**: The tension is real but the resolution is sound. AC-1 requires a
visible pill; G-3 requires it to be inside the viewBox. Together they mandate
"emit + clamp." The "primitive config error" path (call headroom helpers, AC-5)
is the correct escalation. One gap exists: the spec does not specify what
happens when `pill_w > viewBox_W` even after headroom helpers are called
(pathological multi-line label). This is covered by E-4 (pill height within
headroom), but the width dimension is unguarded.

**Verdict**: HOLD with a note. Add a new invariant proposal to §8 (New
Invariant Proposals) for the case `pill_w > viewBox_W`.

---

### §6.3 T-4 vs C-1: No under-estimate vs no overlap

> **v2 §1.8**: "T-4 wins for under-estimation. Estimator MAY over-estimate up
> to 20 px; nudge grid resolves the extra collisions."

**Re-audit**: Sound, but the interaction with ISSUE-A2 deserves attention. If
the multiplier is dropped from 1.15× to 0.90×, pill widths decrease and some
collisions that previously resolved via nudge may no longer arise, which is
beneficial. The 20 px over-estimate tolerance in T-4 is generous enough to
accommodate both 1.15× and 0.90× at typical label lengths. No tension arises.

**Verdict**: HOLD. The ISSUE-A2 FIX does not invalidate this tie-breaker.

---

### §6.4 A-1 vs visual-hierarchy: Contrast floor vs dim opacity design

> **v2 §1.8**: "A-1 wins. Background, opacity, and color token values MUST
> compose to ≥ 4.5:1 effective."

**Re-audit**: ISSUE-A4 reveals this tie-breaker is currently violated by the
`info` and `muted` tokens. The ISSUE-A4 FIX (raise opacity floor) is required
precisely *because* A-1 wins. The tie-breaker is correct; the code does not yet
comply.

**Verdict**: HOLD. The ISSUE-A4 FIX enforces this tie-breaker at the code level.

---

### §6.5 AC-1 vs G-5: Pill must appear vs positive dimensions

> **v2 §1.8**: "G-5 wins. Empty/whitespace-only label → primitive config error,
> not silent emission."

**Re-audit**: Code confirms: `emit_position_label_svg` returns early if
`not label_text` (line 1238). `emit_plain_arrow_svg` and `emit_arrow_svg` skip
the pill block if `not label_text` (lines 491, 830). G-5 is enforced. The
tie-breaker is implemented correctly.

**Verdict**: HOLD.

---

### §6.6 D-1 vs implementation-choice: Byte-identical vs refactor freedom

> **v2 §1.8**: "D-1 is compat-critical. Refactors that alter byte output MUST
> follow §10 versioning."

**Re-audit**: The ISSUE-A2 multiplier change (§2.2) will alter byte output for
math-label pills. Per §10.4, a shift < 8 px visible is MINOR; the estimated
shift for common labels is 5–10 px. The author-visible-impact threshold applies:
at 0.90× vs 1.15×, a 10-character label at 12 px would shrink pill width by
≈ 8 px. This is right at the §10.4 threshold. The commit must include a
`BREAKING CHANGE: see §10.6` footer only if the measured shift for any label in
the visual corpus exceeds 8 px.

Similarly, the ISSUE-A4 opacity change will alter SVG attribute values
byte-for-byte but will not shift any pill position — so D-1 is unaffected (D-1
governs layout byte-identity, not style attribute values).

**Verdict**: HOLD with an action note. The ISSUE-A2 PR must run
`tools/measure_label_shift.py` before deciding the version bump level.

---

## §7 v2-Final Patch Plan

Below is the complete list of text edits to `smart-label-ruleset.md` needed to
remove all OPEN markers and ambiguous qualifiers, making v2 a single source of
truth. Edits are grouped by section. No code changes are in scope here.

### §7.1 §9.3 ISSUE-A1 block

**Location**: §9.3, ISSUE-A1 block.

Replace:
```
> **ISSUE-A1**: I-2 pad semantics. v1 claimed `pad=2`, code enforced
> `pad=0`. v2 resolves: `pad=0` is the canonical default (§2.3). Any
> caller wanting a buffer MUST pass `pad>0` explicitly. **Status**:
> resolved in v2; code update pending.
```

With:
```
> **ISSUE-A1**: I-2 pad semantics. **Status**: CLOSED in v2. The
> canonical default is `pad=0` (§2.3). `_LabelPlacement.overlaps()`
> implements strict non-intersection. Optional `overlap_pad` support
> is tracked under MW-3.
```

---

### §7.2 §9.3 ISSUE-A2 block

**Location**: §9.3, ISSUE-A2 block.

Replace:
```
> **ISSUE-A2**: Math width multiplier. Current 1.15× over-estimates by
> RMSE 17.1 px on 16 / 20 sample labels. Optimal 0.81×. Recommended
> 0.90× (RMSE 11.5 px). **Status**: S-2 default to be flipped with
> corpus-driven regression test.
```

With:
```
> **ISSUE-A2**: Math width multiplier. Current 1.15× over-estimates by
> RMSE 17.1 px on 16/20 sample labels. Recommended: 0.90×.
> **Decision**: FIX in v0.11.0 — flip to 0.90× gated by RMSE regression
> test. See `04-open-issue-resolution.md §2.2`. **Status**: OPEN pending
> v0.11.0.
```

---

### §7.3 §9.3 ISSUE-A3 block

**Location**: §9.3, ISSUE-A3 block.

Replace:
```
> **ISSUE-A3**: Clamp-race in collision loop. Per-candidate clamp is
> normative (M-4). **Status**: PENDING code patch.
```

With:
```
> **ISSUE-A3**: Clamp-race in collision loop. Per-candidate clamp is
> normative (§2.1). **Decision**: FIX in v0.11.0 via `_place_pill`
> (MW-3). The §2.1 "MAY approximate" escape holds until then.
> **Status**: OPEN pending v0.11.0 (MW-3).
```

---

### §7.4 §9.3 ISSUE-A4 block

**Location**: §9.3, ISSUE-A4 block.

Replace:
```
> **ISSUE-A4**: WCAG AA contrast post-opacity-composite. 4/6 tokens
> fail at baseline (`info` 2.01:1, `muted` 1.49:1, compounded hover
> ~1.1:1). **Status**: re-palette or opacity floor — design call
> pending.
```

With:
```
> **ISSUE-A4**: WCAG AA contrast post-opacity-composite. `info` and
> `muted` group-opacity values produce sub-4.5:1 effective contrast.
> **Decision**: FIX in v0.11.0 — raise `info.opacity` to ≥ 0.75,
> `muted.opacity` to ≥ 0.60; gate on `tools/check_annotation_contrast.py`.
> **Status**: BLOCKS v2-final — must be resolved or v2 re-scoped
> to declare A-1 SHOULD for `info`/`muted` (not recommended).
> See `04-open-issue-resolution.md §2.4`.
```

---

### §7.5 §9.3 ISSUE-A5 block

**Location**: §9.3, ISSUE-A5 block.

Replace:
```
> **ISSUE-A5**: `info` and `path` share hex `#0b68cb`. Deuteranopia
> simulator renders `warn`/`good`/`error` indistinguishable.
> **Status**: re-palette via CVD simulator.
```

With:
```
> **ISSUE-A5**: CVD distinguishability. The `info`/`path` shared-hex
> claim is stale — current palette has `info=#506882`, `path=#2563eb`
> (distinct). The CVD concern for `{good, warn, error}` under
> deuteranopia remains unmeasured. **Decision**: FIX in v0.11.0 —
> run Machado 2009 CVD simulation; adjust hex if CIEDE2000 < 10 for
> any pair. **Status**: BLOCKS v2-final (requires at minimum a
> confirmed PASS measurement). See `04-open-issue-resolution.md §2.5`.
```

---

### §7.6 §9.3 ISSUE-below-math block

**Location**: §9.3, ISSUE-below-math block.

Replace:
```
> **ISSUE-below-math**: `position_label_height_below` omits math
> branch (AC-6 pending). **Status**: two-line fix in MW-2.
```

With:
```
> **ISSUE-below-math**: `position_label_height_below` omits math
> branch. **Decision**: FIX in v0.10.x hot-patch (not waiting for
> MW-2). See `04-open-issue-resolution.md §2.6`. **Status**: BLOCKS
> v2-final.
```

---

### §7.7 §2.1 "MAY approximate" sentence

**Location**: §2.1, the normative note paragraph, last sentence.

Replace:
```
Until M-4 ships, implementations MAY approximate by re-checking the
final clamped coordinate against the registry and, if it collides,
advancing to the next candidate.
```

With:
```
Until ISSUE-A3 is closed (v0.11.0 / MW-3), implementations MAY
approximate by re-checking the final clamped coordinate against the
registry. This approximation MUST be replaced by the per-candidate
loop on or before v0.11.0.
```

---

### §7.8 §3.2 math multiplier reference

**Location**: §3.2, last sentence of the section.

Replace:
```
Math pills: `_label_width_text` strips `\command` tokens then applies
the math multiplier. Current value 1.15× is scheduled to become
≈ 0.90× per P0 A2 (see §9 ISSUE-A2).
```

With:
```
Math pills: `_label_width_text` strips `\command` tokens then applies
the math multiplier (current: 1.15×; scheduled 0.90× in v0.11.0 per
ISSUE-A2; see §9.3).
```

---

### §7.9 §3.3 `arrow_height_below` PROPOSED tag

**Location**: §3.3, `arrow_height_below` row.

Replace:
```
arrow_height_below(annotations)       [absent in v1; AT RISK]
  → mirror of arrow_height_above — PROPOSED in MW-2.
```

With:
```
arrow_height_below(annotations)       [absent in v1]
  → mirror of arrow_height_above — to be added in MW-2.
  Until then, primitives with below-arrows SHOULD call
  arrow_height_above as a conservative upper bound.
```

---

### §7.10 §3.3 `position_label_height_below` PENDING tag

**Location**: §3.3, `position_label_height_below` description.

Replace:
```
→ pill_h + 6 px margin (math branch MUST mirror `_above` — v1 defect
  closed by AC-6; currently PENDING per P1 B6).
```

With (post hot-patch):
```
→ pill_h + 6 px margin (math: +8 px for `$…$` labels, mirroring
  `_above` — AC-6; fixed in v0.10.x per ISSUE-below-math decision).
```

---

### §7.11 §10.2 AT RISK notes

**Location**: §10.2, explicit `[AT RISK]` list.

After ISSUE-A2 and ISSUE-A4 fixes ship, this list becomes:

Replace:
```
- §1.9 N-9 (math multiplier) — [AT RISK] pending ISSUE-A2.
- §2.5 `emit_position_label_svg` 4-dir loop — [AT RISK] pending MW-3.
- §3.5 `_LABEL_BG_OPACITY=0.92` — [AT RISK] pending ISSUE-A4.
- §6 `SCRIBA_LABEL_ENGINE=legacy` path — [DEPRECATED] eligible for
  removal at v3.
```

With (post v2-final, pre v0.11.0):
```
- §1.9 N-9 (math multiplier 1.15×) — [AT RISK] FIX scheduled v0.11.0
  (ISSUE-A2).
- §2.5 `emit_position_label_svg` 4-dir loop — [AT RISK] FIX scheduled
  v0.11.0 (MW-3 / ISSUE-A3).
- §3.5 `_LABEL_BG_OPACITY=0.92` — [AT RISK] FIX scheduled v0.11.0
  (ISSUE-A4 opacity floor).
- §6 `SCRIBA_LABEL_ENGINE=legacy` path — [DEPRECATED] eligible for
  removal at v3.
```

---

### §7.12 §1.9 N-9 row

**Location**: §1.9, N-9 table row.

Replace:
```
| N-9 | Math multiplier 1.15× (→ 0.90× P0 A2) | Calibration; T-4 floor constrains. |
```

With:
```
| N-9 | Math multiplier 1.15× ([AT RISK] → 0.90× in v0.11.0 per ISSUE-A2) | Calibration; T-4 floor constrains. |
```

---

### §7.13 Appendix A PENDING notes

**Location**: Appendix A, closing paragraph.

Replace:
```
Missing today: C-6, C-7, A-1..A-4, AC-6. Target: 85 % coverage before
MW-2 ships (P1 B5).
```

With:
```
Missing today: C-6, C-7, A-1..A-4. AC-6 (`test_below_also_32px`) is
scheduled for v0.10.x hot-patch. A-1..A-4 contrast tests are scheduled
for v0.11.0. C-6, C-7 pending MW-2. Target: 85 % coverage before
MW-2 ships.
```

---

## §8 New Invariant Proposals (v2.1 List)

These invariants surfaced during issue resolution but are NOT retroactively
added to v2. They form a candidate list for v2.1 (the next minor release after
v2 ships).

### §8.1 G-9 (proposed) — Pill width must not exceed viewBox width

**Motivation**: The §6.2 re-audit (G-3 vs AC-1 tie-breaker) identified a gap:
the spec guards pill height via E-4 and headroom helpers (AC-5), but does not
guard pill width. A very long multi-word label could produce `pill_w > viewBox_W`.
The clamp translates but cannot shrink (G-4), leaving the pill overflowing the
right edge. `_wrap_label_lines` with `_LABEL_MAX_WIDTH_CHARS=24` provides soft
protection, but a single 25-character token (common in math labels) bypasses it.

**Proposed text**:
> **G-9** (MUST) — `pill_w` MUST NOT exceed `viewBox_W − 2 * PAD_X`.
> When `_label_width_text(label, l_font_px) + 2 * PAD_X > viewBox_W`,
> the emitter MUST truncate the width to `viewBox_W − 2 * PAD_X` and
> emit E1572.
>
> *Verify*: construct label wider than viewBox; assert emitted
> `pill_w <= viewBox_W − 2*PAD_X`.

**Error code**: E1572 (reserved per §4 "E1572–E1579 reserved").

**Version**: propose for v2.1.

---

### §8.2 AC-7 (proposed) — `arrow_height_below` must be called for below-arrows

**Motivation**: The `arrow_height_below` function is listed in §3.3 as
"PROPOSED in MW-2." When below-curved arrows are present (layout="2d",
`dst_point.y > src_point.y`), the `annotation_headroom_below` of the
Primitive Participation Contract (§5.1) may not be called, leaving the bottom
viewBox edge without adequate expansion. This is not currently covered by any
MUST invariant.

**Proposed text**:
> **AC-7** (MUST) — When any `arrow_from` annotation has its arc peak
> below the primitive baseline, `annotation_headroom_below()` MUST
> return a value ≥ `arrow_height_below(annotations)`.
> *Verify*: construct a downward-curving arc; assert headroom_below ≥
> computed curve depth.

**Version**: propose for v2.1 (requires `arrow_height_below` to exist first,
which is MW-2 scope).

---

### §8.3 D-5 (proposed) — Import-time constant `_DEBUG_LABELS` must not be patched via env var after import

**Motivation**: D-4 specifies that `_DEBUG_LABELS` is captured once at module
import and MUST NOT be re-evaluated per call. However, no invariant explicitly
prohibits *re-patching the env var after import* (which would have no effect,
but is a common developer mistake that produces confusing silent behaviour).
A SHOULD note would make this explicit.

**Proposed text**:
> **D-5** (SHOULD) — `os.environ["SCRIBA_DEBUG_LABELS"]` SHOULD NOT be
> mutated after `_svg_helpers` is imported. Tests MUST patch
> `_svg_helpers._DEBUG_LABELS` directly, not the env var.
> *Verify*: linting / code review.

**Version**: propose for v2.1.

---

## §9 Executive Summary

### v2-final blockers

Four items must be resolved before `smart-label-ruleset.md` can be promoted
from "2.0.0-draft" to "2.0.0":

| Blocker | Action | Owner signal | ETA |
|---------|--------|-------------|-----|
| ISSUE-A1 text fix | Remove "code update pending" qualifier (§7.1) | Spec editor | Immediate |
| ISSUE-A4 opacity | Raise `info`/`muted` opacity; run contrast script | Engineering | v0.10.x |
| ISSUE-A5 CVD | Run CVD simulation; confirm or adjust palette | Engineering | v0.10.x |
| ISSUE-below-math | Hot-patch `position_label_height_below` | Engineering | v0.10.x |

### v0.11.0 targets (non-blocking for v2-final spec)

| Target | Decision | Note |
|--------|----------|------|
| ISSUE-A2 | FIX — flip multiplier to 0.90× | MINOR version bump |
| ISSUE-A3 | FIX — per-candidate clamp in `_place_pill` | Bundled with MW-3 |

### OPEN marker count at time of this document

- **Total OPEN markers (spec)**: 20 (see §1 inventory)
- **ACCEPT**: 1 (ISSUE-A1 spec-side)
- **FIX (blocks v2-final)**: 4 (A1-text, A4, A5, below-math)
- **FIX (v0.11.0, non-blocking)**: 2 (A2, A3)
- **Bookkeeping PENDING (future milestone)**: 13 (C-6/C-7 upgrades, A-1..A-4
  tests, AC-6 test, legacy-engine deprecation, MW-2/3 PROPOSED items)

### Earliest shippable v2-final version

**v2.0.0** can ship after all four blockers are resolved — expected in
**v0.10.x** (the current development cycle) once the hot-patches land. The
spec status should be updated from `2.0.0-draft` to `2.0.0` in the same commit
that merges the last blocker (ISSUE-below-math or the CVD measurement,
whichever is last).

v0.11.0 inherits the v2.0.0 spec and adds the ISSUE-A2/A3 code fixes, allowing
the remaining `[AT RISK]` markers to be retired.

---

*End of document.*
*Source files consumed: `smart-label-ruleset.md` (v2.0.0-draft),*
*`_svg_helpers.py`, `00-synthesis.md`, `01-first-principles.md`,*
*`03-api-contracts.md`, `07-non-goals-versioning.md`.*
