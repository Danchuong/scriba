"""Browser-level smoke tests for the Scriba animation runtime.

Covers the 4 critical user flows that unit tests cannot reach:

1. The runtime JS boots and the widget mounts (no console errors).
2. The frame nav buttons advance / rewind the active frame.
3. The theme toggle flips ``data-theme`` AND ``aria-pressed`` together.
4. ``prefers-reduced-motion: reduce`` is honoured (no in-flight CSS
   transitions while the next/prev button advances).

All tests load the same statically generated ``hello.html`` via
``file://`` — there is no dev server because Scriba is a build-time tool.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import ConsoleMessage, Page, expect


pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# 1. Widget mount + zero console errors
# ---------------------------------------------------------------------------


def _main_widget(page: Page):
    """Return locators scoped to the *top-level* widget chrome.

    The rendered HTML embeds duplicate ``.scriba-btn-prev`` /
    ``.scriba-btn-next`` / ``.scriba-step-counter`` nodes inside the
    print-frame and substory subtrees. We only want the live filmstrip
    controls — the ones that sit in the widget's primary
    ``.scriba-controls`` toolbar (the **first** direct controls block
    inside the widget root).
    """
    widget = page.locator("#hello.scriba-widget")
    controls = widget.locator(".scriba-controls").first
    return {
        "widget": widget,
        "next": controls.locator(".scriba-btn-next"),
        "prev": controls.locator(".scriba-btn-prev"),
        "counter": widget.locator(".scriba-step-counter").first,
    }


def test_widget_mounts_without_console_errors(
    page: Page, hello_html_url: str
) -> None:
    """Page loads, widget appears, no JS error in the console."""
    errors: list[str] = []

    def _capture(msg: ConsoleMessage) -> None:
        if msg.type == "error":
            errors.append(msg.text)

    page.on("console", _capture)
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

    page.goto(hello_html_url)

    parts = _main_widget(page)
    expect(parts["widget"]).to_be_visible()
    expect(parts["widget"]).to_have_attribute("role", "region")

    # Animation JS should set step counter to "Step 1 / 3" once mounted.
    expect(parts["counter"]).to_contain_text("Step 1 / 3")

    assert errors == [], f"unexpected console/page errors: {errors}"


# ---------------------------------------------------------------------------
# 2. Frame navigation
# ---------------------------------------------------------------------------


def test_next_button_advances_frame(page: Page, hello_html_url: str) -> None:
    page.goto(hello_html_url)
    parts = _main_widget(page)

    expect(parts["counter"]).to_contain_text("Step 1 / 3")
    parts["next"].click()
    expect(parts["counter"]).to_contain_text("Step 2 / 3")
    parts["next"].click()
    expect(parts["counter"]).to_contain_text("Step 3 / 3")


def test_prev_button_rewinds_frame(page: Page, hello_html_url: str) -> None:
    page.goto(hello_html_url)
    parts = _main_widget(page)

    parts["next"].click()
    expect(parts["counter"]).to_contain_text("Step 2 / 3")
    parts["next"].click()
    expect(parts["counter"]).to_contain_text("Step 3 / 3")
    parts["prev"].click()
    expect(parts["counter"]).to_contain_text("Step 2 / 3")


# ---------------------------------------------------------------------------
# 3. Theme toggle a11y contract
# ---------------------------------------------------------------------------


def test_theme_toggle_flips_data_theme_and_aria_pressed(
    page: Page, hello_html_url: str
) -> None:
    """Phase 3 a11y guarantee — toggle MUST move both attributes together."""
    page.goto(hello_html_url)

    html = page.locator("html")
    toggle = page.locator("button.theme-toggle").first

    # Initial state — light theme, not-pressed.
    expect(html).to_have_attribute("data-theme", "light")
    expect(toggle).to_have_attribute("aria-pressed", "false")

    toggle.click()

    expect(html).to_have_attribute("data-theme", "dark")
    expect(toggle).to_have_attribute("aria-pressed", "true")

    toggle.click()

    expect(html).to_have_attribute("data-theme", "light")
    expect(toggle).to_have_attribute("aria-pressed", "false")


# ---------------------------------------------------------------------------
# 4. Reduced motion — animation does not block frame nav
# ---------------------------------------------------------------------------


@pytest.fixture
def reduced_motion_context(browser):  # noqa: ANN001 — playwright fixture
    """Browser context that emulates ``prefers-reduced-motion: reduce``."""
    ctx = browser.new_context(reduced_motion="reduce")
    yield ctx
    ctx.close()


def test_reduced_motion_does_not_block_navigation(
    reduced_motion_context, hello_html_url: str
) -> None:
    """With reduce-motion on, clicking next must still snap to the next frame
    — the runtime should bypass the morph timeline rather than queue it."""
    page = reduced_motion_context.new_page()
    try:
        page.goto(hello_html_url)
        widget = page.locator("#hello.scriba-widget")
        counter = widget.locator(".scriba-step-counter")
        next_btn = widget.locator(".scriba-btn-next")

        expect(counter).to_contain_text("1")
        next_btn.click()
        expect(counter).to_contain_text("2", timeout=2000)
    finally:
        page.close()
