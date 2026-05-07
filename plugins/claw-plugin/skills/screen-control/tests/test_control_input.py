import sys
import types
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

fake_pyautogui = types.SimpleNamespace(
    FAILSAFE=True,
    PAUSE=0.05,
    size=lambda: (1440, 900),
    position=lambda: (0, 0),
    moveTo=lambda *args, **kwargs: None,
    click=lambda *args, **kwargs: None,
    write=lambda *args, **kwargs: None,
    hotkey=lambda *args, **kwargs: None,
)
sys.modules.setdefault("pyautogui", fake_pyautogui)

import control


def test_macos_paste_text_uses_pbcopy_and_osascript(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return types.SimpleNamespace(returncode=0)

    controller = control.ScreenController()
    monkeypatch.setattr(control.sys, "platform", "darwin")
    monkeypatch.setattr(control.subprocess, "run", fake_run)
    monkeypatch.setattr(control.time, "sleep", lambda _seconds: None)

    controller._paste_text("苦尘")

    assert calls[0][0] == ["pbcopy"]
    assert calls[0][1]["input"] == "苦尘"
    assert calls[0][1]["text"] is True
    assert calls[1][0] == [
        "osascript",
        "-e",
        'tell application "System Events" to keystroke "v" using command down',
    ]


def test_clear_and_type_text_selects_deletes_then_pastes(monkeypatch):
    actions = []

    controller = control.ScreenController()
    monkeypatch.setattr(control.pyautogui, "hotkey", lambda *keys: actions.append(("hotkey", keys)))
    monkeypatch.setattr(controller, "_paste_text", lambda text: actions.append(("paste", text)))
    monkeypatch.setattr(control.time, "sleep", lambda _seconds: None)

    controller.clear_and_type_text("苦尘")

    assert actions == [
        ("hotkey", ("command", "a")),
        ("hotkey", ("delete",)),
        ("paste", "苦尘"),
    ]


def test_locate_parser_accepts_vision_preference():
    parser = control.build_parser()

    args = parser.parse_args(["locate", "搜索按钮", "--prefer", "vision"])

    assert args.command == "locate"
    assert args.prefer == "vision"
