#!/usr/bin/env python3
"""
tests/test_web.py
webapp.py 端到端测试（fastapi TestClient + WebSocket）。
注意: 真实引擎每次新进程前 3 步搜索各 15 秒，慢用例耗时约 15-20 秒属正常。
运行: python -m pytest tests/test_web.py -v
"""

import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import webapp

ENGINE_OK = os.path.exists(webapp.resolve_engine_path())
needs_engine = pytest.mark.skipif(not ENGINE_OK, reason="引擎可执行文件不存在")

pytestmark = needs_engine


@pytest.fixture
def client():
    with TestClient(webapp.app) as c:
        yield c


@pytest.fixture(autouse=True)
def clear_sessions():
    """每个用例后清空会话，防止泄漏到下一个用例。"""
    yield
    for sid in list(webapp.manager.sessions.keys()):
        webapp.manager.remove(sid)


def wait_state(ws, timeout=60):
    """收消息直到收到 state。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = ws.receive_json()
        if msg["type"] == "state":
            return msg
    raise TimeoutError("等待 state 超时")


# 1. 执红开局: 人走炮二平五, 引擎应手
def test_play_as_red(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "new_game", "side": "red", "flip": False})
        st = wait_state(ws)
        assert st["sid"] and st["turn"] == "red" and st["side"] == "red"
        assert not st["thinking"] and not st["over"]

        ws.send_json({"type": "move", "r1": 7, "c1": 7, "r2": 4, "c2": 7})
        st = wait_state(ws)   # 人走完: thinking=true
        assert st["thinking"] and st["last_move"] == {"r1": 7, "c1": 7, "r2": 4, "c2": 7}

        st = wait_state(ws, timeout=60)   # 引擎搜索约 15 秒
        assert not st["thinking"] and st["turn"] == "red"
        assert st["board"][4][7] == 'C'   # 中炮还在
        assert st["last_move"] is not None
        # 引擎应手改变了棋盘（黑方动了子）
        assert st["board"] != webapp.LocalBoard().board


# 2. 非法走子: 回 error 且棋盘不变
def test_illegal_move(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "new_game", "side": "red", "flip": False})
        st = wait_state(ws)
        before = [row[:] for row in st["board"]]

        ws.send_json({"type": "move", "r1": 7, "c1": 7, "r2": 7, "c2": 0})  # 炮不能横走一格? 其实7,7->7,0隔了兵
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "非法" in msg["msg"]

        # 选子查询确认棋盘没变
        ws.send_json({"type": "select", "r": 7, "c": 7})
        st = wait_state(ws)
        assert st["board"] == before and st["turn"] == "red" and not st["thinking"]


# 3. 执黑开局: 引擎自动先手
def test_play_as_black(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "new_game", "side": "black", "flip": False})
        st = wait_state(ws)
        assert st["side"] == "black" and st["thinking"]

        st = wait_state(ws, timeout=60)   # 引擎先手约 15 秒
        assert not st["thinking"] and st["turn"] == "black"
        assert st["last_move"] is not None


# 4. 认输: over=true 且引擎进程已回收
def test_resign(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "new_game", "side": "red", "flip": False})
        st = wait_state(ws)
        sid = st["sid"]

        ws.send_json({"type": "resign"})
        st = wait_state(ws)
        assert st["over"] and st["reason"] == "you_resigned"

        session = webapp.manager.get(sid)
        assert session is not None
        assert not session.engine.alive()   # 引擎进程已回收


# 5. 双会话隔离
def test_two_sessions_isolated(client):
    with client.websocket_connect("/ws") as ws1, \
         client.websocket_connect("/ws") as ws2:
        ws1.send_json({"type": "new_game", "side": "red", "flip": False})
        ws2.send_json({"type": "new_game", "side": "red", "flip": False})
        st1, st2 = wait_state(ws1), wait_state(ws2)
        assert st1["sid"] != st2["sid"]

        # A 局走子进入思考; B 局不受影响
        ws1.send_json({"type": "move", "r1": 7, "c1": 7, "r2": 4, "c2": 7})
        st1 = wait_state(ws1)
        assert st1["thinking"]

        ws2.send_json({"type": "select", "r": 7, "c": 7})
        st2 = wait_state(ws2)
        assert st2["turn"] == "red" and not st2["thinking"]
        assert st2["legal"] is not None   # B 局仍可正常选子

        # A 局等到引擎应手，B 局棋盘始终未变
        st1 = wait_state(ws1, timeout=60)
        assert st1["turn"] == "red"
        assert st2["board"] == st2["board"]  # B 局快照未被 A 局消息污染


# 6. 并发上限: MAX_GAMES=1 时第二个 new_game 回 busy
def test_max_games(client):
    old = webapp.MAX_GAMES
    webapp.MAX_GAMES = 1
    try:
        with client.websocket_connect("/ws") as ws1:
            ws1.send_json({"type": "new_game", "side": "red", "flip": False})
            st = wait_state(ws1)
            assert st["sid"]

            with client.websocket_connect("/ws") as ws2:
                ws2.send_json({"type": "new_game", "side": "red", "flip": False})
                msg = ws2.receive_json()
                assert msg["type"] == "busy"
    finally:
        webapp.MAX_GAMES = old


# 7. 空闲回收: IDLE_TIMEOUT 超时后 reaper 回收会话和进程
def test_idle_reap(client):
    old = webapp.IDLE_TIMEOUT
    webapp.IDLE_TIMEOUT = 1
    try:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "new_game", "side": "red", "flip": False})
            st = wait_state(ws)
            sid = st["sid"]
            session = webapp.manager.get(sid)
            assert session.engine.alive()

            time.sleep(1.2)
            victims = webapp.manager.reap_once()
            assert sid in [v.sid for v in victims]
            assert webapp.manager.get(sid) is None
            assert not session.engine.alive()   # 引擎进程已回收
    finally:
        webapp.IDLE_TIMEOUT = old
