"""Tests for terminal backend detection and factory."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from vibe.core.ipc.terminal.factory import detect_backend, NoTerminalBackendError
from vibe.core.ipc.terminal.kitty import KittyBackend
from vibe.core.ipc.terminal.tmux import TmuxBackend
from vibe.core.ipc.terminal.wezterm import WeztermBackend
from vibe.core.ipc.terminal.alacritty import AlacrittyBackend


class TestBackendDetection:
    def test_kitty_detected_via_env(self) -> None:
        with patch.dict("os.environ", {"KITTY_PID": "1234"}):
            assert KittyBackend.detect() is True

    def test_kitty_not_detected_without_env(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert KittyBackend.detect() is False

    def test_tmux_detected_via_env(self) -> None:
        with patch.dict("os.environ", {"TMUX": "/tmp/tmux-1000/default,12345,0"}):
            assert TmuxBackend.detect() is True

    def test_wezterm_detected_via_env(self) -> None:
        with patch.dict("os.environ", {"WEZTERM_PANE": "0"}):
            assert WeztermBackend.detect() is True


class TestFactory:
    def test_override_known_backend(self) -> None:
        with patch.object(KittyBackend, "detect", return_value=True):
            backend = detect_backend(override="kitty")
            assert isinstance(backend, KittyBackend)

    def test_override_unknown_backend_raises(self) -> None:
        with pytest.raises(NoTerminalBackendError, match="Unknown terminal"):
            detect_backend(override="nonexistent")

    def test_auto_detect_kitty(self) -> None:
        with patch.dict("os.environ", {"KITTY_PID": "1234"}, clear=True):
            backend = detect_backend()
            assert isinstance(backend, KittyBackend)

    def test_auto_detect_tmux(self) -> None:
        with patch.dict("os.environ", {"TMUX": "/tmp/tmux"}, clear=True):
            backend = detect_backend()
            assert isinstance(backend, TmuxBackend)

    def test_no_backend_raises(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("shutil.which", return_value=None),
        ):
            with pytest.raises(NoTerminalBackendError, match="No supported terminal"):
                detect_backend()
