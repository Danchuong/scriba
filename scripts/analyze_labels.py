#!/usr/bin/env python3
"""Analyze rendered HTML files for smart-label placement quality issues.

For each rendered HTML in the input directory:
- Parses all frames (from var frames=[...] in the HTML)
- Extracts annotation pill bounding boxes from SVG
- Classifies each frame for label quality issues

Usage:
    python scripts/analyze_labels.py <rendered_dir> <screenshots_dir> > analysis.json
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import TypedDict


class PillBox(TypedDict):
    x: float
    y: float
    w: float
    h: float
    rx: float
    label: str
    color: str
    ann_id: str


class ArrowDef(TypedDict):
    d: str        # SVG path d attribute
    length_est: float
    ann_id: str


class FrameAnalysis(TypedDict):
    file: str
    frame_idx: int
    viewbox: list[float]      # [x, y, w, h]
    pills: list[PillBox]
    arrows: list[ArrowDef]
    issues: list[str]         # category names
    issue_details: list[str]  # human-readable descriptions


# ─── helpers ─────────────────────────────────────────────────────────────────

def parse_rect(tag: str) -> tuple[float, float, float, float, float]:
    """Return (x, y, w, h, rx) from an SVG <rect ...> tag string."""
    def attr(name: str) -> float:
        m = re.search(rf'\b{name}="([^"]+)"', tag)
        return float(m.group(1)) if m else 0.0
    return attr("x"), attr("y"), attr("width"), attr("height"), attr("rx")


def parse_viewbox(svg: str) -> list[float]:
    m = re.search(r'viewBox="([^"]+)"', svg)
    if not m:
        return [0, 0, 800, 600]
    return [float(v) for v in m.group(1).split()]


def rects_overlap(a: PillBox, b: PillBox, tol: float = 2.0) -> bool:
    """Return True if pill AABBs overlap by more than tol pixels."""
    ax1, ay1 = a["x"] - tol, a["y"] - tol
    ax2, ay2 = a["x"] + a["w"] + tol, a["y"] + a["h"] + tol
    bx1, by1 = b["x"] - tol, b["y"] - tol
    bx2, by2 = b["x"] + b["w"] + tol, b["y"] + b["h"] + tol
    return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1


def pill_clips_viewbox(pill: PillBox, vb: list[float], tol: float = 2.0) -> bool:
    """Return True if pill is partially outside viewBox."""
    vx, vy, vw, vh = vb
    return (
        pill["x"] < vx + tol
        or pill["y"] < vy + tol
        or pill["x"] + pill["w"] > vx + vw - tol
        or pill["y"] + pill["h"] > vy + vh - tol
    )


def path_bbox(d: str) -> tuple[float, float, float, float]:
    """Rough bounding box from SVG path d attribute using coordinate parsing."""
    nums = [float(n) for n in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)]
    if len(nums) < 4:
        return 0, 0, 0, 0
    xs = nums[0::2]
    ys = nums[1::2]
    if not xs or not ys:
        return 0, 0, 0, 0
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def path_length_est(d: str) -> float:
    """Rough estimate of path length from control points."""
    nums = [float(n) for n in re.findall(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", d)]
    if len(nums) < 4:
        return 0.0
    # Use distance between first and last point as proxy
    try:
        x0, y0 = nums[0], nums[1]
        x1, y1 = nums[-2], nums[-1]
        return math.hypot(x1 - x0, y1 - y0)
    except (IndexError, ValueError):
        return 0.0


def rect_path_overlap(pill: PillBox, path_d: str, tol: float = 3.0) -> bool:
    """Check if a pill AABB overlaps with the bounding box of a path."""
    px, py, pw, ph = path_bbox(path_d)
    # Rough overlap check between pill AABB and path AABB
    return (
        pill["x"] < px + pw + tol
        and pill["x"] + pill["w"] > px - tol
        and pill["y"] < py + ph + tol
        and pill["y"] + pill["h"] > py - tol
    )


# ─── SVG frame analysis ───────────────────────────────────────────────────────

def analyze_svg_frame(svg: str, file_name: str, frame_idx: int) -> FrameAnalysis:
    """Analyze a single SVG frame for label placement issues."""
    vb = parse_viewbox(svg)

    # Extract annotation groups
    ann_groups = re.findall(
        r'<g class="scriba-annotation([^"]*)"([^>]*)>(.*?)</g>\s*(?:</g>)?',
        svg,
        re.DOTALL,
    )

    pills: list[PillBox] = []
    arrows: list[ArrowDef] = []

    for color_class, g_attrs, content in ann_groups:
        ann_id_m = re.search(r'data-annotation="([^"]*)"', g_attrs)
        ann_id = ann_id_m.group(1) if ann_id_m else "unknown"
        aria_m = re.search(r'aria-label="([^"]*)"', g_attrs)
        label_text = aria_m.group(1) if aria_m else ""

        # Extract pill rect
        rect_tags = re.findall(r'<rect[^>]+>', content)
        for rect_tag in rect_tags:
            rx_val = float(re.search(r'rx="([^"]+)"', rect_tag).group(1)) if re.search(r'rx="([^"]+)"', rect_tag) else 0
            # Only consider rounded rects as pills (rx > 0)
            if rx_val > 0:
                x, y, w, h, rx = parse_rect(rect_tag)
                pills.append(PillBox(
                    x=x, y=y, w=w, h=h, rx=rx,
                    label=label_text,
                    color=color_class.strip().replace("scriba-annotation-", ""),
                    ann_id=ann_id,
                ))

        # Also find foreignObject pills (math pills)
        fo_tags = re.findall(r'<foreignObject[^>]+>', content)
        for fo_tag in fo_tags:
            xm = re.search(r'\bx="([^"]+)"', fo_tag)
            ym = re.search(r'\by="([^"]+)"', fo_tag)
            wm = re.search(r'\bwidth="([^"]+)"', fo_tag)
            hm = re.search(r'\bheight="([^"]+)"', fo_tag)
            if xm and ym and wm and hm:
                pills.append(PillBox(
                    x=float(xm.group(1)),
                    y=float(ym.group(1)),
                    w=float(wm.group(1)),
                    h=float(hm.group(1)),
                    rx=4,
                    label=label_text + " [math]",
                    color=color_class.strip(),
                    ann_id=ann_id,
                ))

        # Extract arrow path
        path_tags = re.findall(r'<path[^>]+>', content)
        for path_tag in path_tags:
            d_m = re.search(r'\bd="([^"]+)"', path_tag)
            if d_m:
                d = d_m.group(1)
                arrows.append(ArrowDef(
                    d=d,
                    length_est=path_length_est(d),
                    ann_id=ann_id,
                ))

    issues: list[str] = []
    issue_details: list[str] = []

    # Check: pill-pill overlap
    for i in range(len(pills)):
        for j in range(i + 1, len(pills)):
            if rects_overlap(pills[i], pills[j]):
                issues.append("pill-pill overlap")
                issue_details.append(
                    f"pill-pill overlap: '{pills[i]['ann_id']}' overlaps '{pills[j]['ann_id']}'"
                )

    # Check: viewBox clip (pill outside bounds)
    for pill in pills:
        if pill_clips_viewbox(pill, vb):
            issues.append("viewBox clip")
            issue_details.append(
                f"viewBox clip: pill '{pill['ann_id']}' at ({pill['x']:.1f},{pill['y']:.1f})"
                f" size ({pill['w']:.1f}x{pill['h']:.1f}) vs viewBox {vb}"
            )

    # Check: pill-arrow collision (pill AABB overlaps leader path AABB)
    for pill in pills:
        for arrow in arrows:
            if arrow["ann_id"] == pill["ann_id"]:
                continue  # pill + arrow from same annotation is expected co-location
            if rect_path_overlap(pill, arrow["d"]):
                issues.append("pill-arrow collision")
                issue_details.append(
                    f"pill-arrow collision: pill '{pill['ann_id']}' may overlap"
                    f" arrow '{arrow['ann_id']}'"
                )

    # Check: degenerate leader (arrow path < 5px)
    for arrow in arrows:
        if 0 < arrow["length_est"] < 5:
            issues.append("leader degenerate")
            issue_details.append(
                f"leader degenerate: arrow '{arrow['ann_id']}' estimated length"
                f" {arrow['length_est']:.1f}px"
            )

    # Check: dropped annotations (source had \annotate but no pills)
    # We detect this when there are zero pills but annotation groups exist
    if ann_groups and not pills:
        issues.append("dropped")
        issue_details.append(
            f"dropped: {len(ann_groups)} annotation group(s) found but 0 pills emitted"
        )

    # Check: math mis-sized
    for pill in pills:
        if "[math]" in pill.get("label", ""):
            # Math pills should be at least 15px wide; flag if suspiciously narrow
            if pill["w"] < 15 or pill["h"] < 10:
                issues.append("math mis-sized")
                issue_details.append(
                    f"math mis-sized: foreignObject pill '{pill['ann_id']}'"
                    f" size ({pill['w']:.1f}x{pill['h']:.1f})"
                )

    # Check: pill-text occlusion heuristic
    # Extract cell text elements and check if any pill covers a cell value text
    cell_texts = re.findall(
        r'<text[^>]+class="[^"]*scriba-(?:index-label|cell-text)[^"]*"[^>]*x="([^"]+)"[^>]*y="([^"]+)"',
        svg,
    )
    # Also check plain text inside data-primitive groups
    prim_texts = re.findall(
        r'data-target="[^"]*"[^>]*>.*?<text[^>]*x="([^"]+)"[^>]*y="([^"]+)"',
        svg,
        re.DOTALL,
    )
    all_cell_points = []
    for tx, ty in cell_texts + prim_texts:
        try:
            all_cell_points.append((float(tx), float(ty)))
        except ValueError:
            pass

    for pill in pills:
        for cx, cy in all_cell_points:
            if (pill["x"] <= cx <= pill["x"] + pill["w"]
                    and pill["y"] <= cy <= pill["y"] + pill["h"]):
                issues.append("pill-text occlusion")
                issue_details.append(
                    f"pill-text occlusion: pill '{pill['ann_id']}' covers cell text"
                    f" at ({cx:.1f},{cy:.1f})"
                )
                break

    # De-duplicate issues list (keep unique categories only for counting)
    unique_issues = list(dict.fromkeys(issues))

    return FrameAnalysis(
        file=file_name,
        frame_idx=frame_idx,
        viewbox=vb,
        pills=pills,
        arrows=arrows,
        issues=unique_issues,
        issue_details=issue_details,
    )


# ─── HTML parsing ─────────────────────────────────────────────────────────────

def extract_frames_from_html(html_path: Path) -> list[str]:
    """Return list of SVG strings, one per animation frame."""
    html = html_path.read_text(encoding="utf-8", errors="replace")

    # Frames are stored as:  var frames=[\n  {svg:`...`,...}, ...]
    # Use a greedy search over backtick-quoted SVG strings
    svgs = re.findall(r"svg:`(.*?)`", html, re.DOTALL)
    if svgs:
        return svgs

    # Fallback: inline SVG elements in the body
    body_svgs = re.findall(r"<svg\b[^>]*>.*?</svg>", html, re.DOTALL)
    return body_svgs


def analyze_html_file(html_path: Path) -> list[FrameAnalysis]:
    """Analyze all frames in a rendered HTML file."""
    svgs = extract_frames_from_html(html_path)
    results = []
    for i, svg in enumerate(svgs):
        analysis = analyze_svg_frame(svg, html_path.name, i)
        results.append(analysis)
    return results


# ─── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_labels.py <rendered_dir>", file=sys.stderr)
        sys.exit(1)

    rendered_dir = Path(sys.argv[1]).resolve()
    html_files = sorted(rendered_dir.glob("*.html"))

    all_analyses: list[FrameAnalysis] = []

    for html_file in html_files:
        analyses = analyze_html_file(html_file)
        all_analyses.extend(analyses)

    # Write JSON to stdout
    # Simplify for JSON serialization: convert typed dicts to plain dicts
    out = []
    for a in all_analyses:
        out.append({
            "file": a["file"],
            "frame_idx": a["frame_idx"],
            "viewbox": a["viewbox"],
            "pill_count": len(a["pills"]),
            "arrow_count": len(a["arrows"]),
            "issues": a["issues"],
            "issue_details": a["issue_details"],
            "clean": len(a["issues"]) == 0,
        })

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
