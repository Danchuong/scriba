"""Version constants for Scriba. Bumped on HTML output shape changes."""

__version__: str = "0.30.0"
"""PyPI SemVer. Bumped on every release."""

SCRIBA_VERSION: int = 25
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

0.25.0 keeps SCRIBA_VERSION = 18 (NO byte-shape change). This release is
grammar-completeness vocabulary + Tier-D fixes, and every existing valid
document renders byte-identically to 0.24.0:
  * The three new primitives — Bar (``\\shape{h}{Bar}``, E1488–E1490),
    Graph ``positions=`` (E1475), Plane2D ``rotate_point/segment/line``
    (E1437/E1467) — are opt-in and emit NO new SVG bytes for documents
    that don't use them (verified: zero marker leak). They add NO CSS
    rule and NO scriba.js change: Bar rides the shipped ``value_change``
    motion, rotate rides ``position_move``, positions is static layout.
    So even the SHARED inline assets are unchanged this release, unlike
    the 17→18 bump.
  * The five Tier-D fixes touch only error/warning/broken paths, never
    the HTML of a valid render: BST ``reparent`` gains an opt-in
    ``index`` (default append = byte-identical); ``plane2d.*`` in
    ``\\compute`` previously RAISED E1151 (no valid render existed);
    ``${vals[i+1]}`` now raises E1159 instead of pasting garbage (no
    valid doc used it); out-of-range ``\\trace`` warns to stderr E1115
    (HTML bytes unchanged); ``\\recolor{state=${s}}`` swaps a leaked
    repr for a clean E1109 (both error, no render).
The contract ``identical source + identical SCRIBA_VERSION → identical
HTML`` therefore holds across 0.24.0→0.25.0 for every renderable input.

