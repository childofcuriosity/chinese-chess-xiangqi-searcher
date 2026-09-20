#!/usr/bin/env python3
"""云开局库单元测试：不访问真实网络，也不启动真实引擎。"""

import asyncio
import sys
import threading
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import common
import webapp


START_FEN = (
    "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/"
    "RNBAKABNR w - - 0 1"
)
RED_DOWN_A_HORSE_FEN = (
    "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/"
    "R1BAKABNR w - - 0 1"
)
BLACK_DOWN_A_HORSE_FEN = (
    "r1bakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/"
    "RNBAKABNR b - - 0 1"
)


class FakeResponse:
    def __init__(self, text):
        self.data = text.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.data


class FirstChoice:
    @staticmethod
    def choice(items):
        return items[0]


def make_book(response_text, *, threshold=20):
    calls = []

    def opener(url, timeout):
        calls.append((url, timeout))
        return FakeResponse(response_text)

    book = common.CloudOpeningBook(
        enabled=True,
        score_threshold=threshold,
        timeout=0.5,
        opener=opener,
        rng=FirstChoice(),
    )
    return book, calls


def test_uci_move_to_coords_and_legal_move():
    assert common.uci_move_to_coords("h2e2") == ((7, 7), (7, 4))
    assert common.uci_move_to_coords("j2e2") is None
    assert common.uci_move_to_coords("h:e2") is None
    assert common.LocalBoard().is_legal_move(7, 7, 7, 4)


def test_query_uses_actual_best_score_and_encodes_fen():
    book, calls = make_book(
        "move:a0a1,score:10|move:h2e2,score:100|move:b0c2,score:80"
    )
    fen = common.LocalBoard().to_fen()

    assert book.query(fen) == ((7, 7), (7, 4), 100)
    assert len(calls) == 1
    params = parse_qs(urlparse(calls[0][0]).query)
    assert params["action"] == ["queryall"]
    assert params["board"] == [fen]
    assert calls[0][1] == 0.5


def test_forbidden_best_move_recomputes_candidate_window():
    book, _ = make_book(
        "move:h2e2,score:100|move:a0a1,score:50|move:b0c2,score:30"
    )

    assert book.query(
        "position w", forbidden_move=((7, 7), (7, 4))
    ) == ((9, 0), (8, 0), 50)


def test_bad_records_are_skipped_and_parsed_candidates_are_cached():
    book, calls = make_book(
        "unknown|move:bad,score:999|move:a0a1,score:nope|"
        "move:c0e2,score:30|move:b0c2,score:20"
    )

    expected = ((9, 2), (7, 4), 30)
    assert book.query("position w") == expected
    assert book.query("position w") == expected
    assert len(calls) == 1


def test_single_returned_candidate_does_not_supply_cloud_move():
    book, calls = make_book("move:h2e2,score:100")

    assert book.query(START_FEN) is None
    assert book.query(START_FEN) is None
    assert len(calls) == 1


def test_single_scored_candidate_does_not_supply_cloud_move():
    book, calls = make_book(
        "move:h2e2,score:100|move:a0a1,score:79"
    )

    assert book.query(START_FEN) is None
    assert book.query(START_FEN) is None
    assert len(calls) == 1


def test_forbidden_move_leaving_one_candidate_does_not_supply_cloud_move():
    book, _ = make_book(
        "move:h2e2,score:100|move:a0a1,score:90"
    )

    assert book.query(
        START_FEN, forbidden_move=((7, 7), (7, 4))
    ) is None


def test_single_candidate_is_used_when_red_to_move_is_behind():
    book, _ = make_book("move:h2e2,score:100")

    assert book.query(RED_DOWN_A_HORSE_FEN) == ((7, 7), (7, 4), 100)


def test_single_candidate_is_used_when_black_to_move_is_behind():
    book, _ = make_book("move:h9g7,score:100")

    assert book.query(BLACK_DOWN_A_HORSE_FEN) == ((0, 7), (2, 6), 100)


def test_network_failures_are_not_cached():
    calls = []

    def failing_opener(url, timeout):
        calls.append(url)
        raise TimeoutError("offline")

    book = common.CloudOpeningBook(enabled=True, opener=failing_opener)
    assert book.query("position w") is None
    assert book.query("position w") is None
    assert len(calls) == 2


def test_cache_has_a_size_limit():
    book, calls = make_book(
        "move:h2e2,score:100|move:a0a1,score:90"
    )
    book.max_cache_entries = 1

    assert book.query("position-1 w") is not None
    assert book.query("position-2 w") is not None
    assert book.query("position-1 w") is not None
    assert len(calls) == 3


class FakeEngine:
    def __init__(self):
        self.commands = []
        self.closed = False

    def send(self, command):
        self.commands.append(command)

    def close(self):
        self.closed = True


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send_json(self, message):
        self.messages.append(message)


class FailingWebSocket:
    async def send_json(self, message):
        raise RuntimeError("disconnected")


def make_session(*, player_side="black", forbid=None, cloud_book=True):
    session = webapp.GameSession.__new__(webapp.GameSession)
    session.sid = "test-session"
    session.board = common.LocalBoard()
    session.engine_name = "custom"
    session.search_time = 1.0
    session.engine = FakeEngine()
    session.player_side = player_side
    session.flip = False
    session.forbid = forbid
    session.cloud_book_enabled = cloud_book
    session.thinking = False
    session.game_over = False
    session.over_reason = None
    session.last_move = None
    session.evaluation = {"kind": "cp", "value": 10}
    return session


