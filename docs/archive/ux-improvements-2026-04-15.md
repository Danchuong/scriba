# UX Improvements Backlog

> Captured: 2026-04-15

## 1. `id` and `label` in `\begin{animation}` / `\begin{diagram}` are burdensome

**Status: ALREADY IMPLEMENTED**

When `id` is omitted, the renderer auto-generates a deterministic ID via
`scriba-{sha256(raw)[:10]}`. Users can still override manually.

- `AnimationRenderer.render_block()` — `renderer.py:304-309`
- `DiagramRenderer.render_block()` — `renderer.py:588-591`
- Fallback: `_scene_id()` (SHA-256) at `renderer.py:96-99`

---

## 2. `\begin{lstlisting}` does not auto-detect language

**Status: ALREADY IMPLEMENTED**

When `language` is not specified, two-layer auto-detection runs:

1. **Regex heuristics** (`_heuristic_detect`) — cheap pattern matching for
   cpp, python, java, go, rust, c, javascript, csharp. See `highlight.py:18-74`.
2. **Pygments `guess_lexer()`** fallback — if heuristics find nothing.
   Rejects "Text only" results. See `highlight.py:122-130`.

The detected language is reflected in `data-language` attribute on the output.

---

## 3. Duplicate content in `.tex` source files

**Status: IMPLEMENTED (2026-04-15)**

Pipeline now emits a `CollectedWarning(code="E1019", severity="dangerous")`
when two rendered blocks share the same `block_id`. This catches both:
- Explicit `[id="same"]` reuse across `\begin{animation}` blocks
- Duplicated content producing identical SHA-256 auto-generated IDs

The warning surfaces on `Document.warnings` (RFC-002 strict mode).

**Files changed:**
- `scriba/core/pipeline.py` — step 4b, duplicate block_id detection

**Pre-existing (not called in pipeline):**
- `scriba/animation/uniqueness.py:107-134` — `check_duplicate_animation_ids()`
  raises `E1019` as an error. Available for tooling/strict-mode promotion.
