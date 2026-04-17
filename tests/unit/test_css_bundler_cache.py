"""Unit tests for css_bundler lru_cache correctness.

Verifies that:
- ``inline_katex_css()`` returns the same object identity on repeated calls
  (i.e. the lru_cache is active and no re-computation occurs).
- ``load_css()`` returns the same object identity for the same file list.
- The caches are independently clearable via ``cache_clear()``, allowing
  tests that mutate the underlying files to remain correct.
- Cache survives across simulated "renders" within the same process — the
  key property that eliminates the 11 ms per-render overhead.
"""

from __future__ import annotations

import pytest

from scriba.core.css_bundler import inline_katex_css, load_css


@pytest.mark.unit
class TestInlineKaTeXCssCache:
    """lru_cache behaviour for inline_katex_css()."""

    def setup_method(self) -> None:
        # Start each test with a clean cache so cache-miss paths are exercised.
        inline_katex_css.cache_clear()

    def test_same_object_identity_on_repeated_calls(self) -> None:
        """Repeated calls must return the exact same str object (cache hit)."""
        first = inline_katex_css()
        second = inline_katex_css()
        assert first is second, (
            "inline_katex_css() returned different objects on successive calls. "
            "The lru_cache is not active or was cleared between calls."
        )

    def test_third_call_still_cached(self) -> None:
        """Cache hit persists beyond the second call."""
        first = inline_katex_css()
        _ = inline_katex_css()
        third = inline_katex_css()
        assert first is third

    def test_cache_info_hit_count_increments(self) -> None:
        """cache_info() must report cache hits after the first call."""
        inline_katex_css()  # miss
        inline_katex_css()  # hit
        inline_katex_css()  # hit
        info = inline_katex_css.cache_info()
        assert info.hits >= 2, (
            f"Expected at least 2 cache hits, got {info.hits}. "
            "lru_cache may not be wrapping inline_katex_css correctly."
        )
        assert info.misses == 1, (
            f"Expected exactly 1 cache miss (cold start), got {info.misses}."
        )

    def test_cache_clear_forces_recompute(self) -> None:
        """After cache_clear(), the next call recomputes (new object)."""
        first = inline_katex_css()
        inline_katex_css.cache_clear()
        second = inline_katex_css()
        # They must be equal in content but identity is unspecified after clear.
        assert first == second, (
            "inline_katex_css() returned different content after cache_clear(). "
            "The underlying CSS file may have changed, or the function is broken."
        )
        info = inline_katex_css.cache_info()
        assert info.misses == 1, "Expected exactly one miss after cache_clear()."

    def test_simulated_multi_render_cache_hit(self) -> None:
        """Simulate N render() calls — only the first should be a miss."""
        n_renders = 5
        results = [inline_katex_css() for _ in range(n_renders)]
        # All results must be identical objects.
        assert all(r is results[0] for r in results), (
            "Not all simulated render calls returned the same cached object."
        )
        info = inline_katex_css.cache_info()
        assert info.misses == 1
        assert info.hits == n_renders - 1


@pytest.mark.unit
class TestLoadCssCache:
    """lru_cache behaviour for load_css()."""

    def setup_method(self) -> None:
        load_css.cache_clear()

    def test_same_object_identity_single_file(self) -> None:
        """Repeated load_css() calls with the same filename return same object."""
        first = load_css("scriba-scene-primitives.css")
        second = load_css("scriba-scene-primitives.css")
        assert first is second, (
            "load_css() returned different objects for the same file name. "
            "The lru_cache is not active."
        )

    def test_same_object_identity_multiple_files(self) -> None:
        """Repeated calls with the same multi-file tuple return same object."""
        names = ("scriba-scene-primitives.css", "scriba-animation.css")
        first = load_css(*names)
        second = load_css(*names)
        assert first is second

    def test_different_args_produce_different_cache_entries(self) -> None:
        """Different file lists are cached independently."""
        single = load_css("scriba-scene-primitives.css")
        combined = load_css("scriba-scene-primitives.css", "scriba-animation.css")
        # Contents must differ (combined is longer).
        assert len(combined) > len(single)
        # Each should be its own cached entry — verify via cache_info.
        info = load_css.cache_info()
        assert info.currsize == 2, (
            f"Expected 2 distinct cache entries, found {info.currsize}."
        )

    def test_cache_info_hit_count(self) -> None:
        """cache_info() reflects hits correctly for load_css."""
        load_css("scriba-scene-primitives.css")  # miss
        load_css("scriba-scene-primitives.css")  # hit
        load_css("scriba-scene-primitives.css")  # hit
        info = load_css.cache_info()
        assert info.hits >= 2
        assert info.misses >= 1

    def test_cache_clear_forces_recompute(self) -> None:
        """After cache_clear(), load_css() recomputes from disk."""
        first = load_css("scriba-scene-primitives.css")
        load_css.cache_clear()
        second = load_css("scriba-scene-primitives.css")
        assert first == second, (
            "load_css() returned different content after cache_clear(). "
            "Underlying CSS file may have changed, or the function is broken."
        )
        info = load_css.cache_info()
        assert info.misses == 1

    def test_simulated_multi_render_cache_hit(self) -> None:
        """Simulate N renders calling load_css — only first is a miss."""
        n_renders = 5
        names = (
            "scriba-scene-primitives.css",
            "scriba-animation.css",
            "scriba-embed.css",
            "scriba-standalone.css",
        )
        results = [load_css(*names) for _ in range(n_renders)]
        assert all(r is results[0] for r in results)
        info = load_css.cache_info()
        assert info.misses == 1
        assert info.hits == n_renders - 1
