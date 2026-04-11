# Agent 03: Spec Clarity & Example Coverage

**Score:** 6/10 (draft-to-beta, significant gaps in clarity and centralized examples)

**Verdict:** needs-work

## Prior fixes verified

N/A — new scope. No prior audit has measured prose clarity or centralized example coverage.

## Critical Findings

### C1: Frame State Inheritance Undefined (ruleset.md:570)

Spec says "Each frame inherits full state from previous frame, then:" but "full state" is ambiguous. Does it include:
- Ephemeral highlights from prior frame?
- Frame-local `\compute` bindings (drop or persist)?
- Pending `\apply` mutations?

Two reasonable interpretations exist. **First-time authors will guess wrong.** No worked example shows frame 1→2 transition.

### C2: "Snapshot" Timing Bleeding Into Spec (ruleset.md:575)

"Clear `apply_params` after snapshot" references internal detail (`snapshot`) never defined in normative section. When is snapshot taken? Before or after ephemeral drops (step 2)? **Implementation-dependent, not author-facing.** Prose conflates two ephemeral semantics (apply params vs. compute bindings).

### C3: Zero Centralized Worked Examples (ruleset.md §2–7)

14 commands documented with **only 3 pseudo-code examples** (cursor before/after, foreach iteration). No single animation showing:
- Multi-frame progression with 3+ commands per step
- Frame-to-frame state inheritance in action
- Error recovery (invalid selectors, type mismatches)

Examples exist scattered in `primitives.md` (per-primitive) and `environments.md` (per-command), but no integrated reference.

## High Findings

### H1: Ephemeral vs. Persistent Conflation (ruleset.md §8)

Section 8 merges two unrelated concepts:
- `ephemeral=true` annotations (user-facing, visible in command params)
- `apply_params` cleared per-frame (internal state detail)

Spec prose mixes them without clarification. Authors cannot predict when state clears.

### H2: Brace Argument Escaping Undefined (ruleset.md:306–310)

BNF allows `"\\" IDENT` but silent on:
- Can `\{` appear in balanced_text?
- How are LaTeX macros in params parsed? (e.g., `label="$x^2$"`)
- What triggers E1009 (selector syntax error)?

Authors will test edge cases and guess.

### H3: Missing Topics (6 sections)

Not in spec:
1. **Operator precedence** (Starlark compute) — deferred to external docs, no mention
2. **Evaluation order** — are commands in a step executed in source order? Assumed, unstated
3. **Redraw triggers** — what causes SVG re-render in interactive mode?
4. **Frame clock** — no timing controls (delays, transitions, playback speed)
5. **Layout determinism bounds** — Graph `layout_seed` deterministic within what? Minor versions?
6. **Starlark error context** — E1151 runtime error, but no line numbers or stack trace format promised

### H4: Inconsistent Normative Language (9 instances, weak)

9 uses of "must/should/shall" scattered across files. Most are constraints (error codes), not authoring rules. Very few "should" (optional). Unclear RFC 2119 compliance: is "MUST come before TexRenderer" a runtime error or silent fallback?

## Medium Findings

### M1: Tone Drift Across Sections

- §1–3: Formal BNF, lexical tokens (9/10)
- §6: Starlark reference (8/10)
- §8: Prose-only frame lifecycle (4/10, vague)
- §7 (Extensions): Sparse, minimal cross-references (3/10)

Document shifts from spec-speak to tutorial without signposting.

### M2: Missing Hex Color for `dim` State (ruleset.md:321)

Table shows `dim = "50% opacity"` but no explicit hex or base color mentioned. Is it 50% of idle? Current cell? **Authors cannot verify visual output matches intent.**

### M3: Interpolation Subscript Edge Cases (ruleset.md:197)

BNF: `interp_ref ::= "${" IDENT ("[" subscript "]")* "}"` but:
- How does `${arr[i]}` resolve for 1D lists?
- Is syntax recursive (nested arrays)?
- When is E1156 (subscript out of range) thrown? Build time or render?

Deferred to implementation reading.

### M4: Selector Bare Identifier Convention Prose-Only (ruleset.md:123–124)

"Bare identifier (e.g. `G.node[A]`) is treated as string node ID" documented in prose, not BNF. BNF shows `node_id ::= NUMBER | STRING | IDENT | "${" IDENT "}"`, implying three distinct token types, but prose normalizes to one. **Grammar and prose conflict subtly.**

## Low Findings

### L1: Extensions (§7) Cross-Reference Spam

§7.1–7.5 reference external spec files (E1, E2, E4, E5) with zero inline explanation. Authors must navigate 5 files to understand substory max depth (3) or `\hl` step-id format.

### L2: CSS Custom Property Override Undefined

§10.2 lists defaults (`--scriba-state-idle-fill: #f6f8fa`) but no way for authors to override them. Dark mode (§10.4) overrides noted but not the mechanism.

### L3: Determinism Contract Claim Unverified (ruleset.md:986–994)

"Identical source + identical Scriba version = byte-identical HTML" claimed, but layout caching and `layout_seed` behavior across minor versions not specified. Contradiction with layout stability guarantees.

## Notes

1. **Example distribution**: Examples exist but scattered (primitives.md, environments.md). No centralised "Scriba Animation by Example" reference that first-time authors can skim.

2. **Prose vs. formal**: ruleset.md mixes BNF (§3.1) with informal prose (§8 lifecycle). Spec should consistently use formal definitions for all normative rules.

3. **Frame lifecycle diagram needed**: §8 deserves a visual state-machine or timeline showing frame 1→2→3 with ephemeral drops, compute scope, and apply persistence explicitly marked.

4. **Error context**: E1150–E1159 (compute errors) list codes but not the message template or context provided (line numbers, stack depth). Authors debugging Starlark will struggle.

5. **Accessibility of cross-refs**: ruleset.md §14 lists external docs but does not say which are normative (locked), advisory, or examples. Version drift risk high.
