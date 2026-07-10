"""Enforcement test for the theme-attribute contract (JudgeZone bugs #9, #14
+ 15 sibling ESCAPED sites; see _bmad-output/implementation-artifacts/
investigations/judgezone-09-14-dark-theme-attrs-investigation.md).

CONTRACT: every SVG element emitted with a hardcoded light-theme presentation
attribute (``fill=``/``stroke=`` as a literal XML attribute) must be either

  (a) matched by a dark-mode rule in BOTH scopes ([data-theme="dark"] and its
      @media (prefers-color-scheme: dark) twin), or
  (b) whitelisted as theme-neutral, with a comment explaining why.

This file operationalizes that contract two ways:

1. ``FIXED_SITES`` — table-driven, one row per audit-table site this patch
   fixes. Each row asserts the emitter now carries the expected class/attr
   marker AND (for sites that need new CSS) that the dark rule exists in
   both scopes. Mirrors TestGraphPillDarkMode's style in test_contrast.py.
2. A mechanical literal-fill/stroke scanner (``_EXPECTED_WHITE_FILL_COUNTS`` /
   ``_EXPECTED_HEX_WHITE_FILL_COUNTS`` and their ``_STROKE`` twins) that
   counts hardcoded ``fill="white"`` / ``fill="#ffffff"`` / ``stroke="white"``
   / ``stroke="#ffffff"`` occurrences per emitter file. This generalizes past
   today's known sites: a NEW hardcoded white fill or stroke added to any of
   these files in the future must be classified (dark rule, or NEUTRAL_SITES
   whitelist) and the count updated, or this test fails.

Wave 2 (sweep-theme) extended this file with rows 36-38 (annotation/link
label stroke="white" halos, hunted beyond the original audit table), the
stroke="white" scanner generalization described above, and
``TestTexCssDarkTwinParity`` — a structural check that scriba/tex/static's
CSS carries an @media (prefers-color-scheme: dark) twin for every
[data-theme="dark"] rule (a different shape of contract gap than a
hardcoded fill/stroke: the tex sheets used var() correctly throughout, but
were only reachable via an explicit data-theme attribute, never OS
preference alone).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_ANIMATION = _ROOT / "scriba" / "animation"
_PRIMITIVES = _ANIMATION / "primitives"
_STATIC = _ANIMATION / "static"

_SCENE_CSS = _STATIC / "scriba-scene-primitives.css"
_PLANE2D_CSS = _STATIC / "scriba-plane2d.css"
_EMBED_CSS = _STATIC / "scriba-embed.css"
_STANDALONE_CSS = _STATIC / "scriba-standalone.css"
_ANIMATION_CSS = _STATIC / "scriba-animation.css"
_METRICPLOT_CSS = _STATIC / "scriba-metricplot.css"

_TEX_STATIC = _ROOT / "scriba" / "tex" / "static"
_TEX_CONTENT_CSS = _TEX_STATIC / "scriba-tex-content.css"
_TEX_PYGMENTS_DARK_CSS = _TEX_STATIC / "scriba-tex-pygments-dark.css"
_TEX_PYGMENTS_LIGHT_CSS = _TEX_STATIC / "scriba-tex-pygments-light.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _dark_scoped(css: str, selector: str) -> bool:
    """True if `selector` has a declaration block under BOTH the explicit
    [data-theme="dark"] prefix and the @media twin's
    :root:not([data-theme="light"]) prefix (the H6 dual-scoping pattern)."""
    explicit = f'[data-theme="dark"] {selector}'
    twin = f':root:not([data-theme="light"]) {selector}'
    return explicit in css and twin in css


@dataclass(frozen=True)
class Site:
    """One row of the theme-attribute audit that this patch fixes."""

    audit_row: int
    description: str
    kind: str  # "dark_rule" | "self_theme_var" | "value_normalize"
    source_file: Path
    source_marker: str  # literal snippet expected present post-fix
    css_file: "Path | None" = None
    css_selector: "str | None" = None  # required in both scopes if kind == dark_rule


FIXED_SITES: "list[Site]" = [
    Site(
        2, "annotation bracket rect over-reach (#9): rect[fill=\"white\"] scoping",
        "dark_rule",
        _SCENE_CSS, '.scriba-annotation > rect[fill="white"]',
        css_file=_SCENE_CSS, css_selector='.scriba-annotation > rect[fill="white"]',
    ),
    Site(
        7, "plane2d line-label pill rect (#14)",
        "dark_rule",
        _PRIMITIVES / "plane2d.py", 'class="scriba-plane-label-pill"',
        css_file=_PLANE2D_CSS, css_selector=".scriba-plane-label-pill",
    ),
    Site(
        8, "plane2d line-label text (#14)",
        "dark_rule",
        _PRIMITIVES / "plane2d.py", 'css_class="scriba-plane-label-text"',
        css_file=_PLANE2D_CSS, css_selector=".scriba-plane-label-text",
    ),
    Site(
        9, "plane2d point-label text",
        "dark_rule",
        _PRIMITIVES / "plane2d.py", 'css_class="scriba-plane-label-text"',
        css_file=_PLANE2D_CSS, css_selector=".scriba-plane-label-text",
    ),
    Site(
        10, "plane2d x-tick label text",
        "dark_rule",
        _PRIMITIVES / "plane2d.py", 'class="scriba-plane-tick-label"',
        css_file=_PLANE2D_CSS, css_selector=".scriba-plane-tick-label",
    ),
    Site(
        11, "plane2d y-tick label text",
        "dark_rule",
        _PRIMITIVES / "plane2d.py", 'class="scriba-plane-tick-label"',
        css_file=_PLANE2D_CSS, css_selector=".scriba-plane-tick-label",
    ),
    Site(
        15, "graph tint_by_edge idle string-match leak (#ffffff vs white)",
        "value_normalize",
        _PRIMITIVES / "graph.py", '"idle":        "white",',
        # Reuses the pre-existing .scriba-graph-pill[fill="white"] selector
        # (already dark-scoped in both scopes; see TestGraphPillDarkMode in
        # test_contrast.py) — normalizing the literal is what makes it match.
        css_file=_SCENE_CSS, css_selector='.scriba-graph-pill[fill="white"]',
    ),
    Site(
        17, "\\group hull-label pill rect",
        "dark_rule",
        _PRIMITIVES / "graph.py", 'class="scriba-group-label"',
        css_file=_SCENE_CSS, css_selector='.scriba-group-label > rect[fill="white"]',
    ),
    Site(
        18, "\\group hull-label text",
        "dark_rule",
        _PRIMITIVES / "graph.py", 'class="scriba-group-label-text"',
        css_file=_SCENE_CSS, css_selector=".scriba-group-label-text",
    ),
    Site(
        21, "metricplot x-tick label text",
        "self_theme_var",
        _PRIMITIVES / "metricplot.py", 'fill="var(--scriba-fg-muted, #687076)"',
    ),
    Site(
        22, "metricplot left-y-tick label text",
        "self_theme_var",
        _PRIMITIVES / "metricplot.py", 'fill="var(--scriba-fg-muted, #687076)"',
    ),
    Site(
        23, "metricplot right-y-tick label text",
        "self_theme_var",
        _PRIMITIVES / "metricplot.py", 'fill="var(--scriba-fg-muted, #687076)"',
    ),
    Site(
        24, "metricplot xlabel",
        "self_theme_var",
        _PRIMITIVES / "metricplot.py", 'fill="var(--scriba-fg, #11181c)"',
    ),
    Site(
        25, "metricplot ylabel (left)",
        "self_theme_var",
        _PRIMITIVES / "metricplot.py", 'fill="var(--scriba-fg, #11181c)"',
    ),
    Site(
        26, "metricplot ylabel (right, two-axis)",
        "self_theme_var",
        _PRIMITIVES / "metricplot.py", 'fill="var(--scriba-fg, #11181c)"',
    ),
    Site(
        29, "codepanel panel background/border rect",
        "dark_rule",
        _PRIMITIVES / "codepanel.py", 'class="scriba-codepanel-chrome"',
        css_file=_SCENE_CSS, css_selector=".scriba-codepanel-chrome",
    ),
    Site(
        30, "codepanel empty-panel \"no code\" text",
        "dark_rule",
        _PRIMITIVES / "codepanel.py", 'class="scriba-codepanel-empty-text"',
        css_file=_SCENE_CSS, css_selector=".scriba-codepanel-empty-text",
    ),
    Site(
        34, "codepanel header title-bar path",
        "dark_rule",
        _PRIMITIVES / "codepanel.py", 'class="scriba-codepanel-chrome"',
        css_file=_SCENE_CSS, css_selector=".scriba-codepanel-chrome",
    ),
    Site(
        35, "codepanel header/divider line",
        "dark_rule",
        _PRIMITIVES / "codepanel.py", 'class="scriba-codepanel-chrome"',
        css_file=_SCENE_CSS, css_selector=".scriba-codepanel-chrome",
    ),
    # --- Wave 2 (sweep-theme): residual escapes NOT in the original
    # audit table above — found while hunting stroke="white" / paint-order
    # halo sites across scriba/animation/**/*.py. Numbered 36+ to make
    # clear these are new discoveries, not renumbered originals.
    Site(
        36, "annotation pill-label text halo (wave 2): stroke=\"white\" "
            "paint-order halo unmatched by the pill's dark fill",
        "dark_rule",
        _PRIMITIVES / "_svg_helpers.py", 'class="scriba-annot-label-text"',
        css_file=_SCENE_CSS, css_selector=".scriba-annot-label-text",
    ),
    Site(
        37, "annotation pill-label math/FO ink halo (wave 2): inline "
            "text-shadow:...#fff on the scriba-annot-label KaTeX div",
        "dark_rule",
        _PRIMITIVES / "_svg_helpers.py", 'class="scriba-annot-label"',
        css_file=_SCENE_CSS, css_selector=".scriba-annot-label",
    ),
    Site(
        38, "\\link annotation label halo (wave 2): stroke=\"white\" halo "
            "on the un-backed floating link label",
        "dark_rule",
        _ANIMATION / "_frame_renderer.py", 'class="scriba-link-label-text"',
        css_file=_SCENE_CSS, css_selector=".scriba-link-label-text",
    ),
]


# --- Whitelisted theme-neutral sites (explicit, with reasons) --------------
# These sit adjacent to FIXED_SITES in the same files/dicts and must NOT be
# mistaken for escapes by anyone extending this table later.
NEUTRAL_SITES = {
    "graph.py:_PILL_TINT_BY_EDGE_STATE (current/good/bad/done/dim/active/"
    "highlighted/muted)": (
        "row 16 — intentional per-state colour tints (blue/green/red/gray "
        "hues), NOT white; by design not theme-controlled (mirrors "
        "tint_by_source, row 14)."
    ),
    "graph.py:_PILL_TINT_BY_STATE (tint_by_source, all states)": (
        "row 14 — intentional per-state colour tints; documented "
        "light-only limitation (GEP-19 fast-follow), not part of this "
        "bug family."
    ),
    "metricplot.py: user-supplied series/line colors": (
        "row 27 — user-chosen data colors are content, not chrome; "
        "theme-neutral by design."
    ),
    "base.py: bracket annotation stroke color (row 3)": (
        "ESCAPED-minor, explicitly out of scope for this patch per "
        "team-lead's work-item list (#9 + 15 siblings only); tracked as "
        "a follow-up in the investigation doc, not silently missed."
    ),
}


@pytest.mark.unit
class TestThemeAttrContractFixedSites:
    """Every audit-table site this patch closes: the emitter carries its new
    marker, and (where applicable) the CSS dark rule exists in both scopes."""

    @staticmethod
    def _text(path: Path) -> str:
        return _read(path)

    @pytest.mark.parametrize(
        "site", FIXED_SITES, ids=[f"row{s.audit_row}-{s.description}" for s in FIXED_SITES]
    )
    def test_site_marker_present_in_source(self, site: Site):
        source = self._text(site.source_file)
        assert site.source_marker in source, (
            f"row {site.audit_row} ({site.description}): expected marker "
            f"{site.source_marker!r} not found in {site.source_file}"
        )

    @pytest.mark.parametrize(
        "site",
        [s for s in FIXED_SITES if s.kind == "dark_rule"],
        ids=[f"row{s.audit_row}-{s.description}" for s in FIXED_SITES if s.kind == "dark_rule"],
    )
    def test_site_dark_rule_present_in_both_scopes(self, site: Site):
        assert site.css_file is not None and site.css_selector is not None
        css = self._text(site.css_file)
        assert _dark_scoped(css, site.css_selector), (
            f"row {site.audit_row} ({site.description}): selector "
            f"{site.css_selector!r} missing a dark rule in one or both "
            f"scopes ([data-theme=\"dark\"] / @media twin) in {site.css_file}"
        )

    @pytest.mark.parametrize(
        "site",
        [s for s in FIXED_SITES if s.kind == "value_normalize"],
        ids=[f"row{s.audit_row}" for s in FIXED_SITES if s.kind == "value_normalize"],
    )
    def test_value_normalized_site_reuses_existing_dark_rule(self, site: Site):
        """Fix C shape: the emitter now emits a literal that string-matches a
        PRE-EXISTING attribute-scoped dark rule (no new CSS needed)."""
        assert site.css_file is not None and site.css_selector is not None
        css = self._text(site.css_file)
        assert _dark_scoped(css, site.css_selector), (
            f"row {site.audit_row}: pre-existing selector "
            f"{site.css_selector!r} should already be dark-scoped in both "
            f"scopes; value-normalization alone should suffice"
        )


@pytest.mark.unit
class TestAnnotationRectOverReachFixed:
    """Bug #9: `.scriba-annotation > rect` was unscoped in the dark block,
    so the bracket outline (fill="none") was painted a dark fill it should
    never have had. Mirrors TestGraphPillDarkMode's
    test_dark_pill_rule_is_default_scoped_not_blanket."""

    @staticmethod
    def _css() -> str:
        return _read(_SCENE_CSS)

    def test_bare_unscoped_annotation_rect_dark_rule_is_gone(self):
        css = self._css()
        assert re.search(r'\.scriba-annotation\s*>\s*rect\s*\{', css) is None, (
            "an unscoped `.scriba-annotation > rect {` dark rule remains — "
            "this is exactly bug #9's over-reach shape"
        )

    def test_attr_scoped_annotation_rect_dark_rule_present_both_scopes(self):
        assert _dark_scoped(self._css(), '.scriba-annotation > rect[fill="white"]')


@pytest.mark.unit
class TestGraphTintByEdgeIdleColor:
    """Fix C: idle edge-pill tint must be the string "white" (not "#ffffff")
    so it string-matches [fill="white"], the exact defect shape row 15
    documents (CSS attribute selectors are exact-match, not color-equivalence)."""

    def test_idle_tint_value_is_white_not_hex(self):
        from scriba.animation.primitives.graph import _PILL_TINT_BY_EDGE_STATE

        assert _PILL_TINT_BY_EDGE_STATE["idle"] == "white"

    def test_pill_tint_for_edge_state_fallback_is_white_not_hex(self):
        from scriba.animation.primitives.graph import _pill_tint_for_edge_state

        assert _pill_tint_for_edge_state("some-unknown-state") == "white"


# --- Mechanical regression net: no NEW hardcoded white fill goes unchecked --
_SCANNED_FILES = [
    "_svg_helpers.py",
    "base.py",
    "graph.py",
    "plane2d.py",
    "metricplot.py",
    "codepanel.py",
    "_frame_renderer.py",
    "_text_render.py",
]

# Exact count of literal `fill="white"` occurrences in *code* (comment lines
# excluded) per file. Every occurrence is individually accounted for in
# judgezone-09-14-dark-theme-attrs-investigation.md's audit table.
#
# A count that RISES means a NEW hardcoded fill="white" appeared and hasn't
# been classified — give it a class + dark-rule pair (Fix A/B/D pattern) or
# add it to NEUTRAL_SITES with a reason, then update this number. A count
# that FALLS is fine (a site was fixed away) — lower the number.
_EXPECTED_WHITE_FILL_COUNTS = {
    # rows 4/5 (emit_plain_arrow_svg ~2235, emit_position_label_svg ~3787)
    # plus one more inside emit_plain_arrow_svg's private helper
    # _emit_label_and_pill (~2614, not its own audit row — same function as
    # row 4, same .scriba-annotation-wrapped emission, just factored into a
    # helper) — all legit label-pill backdrops, COVERED (FENCED, untouched).
    "_svg_helpers.py": 3,
    "base.py": 1,           # row 1 — trace-label pill, COVERED (untouched)
    "graph.py": 1,          # row 17 — \group hull-label pill; FIXED via new .scriba-group-label>rect[fill="white"] rule
    "plane2d.py": 1,        # row 7 — line-label pill; FIXED via new class=scriba-plane-label-pill + dark rule
    "metricplot.py": 0,
    "codepanel.py": 0,
    # row 6 — note-annotation pill rect, child of <g class="scriba-annotation
    # scriba-note scriba-annotation-{cls}"> — same shape as rows 1/4/5,
    # already COVERED by Fix A's .scriba-annotation > rect[fill="white"]
    # rule (both scopes). Not in this patch's OWN file list; no edit here.
    "_frame_renderer.py": 1,
    "_text_render.py": 0,
}

# fill="#ffffff" as a literal attribute (not a dict value) — none exist
# today; row 15's leak was a dict-value/f-string-interpolation issue, not
# this literal shape. Kept as a forward-looking guard.
_EXPECTED_HEX_WHITE_FILL_COUNTS = {name: 0 for name in _SCANNED_FILES}

# Same generalization, for stroke="white" (wave-2 sweep: the hand-rolled
# text halo shape, distinct from fill="white" pill backdrops). Rows 36/38
# are FIXED but — like the fill="white" sites above — the literal itself is
# intentionally left in place (a class marker + dark CSS rule re-tints it;
# removing the literal would break test_link_label_carries_halo's regex
# lock on row 38's site). A count that RISES means a NEW hardcoded
# stroke="white" halo appeared unclassified; give it the same treatment.
_EXPECTED_WHITE_STROKE_COUNTS = {
    "_svg_helpers.py": 2,     # row 36 — _emit_pill_label_text + _emit_label_single_line
    "base.py": 0,
    "graph.py": 0,
    "plane2d.py": 0,
    "metricplot.py": 0,
    "codepanel.py": 0,
    "_frame_renderer.py": 1,  # row 38 — \link annotation label
    "_text_render.py": 0,
}
_EXPECTED_HEX_WHITE_STROKE_COUNTS = {name: 0 for name in _SCANNED_FILES}

# _frame_renderer.py lives one directory up from the other scanned files
# (scriba/animation/, not scriba/animation/primitives/).
_FILE_DIRS = {"_frame_renderer.py": _ANIMATION}


def _scanned_path(filename: str) -> Path:
    return _FILE_DIRS.get(filename, _PRIMITIVES) / filename


_WHITE_FILL_RE = re.compile(r'fill="white"')
_HEX_WHITE_FILL_RE = re.compile(r'fill="#ffffff"', re.IGNORECASE)
_WHITE_STROKE_RE = re.compile(r'stroke="white"')
_HEX_WHITE_STROKE_RE = re.compile(r'stroke="#ffffff"', re.IGNORECASE)


def _count_code_matches(text: str, pattern: "re.Pattern[str]") -> int:
    """Count regex matches in code, excluding whole-line and trailing
    comments. A trailing comment is split off at the first whitespace+"#";
    hex-color literals in this codebase are always quote-adjacent
    (``"#1a1d1e"``), never whitespace-adjacent, so this doesn't clip them."""
    count = 0
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        code_part = re.split(r"\s#", line, maxsplit=1)[0]
        count += len(pattern.findall(code_part))
    return count


