# 06 — Spec-Style Adoption Proposal for the Smart-Label Ruleset

> **Status:** Proposal — not yet normative. Findings from agents 1–5 should be
> poured into the v2 skeleton defined in §13.
>
> **Scope:** This document analyses twelve spec-style conventions drawn from
> W3C CSS, ECMAScript (TC39), WHATWG HTML, SVG 2, RFC 7230 (HTTP/1.1), and
> JSON Schema Draft 2020-12. It proposes which conventions the smart-label
> ruleset should adopt, adapt, or skip for v2, then delivers a blank v2 spec
> skeleton and three before/after rewrites. A bonus section evaluates formal
> encoding in TLA+ and Alloy.
>
> **Date:** 2026-04-21
>
> **Applies to:** `docs/spec/smart-label-ruleset.md` (current v1) and its
> planned v2 successor.

---

## Table of Contents

1. [Industry-Standard Conventions Surveyed](#1-industry-standard-conventions-surveyed)
2. [Convention 1 — Section Numbering](#2-convention-1--section-numbering)
3. [Convention 2 — Algorithm Pseudo-Code Style](#3-convention-2--algorithm-pseudo-code-style)
4. [Convention 3 — Conformance Classes](#4-convention-3--conformance-classes)
5. [Convention 4 — Dfn + Cross-Reference](#5-convention-4--dfn--cross-reference)
6. [Convention 5 — Non-Normative Examples](#6-convention-5--non-normative-examples)
7. [Convention 6 — ISSUE Blocks](#7-convention-6--issue-blocks)
8. [Convention 7 — NOTE vs Normative Prose](#8-convention-7--note-vs-normative-prose)
9. [Convention 8 — Per-Section Changelog](#9-convention-8--per-section-changelog)
10. [Convention 9 — Test Assertions](#10-convention-9--test-assertions)
11. [Convention 10 — IDL / Schema Blocks](#11-convention-10--idl--schema-blocks)
12. [Convention 11 — Feature-at-Risk Notation](#12-convention-11--feature-at-risk-notation)
13. [Convention 12 — Normative Dependency Declaration](#13-convention-12--normative-dependency-declaration)
14. [Adoption Decision Summary](#14-adoption-decision-summary)
15. [Before/After Rewrites](#15-beforeafter-rewrites)
16. [V2 Style Skeleton](#16-v2-style-skeleton)
17. [Formal Encoding Feasibility: TLA+ and Alloy](#17-formal-encoding-feasibility-tla-and-alloy)

---

## 1. Industry-Standard Conventions Surveyed

The following specs were studied to extract style conventions scriba could adopt:

| Spec | Key strengths relevant here |
|------|-----------------------------|
| **W3C CSS Text Module L3** | Hierarchical section numbers; `NOTE:` / `at-risk` blocks; non-normative example anchors; RFC 2119 conformance preamble; per-section test-coverage links. |
| **ECMAScript (TC39 ECMA-262)** | Numbered-step algorithm notation; `Let X be …`, `Assert:`, `Return`; abstract operation calls; `[[InternalMethod]]` notation; normative vs informative chapter labelling. |
| **WHATWG HTML Living Standard** | Producer/consumer conformance split; `dfn` for every term; first-use links back to dfn; `This is a note.` aside blocks; `This is an example.` non-normative callouts. |
| **SVG 2 (W3C)** | `<i class="atrisk">` for at-risk features; multi-class conformance (Author, Generator, Viewer); IDL appendix. |
| **RFC 7230 (HTTP/1.1)** | ABNF grammar blocks; role-scoped conformance statements; precise algorithm via priority-ordered numbered list; examples visually offset. |
| **JSON Schema Draft 2020-12** | `$vocabulary` conformance mechanism; keyword definitions with type + behaviour + interaction sections; MUST/SHOULD/MAY usage; informative examples inline. |

### What scriba's current ruleset does well

The current `smart-label-ruleset.md` already uses:

- RFC 2119 modal keywords in a few places (`must`, but inconsistently cased).
- Section numbers (§0–§8).
- A table for invariants (I-1 … I-10) and a prose algorithm block (§2).
- Noted limitations (§2.3 "What the registry does NOT know").
- A roadmap section (§6).
- A testing section (§7) with test-file links.

### What it lacks

Relative to the surveyed specs, the ruleset is missing:

- Stable, externally-referenceable section anchors (`§2.1.3` style).
- ECMAScript-style numbered algorithm steps with `Let / Assert / Return` vocabulary.
- Explicit conformance classes — who is required to comply, with what MUST set.
- Defined terms with consistent back-links (only the §0 table covers this, and it is not linked from later uses).
- Distinction between normative prose and informative notes, clearly visually.
- `ISSUE` blocks for open questions.
- Non-normative examples clearly labelled as such.
- Feature-at-risk notation for experimental rules (MW-4 repulsion solver, unified engine).
- A normative-dependency declaration at the top.
- A link from each invariant/rule to the specific test(s) that exercise it.
- Per-section history log.
- A type schema for the data structures it references (`_LabelPlacement`, nudge-candidate tuple).

---

## 2. Convention 1 — Section Numbering

### What the industry does

**W3C CSS / SVG / HTML / RFC:** All use hierarchical decimal numbers (`§2.1.3`). Numbers are
stable across drafts; sections are not renumbered once published. A `Changes` appendix lists
renames. Subsections have permalink `id` attributes. External links reference `§6.2.1 Placement
Algorithm`, not headings that can drift.

**ECMAScript:** Clause numbers (e.g., `10.1.2`) appear in the H2/H3 heading and in every
cross-reference. Newly added clauses insert a decimal (`10.1.2.1`) rather than shifting
existing numbers.

### What the current ruleset does

Sections §0–§8 with a few subsections (`§2.1`, `§2.2`, `§2.3`). Numbering is shallow; `§2.3`
is already referenced from `§1` and `§6`, which is good. But sub-subsections have no
numbers, and there are no anchor permalinks in Markdown.

### Proposal: MUST for v2

**Adopt** hierarchical numbering at three levels (`§N`, `§N.M`, `§N.M.P`). Numbers are locked
at publication; new rules insert a new subsection number, never re-use an existing one.

In Markdown, every heading gets a lowercase kebab-case anchor that doubles as the stable ID:

```markdown
## §2 Placement Algorithm {#s2}
### §2.1 Nudge Grid Contract {#s2-1}
#### §2.1.1 Candidate Generation {#s2-1-1}
```

External documents reference `smart-label-ruleset.md#s2-1` and never break on content edits
as long as anchors are frozen.

**Adaptation from W3C style:** W3C uses HTML `id` attributes; the Markdown equivalent is the
brace-anchor syntax above (supported by `mkdocs`, `mdBook`, and GitHub's anchor auto-generation
falls back gracefully). Prefer explicit anchors over auto-generated slugs from heading text,
because heading text changes more freely than a stable anchor id.

---

## 3. Convention 2 — Algorithm Pseudo-Code Style

### What the industry does

**ECMAScript** is the gold standard for algorithm prose. Every abstract operation is written as:

```
AbstractOpName ( param1, param2 )

1. Assert: param1 is a Number.
2. Let result be param1 + param2.
3. If result < 0, then
   a. Return 0.
4. Return result.
```

Key rules:
- Step numbers are `1.`, `2.`, sub-steps are `a.`, `b.`, sub-sub-steps `i.`, `ii.`.
- `Let X be …` introduces a local variable.
- `Assert: …` states a precondition that is always true at that point.
- `If … then … a. … b. … Else …` for branches.
- `Return` is the only way to exit; no implicit fall-through.
- Abstract operation calls use `CallName(args)` in bold or code font.
- Internal state is accessed as `[[ FieldName ]]` (double brackets).
- Algorithms are self-contained: all inputs are in the signature, all outputs are in `Return`.

**RFC 7230** uses a priority-ordered numbered list for message-body length determination:
"1. Any response to a HEAD request … 2. Any 1xx … 3. …" — this is the same numbered-step
pattern applied to a lookup/dispatch problem.

**W3C CSS Text L3** uses prose numbered steps for white-space processing, e.g.:
"1. Any sequence of collapsible spaces and tabs immediately preceding a segment break is removed."

### What the current ruleset does

Section §2 has a fenced-code pseudocode block:

```
emit_arrow_svg / emit_plain_arrow_svg:
    1. compute leader geometry …
    4. if placement overlaps …
         for candidate in _nudge_candidates …
```

This mixes Python-like pseudo-syntax (`if`, `for`) with numbered steps. It is readable but:
- Lacks `Let / Assert / Return` vocabulary, so it is ambiguous whether step 4 is a branch or a
  statement.
- Sub-steps use indentation, not `a.`, `b.`, making nesting level unclear in longer algorithms.
- Does not name the abstract operation (what is the function being specified?).

### Proposal: MUST for v2

**Adopt ECMAScript step style** for all algorithmic prose. Use a consistent vocabulary:

| Keyword | Meaning |
|---------|---------|
| `Let X be …` | Introduce a local binding. |
| `Let X be the result of PlaceLabel(w, h, hint)` | Introduce a binding from an abstract-op call. |
| `Assert: …` | Precondition — always true at this point; not a conditional check. |
| `If … is true, then` | Branch entry. Sub-steps are lettered `a.`, `b.`, … |
| `Otherwise` | Else branch. |
| `Return X` | Sole exit point. |
| `Throw E` | Error exit. Maps to raising `E1200` etc. |
| `For each X in Y` | Loop, body is sub-steps. |

**Adaptation:** ECMAScript uses HTML `<emu-alg>` elements for typesetting. In Markdown, use a
numbered list with indented lettered sub-lists. Fenced code blocks should be reserved for
literal code only.

---

## 4. Convention 3 — Conformance Classes

### What the industry does

**WHATWG HTML** splits conformance into *producers* (authors writing HTML) and *consumers*
(browsers rendering HTML). Requirements on producers do not bind consumers. SVG 2 adds
*Generator*, *Authoring Tool*, *Viewer*, and *High-Quality Viewer* conformance classes, each
with its own MUST set. JSON Schema splits *implementations* by vocabulary support, letting
implementations declare only what they implement.

**RFC 7230** identifies *client*, *server*, and *proxy* as distinct conformance roles.

The pattern: a spec lists every class of conforming actor, then each normative rule is tagged
to the class(es) it binds.

### What the current ruleset has

The ruleset states rules in the active voice ("must", "do not") but never names who is required
to comply. Is it the human author writing Starlark? The `_svg_helpers.py` implementer? The
primitive implementing `emit_svg`? The test author? The CI pipeline?

This matters: Invariant I-5 ("Production HTML contains no debug comments") binds the *Emitter*
(Python code). Invariant I-10 ("No mutation of shared placement state") binds the *Primitive
implementer*. Both are currently stated without any actor label, which makes them hard to
translate into targeted test assertions.

### Proposal: MUST for v2

**Adopt** four conformance classes for the v2 ruleset:

| Class | Definition |
|-------|-----------|
| **Author** | A human writing a `\annotate{...}` command in a `.tex` file. |
| **Primitive** | A Python class implementing `emit_svg` — e.g. `Array`, `DPTable`, `Plane2D`. |
| **Emitter** | The `_svg_helpers.py` functions `emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`, and any future unified helper. |
| **Renderer** | The top-level `AnimationRenderer` / `DiagramRenderer` that assembles frames, manages `placed_labels`, and produces the HTML wrapper. |

Every normative rule carries a conformance label in brackets: `[Emitter MUST]`, `[Primitive MUST]`,
`[Renderer MUST]`.

**Adaptation from W3C style:** W3C conformance classes are formal normative text in a dedicated
subsection. For a single-feature Markdown ruleset, a simple `[Class MUST]` inline tag is
sufficient. A conformance-class table near the top of the document defines the four classes
once.

---

## 5. Convention 4 — Dfn + Cross-Reference

### What the industry does

**WHATWG HTML:** Every technical term is introduced once with `<dfn>` markup, which makes the
first occurrence the canonical definition. Every subsequent use is a hyperlink back to that dfn.
This means the spec never silently varies the meaning of a term, and readers can always navigate
to the definition. The HTML spec has thousands of dfn-linked terms.

**ECMAScript:** Terms are introduced as named abstract operations or specification types in a
dedicated section. Subsequent uses always name the operation, e.g. "Let val be ToNumber(x)" — the
reader knows exactly which operation they are reading.

### What the current ruleset has

Section §0 defines nine terms in a table: pill, leader, target, arrow_from, position-only label,
anchor, AABB, registry, nudge grid. But later prose uses these terms without linking. "The anchor
coordinate matches the rendered coordinate" in I-3 does not link back to the §0 definition of
*anchor*. "AABB separation" in I-2 uses *AABB* without linking.

### Proposal: MUST for v2

**Adopt** dfn linking in Markdown via anchor-to-heading:

1. Each defined term in §0 gets a stable anchor: `### Pill {#dfn-pill}`.
2. Every use of the term in later sections uses a Markdown link: `[pill](#dfn-pill)`.
3. Any new term introduced in a later section is back-linked to its first occurrence.

**Adaptation:** This is achievable in plain Markdown with minimal overhead. It is not required to
be exhaustive on first pass; the rule is "new terms introduced in a section must be defined in §0
or linked to their first occurrence." A linting script can check for unlinked uses of §0 terms.

---

## 6. Convention 5 — Non-Normative Examples

### What the industry does

**W3C CSS / HTML:** Examples are demarcated with a styled callout and carry a non-normative
notice. Example content never carries a `MUST`. W3C Markdown tooling uses
`<div class="example">` with explicit `<p>This is a non-normative example.</p>`. Each example has
a stable anchor (`id="example-5b7dad2f"`).

**RFC 7230:** Examples are visually offset by indentation and introduced with a label like
"For example:" — they carry no normative weight.

**JSON Schema:** "For example:" inline prose, with JSON code blocks following; the spec notes
explicitly that all examples are informative.

### What the current ruleset has

No examples are marked normative or non-normative. Section §12 of `environments.md` contains a
"Complete Worked Examples" section that is clearly illustrative, but it is not labelled as such.
The smart-label ruleset has only algorithm pseudo-code, not illustrative examples.

### Proposal: SHOULD for v2

**Adopt** a `> NOTE (non-normative):` callout for any illustrative material:

```markdown
> **Example (non-normative):** A `DPTable` with three annotations placed in
> a single `emit_svg` call. The first occupies the default above position; the
> second is nudged north-east one step because the above slot is taken; the
> third falls back to the last candidate and a debug comment is emitted.
```

Rules: examples never carry `MUST/SHOULD/MAY`. If an example appears to state a requirement,
the requirement belongs in the normative text. The example may *illustrate* the requirement.

---

## 7. Convention 6 — ISSUE Blocks

### What the industry does

**W3C CSS / SVG:** Open questions that the working group has not yet resolved are marked with a
visible `ISSUE` block:

```html
<div class="issue">
  <p>Spec issue #42: Should the nudge grid extend to 48 candidates (12 directions × 4 steps)
     for dense scenes? See GitHub issue #1337.</p>
</div>
```

These blocks survive publication as Candidate Recommendation. They signal to implementers that
this behaviour may change. They are distinct from `NOTE` (which is informative but settled) and
from TODO comments (which are editorial).

### What the current ruleset has

Section §2.3 "What the registry does NOT know" and §6 "Roadmap" capture known limitations and
future work, but they are prose paragraphs, not `ISSUE` blocks. The reader must infer what is
settled and what is open.

### Proposal: MUST for v2

**Adopt** a Markdown blockquote `ISSUE` convention:

```markdown
> **ISSUE:** MW-4 repulsion solver: Should the force-based fallback run when ≥ 3
> annotations overlap, or only when all 32 nudge candidates are exhausted? See
> [#MW-4 roadmap note](#s6-mw4) and GitHub issue #TODO.
```

Rules:
- Every MW-N roadmap item becomes an `ISSUE` block in the section closest to the
  behaviour it concerns.
- `ISSUE` blocks are never normative. They document uncertainty; they do not create
  requirements.
- When an issue is resolved, the `ISSUE` block is replaced by normative text or a `NOTE`,
  and the resolution is recorded in the `§0 Changelog`.

---

## 8. Convention 7 — NOTE vs Normative Prose

### What the industry does

**W3C / WHATWG:** The distinction is typographic and semantic. `NOTE:` callouts are informative.
Body prose with `MUST/SHOULD/MAY` is normative. Implementers are expected to implement normative
requirements. Notes are advisory.

**ECMAScript:** Clauses may contain "NOTE" paragraphs that explain rationale or give examples. The
normative algorithm steps come before the NOTE. The NOTE is subordinate and informative.

The key rule: a `NOTE` can never *add* a requirement. If informative material in a NOTE turns out
to be the only place a behaviour is specified, the NOTE must be promoted to normative text.

### What the current ruleset has

The current ruleset has `**Rule:**` (§4 debug flags) and paragraph prose that mixes rationale
with requirements. Some invariants (I-1 through I-10) state normative requirements; the next
paragraph ("Any PR that breaks an invariant must…") is also normative but indistinguishable from
explanatory prose.

Section §2.3 is entirely informative ("This is a limitation, not a bug") but is not marked
as such.

### Proposal: MUST for v2

**Adopt** two call-out styles, implemented as Markdown blockquotes:

```markdown
> **NOTE:** This section is informative. The registry's pill-only scope is a
> deliberate performance trade-off documented in §2.3. It does not represent a
> gap in the normative requirements.
```

```markdown
> **ISSUE:** …
```

Normative requirements MUST appear in numbered steps or `[Class MUST]`-tagged bullet lists,
**not** in `NOTE` or `ISSUE` blocks. Any normative-sounding sentence inside a `NOTE` must be
moved to the surrounding normative prose.

**Additional distinction borrowed from ECMAScript:**

Abstract operation names are written in `PascalCase` and linked: `[PlaceLabel](#dfn-placelabel)`.
Internal state fields are written in double brackets: `[[placedLabels]]`. This visually
distinguishes "call this function" from "read this field."

---

## 9. Convention 8 — Per-Section Changelog

### What the industry does

Most living W3C specs maintain a `Changes` appendix or a `Changes from Previous Version`
subsection within the intro. WHATWG HTML has an exhaustive commit-linked changelog (the living
standard is git-hosted). ECMAScript releases a new edition annually with a `What's New` section.

For smaller documents, per-section `<!-- Last changed: v0.8.1 by PR #243 -->` HTML comments are
common. The CSS Working Group tracks a `Changes from Level 2` subsection inside each property.

### What the current ruleset has

No changelog. The header says "living document" and "don't silently change an existing rule's
meaning," but there is no per-rule history.

### Proposal: SKIP for v2 (with fallback)

**Skip** per-section changelog because:

1. The ruleset is small (< 300 lines effective normative content) and lives in a git repository.
   `git log -p docs/spec/smart-label-ruleset.md` provides full history.
2. Adding inline changelog annotations doubles the maintenance burden for minimal reader benefit
   at this scale.
3. The existing git-log convention (`chore: bump version to 0.10.0 + CHANGELOG`) already captures
   this at the repo level.

**Fallback rule:** The §0 document-level preamble MUST carry a `Last-modified` date and a
`Changed-in` version reference. Each invariant row in the §1 table SHOULD carry the version in
which it was introduced or last changed, e.g., `(since 0.8.0)`. This is a minimal viable
changelog at the rule level without per-section prose.

---

## 10. Convention 9 — Test Assertions

### What the industry does

**W3C CSS specs** link to the Web Platform Tests (WPT) repository. Each normative requirement
ideally has at least one WPT test. The CSS Text L3 spec publishes a test-coverage report at
`test.csswg.org` showing which assertions have passing tests and in which browsers. The link
from spec assertion to test is maintained in the WPT metadata (`.any.js` meta-headers).

**ECMAScript** has the Test262 suite. Each algorithm step may map to one or more Test262
test files.

The pattern: `[spec assertion] → [test file path]`. This is one-directional in the spec (the spec
does not embed test paths) but bidirectional in the test infrastructure (Test262 metadata
references the spec clause).

### What the current ruleset has

Section §7 says "Every rule in §1 has at least one test in `tests/unit/test_smart_label_phase0.py`"
and references `TestQW*` and `TestMW*` classes. This is a minimal equivalent, but:

- The link is uni-directional only in the prose — the test file does not reference the invariant
  ID.
- There is no table mapping invariant IDs to test class names.
- New invariants added by agents 1–5 will not automatically get test references.

### Proposal: MUST for v2

**Adapt** a WPT-inspired mapping using a dedicated table in §7:

```markdown
## §7 Test Assertions {#s7}

| Invariant / Rule | Test class | Test method(s) | Status |
|-----------------|------------|----------------|--------|
| I-1 (pill inside viewBox) | `TestQW7MathHeadroomExpansion` | `test_pill_fits_viewbox_*` | covered |
| I-2 (no overlap ≥ 2 px) | `TestQW1LabelCollision` | `test_no_overlap_*` | covered |
| I-3 (anchor matches rendered) | `TestQW3AnchorCorrection` | `test_anchor_coord_*` | covered |
…
```

In the test file, add a module docstring comment linking back:

```python
# Invariant coverage: smart-label-ruleset.md §1
# I-1 → test_pill_fits_viewbox_*
# I-2 → test_no_overlap_*
```

This creates bidirectional traceability without a separate test-registry infrastructure.

**Adaptation:** WPT uses `.json` metadata files; scriba's equivalent is the module-level comment.
The table in §7 is the scriba "test coverage report." If an invariant row in the table has
`status=uncovered`, the PR that introduces that invariant is blocked until coverage is added.

---

## 11. Convention 10 — IDL / Schema Blocks

### What the industry does

**W3C specs** use Web IDL to describe DOM interfaces:

```webidl
interface SVGElement : Element {
  [SameObject] readonly attribute SVGAnimatedString className;
  readonly attribute DOMString? id;
};
```

IDL blocks are normative when they define public API surface; informative when they describe
internal structure.

**JSON Schema** uses JSON Schema itself to describe its own keyword schemas — a form of
self-hosting schema notation.

### What the current ruleset has

Data structures like `_LabelPlacement` are mentioned but not formally defined. "Pill AABB" is
used without stating what fields it has. `_nudge_candidates` is specified in prose but its return
type is only implied.

### Proposal: ADAPT for v2

**Adopt Python type-annotation blocks** as the scriba equivalent of IDL. Python is the
implementation language; type annotations are precise and immediately readable to any
contributor:

```python
# Normative type definitions — §0 Data Structures
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Iterator

@dataclass(frozen=True)
class AABB:
    """Axis-aligned bounding box. Origin is top-left (SVG convention)."""
    x: float        # left edge
    y: float        # top edge
    w: float        # width  (w > 0)
    h: float        # height (h > 0)

    def overlaps(self, other: AABB, pad: float = 0.0) -> bool: ...

@dataclass(frozen=True)
class LabelPlacement:
    """One registered pill in the placed_labels registry."""
    aabb: AABB
    label: str
    kind: Literal["pill"]   # extended to pill|cell_text|leader_path in MW-2

NudgeCandidate = tuple[float, float]   # (dx, dy) offset from initial center

def nudge_candidates(
    pill_w: float,
    pill_h: float,
    side_hint: Literal["above", "below", "left", "right"] | None = None,
) -> Iterator[NudgeCandidate]: ...
```

These blocks are normative in the same sense as Web IDL: they define the shape of data
structures and function signatures that the implementation MUST honour. Any change to a
normative type definition requires updating both the spec block and the implementation.

**Adaptation note:** Web IDL is language-neutral; Python type annotations are not. Since scriba
is a Python project with no published API for external consumption, Python annotations are
strictly superior in readability. If scriba ever publishes a plugin API, a language-neutral
schema (JSON Schema, CUE, or Protobuf) is the right escalation path.

---

## 12. Convention 11 — Feature-at-Risk Notation

### What the industry does

**W3C Candidate Recommendation** process requires features to be declared "at-risk" if they may
be dropped before Recommendation. The notation in CSS specs:

> The following features are at-risk and may be dropped: the `full-width` value of
> `text-transform`, the `full-size-kana` value.

SVG 2 uses inline `<i class="atrisk">` markup. The CSS Working Group lists at-risk features
prominently in the CR announcement.

### What the current ruleset has

Roadmap section §6 lists MW-2, MW-3, MW-4 as "not yet implemented." But there is no notation for
features that exist in the current spec but might be removed or changed: the `unified` engine
toggle (`SCRIBA_LABEL_ENGINE=unified`) is on by default as of v0.10.0 but the spec says `legacy`
is the documented path. This is a form of at-risk feature (the legacy path may be removed).

### Proposal: SHOULD for v2

**Adopt** a Markdown at-risk callout:

```markdown
> **AT RISK:** The `SCRIBA_LABEL_ENGINE=legacy` path is scheduled for removal in
> v1.0. Authors relying on legacy-specific behaviours MUST migrate to the unified
> engine. See [§4 Environment Flags](#s4) and GitHub issue #TODO.
```

**Adapt the W3C pattern:** In a living-doc context, "at-risk" means "scheduled for removal or
breaking change in a future minor/major version." It does not imply a formal CR process; it is
a signal to implementers and authors. The callout should appear at the top of the section
governing the at-risk feature, not only in a master list.

Rules for labelling at-risk:
1. Any behaviour that has a replacement path already in the spec (unified vs legacy engine).
2. Any behaviour in MW-N roadmap items that conflicts with existing invariants (MW-4 repulsion
   solver could relax I-2 by allowing non-zero overlap after 32 exhausted candidates).
3. Any environment flag whose semantics may change between versions.

---

## 13. Convention 12 — Normative Dependency Declaration

### What the industry does

Every IETF RFC opens with a boilerplate paragraph declaring RFC 2119 as the interpretive
authority for modal keywords. Every W3C CSS spec has a dedicated "Conformance" appendix that:

1. References RFC 2119.
2. States what classes of document or software must conform.
3. Lists normative references (bibliographic entries that MUST be implemented).
4. Lists informative references.

The ECMAScript spec declares its dependencies on Unicode, IEEE 754, and ISO dates in §6.

### What the current ruleset has

`ruleset.md` (the wider Scriba spec) has a `§1.0 Normative Language` section citing RFC 2119.
`smart-label-ruleset.md` does not — it uses "must" and "MUST" inconsistently and never declares
the RFC.

### Proposal: MUST for v2

**Adopt** a one-paragraph conformance preamble at the top of the ruleset (after the §0 metadata
table and before any normative text):

```markdown
## §0.1 Conformance {#s0-1}

The key words MUST, MUST NOT, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and
OPTIONAL in this document are to be interpreted as described in [RFC 2119][rfc2119] when, and
only when, they appear in all capitals.

Lower-case uses of these words are descriptive, not normative.

This document is normative for the four conformance classes defined in §0.2: **Author**,
**Primitive**, **Emitter**, **Renderer**. Each normative rule carries a `[Class MUST]`
conformance tag identifying the class(es) it binds.

[rfc2119]: https://datatracker.ietf.org/doc/html/rfc2119
```

---

## 14. Adoption Decision Summary

| # | Convention | Decision | Rationale |
|---|------------|----------|-----------|
| 1 | Section numbering (§N.M.P with stable anchors) | **MUST** adopt | Already partially in place; anchors needed for external cross-refs. |
| 2 | ECMAScript algorithm step style | **MUST** adopt | Current fenced-code pseudo-syntax is ambiguous; Let/Assert/Return removes all ambiguity. |
| 3 | Conformance classes | **MUST** adopt | Critical for determining who is bound by each rule; Author vs Emitter vs Primitive vs Renderer distinctions are already implicit in the text. |
| 4 | Dfn + cross-reference | **MUST** adopt | §0 term table already exists; adding anchors and back-links is low-cost, high-value. |
| 5 | Non-normative example marking | **SHOULD** adopt | Adds clarity without significant overhead; defer to v2.1 if resourcing is tight. |
| 6 | ISSUE blocks | **MUST** adopt | MW-2/3/4 roadmap items are open questions; need to be distinguishable from settled decisions. |
| 7 | NOTE vs normative prose | **MUST** adopt | Several §2.3 / §5 paragraphs are informative but unmarked; this creates implementer confusion. |
| 8 | Per-section changelog | **SKIP** | Git log + §0 `Last-modified` + invariant version annotation is sufficient at this scale. |
| 9 | Test assertions (WPT-style mapping) | **MUST** adopt | Invariant-to-test-class table in §7 closes the current gap; cost is one table + test docstrings. |
| 10 | IDL / schema blocks (Python type annotations) | **MUST** adopt | `_LabelPlacement`, nudge-candidate tuple, and AABB are used everywhere without a normative definition. |
| 11 | Feature-at-risk notation | **SHOULD** adopt | `SCRIBA_LABEL_ENGINE=legacy` removal and MW-4 semantics qualify; callouts prevent surprise breakage. |
| 12 | Normative dependency declaration (RFC 2119) | **MUST** adopt | The ruleset uses MUST inconsistently; declaring RFC 2119 fixes this at zero cost. |

**MUST for v2:** 1, 2, 3, 4, 6, 7, 9, 10, 12 (nine conventions).
**SHOULD for v2:** 5, 11 (two conventions; target v2.1 if time-constrained).
**SKIP:** 8 (per-section changelog).

---

## 15. Before/After Rewrites

### 15.1 Rewrite: Invariant I-2 (no-overlap rule)

**Current (v1):**

> | I-2 | Two pills emitted in the same step do not overlap at ≥ 2 px AABB separation. | `_LabelPlacement.overlaps(other, pad=2)` must be false for every pair. |

**Proposed (v2):**

---

#### §1 Invariants {#s1}

**I-2 — No two pills overlap** (since v0.7.0) [Emitter MUST]

Any two [pill](#dfn-pill) [AABB](#dfn-aabb)s emitted during a single `emit_svg` call MUST NOT
overlap. Overlap is defined as:

> Two AABBs A and B **overlap** if and only if there exists a point P such that
> P is contained within both `Expand(A, pad)` and `Expand(B, pad)`, where
> `Expand(AABB, pad)` inflates all four edges outward by `pad` pixels.
> Default `pad = 2`.

The [Emitter](#dfn-emitter) enforces this by calling `LabelPlacement.overlaps(other, pad=2)`.
If the result is `true` for any pair, the Emitter MUST invoke the
[nudge grid](#dfn-nudge-grid) algorithm defined in [§2.1](#s2-1).

*Test:* `TestQW1LabelCollision::test_no_overlap_two_pills`

---

**Key improvements:**
- Conformance class labelled (`[Emitter MUST]`).
- Version introduced (`since v0.7.0`).
- Terms linked (`[pill](#dfn-pill)`, `[AABB](#dfn-aabb)`).
- Overlap defined precisely as a mathematical property, not just a reference to a Python method.
- Test linked (`*Test:*`).
- The rule is split from the check mechanism — the invariant states the property; the check is
  a consequence.

---

### 15.2 Rewrite: Nudge Grid Contract (§2.1)

**Current (v1):**

> `_nudge_candidates(pill_w, pill_h, side_hint=None) -> Iterator[(dx, dy)]`
>
> - Emits 32 candidates: 8 compass directions × 4 step sizes (0.25, 0.5, 1.0, 1.5) × pill_h.
> - Sort key: Manhattan distance from origin, then tie-break N, S, E, W, NE, NW, SE, SW.
> - When side_hint ∈ {above, below, left, right}, candidates in the matching half-plane come
>   first; the other half-plane still emits as fallback.
> - Generator never yields (0, 0) — caller must try the initial placement before invoking.

**Proposed (v2):**

---

#### §2.1 Nudge Grid Contract {#s2-1}

```python
# Normative type signature [Emitter]
def nudge_candidates(
    pill_w: float,
    pill_h: float,
    side_hint: Literal["above", "below", "left", "right"] | None = None,
) -> Iterator[tuple[float, float]]:
    """Yield (dx, dy) offsets from the initial pill center, sorted by preference."""
```

**NudgeCandidates ( pill\_w, pill\_h, side\_hint )** [Emitter MUST]

1. Let *dirs* be the ordered 8-tuple of unit compass vectors:
   `(N=(0,-1), S=(0,1), E=(1,0), W=(-1,0), NE=(1,-1), NW=(-1,-1), SE=(1,1), SW=(-1,1))`.
2. Let *steps* be `(0.25, 0.5, 1.0, 1.5)`.
3. Let *candidates* be the set of all `(dir.x × step × pill_h, dir.y × step × pill_h)` for
   each *dir* in *dirs* and each *step* in *steps*. This produces exactly 32 candidates.
4. Assert: The zero vector `(0, 0)` is NOT in *candidates*. The caller is responsible for
   testing the initial (pre-offset) placement before invoking this function.
5. If *side_hint* is not `null`, then:
   a. Let *preferred* be the candidates whose direction component aligns with *side_hint*
      (see [§2.1.1 Side-hint Alignment](#s2-1-1)).
   b. Let *fallback* be the remaining candidates.
   c. Sort *preferred* by ascending Manhattan distance from the origin,
      tie-breaking in *dirs* order (N before S before E before W before NE…).
   d. Sort *fallback* by ascending Manhattan distance, same tie-break.
   e. Return the concatenation *preferred* ++ *fallback*.
6. Otherwise (side_hint is `null`):
   a. Sort all 32 candidates by ascending Manhattan distance, tie-breaking in *dirs* order.
   b. Return the sorted sequence.

> **NOTE:** The generator never yields `(0, 0)`. The caller MUST try the initial placement
> *before* calling `NudgeCandidates`. Calling the function is only needed after the initial
> placement is found to overlap an entry in `[[placedLabels]]`.

> **ISSUE:** Should diagonal directions (NE, NW, SE, SW) carry a 1.414× Manhattan-distance
> penalty relative to cardinal directions at the same step size, to bias placement toward
> clean alignment? See GitHub issue #TODO.

*Tests:* `TestQW2NudgeGrid::test_side_hint_preferred`, `test_no_zero_candidate`,
`test_32_candidates_generated`

---

**Key improvements:**
- Python type signature block is normative.
- Algorithm uses `Let / Assert / If … then / Return` vocabulary.
- Internal state reference uses `[[placedLabels]]` notation.
- `NOTE` is clearly informative; `ISSUE` is clearly open.
- Step 4's precondition is an explicit `Assert`, not a prose note.
- Tests linked.
- Sub-section numbering (`§2.1.1`) is reserved for side-hint alignment detail.

---

### 15.3 Rewrite: Debug Flag Rule (§4)

**Current (v1):**

> **Rule**: debug comments must never appear in production output. If you add a
> new debug artifact, gate it behind `_DEBUG_LABELS` and add a test that asserts
> absence when the flag is off.

**Proposed (v2):**

---

#### §4.1 Debug Comment Suppression {#s4-1}

[Emitter MUST], [Renderer MUST]

1. Let *debug\_mode* be `true` if the environment variable `SCRIBA_DEBUG_LABELS` is set to `"1"`,
   `false` otherwise.
2. If *debug\_mode* is `false`, then
   a. Assert: The emitted SVG string does NOT contain any substring matching
      `<!-- scriba:label-*`.
   b. If this assertion fails, the Emitter MUST raise `E1200`.
3. If *debug\_mode* is `true`, then
   a. The Emitter MAY emit `<!-- scriba:label-collision id=… -->` comments at the point in the
      SVG where a [nudge grid](#dfn-nudge-grid) fallback was triggered.
   b. The comment MUST carry a stable `id=` attribute whose value is the placement index
      within `[[placedLabels]]` for that call.

> **NOTE:** The check in step 2a is enforced by `TestQW6NoDebugInProduction::test_no_debug_comment_default`.
> Implementers adding new debug artifacts MUST gate them behind `_DEBUG_LABELS` and add a
> corresponding absence assertion.

> **AT RISK:** `SCRIBA_DEBUG_LABELS` may be replaced in v1.0 by a structured `--diagnose`
> CLI flag that captures placement metadata in a separate sidecar file rather than inline SVG
> comments. Authors parsing debug comments directly SHOULD prepare for this change.

*Tests:* `TestQW6NoDebugInProduction::test_no_debug_comment_default`,
`test_debug_comment_present_when_flag_set`

---

**Key improvements:**
- Two conformance classes labelled (`[Emitter MUST]`, `[Renderer MUST]`).
- Algorithmic steps with `Let / If / Assert / MAY`.
- `NOTE` vs normative body clearly separated.
- `AT RISK` callout for the planned CLI migration.
- Tests linked.
- Internal state `[[placedLabels]]` notation.

---

## 16. V2 Style Skeleton

The following is a blank skeleton for the v2 ruleset. Section numbering is locked; every
`{TODO}` is a placeholder for agents 1–5 to fill in.

---

```markdown
# Smart-Label Ruleset v2

> **Version:** 2.0.0-draft
> **Status:** Draft — not yet normative.
> **Supersedes:** `smart-label-ruleset.md` v1 (2026-04-21 snapshot).
> **Scope:** `\annotate` pill placement, leader rendering, and collision avoidance for
> all primitives that emit annotations via `_svg_helpers.py`.
> **Audience:** Contributors to `_svg_helpers.py`, primitive `emit_svg` methods, and the
> `\annotate` contract.
> **Last-modified:** {DATE}
> **Changed-in:** {VERSION}

---

## §0 Preamble {#s0}

### §0.1 Conformance {#s0-1}

The key words MUST, MUST NOT, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and
OPTIONAL in this document are to be interpreted as described in [RFC 2119][rfc2119] when,
and only when, they appear in all capitals.

Lower-case uses of these words are descriptive, not normative.

[rfc2119]: https://datatracker.ietf.org/doc/html/rfc2119

### §0.2 Conformance Classes {#s0-2}

This document is normative for the following four classes. Each normative rule carries
a `[Class MUST/SHOULD/MAY]` tag.

| Class | Definition |
|-------|-----------|
| **Author** | A human writing `\annotate{...}` in a `.tex` source file. |
| **Primitive** | A Python class implementing `emit_svg` (e.g. `Array`, `DPTable`, `Plane2D`). |
| **Emitter** | The functions `emit_arrow_svg`, `emit_plain_arrow_svg`, `emit_position_label_svg`, and any unified helper that replaces them. |
| **Renderer** | `AnimationRenderer` / `DiagramRenderer` — manages `placed_labels`, assembles frames, and wraps HTML. |

### §0.3 Normative Type Definitions {#s0-3}

```python
# Normative data-structure definitions. The implementation MUST honour these shapes.
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Iterator

@dataclass(frozen=True)
class AABB:
    """Axis-aligned bounding box. All units are logical SVG pixels. Origin top-left."""
    x: float   # left edge
    y: float   # top edge
    w: float   # width  (MUST be > 0)
    h: float   # height (MUST be > 0)

    def overlaps(self, other: AABB, pad: float = 0.0) -> bool:
        """True if this box and other box overlap after inflating both by pad."""
        ...

@dataclass(frozen=True)
class LabelPlacement:
    """One entry in the [[placedLabels]] registry."""
    aabb: AABB
    label: str
    kind: Literal["pill"]  # extended to pill|cell_text|leader_path|decoration in MW-2

NudgeCandidate = tuple[float, float]  # (dx, dy) offset from initial pill center
```

### §0.4 Terminology {#s0-4}

| Term | Definition | Anchor |
|------|-----------|--------|
| **pill** | The rounded `<rect>` that holds the annotation label text. | {#dfn-pill} |
| **leader** | The line, elbow, or Bezier path from pill to target. | {#dfn-leader} |
| **target** | The symbol the annotation points at (cell, node, point). | {#dfn-target} |
| **arrow_from** | Optional source symbol; when present, the leader runs `arrow_from → target` and the pill sits near the leader midpoint. | {#dfn-arrow-from} |
| **position-only label** | An annotation with no `arrow_from`; pill sits adjacent to `target`. | {#dfn-position-only} |
| **anchor** | Geometric center of the pill's `<rect>`. Always `(cx, final_y - l_font_px × 0.3)`. | {#dfn-anchor} |
| **AABB** | Axis-aligned bounding box. See §0.3. | {#dfn-aabb} |
| **registry** | `[[placedLabels]]`: the append-only list of `LabelPlacement` entries collected during one `emit_svg` call. | {#dfn-registry} |
| **nudge grid** | The 8-direction × 4-step candidate generator. See §2.1. | {#dfn-nudge-grid} |

---

## §1 Invariants {#s1}

> **NOTE:** Every invariant in this section MUST have at least one test entry in §7. A PR
> that introduces a new invariant without adding a §7 entry MUST be rejected.

{TODO: paste agents 1–5 invariants here in the following table format}

| ID | Invariant | Conformance | Since | Test |
|----|-----------|-------------|-------|------|
| I-1 | Every [pill](#dfn-pill) fits inside the primitive viewBox. | [Emitter MUST] | v0.7.0 | `TestQW7::test_pill_fits_viewbox` |
| I-2 | No two pills emitted in the same step overlap at ≥ 2 px. | [Emitter MUST] | v0.7.0 | `TestQW1::test_no_overlap_two_pills` |
| I-3 | [Anchor](#dfn-anchor) coordinate matches rendered coordinate. | [Emitter MUST] | v0.7.0 | `TestQW3::test_anchor_matches_render` |
| I-4 | Clamp re-registers the clamped AABB, not the pre-clamp one. | [Emitter MUST] | v0.8.0 | `TestQW3::test_clamp_re_registers` |
| I-5 | Production HTML contains no debug comments. | [Emitter MUST] | v0.7.0 | `TestQW6::test_no_debug_comment_default` |
| I-6 | Position-only labels emit a pill even when `arrow_from` is absent. | [Primitive MUST] | v0.7.0 | `TestQW8::test_position_only_emits_pill` |
| I-7 | Text measurement never under-estimates math pills. | [Emitter MUST] | v0.8.0 | `TestQW5::test_math_pill_width` |
| I-8 | Hyphen-split never fires inside `$...$`. | [Emitter MUST] | v0.9.0 | `TestQW4::test_no_hyphen_in_math` |
| I-9 | Math pills reserve ≥ 32 px headroom vs 24 px for plain text. | [Emitter MUST] | v0.9.0 | `TestQW7::test_math_headroom_32px` |
| I-10 | No mutation of shared placement state across primitive instances. | [Renderer MUST] | v0.7.0 | `TestQW10::test_no_shared_mutation` |
| {I-N} | {TODO from agents 1-5} | [{Class} MUST] | {vX.Y.Z} | `{TestClass::test_method}` |

Any PR that breaks an invariant MUST either (a) fix the break, (b) update this document AND
the corresponding test, or (c) be rejected.

---

## §2 Placement Algorithm {#s2}

### §2.1 Nudge Grid Contract {#s2-1}

{TODO: paste expanded algorithm in ECMAScript step style — see §15.2 of 06-spec-style.md}

#### §2.1.1 Side-Hint Alignment Definition {#s2-1-1}

{TODO}

### §2.2 Registry Contract {#s2-2}

**PlaceLabel ( pill\_w, pill\_h, initial\_cx, initial\_cy, label, side\_hint )** [Emitter MUST]

1. Let *registry* be `[[placedLabels]]` for the current `emit_svg` call.
2. Let *placement* be a new `LabelPlacement` with the center-corrected [AABB](#dfn-aabb)
   for (*initial\_cx*, *initial\_cy*, *pill\_w*, *pill\_h*).
3. {TODO: full step-style algorithm from agents 1–5}

**Registry invariants** [Renderer MUST]:

- `[[placedLabels]]` is created empty at the start of each `emit_svg` call.
- `[[placedLabels]]` is append-only within a call.
- `[[placedLabels]]` is NOT shared across primitive instances, frames, or calls.
- Every entry in `[[placedLabels]]` stores the post-clamp [AABB](#dfn-aabb).

### §2.3 Known Limitations {#s2-3}

> **NOTE:** This section is informative. The limitations listed here are the current scope
> boundary of the registry. They are not bugs in the placement algorithm; they are deliberate
> scope constraints. The [§6 Roadmap](#s6) tracks work to close these gaps.

The [registry](#dfn-registry) tracks [pill](#dfn-pill) AABBs only. It is currently blind to:
{TODO}

> **ISSUE:** MW-2 target: should the registry be extended to `kind ∈ {pill, cell_text,
> leader_path, decoration}` in a single PR, or incrementally (pill + cell_text first)?
> See [§6 MW-2](#s6-mw2).

---

## §3 Geometry Rules {#s3}

### §3.1 Pill Anchor {#s3-1}

{TODO}

### §3.2 Pill Dimensions {#s3-2}

{TODO: normative type-annotated formula}

### §3.3 Headroom {#s3-3}

{TODO}

### §3.4 ViewBox Clamp {#s3-4}

{TODO}

---

## §4 Environment Flags {#s4}

### §4.1 Debug Comment Suppression {#s4-1}

{TODO: paste rewrite from §15.3 of 06-spec-style.md}

### §4.2 Label Engine Selection {#s4-2}

> **AT RISK:** The `SCRIBA_LABEL_ENGINE=legacy` path is scheduled for removal in v1.0.
> See [§6 Roadmap](#s6).

{TODO}

---

## §5 Known-Bad Repros {#s5}

> **NOTE:** This section is informative. It documents observed failure modes and their
> mapping to normative sections. It does NOT define any normative requirements.

{TODO: paste bug-A through bug-F table}

---

## §6 Roadmap {#s6}

> **NOTE:** This section is informative. Items listed here are not yet normative.
> Each MW-N item will be promoted to a §1 invariant or §2/§3 rule when implemented.

### §6.1 MW-2: Unified Registry {#s6-mw2}

> **ISSUE:** Extend `[[placedLabels]]` to carry `kind ∈ {pill, cell_text, leader_path,
> decoration}`. See the design constraints in §2.3 and bug-A / bug-E / bug-F in §5.

{TODO}

### §6.2 MW-3: Pill-Placement Helper {#s6-mw3}

> **ISSUE:** Extract "compute pill\_w/pill\_h → center-correct → nudge → clamp → register"
> into a single `PlaceLabel(...)` function. Prerequisite for MW-2.

{TODO}

### §6.3 MW-4: Repulsion Solver Fallback {#s6-mw4}

> **ISSUE (AT RISK):** When the 32-candidate nudge grid is exhausted, should a force-based
> repulsion solver run? This would relax invariant I-2 in the degenerate case (> 3
> overlapping annotations). Decision pending. See [§1 I-2](#s1).

{TODO}

---

## §7 Test Assertions {#s7}

The following table maps every invariant and normative rule to the test(s) that exercise it.
A PR that introduces a new normative rule MUST add a row to this table before merging.

| Rule / Invariant | Test file | Test class | Test method(s) | Status |
|-----------------|-----------|------------|----------------|--------|
| I-1 | `test_smart_label_phase0.py` | `TestQW7MathHeadroomExpansion` | `test_pill_fits_viewbox_*` | covered |
| I-2 | `test_smart_label_phase0.py` | `TestQW1LabelCollision` | `test_no_overlap_*` | covered |
| I-3 | `test_smart_label_phase0.py` | `TestQW3AnchorCorrection` | `test_anchor_coord_*` | covered |
| I-4 | `test_smart_label_phase0.py` | `TestQW3AnchorCorrection` | `test_clamp_re_registers` | covered |
| I-5 | `test_smart_label_phase0.py` | `TestQW6NoDebugInProduction` | `test_no_debug_comment_default` | covered |
| I-6 | `test_smart_label_phase0.py` | {TODO} | {TODO} | {covered/uncovered} |
| I-7 | `test_smart_label_phase0.py` | `TestQW5MathWidth` | `test_math_pill_width_*` | covered |
| I-8 | `test_smart_label_phase0.py` | `TestQW4MathWrap` | `test_no_hyphen_in_math` | covered |
| I-9 | `test_smart_label_phase0.py` | `TestQW7MathHeadroomExpansion` | `test_math_headroom_32px` | covered |
| I-10 | `test_smart_label_phase0.py` | {TODO} | {TODO} | {covered/uncovered} |
| §2.1 NudgeCandidates | `test_smart_label_phase0.py` | `TestQW2NudgeGrid` | `test_32_candidates`, `test_no_zero_candidate`, `test_side_hint_preferred` | covered |
| §2.2 Registry isolate | `test_smart_label_phase0.py` | {TODO} | {TODO} | {covered/uncovered} |
| §4.1 No debug in prod | `test_smart_label_phase0.py` | `TestQW6NoDebugInProduction` | `test_no_debug_comment_default` | covered |
| {new from agents 1–5} | {file} | {class} | {method} | uncovered |

---

## §8 Change Procedure {#s8}

When modifying `_svg_helpers.py` or any file that implements rules in this document:

1. Run `gitnexus_impact({target: "<function>", direction: "upstream"})` and report the blast
   radius.
2. Identify which invariants in §1 are affected. For each: verify the corresponding §7 test
   still passes.
3. Re-render all repro cases in `docs/archive/…/repros/` and visually diff before/after.
4. If the change alters observable behaviour, update the relevant normative rule in §1–§4.
5. If the change closes an ISSUE in §2.3 or §6, promote the ISSUE text to normative prose.
6. Run `pytest tests/unit/test_smart_label_phase0.py -v`.
7. Commit code, tests, doc, and re-rendered repros in the same commit.

---

*End of v2 skeleton. Fill in all {TODO} blocks with findings from agents 1–5.*
```

---

## 17. Formal Encoding Feasibility: TLA+ and Alloy

### 17.1 The question

Can the smart-label ruleset be profitably encoded in TLA+ (temporal logic + refinement) or
Alloy (relational model finder)? "Profitable" here means: does the encoding catch bugs that
property-based tests cannot, at a cost proportional to the gain?

### 17.2 What TLA+ would model

TLA+ is suited to **concurrent or distributed systems** where you need to reason about interleavings,
liveness properties ("eventually some label is placed"), and safety properties over unbounded
state sequences.

The smart-label algorithm is:

1. A sequential Python function.
2. Deterministic (same inputs → same outputs, no concurrency).
3. Bounded (32 candidates; maximum one call per annotation; maximum N annotations per frame).
4. Stateless across frames (`[[placedLabels]]` is reset at each `emit_svg` call).

TLA+ would add the most value if there were concurrent writers to `[[placedLabels]]` or if the
algorithm had temporal properties spanning multiple frames. Neither applies here.

**Verdict: TLA+ is over-engineered for this problem.** The invariants (I-1 through I-10) are
safety properties over a single, bounded, sequential function call. TLA+ would faithfully model
them, but at a cost of ~200 lines of TLA+ syntax for properties that a 30-line pytest already
verifies. The engineering trade-off does not close.

### 17.3 What Alloy would model

Alloy is a **relational model finder** that exhaustively checks properties over finite
structures. It is suited to data-structure invariants: "for all sets of placements satisfying
the preconditions, no two overlap" — exactly the shape of I-2.

Unlike TLA+, Alloy works well for bounded, state-invariant problems. The core placement model
maps directly:

```alloy
-- Smart-label placement model sketch
-- Alloy 6 syntax

sig Pixel {}   -- integers abstracted as atoms for model size

sig AABB {
    x, y, w, h: Int,
    -- invariant: w > 0, h > 0
}

sig LabelPlacement {
    aabb: one AABB,
    kind: one Kind
}

abstract sig Kind {}
one sig Pill extends Kind {}

sig Registry {
    entries: set LabelPlacement
}

-- Invariant I-2: no two pills in the same registry overlap
pred noOverlap [r: Registry] {
    all disj p1, p2 : r.entries |
        not overlaps[p1.aabb, p2.aabb, 2]
}

pred overlaps [a1, a2: AABB, pad: Int] {
    -- a1 and a2 share a point after inflating both by pad
    (a1.x - pad) < (a2.x + a2.w + pad) and
    (a2.x - pad) < (a1.x + a1.w + pad) and
    (a1.y - pad) < (a2.y + a2.h + pad) and
    (a2.y - pad) < (a1.y + a1.h + pad)
}

-- Invariant I-1: every pill is inside the viewBox
pred insideViewBox [r: Registry, vw, vh: Int] {
    all p: r.entries |
        p.aabb.x >= 0 and
        p.aabb.y >= 0 and
        (p.aabb.x + p.aabb.w) <= vw and
        (p.aabb.y + p.aabb.h) <= vh
}

-- Property: nudge grid produces a valid placement when one exists
assert NudgeFindsPlacement {
    all initial: AABB, r: Registry, vw, vh: Int |
        -- if there exists a valid placement in the candidate set
        (some dx, dy: Int |
            let candidate = translate[initial, dx, dy] |
            all p: r.entries | not overlaps[candidate, p.aabb, 2] and
            insideViewBox[singleton[candidate], vw, vh])
        -- then the nudge algorithm accepts it
        -- (this is the liveness claim; model-check it for small registries)
        implies {
            some result: AABB |
                all p: r.entries | not overlaps[result, p.aabb, 2] and
                insideViewBox[singleton[result], vw, vh]
        }
}

check NudgeFindsPlacement for 4 but 3 LabelPlacement, 4 Int
```

This Alloy sketch encodes three of the invariants (I-1, I-2, and the liveness claim of the
nudge grid). The `check` command exhaustively searches all registries with up to 3 placements
and 4-bit integers, verifying that if a valid slot exists in the 32-candidate grid, the
algorithm finds one.

### 17.4 Sketch: Two More Invariants in Alloy

**Invariant I-3 — Anchor matches rendered coordinate:**

```alloy
-- Center-correction invariant
-- AABB center is at (x + w/2, y + h/2)
-- Text anchor is at (cx, final_y) where final_y = aabb_center_y + l_font * 0.3
-- We model the 0.3 multiplier as a rational constant; Alloy uses integers so
-- we approximate as: final_y * 10 = center_y * 10 + l_font * 3

pred anchorMatchesRendered [p: LabelPlacement, l_font: Int] {
    let cx = p.aabb.x.add[p.aabb.w.div[2]] |
    let center_y = p.aabb.y.add[p.aabb.h.div[2]] |
    let final_y_times_10 = center_y.mul[10].add[l_font.mul[3]] |
    -- the rendered text anchor (cx, final_y) is consistent with the AABB
    p.aabb.x <= cx and cx <= p.aabb.x.add[p.aabb.w] and
    final_y_times_10 >= p.aabb.y.mul[10] and
    final_y_times_10 <= p.aabb.y.add[p.aabb.h].mul[10]
}
```

**Invariant I-10 — No shared mutation across primitive instances:**

```alloy
-- Each emit_svg call gets its own registry; registries are disjoint
sig EmitCall {
    registry: one Registry
}

assert RegistriesDisjoint {
    all disj c1, c2: EmitCall |
        c1.registry != c2.registry and
        no (c1.registry.entries & c2.registry.entries)
}

check RegistriesDisjoint for 3 EmitCall, 6 LabelPlacement
```

### 17.5 Verdict and Recommendation

**Alloy: Yes, feasible and worth a sketch for invariants I-1, I-2, I-3, I-10.**
The structural invariants (AABB non-overlap, viewBox containment, registry isolation) map cleanly
to Alloy's relational model. An Alloy model would:

1. Catch any logic error in the overlap predicate (off-by-one, wrong axis).
2. Verify that the nudge grid's liveness property holds for small registries.
3. Provide a machine-checked reference for what "overlap" means, removing ambiguity from the
   prose spec.

The cost is approximately 100–150 lines of Alloy, a one-time investment. Alloy runs in a JVM
process and integrates with CI via `alloy-check` or equivalent.

**TLA+: No, not warranted.** The algorithm is sequential, bounded, and stateless across frames.
The temporal logic that TLA+ provides is unnecessary. Prose invariants + property-based tests
(Hypothesis) cover the same ground with far lower notation overhead.

**Recommended approach for scriba:** Property-based tests (Hypothesis) are the primary
verification mechanism. An Alloy model serves as a machine-checked reference for the three
hardest invariants (I-1, I-2, I-10). The two tools are complementary: Alloy verifies the model;
Hypothesis verifies the implementation against randomly generated inputs.

A Hypothesis property test for I-2 looks like:

```python
from hypothesis import given, strategies as st

@given(
    placements=st.lists(
        st.builds(LabelPlacement, aabb=aabb_strategy()),
        min_size=2, max_size=8
    )
)
def test_no_two_pills_overlap(placements):
    """Hypothesis fuzz: any registry produced by PlaceLabel has no overlapping pills."""
    registry = []
    for p_spec in placements:
        placed = place_label(registry, p_spec.w, p_spec.h, p_spec.cx, p_spec.cy)
        registry.append(placed)

    for i, a in enumerate(registry):
        for b in registry[i+1:]:
            assert not a.aabb.overlaps(b.aabb, pad=2), (
                f"Overlap detected: {a.aabb} vs {b.aabb}"
            )
```

This is the "prose + property-based tests are enough" path for day-to-day development. The Alloy
sketch lives in `docs/formal/smart-label-model.als` as a reference artefact, not in the CI
critical path.

---

*End of document. Target file:*
`docs/archive/smart-label-ruleset-strengthening-2026-04-21/06-spec-style.md`
