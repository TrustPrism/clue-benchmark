"""The one-time watcher must not finalize merely because a worker sleeps."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location(
    "finalize_continuation",
    Path(__file__).parents[1] / "scripts/finalize_continuation.py",
)
watcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watcher)


def test_process_identity_stays_constant_across_running_and_sleeping(monkeypatch):
    outputs = iter(("Sat Oct  3 18:00:00 2026 R+\n", "Sat Oct  3 18:00:00 2026 S+\n"))
    monkeypatch.setattr(
        watcher.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=next(outputs)),
    )
    assert watcher.process_identity(123) == watcher.process_identity(123)


def test_exited_or_zombie_workers_are_finished(monkeypatch):
    for code, text in ((1, ""), (0, "Sat Oct  3 18:00:00 2026 Z+\n")):
        monkeypatch.setattr(
            watcher.subprocess,
            "run",
            lambda *a, **k: SimpleNamespace(returncode=code, stdout=text),
        )
        assert watcher.process_identity(123) is None