@pytest.mark.unit
class TestNoUnaccountedHardcodedWhiteFill:
    """Generalizes past today's known sites: scans every primitive emitter
    file for literal fill="white" / fill="#ffffff" and asserts the count
    matches the explicit, commented baseline above."""

    @pytest.mark.parametrize("filename", _SCANNED_FILES)
    def test_white_fill_literal_count_matches_baseline(self, filename: str):
        text = _read(_scanned_path(filename))
        actual = _count_code_matches(text, _WHITE_FILL_RE)
        expected = _EXPECTED_WHITE_FILL_COUNTS[filename]
        assert actual == expected, (
            f'{filename}: found {actual} literal fill="white" occurrence(s), '
            f"baseline expects {expected}. If you ADDED one, give it a dark "
            f"rule (or whitelist it in NEUTRAL_SITES) and update the "
            f"baseline; if you REMOVED one, lower the baseline."
        )

    @pytest.mark.parametrize("filename", _SCANNED_FILES)
    def test_hex_white_fill_literal_count_matches_baseline(self, filename: str):
        text = _read(_scanned_path(filename))
        actual = _count_code_matches(text, _HEX_WHITE_FILL_RE)
        expected = _EXPECTED_HEX_WHITE_FILL_COUNTS[filename]
        assert actual == expected, (
            f'{filename}: found {actual} literal fill="#ffffff" '
            f"occurrence(s), baseline expects {expected}. Prefer the string "
            f'"white" so it string-matches the existing [fill="white"] '
            f"selector family (see row 15 / Fix C)."
        )

    @pytest.mark.parametrize("filename", _SCANNED_FILES)
    def test_white_stroke_literal_count_matches_baseline(self, filename: str):
        """wave-2 sweep: same generalization as the fill="white" scan above,
        for the hand-rolled stroke="white" text-halo shape (rows 36/38)."""
        text = _read(_scanned_path(filename))
        actual = _count_code_matches(text, _WHITE_STROKE_RE)
        expected = _EXPECTED_WHITE_STROKE_COUNTS[filename]
        assert actual == expected, (
            f'{filename}: found {actual} literal stroke="white" '
            f"occurrence(s), baseline expects {expected}. If you ADDED one, "
            f"give it a dark rule (or whitelist it in NEUTRAL_SITES) and "
            f"update the baseline; if you REMOVED one, lower the baseline."
        )

    @pytest.mark.parametrize("filename", _SCANNED_FILES)
    def test_hex_white_stroke_literal_count_matches_baseline(self, filename: str):
        text = _read(_scanned_path(filename))
        actual = _count_code_matches(text, _HEX_WHITE_STROKE_RE)
        expected = _EXPECTED_HEX_WHITE_STROKE_COUNTS[filename]
        assert actual == expected, (
            f'{filename}: found {actual} literal stroke="#ffffff" '
            f"occurrence(s), baseline expects {expected}. Prefer the string "
            f'"white" so it string-matches the existing selector family.'
        )


