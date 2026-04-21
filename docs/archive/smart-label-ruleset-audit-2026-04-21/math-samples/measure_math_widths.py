"""
Math-label width audit: compare _label_width_text estimator predictions
against real KaTeX-rendered bbox measurements via Playwright headless Chromium.

Usage (from repo root with venv active):
    python docs/archive/smart-label-ruleset-audit-2026-04-21/math-samples/measure_math_widths.py

Outputs:
  - 20 .tex sample files in the same directory
  - JSON results file: results.json
  - Prints a summary table to stdout
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

# ---- add repo root to path -----------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[4]  # 4 levels up from math-samples/
sys.path.insert(0, str(REPO_ROOT))

from scriba.animation.primitives._svg_helpers import _label_width_text
from scriba.animation.primitives._text_render import estimate_text_width
from scriba.core.css_bundler import inline_katex_css
from scriba.tex.renderer import TexRenderer
from scriba.core.workers import SubprocessWorkerPool

# ---------------------------------------------------------------------------
# Corpus: 20 labels spanning complexity tiers
# ---------------------------------------------------------------------------
# Format: (id, label_source, description)
CORPUS: list[tuple[str, str, str]] = [
    # --- Tier 1: trivial single-symbol math ---
    ("S01", r"$x$",                          "single variable"),
    ("S02", r"$n$",                          "single letter n"),
    ("S03", r"$1$",                          "single digit"),
    # --- Tier 2: simple expressions ---
    ("S04", r"$x^2$",                        "variable with superscript"),
    ("S05", r"$x_i$",                        "variable with subscript"),
    ("S06", r"$\alpha + \beta$",             "greek letters with operator"),
    ("S07", r"$n-1$",                        "subtraction (no \\-split)"),
    # --- Tier 3: command-heavy (stripped by regex) ---
    ("S08", r"$\mathbb{R}$",                 "double-struck R"),
    ("S09", r"$\mathcal{O}(n)$",             "calligraphic O with arg"),
    ("S10", r"$\textbf{x}$",                 "textbf command"),
    ("S11", r"$\mathbf{v}$",                 "mathbf vector"),
    # --- Tier 4: fractions and stacked structures ---
    ("S12", r"$\frac{a}{b}$",               "simple fraction"),
    ("S13", r"$\frac{n+1}{2}$",             "fraction with expression"),
    ("S14", r"$\frac{\partial f}{\partial x}$", "partial derivative fraction"),
    # --- Tier 5: large operators with limits ---
    ("S15", r"$\sum_{i=0}^{n} x_i$",        "sum with limits"),
    ("S16", r"$\prod_{k=1}^{n} k$",         "product with limits"),
    # --- Tier 6: mixed text + math ---
    ("S17", r"value = $\frac{a+b}{2}$",     "mixed text+fraction"),
    ("S18", r"$O(n \log n)$",               "big-O with log"),
    # --- Tier 7: edge cases ---
    ("S19", r"$\displaystyle\sum_{i=1}^{n} \frac{1}{i^2}$", "displaystyle sum-frac"),
    ("S20", r"$\hat{\theta} = \bar{x} \pm \frac{\sigma}{\sqrt{n}}$",
            "estimate with pm and sqrt"),
]

FONT_PX = 11   # default annotation font size


def compute_estimator(label: str) -> tuple[str, int]:
    """Return (stripped_string, estimated_px_width)."""
    est_str = _label_width_text(label)
    est_px = estimate_text_width(est_str, FONT_PX)
    return est_str, est_px


def render_all_html(labels: list[str]) -> list[str]:
    """Render all labels through TexRenderer, return HTML strings."""
    pool = SubprocessWorkerPool()
    renderer = TexRenderer(worker_pool=pool)
    results = []
    for label in labels:
        try:
            html = renderer.render_inline_text(label)
        except Exception as exc:
            html = f"<span>ERROR: {exc}</span>"
        results.append(html)
    renderer.close()
    return results


def build_measurement_html(label_htmls: list[tuple[str, str, str]]) -> str:
    """
    Build an HTML page that renders each KaTeX label in an absolutely-positioned
    span, assigns each a unique ID, then measures getBoundingClientRect() via JS.

    label_htmls: list of (label_id, label_source, rendered_html)
    Returns: full HTML string
    """
    katex_css = inline_katex_css()

    items_html = ""
    for lid, _src, html in label_htmls:
        items_html += (
            f'<span id="{lid}" style="display:inline-block;white-space:nowrap;'
            f'font-size:{FONT_PX}px;font-family:ui-monospace,monospace;'
            f'position:absolute;visibility:hidden;">'
            f'{html}</span>\n'
        )

    measure_js = """
    const results = {};
    document.querySelectorAll('span[id]').forEach(el => {
        const rect = el.getBoundingClientRect();
        results[el.id] = {width: rect.width, height: rect.height};
    });
    return results;
    """

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{katex_css}
body {{ margin: 0; padding: 0; background: white; }}
</style>
</head>
<body>
{items_html}
</body>
</html>
"""


