"""R-15 Accessible-Name Policy — conformance test suite (JudgeZone #10 sweep).

Spec: docs/spec/smart-label-ruleset.md (R-15, "<title> as first child of
each <svg> root") and the shared JudgeZone #10 family contract: accessible
names MUST come from author natural language (env/step ``label=``, step
``title=``, narration text). When no natural language exists, the name
channel is OMITTED — never defaulted to an internal system slug
(``scene_id`` / ``data-substory-id`` / widget ``id=``).

These tests walk the BLESSED golden corpus (``tests/golden/examples/corpus/
*.html``) directly rather than re-rendering fixtures: the corpus is the
rendered truth already reviewed for byte-for-byte regression testing, so it
is the cheapest, most representative surface to assert the policy over.

Error codes tested:
  R15-01  <title> text equals an internal id in the same document
  R15-02  aria-label on a role="img"/"region" element equals an internal id
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CORPUS_DIR = _REPO_ROOT / "tests" / "golden" / "examples" / "corpus"

_HTML_FILES = sorted(_CORPUS_DIR.glob("*.html"))
_HTML_IDS = [f.stem for f in _HTML_FILES]


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

# Internal system slugs: the identifiers the R-15 policy forbids from ever
# surfacing as an accessible name. Deliberately narrow — author-supplied
# structural content (graph node ids, cursor ids, annotation selectors) is
# NOT in this set; it is legitimate accessible content, not a system slug.
_INTERNAL_ID_RE = re.compile(
    r'data-scriba-scene="([^"]*)"'
    r'|data-substory-id="([^"]*)"'
    r'|class="scriba-widget"[^>]*\bid="([^"]*)"'
)

_TITLE_RE = re.compile(r"<title>([^<]*)</title>")

# One opening tag, non-greedy, single line (all emitters in this codebase
# emit attributes on one logical `<tag ...>` without embedded `>`).
_OPEN_TAG_RE = re.compile(r"<[a-zA-Z][a-zA-Z0-9]*\b[^>]*>")
_ROLE_IMG_OR_REGION_RE = re.compile(r'\brole="(?:img|region)"')
_ARIA_LABEL_RE = re.compile(r'aria-label="([^"]*)"')


def _internal_ids(html: str) -> set[str]:
    ids: set[str] = set()
    for match in _INTERNAL_ID_RE.finditer(html):
        for group in match.groups():
            if group:
                ids.add(group)
    return ids


def _titles(html: str) -> list[str]:
    return _TITLE_RE.findall(html)


def _role_scoped_aria_labels(html: str) -> list[str]:
    """aria-label values on elements carrying role="img" or role="region"."""
    labels: list[str] = []
    for tag in _OPEN_TAG_RE.findall(html):
        if not _ROLE_IMG_OR_REGION_RE.search(tag):
            continue
        m = _ARIA_LABEL_RE.search(tag)
        if m:
            labels.append(m.group(1))
    return labels


# ---------------------------------------------------------------------------
# Conformance tests
# ---------------------------------------------------------------------------


@pytest.mark.conformance
@pytest.mark.parametrize("html_path", _HTML_FILES, ids=_HTML_IDS)
def test_title_never_surfaces_internal_id(html_path: Path) -> None:
    """R15-01: no <title> text may equal a data-scriba-scene / widget id.

    Internal slugs are for wiring (DOM lookups, CSS hooks), not for the
    accessible-name tree. If a <title> exactly equals one of the document's
    own internal ids, the slug leaked into the accessibility tree instead
    of author natural language (or omission).
    """
    html = html_path.read_text(encoding="utf-8")
    internal_ids = _internal_ids(html)
    if not internal_ids:
        pytest.skip(f"{html_path.name}: no data-scriba-scene/widget id present")

    for title_text in _titles(html):
        assert title_text.strip() not in internal_ids, (
            f"R15-01 VIOLATION [{html_path.name}]: <title>{title_text}</title> "
            f"equals an internal id in this document ({sorted(internal_ids)}). "
            "Accessible names must come from author natural language "
            "(label=/title=/narration) or be omitted -- never an internal "
            "scene_id/widget id slug."
        )


@pytest.mark.conformance
@pytest.mark.parametrize("html_path", _HTML_FILES, ids=_HTML_IDS)
def test_role_img_or_region_aria_label_traces_to_author_content(
    html_path: Path,
) -> None:
    """R15-02: aria-label on role="img"/"region" must not equal an internal id.

    Covers the SVG root (role="img") and the interactive PLAYER widget
    container (role="region") -- the two channels the shared accessible-name
    policy governs directly. A match against an internal id is a
    spot-verifiable proxy for "this label is a slug, not author content."
    """
    html = html_path.read_text(encoding="utf-8")
    internal_ids = _internal_ids(html)
    if not internal_ids:
        pytest.skip(f"{html_path.name}: no data-scriba-scene/widget id present")

    for aria_label in _role_scoped_aria_labels(html):
        assert aria_label.strip() not in internal_ids, (
            f'R15-02 VIOLATION [{html_path.name}]: aria-label="{aria_label}" '
            f'on a role="img"/"region" element equals an internal id in this '
            f"document ({sorted(internal_ids)}). Accessible names must come "
            "from author natural language or a generic fallback word -- "
            "never an internal scene_id/widget id slug."
        )


def test_corpus_is_non_empty() -> None:
    """Guard against a silently-empty parametrize list (e.g. path drift)."""
    assert len(_HTML_FILES) >= 100, (
        f"Expected the blessed golden corpus at {_CORPUS_DIR} to contain "
        f"100+ HTML fixtures; found {len(_HTML_FILES)}. If the corpus moved "
        "or sync_corpus.py wasn't run, R15-01/R15-02 above are silently "
        "vacuous (0 params), not passing on merit."
    )