# --- Wave 2 (sweep-theme) target (b): CSS dark-twin structural parity ------
# scriba-tex-content.css and scriba-tex-pygments-dark.css previously carried
# [data-theme="dark"] rules with NO @media (prefers-color-scheme: dark) twin
# anywhere in the file — unlike every other themed CSS asset in this
# codebase (scriba-scene-primitives.css, scriba-embed.css's own H6 fix,
# scriba-plane2d.css). Both tex sheets can ship standalone into a host page
# that never sets data-theme explicitly (see TexRenderer.assets() and
# examples/integration/minimal.py — render.py's own page template is not the
# only consumer, and its own theme-toggle <script> is a pure click listener
# with no matchMedia/OS-preference sync, so data-theme is only ever set by
# an explicit user click or an explicit host page). Without the twin, OS
# dark preference was silently ignored for tex content until that click.
# Every rule body already used var(--scriba-*) correctly — this is a
# structural/token-scope gap, not a hardcoded-literal escape, so it doesn't
# fit the Site/FIXED_SITES shape (no Python emitter literal to match).
#
# _count_code_matches above is Python-comment-aware (strips "#" lines); CSS
# comments are "/* ... */", so a dedicated CSS-comment-aware counter is used
# instead of reusing it directly.
_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _count_css_matches(text: str, pattern: "re.Pattern[str]") -> int:
    """Count regex matches in CSS, excluding /* ... */ comments."""
    return len(pattern.findall(_CSS_COMMENT_RE.sub("", text)))


