# Agent 01: Grammar Formalism & Ambiguity

**Score:** 8/10 (1=broken, 5=alpha, 7=beta, 9=production, 10=perfect)

**Verdict:** ship-with-caveats

## Prior fixes verified
- **H3 (Selector parse errors missing codes):** PRESENT — SelectorParser._error() assigns code="E1010" and code="E1009" for all selector syntax errors. Verified with test cases.
- **M4 (NamedAccessor catch-all delays error reporting):** STILL MISSING — By design; unknown accessor names parse silently as NamedAccessor(name=...). Downstream semantic validation defers error reporting. No regression.
- **M3 (Indexed accessor BNF gap):** DOCUMENTED — Section 3, line 92 defines `IDENT "[" idx "]"` production; implementation creates `NamedAccessor(name="point[0]")` for generic indexed parts. Spec and code match; edge case about index type collapsing into name string remains unaddressed.
- **C1 (Diagram mode unimplemented):** STILL MISSING — Parser always returns `AnimationIR` regardless of environment. No `DiagramIR` class or diagram parsing code. Spec documents `\begin{diagram}` as a top-level environment; unimplemented.
- **H1 (step[label=...] rejected):** STILL MISSING — `_check_step_trailing()` explicitly rejects any non-NEWLINE after `\step` (raises E1052). Spec line 546 documents `\step[label=...]` syntax; parser forbids it.

## Critical Findings

### C1: Diagram Mode Unimplemented (scriba/animation/parser/grammar.py, scriba/animation/renderer.py:546)
Parser forces all input through `allow_highlight_in_prelude=True` for diagram rendering, but does not distinguish between animation and diagram IRs at parse time. Returns `AnimationIR` with zero frames for diagram content. Spec promises `\begin{diagram}` as a valid environment; no DiagramIR implementation exists. Users cannot use diagram mode; dead AST code.

## High Findings

### H1: Step Label Options Not Supported (scriba/animation/parser/grammar.py:221)
Spec section 7.1 documents `\step[label=...]` syntax for frame IDs. Parser's `_check_step_trailing()` rejects any non-NEWLINE token after `\step` (error code E1052). Syntax is documented but unusable.

### H2: Unknown Commands Silently Ignored (scriba/animation/parser/lexer.py:136)
Lexer emits unknown `\foo` as TokenKind.CHAR instead of TokenKind.BACKSLASH_CMD (due to _KNOWN_COMMANDS whitelist). Parser treats CHAR tokens as trailing garbage in most contexts, making typos in command names undetected until runtime. No error code assigned.

## Medium Findings

### M1: Nested Interpolation Accepted Without Validation (scriba/animation/parser/grammar.py:1198)
Interpolation syntax `${x[${y}]}` (nesting interpolations) parses successfully but produces unpredictable behavior at eval time. Spec does not explicitly forbid or define semantics. InterpolationRef subscripts can recursively contain InterpolationRef, creating potential scope ambiguity.

### M2: Generic Indexed Accessors Embed Index in Name String (scriba/animation/parser/selectors.py:97)
Production `IDENT "[" idx "]"` stores result as `NamedAccessor(name="point[0]")` instead of a dedicated AST node. Index expression (which may be InterpolationRef) is concatenated into the name string. Downstream pattern-matching on accessor names becomes fragile; interpolation refs lose type information.

### M3: Selector Allowlist Not Enforced at Parse Time (scriba/animation/parser/selectors.py:98)
Any unrecognized accessor name (e.g., `a.typo`) parses successfully as `NamedAccessor`. Typos in well-known accessor names (`cell`, `node`, `edge`) are not caught until the primitive rejects the unknown part at render time.

## Low Findings

### L1: Reserved Keyword Collision (scriba/animation/parser/selectors.py:88)
The keyword `all` is both a reserved accessor name and can be used as a shape name (e.g., `\shape{all}{Array}`). Parser treats `shape.all` unambiguously (as AllAccessor), but the context-dependent meaning could confuse users authoring selectors.

### L2: Trailing Comma in Parameter Lists Silently Accepted (scriba/animation/parser/grammar.py:1120)
BNF line 191 allows optional trailing comma: `param_list ::= param ("," param)* ","?`. Trailing commas are accepted but serve no purpose. Minor inconsistency with LaTeX style.

## Notes

**Strengths:**
- Parser is **deterministic and LL(1)**: single-token lookahead sufficient for all decisions. No reduce-reduce or shift-reduce conflicts.
- **Selector parsing is unambiguous**: BNF-to-implementation fidelity is high. No legal input parses two different ways.
- **Error codes present for selector syntax errors**: prior H3 finding is resolved.
- **Extension commands (foreach, substory, cursor, reannotate) are cleanly factored** into the grammar with proper nesting constraints enforced.

**Defects:**
- Diagram mode is dead code: spec promises it, AST defines it, parser never produces it.
- step[label=...] is documented but explicitly forbidden by the parser.
- Unknown commands silently disappear (lexer emits as CHAR, parser ignores).
- Generic indexed accessors lose type information (index embedded in name string).

**Scope:** This audit covers grammar rules, tokenization, command dispatch, selector parsing, and parameter value parsing. Does not cover semantic validation (type checking of accessor names against primitives), code execution sandbox, or frame lifecycle.