def test_web_book_hit_updates_board_and_syncs_engine(monkeypatch):
    session = make_session()
    ws = FakeWebSocket()
    monkeypatch.setattr(
        webapp,
        "query_cloud_book",
        lambda fen, forbidden_move=None, enabled=None: ((7, 7), (7, 4), 100),
    )

    asyncio.run(webapp._play_engine_turn(ws, session))

    assert session.board.turn == "black"
    assert session.board.board[7][4] == "C"
    assert session.last_move == {"r1": 7, "c1": 7, "r2": 7, "c2": 4}
    assert session.evaluation is None
    assert session.engine.commands == ["move 7 7 7 4"]
    assert [message["thinking"] for message in ws.messages] == [True, False]


def test_web_book_miss_falls_back_to_forbid_and_search(monkeypatch):
    forbidden = ((7, 7), (7, 4))
    session = make_session(forbid=forbidden)
    ws = FakeWebSocket()
    monkeypatch.setattr(
        webapp,
        "query_cloud_book",
        lambda fen, forbidden_move=None, enabled=None: None,
    )

    async def finish_search(fake_ws, fake_session):
        fake_session.thinking = False
        await fake_ws.send_json(fake_session.state_msg())

    monkeypatch.setattr(webapp, "_wait_engine", finish_search)
    asyncio.run(webapp._play_engine_turn(ws, session))

    assert session.engine.commands == ["forbid 7 7 7 4", "search"]
    assert session.board.turn == "red"


def test_disconnect_during_thinking_state_does_not_leave_stuck_session(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        webapp,
        "query_cloud_book",
        lambda fen, forbidden_move=None, enabled=None: ((7, 7), (7, 4), 100),
    )

    try:
        asyncio.run(webapp._play_engine_turn(FailingWebSocket(), session))
    except RuntimeError as exc:
        assert str(exc) == "disconnected"
    else:
        raise AssertionError("断线异常应继续向上传播")

    assert not session.thinking
    assert session.board.turn == "black"
    assert session.engine.commands == ["move 7 7 7 4"]


def test_disconnect_on_book_miss_still_starts_engine_search(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        webapp,
        "query_cloud_book",
        lambda fen, forbidden_move=None, enabled=None: None,
    )

    try:
        asyncio.run(webapp._play_engine_turn(FailingWebSocket(), session))
    except RuntimeError as exc:
        assert str(exc) == "disconnected"
    else:
        raise AssertionError("断线异常应继续向上传播")

    assert session.thinking
    assert session.engine.commands == ["search"]


def test_task_cancellation_waits_for_recoverable_turn_state(monkeypatch):
    session = make_session()
    ws = FakeWebSocket()
    started = threading.Event()
    release = threading.Event()

    def delayed_book_query(fen, forbidden_move=None, enabled=None):
        started.set()
        assert release.wait(timeout=2)
        return ((7, 7), (7, 4), 100)

    monkeypatch.setattr(webapp, "query_cloud_book", delayed_book_query)

    async def cancel_during_query():
        task = asyncio.create_task(webapp._play_engine_turn(ws, session))
        while not started.is_set():
            await asyncio.sleep(0)
        task.cancel()
        release.set()
        try:
            await task
        except asyncio.CancelledError:
            return
        raise AssertionError("取消应在回合状态收敛后继续向上传播")

    asyncio.run(cancel_during_query())

    assert not session.thinking
    assert session.board.turn == "black"
    assert session.engine.commands == ["move 7 7 7 4"]


def test_cloud_book_option_is_strict_boolean_and_in_state():
    assert webapp.parse_cloud_book(True) == (True, None)
    assert webapp.parse_cloud_book(False) == (False, None)
    assert webapp.parse_cloud_book() == (webapp.CLOUD_BOOK_ENABLED, None)
    for invalid in (None, 0, 1, "false"):
        assert webapp.parse_cloud_book(invalid)[1] is not None
    assert webapp.parse_cloud_book(allow_default=False)[1] is not None

    session = make_session(cloud_book=False)
    assert session.state_msg()["cloud_book"] is False


def test_set_cloud_book_changes_current_session(monkeypatch):
    session = make_session(cloud_book=False)
    ws = FakeWebSocket()

    assert asyncio.run(webapp._handle_message(
        ws, session, {"type": "set_cloud_book", "enabled": True}
    ))
    assert session.cloud_book_enabled is True
    assert ws.messages[-1]["cloud_book"] is True

    for message in (
        {"type": "set_cloud_book"},
        {"type": "set_cloud_book", "enabled": None},
        {"type": "set_cloud_book", "enabled": 1},
        {"type": "set_cloud_book", "enabled": "yes"},
    ):
        assert asyncio.run(webapp._handle_message(ws, session, message))
        assert session.cloud_book_enabled is True
        assert ws.messages[-1]["type"] == "error"


def test_engine_turn_uses_session_cloud_book_setting(monkeypatch):
    session = make_session(cloud_book=False)
    ws = FakeWebSocket()
    seen = []

    def fake_query(fen, forbidden_move=None, enabled=None):
        seen.append(enabled)
        return None

    async def finish_search(fake_ws, fake_session):
        fake_session.thinking = False
        await fake_ws.send_json(fake_session.state_msg())

    monkeypatch.setattr(webapp, "query_cloud_book", fake_query)
    monkeypatch.setattr(webapp, "_wait_engine", finish_search)
    asyncio.run(webapp._play_engine_turn(ws, session))

    assert seen == [False]
    assert session.engine.commands == ["search"]