_DARK_ATTR_RE = re.compile(r'\[data-theme="dark"\]')
_MEDIA_TWIN_RE = re.compile(r':root:not\(\[data-theme="light"\]\)')

_TEX_CSS_FILES = [_TEX_CONTENT_CSS, _TEX_PYGMENTS_DARK_CSS, _TEX_PYGMENTS_LIGHT_CSS]


@pytest.mark.unit
class TestTexCssDarkTwinParity:
    """Every [data-theme="dark"] selector-prefix occurrence in a tex CSS
    file must have a matching :root:not([data-theme="light"]) occurrence
    inside an @media (prefers-color-scheme: dark) block in the SAME file
    (the H6 fix pattern duplicates each dark rule 1:1 into its twin). A
    mismatch means a dark rule was added, or removed, on only one side."""

    @pytest.mark.parametrize(
        "css_file", _TEX_CSS_FILES, ids=[p.name for p in _TEX_CSS_FILES]
    )
    def test_dark_attr_count_matches_media_twin_count(self, css_file: Path):
        text = _read(css_file)
        dark_count = _count_css_matches(text, _DARK_ATTR_RE)
        twin_count = _count_css_matches(text, _MEDIA_TWIN_RE)
        assert dark_count == twin_count, (
            f'{css_file.name}: {dark_count} [data-theme="dark"] '
            f"selector-prefix occurrence(s) but {twin_count} "
            f':root:not([data-theme="light"]) twin occurrence(s) in the '
            f"same file — every dark rule needs a duplicate under @media "
            f"(prefers-color-scheme: dark) so OS-level dark preference "
            f"works before any explicit theme-toggle click (H6 fix "
            f"pattern; see scriba-embed.css)."
        )


