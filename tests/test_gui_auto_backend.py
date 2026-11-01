"""``gui.jobs.auto_backend``: platform-derived only, never probes hardware or spawns a process."""
from __future__ import annotations

import os
import subprocess

import pytest

from hornlab_search.gui import jobs


def _boom(*_a, **_k):
    raise AssertionError("auto_backend must not spawn a process")


def test_auto_backend_spawns_nothing(monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", _boom)
    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(os, "system", _boom)
    # Must return without raising on whatever host the suite runs on.
    assert jobs.auto_backend() in (None, "beat_metal")


@pytest.mark.parametrize("machine", ["arm64", "aarch64", "ARM64"])
def test_auto_backend_apple_silicon_is_metal(monkeypatch, machine):
    monkeypatch.setattr(jobs.sys, "platform", "darwin")
    monkeypatch.setattr(jobs.platform, "machine", lambda: machine)
    assert jobs.auto_backend() == "beat_metal"


@pytest.mark.parametrize("platform_name,machine", [
    ("win32", "AMD64"),
    ("linux", "x86_64"),
    ("darwin", "x86_64"),
])
def test_auto_backend_otherwise_none(monkeypatch, platform_name, machine):
    monkeypatch.setattr(jobs.sys, "platform", platform_name)
    monkeypatch.setattr(jobs.platform, "machine", lambda: machine)
    assert jobs.auto_backend() is None
