"""Version constants for Scriba. Bumped on HTML output shape changes."""

__version__: str = "0.23.1"
"""PyPI SemVer. Bumped on every release."""

SCRIBA_VERSION: int = 18
"""Integer version of the core abstractions (Pipeline, Document, Renderer,
RenderArtifact, RenderContext). Bumped whenever the core API changes in a
way that invalidates consumer caches, independent of __version__.

Note: 0.6.0 keeps SCRIBA_VERSION = 3 (bumped 2→3 in 0.6.0-alpha1). The
``Document`` dataclass gained a new ``warnings: tuple[CollectedWarning, ...]``
field (RFC-002) and the Tree/Graph/Plane2D primitives gained structural
mutation APIs (RFC-001). The additions are backward-compatible at the read
side, but consumer caches keyed on primitive rendered output MUST invalidate
because new states (``hidden``) and new edge parsing (3-tuple weighted)
produce strictly different SVG. This is the first SCRIBA_VERSION break
since v0.1.1.

0.16.0 bumps 3→4: every SVG ``font-size`` is now emitted as
``calc(Npx * var(--scriba-diagram-font-scale, 1))`` and substory widget ids
became deterministic, so rendered HTML/SVG bytes differ from 0.15.x even at
the default scale. Consumer caches keyed on rendered output MUST invalidate.

0.17.0 bumps 4→5: the animation viewBox is now sized to the maximum extent
across all frames (size-changing primitives like Stack/Queue no longer clip),
and ``CodePanel`` renders its label as a top header bar instead of a bottom
caption. Both change rendered SVG/HTML bytes from 0.16.x; consumer caches
keyed on rendered output MUST invalidate.

0.18.0 bumps 5→6: Phase-2 render-content fixes alter SVG/HTML bytes — the
NumberLine axis and MetricPlot root now carry a ``scriba-state-*`` class
(``\\recolor`` honoured), directed graphs emit the arrow-marker ``<defs>``
once instead of twice, ``\\narrate`` resolves ``${compute}`` bindings,
``\\apply`` captions and ``\\reannotate`` updates now render, and
``position=inside`` annotations are centred. Consumer caches keyed on
rendered output MUST invalidate.

0.19.0 bumps 6→7: Graph layout stability work changes node coordinates.
Node positions are now pinned across edge mutations (add_edge/remove_edge no
longer re-solve the layout), isolated (degree-0) nodes are placed in a
reserved inner lane instead of a canvas corner, and an unpinned
``layout="force"`` graph auto-selects the best-scoring seed (0–7) instead of
always using seed 42. Graphs that mutate edges, contain isolated nodes, or
rely on the default seed render different SVG bytes; consumer caches keyed on
rendered output MUST invalidate.

0.20.0 bumps 7→8: interactive-widget chrome and primitive spacing changed. The
step controls now float as an overlay pill over the stage (the top control bar
is gone) and the narration is a borderless caption; the progress-dots row was
removed (the counter is the sole indicator); prev/next use chevron glyphs and
the counter dropped the "Step"/"Sub-step" word ("N / M"). The stage ``<svg>``
now carries an intrinsic ``max-width`` so a viewBox-only drawing is never
upscaled. Every primitive's ``bounding_box`` now reserves ``position=below``
annotation-pill headroom and ``arrow_height_above`` is a true upper bound on
arrow/label extent, so the inter-primitive gap could tighten (50→20) with
``_PADDING`` 16→12 without overlap. VariableWatch borders/centering were also
fixed. Rendered HTML/SVG bytes differ from 0.19.x; consumer caches keyed on
rendered output MUST invalidate.

0.21.0 bumps 8→9: annotation and caption legibility was lifted across the whole
primitive catalog, changing rendered SVG/HTML bytes. Long captions now wrap and
their width and height fold into every primitive's ``bounding_box`` (Layer A);
``range[a:b]`` and ``position=below`` annotation targets that were silently
dropped now resolve and render on all data-structure primitives (Layer B/C);
``position=below`` pills move to a leader-connected callout lane, wide ``left``/
``right`` pills extend the bounding box, competing above-labels stack instead of
dropping, and ``range`` labels gain a span bracket. Cross-primitive
segment-obstacle avoidance for position pills was also restored, and the
diagram font-scale now scales the whole viewport uniformly. Consumer caches
keyed on rendered output MUST invalidate.
0.21.2 bumps 9→10: the annotation lane above every primitive is now the
EXACT painted extent instead of a heuristic upper bound. Each primitive's
``annotation_height_above`` runs the real annotation emitters into a scratch
buffer and measures the output (closed-form Bézier extrema, stroke included),
so the reserved translate offset shrinks (or, for under-reserved self-loop
arrows, grows) to exactly what is painted; six primitives that previously
ignored ``set_min_arrow_above`` now honour the cross-frame floor and substory
scenes receive the reservation for the first time. Every annotated scene's
viewBox height and translate offsets change; consumer caches keyed on
rendered output MUST invalidate.

0.21.2 bumps 10→11 (same release, second byte-shape change): annotation pill
labels containing $...$ now WRAP like plain labels and render KaTeX per line;
foreignObject text carries explicit font-size matching its plain-text twin
(cells 14px, index/tick 10-11px); graph/tree math node labels overflow like
plain node text instead of clipping; metricplot/plane2d/codepanel floating
labels get measured boxes; single-line captions carry an inline
text-anchor; the primitive-label CSS rule is a descendant selector;
wrapped tspans keep a trailing space per line (copy-paste word breaks);
env options label/width/height/layout are now honoured in output and the
dead `grid` option key is rejected (E1004). Rendered bytes differ across
all annotated/labelled scenes; consumer caches MUST invalidate.

Also folded into the 11 byte-shape (same 0.21.2 release): pills treat the
primitive's own cells as obstacles and wrap to the content span (R-33),
short in-grid arrows escape to the clear lane above/below the content
(R-34), every caption clears its content by a uniform 8px gap, graph split
edge labels with math yield to the KaTeX path, and the interactive-widget
inline runtime commits the frame index before the transition (rapid
Next/Prev no longer swallowed). Page-level output additionally changed:
TeX regions are wrapped in ``.scriba-tex-content`` and the CSS bundle now
ships the artifact-declared content + pygments light/dark sheets.

0.22.0 bumps 11→12: cell/node text (the 14px surface that sizes every
viewBox) is measured against a shipped, pinned sans — a 34KB Inter subset
embedded as "Scriba Sans" with full Vietnamese coverage — using exact
per-glyph advances with tabular-nums honoured, instead of the 0.62em/char
heuristic (which measured -38%..+154% per string). Text widths, line
wraps, cell widths and viewBox extents change across every labelled
scene, and standalone pages embed the font @font-face. Consumer caches
keyed on rendered output MUST invalidate.

0.22.0 bumps 12→13 (same release, all-script rung 0): every narration
<p> carries dir="auto" (was 1 of 5 emit sites); SVG text/foreignObject
containing RTL codepoints gains unicode-bidi:plaintext; spaceless-script
labels (Thai/Lao/Khmer) wrap cluster-safely instead of overflowing as one
token; identifier charsets accept combining marks (Thai/Devanagari
selector/var/label names — Python's ``\\w`` excludes Mn/Mc, which the 0.21.1
Unicode pass missed). LTR-only documents change only by the dir="auto"
attribute. Consumer caches keyed on rendered output MUST invalidate.

0.22.1 bumps 13→14 (exact label-math metrics): annotation/caption/tick
label widths containing $math$ are measured by a KaTeX advance-sum over
the vendored font tables (p50 0.06%/p95 0.66% vs Chromium) instead of the
strip-and-x1.15 heuristic (p50 43%, and 0px for pure-command fragments
like $\to$). Pills get narrower, wrap points shift, per-line label
foreignObjects flip overflow:hidden->visible, the single-line math label
drops its flex wrapper (space-swallowing) for the same inline model as
multi-line, and .scriba-annot-label divs pin to the annotation mono font.
Consumer caches keyed on rendered output MUST invalidate.

0.22.2 bumps 14→15 (decoration features): the inline stylesheet gains the
``--scriba-annotation-state-*`` tokens and their rule family (R-36), so
every rendered page's bytes differ even for documents that use none of
the new surface. The new surface itself — ``block[r0:r1][c0:c1]``,
``bracket=true``, ``color="state:X"``, ``leader=true``, ``\\trace`` — is
opt-in and leaves existing documents' geometry untouched. Consumer caches
keyed on rendered output MUST invalidate.

0.23.0 bumps 15→16 (animation-clarity phases A–D): the runtime core gains reverse
tweening (Prev/ArrowLeft now animate via manifest inversion), delta
emphasis on arrival, the cursor_move handler, an annotation_recolor
handler (previously a silent no-op off the full-sync path) and a
position-pill key fallback — the inline script and external runtime hash
change in every widget. Phase D adds the `.scriba-sentinel` CSS rule
(one more inline-stylesheet byte change). New author surface (\\cursor id=/at= binding
carets, plus the phase-B \\ref/\\focus/step-title/\\invariant surfaces) is opt-in and leaves plain documents' geometry untouched.
Consumer caches keyed on rendered output MUST invalidate.

0.23.1 errata → 17: 0.23.1 shipped the `.scriba-ref-mark` CSS rule (and
the phase-D `.scriba-sentinel` rule) — inline-stylesheet bytes changed in
every page — while still carrying marker 16, so two byte-different
releases briefly shared a marker. 17 corrects the signal; treat 0.23.0
and 0.23.1 outputs as distinct cache keys regardless. Consumer caches
keyed on rendered output MUST invalidate.

0.24.0 bumps 17→18 (capability Wave 1): ShapeTargetState.state now
defaults to None ("never recolored") instead of "idle", so value-only
writes can't clobber a state applied through an expanded selector
(row/col/diag/block). Manifest bytes shift where a highlight-only entry
used to emit recolor from_val null — it now says "idle", which also
makes the runtime class replace match (smooth recolor instead of a
fullscreen-snap lurch). The ``position_move`` runtime handler now glides
the element to its NEW seat (``translate(0,0)→translate(to-from)``, the
``cursor_move`` geometry) instead of settling at the old seat and
teleporting on fs-snap, curing the A-4 lurch for Tree reparent/BST
rotation and readying the substrate for reorder/union glides; the
inline+external runtime bytes change in every widget. New surface
(row/col/diag sugar, Matrix value mutation, Plane2D circle/arc/wedge,
Tree kind=heap) is opt-in and leaves existing documents' geometry
untouched. The same 17→18 CSS bump also carries the `.scriba-link` rule for
the new `\\link` / `\\combine` cross-shape bridges (one more inline-stylesheet
byte change; the bridge overlay itself is opt-in). Consumer caches keyed on
rendered output MUST invalidate.

Also opt-in under the same marker (no byte change for documents that use none
of it, and no new CSS): the ``\\group`` / ``\\ungroup`` overlay-hull surface
(investigations/gap-dsu-forest-design.md §6 Phase 1). ``\\group{G}{nodes=[...],
id=...}`` paints a rounded convex-hull decoration around a named node cluster
on a Graph — the Graph node-set (and viewBox) is untouched, so A1 pinning and
R-32 hold — and it rides the shipped ``annotation_add`` / ``annotation_remove``
/ ``annotation_recolor`` kinds (zero new motion vocabulary, scriba.js
unchanged). The hull is styled by inline presentation attributes (like
``\\trace`` and the R-35 block bracket), so the shared stylesheet is unchanged
and group-free scenes render byte-identically.

Scope of the "byte-identical for non-users" claim (investigations/
byte-identity-asset-inlining.md): it holds at the PRIMITIVE-MARKUP layer
WITHIN this marker — a document that uses none of the new features emits no
new SVG/markup bytes (verified: zero marker leak). It is NOT a cross-version
guarantee: the SHARED inline assets deliberately changed under this single
17→18 bump — the ``position_move`` glide rewrite and the boundary
keyboard-focus fix in ``scriba.js`` (every animated widget), and the
``.scriba-link`` rule in the stylesheet (every page). That is exactly what the
version bump signals; the contract is ``identical source + identical
SCRIBA_VERSION → identical HTML`` (svg-emitter.md, environments.md §34), never
identity across a bump. (Correction to earlier notes: ``\\group`` adds no CSS —
only ``\\link`` touched the stylesheet.)

Dark-mode a11y (investigations/darkmode-edge-contrast.md): the dark idle
stroke ``--scriba-state-idle-stroke`` rose #313538→#62696d (WCAG 1.4.11
non-text contrast 1.45:1 → 3.22:1) in both dark blocks, and Hypercube
lattice edges became theme-aware (a ``.scriba-hypercube-edge`` class in
place of a hard-coded light hex). Inline-stylesheet bytes change on every
page; light mode and all SVG geometry are untouched.
"""