_ANIMATION_STATIC_CSS_FILES = [_EMBED_CSS, _STANDALONE_CSS, _ANIMATION_CSS, _METRICPLOT_CSS]


@pytest.mark.unit
class TestAnimationStaticCssDarkTwinParity:
    """Same H6 dual-scoping guarantee as TestTexCssDarkTwinParity (see above),
    applied to the widget/page-shell CSS bundle (target (c) of the wave-2
    theme-attr sweep). scriba-animation.css and scriba-metricplot.css
    currently have zero [data-theme="dark"] rules — their colors are all
    var(...) references with graceful fallback, so 0 == 0 passes and this
    doubles as a regression guard if a future edit adds a dark-scoped rule
    to either file without its @media twin."""

    @pytest.mark.parametrize(
        "css_file",
        _ANIMATION_STATIC_CSS_FILES,
        ids=[p.name for p in _ANIMATION_STATIC_CSS_FILES],
    )
    def test_dark_attr_count_matches_media_twin_count(self, css_file: Path):
        text = _read(css_file)
        dark_count = _count_css_matches(text, _DARK_ATTR_RE)
        twin_count = _count_css_matches(text, _MEDIA_TWIN_RE)
        assert dark_count == twin_count, (
            f'{css_file.name}: {dark_count} [data-theme="dark"] '
            f"selector-prefix occurrence(s) but {twin_count} "
            f':root:not([data-theme="light"]) twin occurrence(s) in the '
            f"same file — every dark rule needs a duplicate under @media "
            f"(prefers-color-scheme: dark) so OS-level dark preference "
            f"works before any explicit theme-toggle click (H6 fix "
            f"pattern; see scriba-embed.css)."
        )