Bumps 18→19: the ``Equation`` primitive (math as an evolving object;
primitive #21, investigations/design-math.md). The bump is forced by a
single additive shared-asset change: ``scriba-scene-primitives.css`` gains
the ``.scriba-term.scriba-state-*`` colour family so a KaTeX ``\\term``
sub-expression (an HTML ``<span>`` inside a ``<foreignObject>``, coloured
via CSS ``color`` not the SVG ``fill`` the ``.scriba-state-* > text`` rules
use) tints on ``\\recolor``. The rule family is opt-in-inert: only an
``Equation``'s terms carry ``.scriba-term``, so a document that uses no
Equation emits byte-identical SVG/markup — ONLY the shared inlined
stylesheet hash changes (per DNA-3 that alone forces the bump). The
``katex_worker.js`` trust flip (``trust:false`` →
``(ctx)=>ctx.command==="\\htmlClass"``) is build-time only and inert for
any input that never uses ``\\htmlClass``/``\\term`` (output byte-identical
to ``trust:false``; verified no cookbook/golden uses it), so it forces no
bump on its own. ``differ.py`` is untouched — terms and
lines ride the existing ``[data-target]`` ``recolor`` / ``value_change`` /
``annotation_*`` machinery (zero new motion kinds). Consumer caches keyed on
rendered output MUST invalidate (the shared stylesheet bytes changed).

Also folded into the 18→19 marker (same release): the live ``\\invariant``
(investigations/design-accumulate.md §3.6) — an ``\\invariant`` body now
resolves ``${}`` per frame through the same interpolator ``\\narrate`` uses.
This adds a ~2-line swap to ``scriba.js`` (``_setInv`` mirrors the narration
innerHTML swap), so — CORRECTING the "scriba.js untouched" phrasing that the
Equation note above carried — the shared runtime hash DOES move for every
widget under this marker (as any runtime-touching release does). It is gated:
a static ``\\invariant`` (no ``${}``) emits no per-frame ``inv`` key and the JS
path is untaken, so its panel markup stays byte-identical; only the runtime
asset bytes change. ``differ.py`` stays untouched (the panel is pinned chrome,
not a ``[data-target]`` motion). Consumer caches MUST invalidate.

0.26.1 keeps SCRIBA_VERSION = 19 (NO rendered-output change). This is a
docs-consistency + error-catalog-completeness patch:
  * ``ERROR_CATALOG`` gained the four codes it was missing — E1491/E1492
    (``\\trace`` cells<2 / bad arrowhead) and E1183/E1184 (``\\cursor``
    binding). These are raised/emitted in the parser but were absent from
    the catalog; they are a REGISTRY read only by the parity test and doc
    tooling — no code reads ``ERROR_CATALOG`` at raise time (messages are
    inline at the raise site), so no rendered HTML/SVG and no user-facing
    error message changes. Every animation-raised/warned code is now
    catalogued (verified: 0 missing of 57).
  * Docs were swept to 0.26.0 reality: primitive count 21, inner-command
    count 23 (environments.md §3 refreshed to document all 23), semantic
    states 9, motion kinds 11, and the phantom §9.2 state names
    (focus/update/reject/accept/hint) purged from the primitive pages.
The rendered-output contract is unchanged from 0.26.0; a document renders
byte-identically under 0.26.0 and 0.26.1.

0.26.2 keeps SCRIBA_VERSION = 19 (NO rendered-output change for VALID docs).
A hardening patch: the "accepted, dropped, no signal" silent-swallow class
(the failure mode 0.25.0 hardened elsewhere via E1159/E1115) is closed across
the command surface, plus adversarial-sweep fixes. Verified byte-identical:
the full 104-example corpus renders IDENTICALLY to 0.26.1 in both interactive
and static mode (hunt2-corpus-drift), and every change is an error-path or
opt-in surface — so a VALID document is unaffected. What changed:
  * Silent \\apply/\\shape/decoration param swallows now RAISE: unknown
    \\apply param → E1105 (+ \\recolor hint for state=), unknown key on the 9
    decoration/stage commands → E1123 (did-you-mean), Tree pairs-form nodes=
    → E1104, Equation tex=+lines= together → E1530, two \\zoom per step →
    E1124, invalid-selector set_value/set_state warnings gained the [E1115]
    prefix. These only fire on input that was ALREADY broken (silently) —
    JudgeZone's ask #3 "protect authors at author time, not reader time".
  * Geometry/honesty fixes (all opt-in or error paths): strike skips hidden
    targets and no longer recurses on bare-shape targets (was a RecursionError
    on 13 primitive types), \\note wraps/clamps to the board (E1125 warn) and
    re-anchors inside a \\zoom crop, at= compacts empty tracks (killed a
    2,000,000px viewBox detonation), \\invariant now renders in the static
    zero-JS filmstrip + interactive print, and a bogus no-op element_add on
    pure removals is suppressed (one golden re-blessed to drop that record).
  * side= and \\reannotate ephemeral= are wired through (were parsed-but-inert).
Two full adversarial sweeps (8 hunters) drove this; the only bug the second
sweep found was in a first-sweep fix, now fixed with its whole class swept.
Documents render byte-identically under 0.26.1 and 0.26.2.

0.26.3 bumps 19→20 (runtime-only, no rendered-geometry change): delta-emphasis
now excludes self-announcing motion kinds on the single-step path (motion-ruleset
A-9). The arrival pulse (the transient ``.scriba-emphasis`` throb) previously
fired on EVERY changed identity, including ones that already announced their own
change through handler motion — a caret that glided then scale-throbbed read as a
jolt. The runtime now pulses only identities that did NOT self-announce: the 7
self-announcing kinds (``value_change``, ``element_add/remove``, ``position_move``,
``annotation_add/remove``, ``cursor_move``) are excluded by identity via a two-pass
over the step manifest (``_pulseTargets`` replaces ``_manifestTargets``); the 4
silent kinds (``recolor``, ``highlight_on/off``, ``annotation_recolor``) keep the
pulse, where it is the real "this changed" signal. On the multi-step JUMP path a
snap plays no per-kind motion for cells/nodes/carets, so their pulse is kept —
but ``snapToFrame`` still fades genuinely-new annotations in
(``_fadeInNewAnnotations``), so ``annotation_add``/``annotation_remove`` are
excluded from the jump pulse too (the same two-pass in ``_changedTargets``),
leaving the fade as the annotation's sole cue. Only ``scriba.js`` changed — its inline slice + external hash
move in every interactive widget, so consumer caches keyed on rendered output MUST
invalidate — but emphasis is a runtime-only class never baked into static SVG, so
every scene's SVG geometry, ``tr``/``fs`` manifest, narration and stylesheet bytes
are byte-identical to 0.26.2. ``differ.py`` is untouched (zero new motion kinds)
and no CSS changed; the ~93 interactive corpus goldens re-bless by the identical
inline-``<script>`` delta, and the static/diagram HTMLs + static-mode animation
goldens + ``differ_*.json`` manifests are byte-identical.

0.26.4 bumps 20→21 (value_change now targets the VALUE text node): the runtime
``value_change`` handler used ``querySelector('text')`` = the FIRST ``<text>``
in the target ``<g data-target>``. On a name+value row (``VariableWatch`` var,
``HashMap`` bucket) the first ``<text>`` is the NAME/index label, so the incoming
value was stamped and scale-throbbed onto the LABEL, then the fs-snap restored it
(JudgeZone report #6: a ``var[j]`` value flashed onto "j" and reverted). Two
layers change bytes: (a) the renderer tags the value ``<text>`` with
``data-role="value"`` (and the label with ``data-role="name"``) on the three
affected primitives — ``VariableWatch`` (name+value), ``HashMap`` (index+value)
and ``LinkedList`` (value FIRST, index caption LAST, so a naive last-text
fallback would grab the caption); (b) ``scriba.js`` prefers
``text[data-role="value"]`` and falls back to the LAST ``<text>`` (value is last
in every affected row layout). The renderer delta touches ONLY the three affected
primitives' SVG (single-text cells — Array/Grid/Queue/Stack/DPTable/Tree/Matrix/
Bar/Graph — emit no ``data-role`` and stay byte-identical; ``Equation`` lines are
KaTeX ``<foreignObject>``, never a ``<text>`` value, and are untouched). The
runtime delta touches every interactive widget's inline slice + external hash.
``differ.py`` is UNTOUCHED (zero new motion kinds, the ``tr``/``fs`` manifest is
unchanged), no CSS changed, and no SVG geometry/viewBox moved — so static/diagram
HTMLs, static-mode animation goldens and ``differ_*.json`` manifests are
byte-identical. Consumer caches keyed on rendered output MUST invalidate.

0.26.5 bumps 21→22 (shared-obstacle decoration routing): the remaining
direct-emit decoration surfaces now share the R-33/R-34 smart-label placer
instead of colliding with content (investigations/design-shared-obstacle.md,
following the caret fix in 0.26.4). Decoration TEXT routes through the placer so
it DODGES content — the ``\\group`` title pill slides off a hull-corner node, the
``\\note`` callout slides off the cell value it floats over, the ``\\trace``
mid-label lifts off the grid cells it grazed (the old x-only clamp is gone), and
the ``\\link`` / ``\\combine`` mid-bridge label slides off the shapes it crosses.
Decoration GEOMETRY that physically cannot move is instead REGISTERED as a
SHOULD obstacle so OTHER placer clients dodge it: the ``\\trace`` stroke and the
``\\link`` bridge are byte-identical (register-only), but a pill/note near one now
avoids it. So the OUTPUT SHAPE for a document that places a group/note/trace-
label/link-label near content changes (the decoration's own pill x/y moves — and
ONLY that pill; grid cells, values, nodes and the trace/bridge strokes stay
byte-identical). ``differ.py`` is UNTOUCHED (zero new motion kinds — the pills
keep riding ``annotation_add``/``_remove``/``_recolor``), and no CSS changed
(the annotation pill classes are reused). The byte-golden corpus has no
``\\group``/``\\note``/``\\link`` document and exactly one ``\\trace`` document
(``decoration_spiral``), whose two trace LABELS relocate to clear the cells while
its strokes stay byte-identical; every other corpus document is byte-identical.
Consumer caches keyed on rendered output MUST invalidate.

0.27.0 keeps SCRIBA_VERSION = 22 (value-channel completeness; the 4 items are the
research follow-ups to reports #6/#7). Every existing document renders
byte-identically:
  * NEW capability — Graph per-node value: ``\\apply{g.node[X]}{value=...}`` now
    renders the value (overriding the node id, mirroring Tree/Forest) instead of
    raising E1105. The runtime already stamped node values (the old flip-back
    cause), so the server now agrees; scriba.js is untouched. No corpus document
    applies ``value=`` to a graph node (it was E1105 since 0.26.3), so all
    existing docs are byte-identical and 0 goldens re-bless — the new capability
    is opt-in and inert for non-users, so no marker bump is required.
  * HARDENING (error-path / manifest-hygiene, no rendered-output change): a
    non-numeric ``value=`` on Bar/Matrix now raises **E1107** (a dormant spec
    code, environments.md §2.3, made live) instead of a silent flip-back;
    Plane2D ``point[i]`` ``value=`` joins the value-less E1105 class; and a
    spurious ``value_change`` on an E1115-invalid selector is dropped (completing
    the E1115 soft-drop). ``differ.py`` untouched. It is a SemVer MINOR only for
    the new Graph capability; the rendered-output contract is unchanged from
    0.26.5 for every renderable input.

0.28.0 bumps 22→23 (render-quality sweep — four structural families found by a
numeric render-defect sweep + BMAD analysis, investigations/hunt-rq-*.md +
bmad-rq-*.md). Each fix reserves/fits the extent it PAINTS; all are opt-in-inert
for scenes that don't hit the defect, so exactly SIX corpus goldens re-bless and
every other document is byte-identical:
  * FAMILY A — coincident/colliding markers. N ``\\cursor`` carets meeting on one
    cell (the ``lo==hi`` / ``i==j`` two-pointers moment) fanned byte-identical
    triangles + id labels; they now spread via a symmetric coincidence fan (a
    lone caret keeps offset 0 → byte-identical). Queue/Deque front+rear pointer
    TRIANGLES coincided when both land on one cell (labels were already fanned);
    the triangle now takes the same nudge. A caret also registers as a MUST
    obstacle so a same-cell ``position=below`` pill yields below it instead of
    burying the id. Byte: the five small-queue goldens (``queue``, ``bfs``,
    ``bfs_grid_editorial``, ``test_reference_datastruct``, ``07_prescan_no_
    pollution``) re-bless in their coincident-pointer frames only; the caret
    fixes are byte-identical across the corpus (no doc has coincident carets or a
    caret co-located with a pill).
  * FAMILY B — value-channel width reservation. ``Array.set_value`` painted an
    applied ``value=`` without growing ``_cell_width`` (its ``_grow_cell_width``
    was reachable only via ``insert=``), so a wide value clipped the cell /
    overran neighbours; Array now grows like the nine sibling cell-box primitives.
    ``Matrix`` ``show_values`` measured its reserve at the pre-growth font but
    painted at the post-growth font; the value font is now pinned so measure ≡
    paint. Byte: ``two_sum_editorial`` re-blesses (its ``2+11=13``/``2+15=17``
    status values now fit a grown cell instead of overflowing a 58px box); every
    other Array/Matrix scene keeps values under the floor → byte-identical.
  * FAMILY D — text-measurement oracle + a consumer. ``measure_text`` (the 14px
    cell/node surface) charged out-of-Inter math symbols (``∞ → ← ≤ ≥ −(U+2212)
    √``) a flat 0.62em (9px), under-measuring 22–56% and clipping arrow-chain / ∞
    cells; it now consults the vendored KaTeX per-glyph em-advances on the
    Inter-miss branch (``∞→←``→14, ``≤≥−``→11, ``√``→12; ``± × ÷`` are IN the
    subset and stay 9px exactly — CJK/scripts still take the heuristic + W1301).
    ``Bar`` ``show_values`` labels overprinted for near-equal large values (all
    on one y-row) — the column pitch now reserves the timeline-max label width.
    Byte: 0 goldens (no corpus cell holds a literal uncovered symbol; no corpus
    Bar uses ``show_values``).
  * FAMILY E — content-extent vs viewport. ``Plane2D`` ``aspect="equal"`` sized
    the plot height purely from the domain ratio, collapsing/​inverting the Y
    transform on a wide domain and running the viewBox to ~32000px on a tall one
    (and capping an explicit height); the auto height is now clamped to a
    legible, non-runaway band (``[_MIN_PLOT_H=96, _MAX_PLOT_H=1280]``) and an
    explicit height is honoured verbatim. A multi-line ``\\note`` was bounded by
    board WIDTH but never HEIGHT, so a tall pill spilled silently out the viewBox
    bottom; it is now height-bounded (truncate + ellipsis) and soft-warns the new
    **E1126**. Byte: 0 goldens (no corpus asymmetric plot or over-tall note).
``differ.py`` is untouched (zero new motion kinds — carets keep
``cursor_move``/``annotation_*``, pointers are static). No CSS change. The
Graph/Tree/Hypercube node-label overflow family (bmad-rq-nodefit.md) is a
larger layout-engine change (node pitch + viewBox), deferred to a focused next
cycle. Consumer caches keyed on rendered output MUST invalidate.

0.29.0 bumps 23→24 (render-quality sweep round 2 — a second numeric sweep on the
angles round 1 didn't cover: animation transitions, theme/a11y, extreme scale,
cross-primitive composition, investigations/hunt2-*.md). The sweep VALIDATED the
engine as otherwise sound (transitions always fs-snap to the correct server
frame — the flip-back class is absent; geometry never runs away/collapses/clips
at extreme scale; \\zoom/\\group/board-at=/cells-RTL all clean) and surfaced five
fixable defects, all fixed structurally here. Four are opt-in-inert (0 corpus SVG
churn — no corpus scene hits them); the fifth is a shared-CSS change that
re-blesses every page's inline stylesheet by one identical 3-line delta:
  * \\focus now dims Tree/Forest NODES. The defocus/ref-mark regex required
    ``class=`` immediately after ``data-target=``, but tree/forest node ``<g>``
    interpose ``data-node-x/y``, so a focused tree dimmed its edges but not its
    nodes (read as half-working). The regex now tolerates interposed attributes
    and preserves them in the rewrite. Byte-identical for cell/node primitives.
  * RTL/mixed annotation pills carry ``unicode-bidi:plaintext``. The multi-line
    label path applied it; the single-line ``<text>`` fallback omitted it, so a
    short Arabic/Hebrew pill scrambled. Empty (byte-identical) for LTR labels.
  * A cross-shape ``\\link`` / ``\\combine`` label stays inside the stage viewBox.
    ``_emit_scene_links`` placed the mid-bridge label against a ±8192 sentinel
    viewBox, so a blocked label escaped above the board (y≈−1, clipped); it now
    clamps to the real (or zoom-crop) viewBox. Byte-identical when the natural
    seat is clear.
  * A ``Bar`` value that is nonzero but tiny beside a huge one no longer collapses
    to a 0px invisible column — a 2px min-visible floor (a true zero stays empty).
  * The ``dim`` state dropped its group ``opacity: 0.5``. Layered on the muted
    dim-* tokens (designed for ≥4.5:1), the opacity composited text+fill toward
    the stage and halved the REAL contrast to ~1.9:1 on every dim cell — below
    the 3:1 floor, so the tokens' AA was never delivered. Desaturation
    (``saturate(0.3)``) alone keeps the washed-out look. SVG geometry is
    untouched; only the shared inline stylesheet changes (every page re-blesses
    by the identical delta — the DNA-3 shared-asset bump).
``differ.py`` is untouched (zero new motion kinds). Deferred to the theme/layout
cycle: the graph edge-weight pill's dark-mode theming (needs a tint-preserving
rework), the Graph force-layout canvas not scaling with node count (couples with
the node-label layout family), and four LOW transition-window polish items.
Consumer caches keyed on rendered output MUST invalidate.

0.30.0 bumps 24→25 (the graph/theme cluster — the two 0.29.0 deferrals plus the
node-label fit family, one combined bump):
  * Graph edge-weight pill dark theming, tint-preserving: the DEFAULT pill emits
    the literal ``fill="white"`` while every tint emits a hex, so a CSS attribute
    selector ``.scriba-graph-pill[fill="white"]`` (+ ``~ .scriba-graph-weight``
    sibling text rule, both dark scopes) flips ONLY the default chip to the
    idle-fill/idle-text pair (3.71:1 → 14.47:1 on-chip, 12.48:1 bright island →
    blends) and leaves the state-tint signal untouched. Light byte-identical;
    all 107 corpus goldens re-bless by the identical CSS delta (DNA-3).
  * nodefit substrate: ``PrimitiveBase._node_label_wmax`` — monotonic per-node
    cross-frame-max painted label width, seeded from static ids/labels at
    ``__init__`` and grown by ``set_value`` during the ``_prescan_value_widths``
    replay (survives the prescan restore like Queue ``_cell_width``).
  * nodefit A (viewBox honesty): Graph/Tree/Forest/Hypercube fold the painted
    node-label overhang into ``_h_label_pad`` (Forest: into its monotonic
    envelope), so a wide ``value=``/id label grows the frame and shifts the
    translate instead of clipping (the confirmed "dist[v]=infinity" 8px CLIP-L).
  * nodefit B (label-aware pitch): Tree leaf pitch, Hypercube per-row pitch,
    Forest column/seam gaps and the Graph overlap post-pass (per-pair
    ``halves`` separations, one-shot ``_settle_label_layout`` re-spread with
    the canvas re-grown by the label overhang) spread wide labels apart
    instead of letting adjacent node labels collide. Layout settles during
    the prescan, before the first viewbox read (R-32 frame-stable).
  * Graph force-canvas scaling: ``_grow_force_canvas`` sizes the force solve
    by area-per-node (``max(400*300, 7500*N)``, 4:3 kept, floored at the
    default so N ≤ 16 is byte-identical); the auto-seed sweep stays at the
    native pass budget and the WINNER alone gets a convergent overlap resolve
    (10N passes, min_sep from the painted radius). 0/0 overlap/coincident at
    N=40 and N=100 across ring/chords/dense/grid/tree/star probes (was 93
    overlaps + 2 coincident at N=100).
All four are byte-inert on the shipped corpus — the 107 golden re-blesses carry
ONLY the shared-stylesheet delta; no SVG geometry changed in any golden.
Consumer caches keyed on rendered output MUST invalidate."""
