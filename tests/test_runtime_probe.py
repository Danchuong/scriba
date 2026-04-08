"""Tests for the Node.js + KaTeX runtime probe in ``scriba.tex.renderer``.

The probe runs once per process from ``TexRenderer.__init__`` and raises
``ScribaRuntimeError`` with an actionable, multi-line message when either
``node`` is missing from PATH or the vendored ``katex.min.js`` shipped
inside the wheel cannot be ``require()``'d by Node (a packaging bug).
"""

from __future__ import annotations

import subprocess

import pytest

from scriba.core.errors import ScribaRuntimeError
from scriba.tex import renderer as renderer_mod


@pytest.fixture(autouse=True)
def _reset_probe_flag(monkeypatch):
    """Force the probe to re-run in every test and clear the bypass env var."""
    monkeypatch.setattr(renderer_mod, "_RUNTIME_PROBED", False)
    monkeypatch.delenv("SCRIBA_SKIP_RUNTIME_PROBE", raising=False)
    yield
    monkeypatch.setattr(renderer_mod, "_RUNTIME_PROBED", False)


def test_probe_succeeds_on_dev_env():
    """Current dev env has node; vendored katex.min.js ships with the package."""
    renderer_mod._probe_runtime("node")  # should not raise


def test_probe_raises_when_node_missing(monkeypatch):
    monkeypatch.setattr(renderer_mod.shutil, "which", lambda _name: None)
    with pytest.raises(ScribaRuntimeError) as exc:
        renderer_mod._probe_runtime("node")
    msg = str(exc.value)
    assert "Node.js" in msg
    assert "brew install node" in msg
    assert "apt install" in msg
    assert "nodejs.org" in msg
    assert exc.value.component == "node"


def test_probe_raises_when_vendored_katex_unreadable(monkeypatch):
    """If the vendored katex.min.js cannot be loaded it's a packaging bug."""
    monkeypatch.setattr(renderer_mod.shutil, "which", lambda _name: "/usr/bin/node")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="Error: Cannot find module '/pkg/scriba/tex/vendor/katex/katex.min.js'",
        )

    monkeypatch.setattr(renderer_mod.subprocess, "run", fake_run)
    with pytest.raises(ScribaRuntimeError) as exc:
        renderer_mod._probe_runtime("node")
    msg = str(exc.value)
    assert "packaging bug" in msg
    assert "file a bug" in msg
    assert "Cannot find module" in msg
    assert exc.value.component == "katex"


def test_probe_bypassed_by_env_var(monkeypatch):
    monkeypatch.setenv("SCRIBA_SKIP_RUNTIME_PROBE", "1")

    def _boom(*_args, **_kwargs):
        raise AssertionError("probe must not run when bypass env var is set")

    monkeypatch.setattr(renderer_mod.shutil, "which", _boom)
    monkeypatch.setattr(renderer_mod.subprocess, "run", _boom)
    renderer_mod._probe_runtime("node")  # should silently return
