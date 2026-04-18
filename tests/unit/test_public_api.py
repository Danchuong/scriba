"""Pin the public API surface exported by ``scriba`` and ``scriba.core``.

This test is the source of truth for
`STABILITY.md` §Public API surface. Removing or renaming any symbol
below is a BREAKING change and must be accompanied by an explicit
MAJOR version bump.
"""

from __future__ import annotations

import importlib
import warnings

import pytest


# ---------------------------------------------------------------------------
# Expected public surfaces
# ---------------------------------------------------------------------------

EXPECTED_SCRIBA_ALL: frozenset[str] = frozenset(
    {
        "__version__",
        "SCRIBA_VERSION",
        "Block",
        "CollectedWarning",
        "RenderArtifact",
        "Document",
        "RenderContext",
        "ResourceResolver",
        "Renderer",
        "RendererAssets",
        "ContextProvider",
        "Pipeline",
        "Worker",
        "SubprocessWorker",
        "PersistentSubprocessWorker",
        "OneShotSubprocessWorker",
        "SubprocessWorkerPool",
        "ScribaError",
        "RendererError",
        "WorkerError",
        "ScribaRuntimeError",
        "ValidationError",
        "ALLOWED_TAGS",
        "ALLOWED_ATTRS",
    }
)

EXPECTED_SCRIBA_CORE_ALL: frozenset[str] = frozenset(
    {
        "Block",
        "CollectedWarning",
        "RenderArtifact",
        "Document",
        "RenderContext",
        "ResourceResolver",
        "Renderer",
        "RendererAssets",
        "ContextProvider",
        "Pipeline",
        "Worker",
        "SubprocessWorker",
        "PersistentSubprocessWorker",
        "OneShotSubprocessWorker",
        "SubprocessWorkerPool",
        "ScribaError",
        "RendererError",
        "WorkerError",
        "ScribaRuntimeError",
        "ValidationError",
    }
)


# ---------------------------------------------------------------------------
# Surface snapshot
# ---------------------------------------------------------------------------


def test_scriba_all_matches_snapshot() -> None:
    import scriba

    assert frozenset(scriba.__all__) == EXPECTED_SCRIBA_ALL


def test_scriba_core_all_matches_snapshot() -> None:
    import scriba.core

    assert frozenset(scriba.core.__all__) == EXPECTED_SCRIBA_CORE_ALL


def test_scriba_core_all_is_subset_of_scriba_all() -> None:
    """Core symbols must all be re-exported at the top level."""
    import scriba
    import scriba.core

    top = frozenset(scriba.__all__)
    core = frozenset(scriba.core.__all__)
    missing = core - top
    assert not missing, f"core symbols missing from scriba.__all__: {missing}"


# ---------------------------------------------------------------------------
# Every symbol in __all__ must actually be importable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(EXPECTED_SCRIBA_ALL))
def test_scriba_symbol_importable(name: str) -> None:
    scriba = importlib.import_module("scriba")

    # SubprocessWorker is lazy and emits a DeprecationWarning on access;
    # silence it here — the deprecation behaviour is verified below.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        value = getattr(scriba, name)

    assert value is not None, f"scriba.{name} resolved to None"


@pytest.mark.parametrize("name", sorted(EXPECTED_SCRIBA_CORE_ALL))
def test_scriba_core_symbol_importable(name: str) -> None:
    core = importlib.import_module("scriba.core")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        value = getattr(core, name)
    assert value is not None, f"scriba.core.{name} resolved to None"


# ---------------------------------------------------------------------------
# Errors: hierarchy and ScribaRuntimeError export
# ---------------------------------------------------------------------------


def test_error_classes_importable_from_scriba_top_level() -> None:
    from scriba import (
        ScribaError,
        RendererError,
        WorkerError,
        ValidationError,
        ScribaRuntimeError,
    )

    for cls in (
        RendererError,
        WorkerError,
        ValidationError,
        ScribaRuntimeError,
    ):
        assert issubclass(cls, ScribaError)


def test_scriba_runtime_error_listed_in_all() -> None:
    import scriba

    assert "ScribaRuntimeError" in scriba.__all__


def test_scriba_runtime_error_listed_in_core_all() -> None:
    import scriba.core

    assert "ScribaRuntimeError" in scriba.core.__all__


# ---------------------------------------------------------------------------
# Version constant
# ---------------------------------------------------------------------------


def test_scriba_version_is_int_at_least_two() -> None:
    import scriba

    assert isinstance(scriba.SCRIBA_VERSION, int)
    assert scriba.SCRIBA_VERSION >= 2


def test_scriba_version_string_is_non_empty() -> None:
    import scriba

    assert isinstance(scriba.__version__, str)
    assert scriba.__version__


# ---------------------------------------------------------------------------
# DeprecationWarning: must NOT fire on plain imports
# ---------------------------------------------------------------------------


# NOTE: Do NOT delete scriba.* entries from sys.modules in this test file.
# An earlier version of these tests used a `_reload_module` helper that
# invalidated cached references other test modules (notably
# tests/unit/test_security.py) rely on — monkey-patches on
# `scriba.animation.starlark_worker._STEP_LIMIT` silently targeted a
# dead module reference, and step-counter tests started failing in the
# full suite while passing in isolation. Use subprocess isolation for
# anything that needs a clean import state.


def test_import_scriba_does_not_emit_deprecation_warning() -> None:
    """Plain `import scriba` must not fire DeprecationWarning.

    Runs in a subprocess so the check is hermetic and does not pollute
    the parent test process's sys.modules cache.
    """
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::DeprecationWarning",
            "-c",
            "import scriba",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`import scriba` raised a warning-as-error:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_import_scriba_core_does_not_emit_deprecation_warning() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::DeprecationWarning",
            "-c",
            "from scriba.core import Pipeline",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`from scriba.core import Pipeline` raised a warning-as-error:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# DeprecationWarning: DOES fire on SubprocessWorker access
# ---------------------------------------------------------------------------


def test_subprocess_worker_alias_emits_deprecation_warning() -> None:
    # The lazy PEP 562 __getattr__ fires the warning every time external
    # code touches the alias, so no fresh-import dance is needed — just
    # access the attribute through the already-imported module.
    import scriba.core.workers as workers_mod

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = workers_mod.SubprocessWorker

    dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert dep, (
        "accessing scriba.core.workers.SubprocessWorker must emit "
        "DeprecationWarning"
    )
    assert any("SubprocessWorker" in str(w.message) for w in dep)


def test_scriba_subprocess_worker_attr_emits_deprecation_warning() -> None:
    import scriba

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _ = scriba.SubprocessWorker

    dep = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert dep, "scriba.SubprocessWorker must emit DeprecationWarning"


def test_subprocess_worker_alias_resolves_to_persistent() -> None:
    from scriba.core.workers import PersistentSubprocessWorker

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from scriba.core.workers import SubprocessWorker

    assert SubprocessWorker is PersistentSubprocessWorker
