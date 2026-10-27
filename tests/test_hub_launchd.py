from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch


def load_hub_launchd():
    path = Path(__file__).resolve().parents[1] / "scripts" / "hub-launchd"
    name = "hub_launchd_for_tests"
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError("could not load hub-launchd")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


hub_launchd = load_hub_launchd()


class FakeLaunchd:
    """launchd whose bootout returns before the service leaves the domain."""

    def __init__(self, polls_until_unloaded: int) -> None:
        self.loaded = True
        self.unloading_polls = 0
        self.polls_until_unloaded = polls_until_unloaded
        self.calls: list[str] = []

    def __call__(self, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
        verb = args[0]
        self.calls.append(verb)
        if verb == "print":
            if self.unloading_polls:
                self.unloading_polls -= 1
                if not self.unloading_polls:
                    self.loaded = False
                return self.result(0)
            return self.result(0 if self.loaded else 113)
        if verb == "bootout":
            self.unloading_polls = self.polls_until_unloaded
            if not self.unloading_polls:
                self.loaded = False
            return self.result(0)
        if verb == "bootstrap":
            return self.result(37 if self.loaded else 0, check, on_success=self.mark_loaded)
        if verb == "kickstart":
            return self.result(0 if self.loaded else 113, check)
        return self.result(0)

    def mark_loaded(self) -> None:
        self.loaded = True

    def result(self, code: int, check: bool = False, on_success=None) -> subprocess.CompletedProcess[str]:
        if code and check:
            raise RuntimeError(f"launchctl failed with {code}")
        if not code and on_success:
            on_success()
        return subprocess.CompletedProcess([], code, "", "")


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class HubLaunchdRestartTest(unittest.TestCase):
    def run_restart(self, launchd: FakeLaunchd) -> int:
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            plist = Path(tmp) / "runtime.plist"
            plist.write_text("plist", encoding="utf-8")
            with patch.object(hub_launchd, "run_launchctl", launchd), \
                    patch.object(hub_launchd, "require_launchctl", return_value="launchctl"), \
                    patch.object(hub_launchd.shutil, "which", return_value="launchctl"), \
                    patch.object(hub_launchd.sys, "platform", "darwin"), \
                    patch.object(hub_launchd, "PLIST_PATH", plist), \
                    patch.object(hub_launchd.time, "monotonic", clock.monotonic), \
                    patch.object(hub_launchd.time, "sleep", clock.sleep), \
                    patch("builtins.print"):
                return hub_launchd.command_restart(argparse.Namespace())

    def test_restart_waits_for_asynchronous_bootout_before_bootstrap(self) -> None:
        launchd = FakeLaunchd(polls_until_unloaded=3)
        self.assertEqual(self.run_restart(launchd), 0)
        self.assertTrue(launchd.loaded)
        self.assertLess(launchd.calls.index("bootout"), launchd.calls.index("bootstrap"))
        self.assertEqual(launchd.calls[-1], "kickstart")

    def test_stop_fails_when_service_never_unloads(self) -> None:
        launchd = FakeLaunchd(polls_until_unloaded=10_000)
        with self.assertRaisesRegex(RuntimeError, "still loaded"):
            self.run_restart(launchd)
        self.assertNotIn("bootstrap", launchd.calls)


if __name__ == "__main__":
    unittest.main()