def measure_with_playwright(html_content: str) -> dict[str, dict[str, float]]:
    """Launch headless Chromium, load the page, measure bbox for each span."""
    from playwright.sync_api import sync_playwright

    measure_js = """() => {
    const results = {};
    document.querySelectorAll('span[id]').forEach(el => {
        // Make visible for measurement
        el.style.visibility = 'visible';
        const rect = el.getBoundingClientRect();
        results[el.id] = {width: rect.width, height: rect.height};
        el.style.visibility = 'hidden';
    });
    return results;
    }"""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 2000, "height": 2000})
        page.set_content(html_content, wait_until="networkidle")
        # Give KaTeX fonts time to settle; they're data-URIs so no network needed
        page.wait_for_timeout(300)
        results = page.evaluate(measure_js)
        browser.close()

    return results


def main() -> None:
    sample_dir = Path(__file__).parent
    sample_dir.mkdir(parents=True, exist_ok=True)

    # ---- 1. Write .tex sample files ----------------------------------------
    print("Writing .tex sample files...")
    for lid, label, description in CORPUS:
        tex_path = sample_dir / f"{lid}.tex"
        tex_path.write_text(f"% {description}\n{label}\n", encoding="utf-8")

    # ---- 2. Compute estimator predictions ----------------------------------
    print("Computing estimator predictions...")
    estimator_rows: list[dict] = []
    for lid, label, description in CORPUS:
        est_str, est_px = compute_estimator(label)
        estimator_rows.append({
            "id": lid,
            "label": label,
            "description": description,
            "est_str": est_str,
            "est_px": est_px,
        })

    # ---- 3. Render HTML via KaTeX ------------------------------------------
    print("Rendering KaTeX HTML for all labels...")
    labels = [row["label"] for row in estimator_rows]
    rendered_htmls = render_all_html(labels)

    label_htmls: list[tuple[str, str, str]] = [
        (row["id"], row["label"], html)
        for row, html in zip(estimator_rows, rendered_htmls)
    ]

    # ---- 4. Measure with Playwright ----------------------------------------
    print("Building measurement HTML page...")
    html_content = build_measurement_html(label_htmls)
    html_path = sample_dir / "_measurement_page.html"
    html_path.write_text(html_content, encoding="utf-8")
    print(f"  Saved measurement page: {html_path}")

    print("Measuring with Playwright headless Chromium...")
    bboxes = measure_with_playwright(html_content)

    # ---- 5. Tabulate results ------------------------------------------------
    results = []
    for row in estimator_rows:
        lid = row["id"]
        est_px = row["est_px"]
        bbox = bboxes.get(lid, {})
        true_w = bbox.get("width", 0.0)
        true_h = bbox.get("height", 0.0)

        if true_w > 0:
            error_px = est_px - true_w
            error_pct = (error_px / true_w) * 100.0
        else:
            error_px = float("nan")
            error_pct = float("nan")

        results.append({
            "id": lid,
            "label": row["label"],
            "description": row["description"],
            "est_str": row["est_str"],
            "est_px": est_px,
            "true_w": round(true_w, 2),
            "true_h": round(true_h, 2),
            "error_px": round(error_px, 2) if not math.isnan(error_px) else None,
            "error_pct": round(error_pct, 2) if not math.isnan(error_pct) else None,
        })

    # ---- 6. Compute RMSE and summary stats ---------------------------------
    errors_px = [r["error_px"] for r in results if r["error_px"] is not None]
    errors_pct = [r["error_pct"] for r in results if r["error_pct"] is not None]

    if errors_px:
        rmse = math.sqrt(sum(e**2 for e in errors_px) / len(errors_px))
        mean_err = sum(errors_px) / len(errors_px)
        underestimates = [r for r in results if r["error_px"] is not None and r["error_px"] < 0]
        overestimates  = [r for r in results if r["error_px"] is not None and r["error_px"] > 0]
    else:
        rmse = float("nan")
        mean_err = float("nan")
        underestimates = []
        overestimates  = []

    # ---- 7. Save JSON -------------------------------------------------------
    out = {
        "corpus_size": len(results),
        "font_px": FONT_PX,
        "summary": {
            "rmse_px": round(rmse, 2),
            "mean_error_px": round(mean_err, 2),
            "under_count": len(underestimates),
            "over_count": len(overestimates),
            "exact_count": len(results) - len(underestimates) - len(overestimates),
        },
        "rows": results,
    }
    json_path = sample_dir / "results.json"
    json_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved: {json_path}")

    # ---- 8. Print table ----------------------------------------------------
    print("\n" + "=" * 110)
    print(f"{'ID':<5} {'Label':<50} {'Est':>6} {'True':>7} {'Err px':>8} {'Err %':>8} {'Description'}")
    print("-" * 110)
    for r in results:
        err_px = f"{r['error_px']:+.1f}" if r["error_px"] is not None else "N/A"
        err_pct = f"{r['error_pct']:+.1f}%" if r["error_pct"] is not None else "N/A"
        label_disp = r["label"][:48]
        print(f"{r['id']:<5} {label_disp:<50} {r['est_px']:>6} {r['true_w']:>7.1f} {err_px:>8} {err_pct:>8}  {r['description']}")
    print("-" * 110)
    print(f"{'RMSE':>61}: {rmse:.2f} px   mean_err: {mean_err:+.2f} px")
    print(f"  Under-estimates (est < true): {len(underestimates)}")
    print(f"  Over-estimates  (est > true): {len(overestimates)}")
    print(f"  Exact (within 0 px):          {len(results) - len(underestimates) - len(overestimates)}")
    print("=" * 110)


if __name__ == "__main__":
    main()
