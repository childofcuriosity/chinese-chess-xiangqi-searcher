#!/usr/bin/env python3
"""桌面版云库开关测试；没有安装 pygame 时自动跳过。"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("pygame")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gui
from common import LocalBoard


class FakeEngine:
    def __init__(self):
        self.commands = []

    def send(self, command):
        self.commands.append(command)


def test_gui_toggle_controls_next_cloud_query(monkeypatch):
    app = gui.XiangqiGUI.__new__(gui.XiangqiGUI)
    app.replace_ai_mode = False
    app.replace_ai_pending = False
    app.board = LocalBoard()
    app.forbid_text = "1 1 1 1"
    app.cloud_book_enabled = False
    app.btn_cloud_book = SimpleNamespace(text="云库: 关")
    app.ai = FakeEngine()
    app.ai_thinking = False
    seen = []

    def fake_query(fen, forbidden_move=None, enabled=None):
        seen.append(enabled)
        return None

    monkeypatch.setattr(gui, "query_cloud_book", fake_query)

    app.request_ai_move()
    app.toggle_cloud_book()
    app.request_ai_move()

    assert seen == [False, True]
    assert app.btn_cloud_book.text == "云库: 开"
    assert app.ai.commands == ["search", "search"]
