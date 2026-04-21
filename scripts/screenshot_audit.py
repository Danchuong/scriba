#!/usr/bin/env python3
"""Screenshot rendered HTML files for visual regression audit.

Usage:
    python scripts/screenshot_audit.py <rendered_dir> <screenshots_dir>

For each .html file in rendered_dir, screenshots each animation frame
at 1200x800 viewport. Saves <name>-step0.png, <name>-step1.png, ...
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, Page

VIEWPORT = {"width": 1200, "height": 800}
MAX_STEPS = 25  # safety cap


def screenshot_html(page: Page, html_path: Path, screenshots_dir: Path) -> list[Path]:
    """Screenshot all frames of a rendered HTML file.
    Returns list of screenshot paths created.
    """
    url = html_path.as_uri()
    page.goto(url, wait_until="networkidle")
    # Give KaTeX and any JS init time to render
    page.wait_for_timeout(800)

    name = html_path.stem
    saved = []

    # Get total number of frames from the step counter text "Step 1 / N"
    # Or from the scriba widget data
    total_frames = page.evaluate("""
        () => {
            // Look for scriba step counter "Step X / N"
            const ctr = document.querySelector('.scriba-step-counter');
            if (ctr && ctr.textContent) {
                const m = ctr.textContent.match(/\\/ (\\d+)/);
                if (m) return parseInt(m[1], 10);
            }
            // Look for frames embedded in script/data
            const widgets = document.querySelectorAll('.scriba-widget');
            if (widgets.length > 0) {
                // Can't easily get frame count without deeper inspection
                return 50; // will cap at MAX_STEPS
            }
            return 1;
        }
    """)

    # Take step 0 (initial state)
    step_path = screenshots_dir / f"{name}-step0.png"
    page.screenshot(path=str(step_path), full_page=False)
    saved.append(step_path)

    # Try to advance frames using the next button
    steps_to_take = min((total_frames or 1) - 1, MAX_STEPS)

    for step_idx in range(1, steps_to_take + 1):
        # Click the next button - use the main widget's next button
        clicked = page.evaluate("""
            () => {
                const btn = document.querySelector('.scriba-btn-next:not([disabled])');
                if (btn) { btn.click(); return true; }
                return false;
            }
        """)
        if not clicked:
            # Next button disabled means we're at the end
            break

        page.wait_for_timeout(200)

        step_path = screenshots_dir / f"{name}-step{step_idx}.png"
        page.screenshot(path=str(step_path), full_page=False)
        saved.append(step_path)

    return saved


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python scripts/screenshot_audit.py <rendered_dir> <screenshots_dir>")
        sys.exit(1)

    rendered_dir = Path(sys.argv[1]).resolve()
    screenshots_dir = Path(sys.argv[2]).resolve()
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(rendered_dir.glob("*.html"))
    print(f"Found {len(html_files)} HTML files to screenshot")

    results: dict[str, list[str]] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport=VIEWPORT)
        page = context.new_page()

        for html_file in html_files:
            print(f"  Screenshotting {html_file.name} ...", end=" ", flush=True)
            try:
                paths = screenshot_html(page, html_file, screenshots_dir)
                results[html_file.name] = [str(p) for p in paths]
                print(f"{len(paths)} frames")
            except Exception as exc:
                print(f"ERROR: {exc}")
                results[html_file.name] = []

        browser.close()

    # Write manifest
    manifest_path = screenshots_dir / "manifest.json"
    manifest_path.write_text(json.dumps(results, indent=2))
    print(f"\nDone. Manifest: {manifest_path}")
    total_screenshots = sum(len(v) for v in results.values())
    print(f"Total screenshots: {total_screenshots}")


if __name__ == "__main__":
    main()
