#!/usr/bin/env python3
"""
webapp.py
网页版象棋对弈后端：FastAPI + WebSocket。
每个对局会话 = 一个 LocalBoard + 一个独立引擎进程（有状态）。
规则校验全部在服务端，前端只负责渲染和点击。

运行: uvicorn webapp:app --host 0.0.0.0 --port 8000   (或 python webapp.py)
环境变量:
  XQ_CUSTOM_ENGINE_PATH       自研引擎路径 (默认: 本目录/xiangqi_ai)
  XQ_PIKAFISH_PST_ENGINE_PATH Pikafish PST 桥接入口路径
  XQ_DEFAULT_SEARCH_TIME      每步默认思考秒数 (默认 5)
  XQ_MAX_GAMES      并发对局上限 (默认 16)
  XQ_IDLE_TIMEOUT   会话空闲回收秒数 (默认 1800)
  XQ_REAP_INTERVAL  回收扫描间隔秒数 (默认 60)
"""

import asyncio
import os
import secrets
import sys
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from common import LocalBoard, EngineClient, ROWS, COLS

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

MAX_GAMES = int(os.environ.get("XQ_MAX_GAMES", "16"))
IDLE_TIMEOUT = float(os.environ.get("XQ_IDLE_TIMEOUT", "1800"))
REAP_INTERVAL = float(os.environ.get("XQ_REAP_INTERVAL", "60"))
ENGINE_WAIT_TIMEOUT = 150.0   # 引擎单步搜索硬上限（秒）
DEFAULT_SEARCH_TIME = float(os.environ.get("XQ_DEFAULT_SEARCH_TIME", "5"))
MIN_SEARCH_TIME = 0.05
MAX_SEARCH_TIME = 120.0


ENGINE_PATHS = {
    "custom": os.environ.get("XQ_CUSTOM_ENGINE_PATH", str(BASE_DIR / "xiangqi_ai")),
    "pikafish_pst": os.environ.get(
        "XQ_PIKAFISH_PST_ENGINE_PATH", str(BASE_DIR / "pikafish_pst_bridge")
    ),
}


def resolve_engine_path(engine="custom"):
    p = ENGINE_PATHS[engine]
    if not os.path.exists(p) and sys.platform == "win32" and not p.lower().endswith(".exe"):
        if os.path.exists(p + ".exe"):
            return p + ".exe"
    return p


def resolve_engine_command(engine="custom"):
    if engine == "pikafish_pst" and sys.platform == "win32":
        return [sys.executable, str(BASE_DIR / "pikafish_bridge.py")]
    return [resolve_engine_path(engine)]


def parse_forbid(text):
    """解析禁招文本 'r1 c1 r2 c2'（0-based，同 gui.py 输入槽）。
    起止相同 = 无禁招。返回 (forbid, err)：forbid 为 ((r1,c1),(r2,c2)) 或 None。"""
    text = (text or "").strip()
    if not text:
        return None, None
    try:
        nums = [int(x) for x in text.split()]
    except ValueError:
        return None, "禁招格式错误：需要 4 个整数 (r1 c1 r2 c2)"
    if len(nums) != 4:
        return None, "禁招格式错误：需要 4 个整数 (r1 c1 r2 c2)"
    r1, c1, r2, c2 = nums
    if (r1, c1) == (r2, c2):
        return None, None
    if not (0 <= r1 < ROWS and 0 <= r2 < ROWS and 0 <= c1 < COLS and 0 <= c2 < COLS):
        return None, "禁招坐标越界 (r:0-9, c:0-8)"
    return ((r1, c1), (r2, c2)), None


def parse_search_time(value):
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return None, "思考时间必须是数字"
    if not MIN_SEARCH_TIME <= seconds <= MAX_SEARCH_TIME:
        return None, f"思考时间必须在 {MIN_SEARCH_TIME:g} 到 {MAX_SEARCH_TIME:g} 秒之间"
    return seconds, None


def has_any_legal_move(board, side):
    """side ('red'/'black') 方是否至少有一个合法走法。"""
    is_red = (side == 'red')
    for r in range(ROWS):
        for c in range(COLS):
            p = board.board[r][c]
            if p != '.' and board.is_red(p) == is_red:
                if board.get_valid_moves(r, c):
                    return True
    return False


class GameSession:
    def __init__(self, sid, player_side, flip, forbid=None, engine="custom",
                 search_time=DEFAULT_SEARCH_TIME):
        self.sid = sid
        self.board = LocalBoard()
        self.engine_name = engine
        self.search_time = search_time
        self.engine = EngineClient(resolve_engine_command(engine))
        self.player_side = player_side      # 'red' | 'black'
        self.flip = flip
        self.forbid = forbid                # ((r1,c1),(r2,c2)) 或 None；只对引擎下一步生效
        self.thinking = False
        self.game_over = False
        self.over_reason = None             # you_resigned | engine_resigned | engine_crashed
                                            # no_legal_moves_you_lost | no_legal_moves_engine_lost
        self.last_move = None               # {"r1":..,"c1":..,"r2":..,"c2":..}
        self.evaluation = None              # {"kind":"cp"|"mate", "value":int}，引擎视角
        self.ws = None                      # 当前挂接的 WebSocket（单写者）
        self.created_at = time.time()
        self.last_active_at = time.time()
        self.lock = threading.Lock()        # 保险锁；session 操作均在事件循环内串行执行

    # ---- 生命周期 ----
    def start(self):
        self.engine.connect()
        self.engine.send(f"time {self.search_time:g}")
        # 协议: side 填人类执子方，引擎下对面
        self.engine.send(f"side {self.player_side}")

    def touch(self):
        self.last_active_at = time.time()

    def set_search_time(self, seconds):
        self.search_time = seconds
        self.engine.send(f"time {seconds:g}")

    def close(self):
        self.engine.close()

    # ---- 人类走子（服务端权威校验） ----
    def try_human_move(self, r1, c1, r2, c2):
        if self.game_over:
            return False, "对局已结束"
        if self.thinking:
            return False, "引擎思考中"
        if self.board.turn != self.player_side:
            return False, "还没轮到你"
        if not self.board.in_board(r1, c1) or not self.board.in_board(r2, c2):
            return False, "坐标越界"
        piece = self.board.board[r1][c1]
        if piece == '.' or self.board.is_red(piece) != (self.player_side == 'red'):
            return False, "不能移动对方棋子"
        if (r2, c2) not in self.board.get_valid_moves(r1, c1):
            return False, "非法走法"
        self.board.move(r1, c1, r2, c2)
        self.last_move = {"r1": r1, "c1": c1, "r2": r2, "c2": c2}
        self.engine.send(f"move {r1} {c1} {r2} {c2}")
        # 人走完后轮到引擎：无合法走法 → 引擎输（将死/困毙），不再 search
        if not has_any_legal_move(self.board, self.board.turn):
            self.game_over = True
            self.over_reason = "no_legal_moves_engine_lost"
        return True, ""

    def resign(self):
        if not self.game_over:
            self.game_over = True
            self.over_reason = "you_resigned"
            self.thinking = False

    def request_engine_move(self):
        if self.forbid is not None:
            (fr, fc), (tr, tc) = self.forbid
            self.engine.send(f"forbid {fr} {fc} {tr} {tc}")
        self.engine.send("search")
        self.thinking = True

    # ---- 引擎消息（drain 读线程队列，更新会话状态） ----
    def poll_engine(self):
        """取出引擎所有已到达消息并更新状态。返回是否有变化。"""
        changed = False
        while True:
            msg = self.engine.get_message()
            if not msg:
                break
            parts = msg.split()
            if parts and parts[0] == "move" and len(parts) >= 5:
                r1, c1, r2, c2 = map(int, parts[1:5])
                self.board.move(r1, c1, r2, c2)
                self.last_move = {"r1": r1, "c1": c1, "r2": r2, "c2": c2}
                if len(parts) >= 8 and parts[5] == "score" and parts[6] in ("cp", "mate"):
                    try:
                        self.evaluation = {"kind": parts[6], "value": int(parts[7])}
                    except ValueError:
                        pass
                self.thinking = False
                changed = True
                # 引擎走完后轮到人类：无合法走法 → 人类输
                if not has_any_legal_move(self.board, self.board.turn):
                    self.game_over = True
                    self.over_reason = "no_legal_moves_you_lost"
            elif parts and parts[0] == "resign":
                self.thinking = False
                self.game_over = True
                self.over_reason = "engine_resigned"
                changed = True
        return changed

    # ---- 查询与状态组装 ----
    def legal_moves_for(self, r, c):
        """返回 (r,c) 处己方棋子的合法落点；空/对方棋子返回 None。"""
        if not self.board.in_board(r, c):
            return None
        p = self.board.board[r][c]
        if p != '.' and self.board.is_red(p) == (self.player_side == 'red'):
            return [[nr, nc] for nr, nc in self.board.get_valid_moves(r, c)]
        return None

    def state_msg(self, legal=None):
        turn = self.board.turn
        in_check = None
        if not self.game_over and self.board._is_in_check(turn == 'red'):
            in_check = turn
        return {
            "type": "state",
            "sid": self.sid,
            "board": [row[:] for row in self.board.board],
            "turn": turn,
            "side": self.player_side,
            "engine": self.engine_name,
            "search_time": self.search_time,
            "flip": self.flip,
            "forbid": [[self.forbid[0][0], self.forbid[0][1]],
                       [self.forbid[1][0], self.forbid[1][1]]] if self.forbid else None,
            "thinking": self.thinking,
            "last_move": self.last_move,
            "evaluation": self.evaluation,
            "in_check": in_check,
            "legal": legal,
            "over": self.game_over,
            "reason": self.over_reason,
        }


class SessionManager:
    def __init__(self):
        self.sessions = {}
        self.lock = threading.Lock()

    def create(self, side, flip, forbid=None, engine="custom",
               search_time=DEFAULT_SEARCH_TIME):
        with self.lock:
            if len(self.sessions) >= MAX_GAMES:
                return None
            sid = secrets.token_hex(16)
            session = GameSession(sid, side, flip, forbid, engine, search_time)
            session.start()          # 引擎启动失败会抛 RuntimeError
            self.sessions[sid] = session
            return session

    def get(self, sid):
        with self.lock:
            s = self.sessions.get(sid)
            if s:
                s.touch()
            return s

    def remove(self, sid):
        with self.lock:
            s = self.sessions.pop(sid, None)
            if s:
                s.close()
            return s

    def reap_once(self, now=None):
        """回收空闲超时的会话，返回被杀会话列表（WS 通知由调用方发）。"""
        now = time.time() if now is None else now
        victims = []
        with self.lock:
            for sid, s in list(self.sessions.items()):
                if not s.engine.alive():
                    victims.append(s)
                    del self.sessions[sid]
                elif now - s.last_active_at > IDLE_TIMEOUT:
                    victims.append(s)
                    del self.sessions[sid]
        for s in victims:
            s.close()
        return victims


manager = SessionManager()


async def reaper_loop():
    while True:
        await asyncio.sleep(REAP_INTERVAL)
        victims = manager.reap_once()
        for s in victims:
            if s.ws is not None:
                try:
                    await s.ws.send_json({"type": "error", "msg": "长时间未操作，对局已结束"})
                    await s.ws.close()
                except Exception:
                    pass


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(reaper_loop())
    yield
    task.cancel()


app = FastAPI(title="Xiangqi Web Play", lifespan=lifespan)


async def _wait_engine(ws, session):
    """等待引擎思考完成（0.1s 轮询读线程队列），结束后推送 state。"""
    deadline = time.monotonic() + ENGINE_WAIT_TIMEOUT
    while session.thinking and time.monotonic() < deadline:
        session.poll_engine()
        if not session.thinking:
            break
        if not session.engine.alive():
            session.thinking = False
            session.game_over = True
            session.over_reason = "engine_crashed"
            break
        await asyncio.sleep(0.1)
    if session.thinking:
        # 搜索硬超时：视为引擎卡死
        session.thinking = False
        session.game_over = True
        session.over_reason = "engine_crashed"
    if session.game_over:
        session.close()   # 终局即回收引擎进程
    await ws.send_json(session.state_msg())


async def _handle_message(ws, session, data):
    """处理一条客户端消息。返回 False 表示连接应结束。"""
    mtype = data.get("type")
    session.touch()

    if mtype == "move":
        if session.game_over or session.thinking:
            await ws.send_json({"type": "error", "msg": "现在不能走子"})
            return True
        r1, c1, r2, c2 = data.get("r1"), data.get("c1"), data.get("r2"), data.get("c2")
        if not all(isinstance(x, int) for x in (r1, c1, r2, c2)):
            await ws.send_json({"type": "error", "msg": "参数不完整"})
            return True
        ok, err = session.try_human_move(r1, c1, r2, c2)
        if not ok:
            await ws.send_json({"type": "error", "msg": err})
            return True
        if session.game_over:
            session.close()
            await ws.send_json(session.state_msg())
            return True
        session.request_engine_move()
        await ws.send_json(session.state_msg())   # thinking=true
        await _wait_engine(ws, session)
        return True

    if mtype == "select":
        if session.game_over or session.thinking or session.board.turn != session.player_side:
            await ws.send_json({"type": "error", "msg": "现在不能选子"})
            return True
        r, c = data.get("r"), data.get("c")
        if not isinstance(r, int) or not isinstance(c, int):
            await ws.send_json({"type": "error", "msg": "参数不完整"})
            return True
        legal = session.legal_moves_for(r, c)
        await ws.send_json(session.state_msg(legal=legal))
        return True

    if mtype == "resign":
        session.resign()
        session.close()
        await ws.send_json(session.state_msg())
        return True

    if mtype == "set_forbid":
        fb, err = parse_forbid(data.get("text"))
        if err:
            await ws.send_json({"type": "error", "msg": err})
            return True
        session.forbid = fb
        await ws.send_json(session.state_msg())
        return True

    if mtype == "set_flip":
        session.flip = bool(data.get("flip", False))
        await ws.send_json(session.state_msg())
        return True

    if mtype == "set_search_time":
        seconds, err = parse_search_time(data.get("search_time"))
        if err:
            await ws.send_json({"type": "error", "msg": err})
            return True
        session.set_search_time(seconds)
        await ws.send_json(session.state_msg())
        return True

    await ws.send_json({"type": "error", "msg": f"未知消息类型: {mtype}"})
    return True


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    session = None
    try:
        # 首条消息：new_game 或 resume（30 秒超时）
        try:
            first = await asyncio.wait_for(ws.receive_json(), timeout=30)
        except asyncio.TimeoutError:
            await ws.close()
            return

        ftype = first.get("type")
        if ftype == "new_game":
            side = first.get("side", "red")
            engine = first.get("engine", "custom")
            search_time, time_error = parse_search_time(
                first.get("search_time", DEFAULT_SEARCH_TIME)
            )
            flip = bool(first.get("flip", False))
            forbid, _ = parse_forbid(first.get("forbid_text"))   # 开新局静默忽略无效禁招
            if side not in ("red", "black"):
                await ws.send_json({"type": "error", "msg": "side 必须是 red 或 black"})
                await ws.close()
                return
            if engine not in ENGINE_PATHS:
                await ws.send_json({"type": "error", "msg": "未知引擎"})
                await ws.close()
                return
            if time_error:
                await ws.send_json({"type": "error", "msg": time_error})
                await ws.close()
                return
            try:
                session = manager.create(side, flip, forbid, engine, search_time)
            except RuntimeError as e:
                await ws.send_json({"type": "error", "msg": f"引擎启动失败: {e}"})
                await ws.close()
                return
            if session is None:
                await ws.send_json({"type": "busy"})
                await ws.close()
                return
            session.ws = ws
            if side == "black":
                # 人执黑：引擎先走（先 search 再推 state，让前端看到 thinking=true）
                session.request_engine_move()
                await ws.send_json(session.state_msg())
                await _wait_engine(ws, session)
            else:
                await ws.send_json(session.state_msg())

        elif ftype == "resume":
            session = manager.get(first.get("sid", ""))
            if session is None:
                await ws.send_json({"type": "error", "msg": "会话不存在，请新开对局"})
                await ws.close()
                return
            # 单写者：新连接接管，旧连接关闭
            old_ws = session.ws
            session.ws = ws
            if old_ws is not None:
                try:
                    await old_ws.close()
                except Exception:
                    pass
            await ws.send_json(session.state_msg())
            if session.thinking and not session.game_over:
                # 接管思考等待（引擎输出是 session 级状态，新连接继续 drain）
                await _wait_engine(ws, session)
        else:
            await ws.send_json({"type": "error", "msg": "首条消息必须是 new_game 或 resume"})
            await ws.close()
            return

        # 主循环
        while True:
            try:
                data = await ws.receive_json()
            except WebSocketDisconnect:
                break
            if not isinstance(data, dict):
                await ws.send_json({"type": "error", "msg": "消息格式错误"})
                continue
            if data.get("type") == "new_game":
                # 同连接重开新局：回收旧会话，创建新会话
                side = data.get("side", "red")
                engine = data.get("engine", "custom")
                search_time, time_error = parse_search_time(
                    data.get("search_time", DEFAULT_SEARCH_TIME)
                )
                flip = bool(data.get("flip", False))
                forbid, _ = parse_forbid(data.get("forbid_text"))   # 开新局静默忽略无效禁招
                if side not in ("red", "black"):
                    await ws.send_json({"type": "error", "msg": "side 必须是 red 或 black"})
                    continue
                if engine not in ENGINE_PATHS:
                    await ws.send_json({"type": "error", "msg": "未知引擎"})
                    continue
                if time_error:
                    await ws.send_json({"type": "error", "msg": time_error})
                    continue
                manager.remove(session.sid)
                try:
                    session = manager.create(side, flip, forbid, engine, search_time)
                except RuntimeError as e:
                    await ws.send_json({"type": "error", "msg": f"引擎启动失败: {e}"})
                    await ws.close()
                    return
                if session is None:
                    await ws.send_json({"type": "busy"})
                    await ws.close()
                    return
                session.ws = ws
                if side == "black":
                    session.request_engine_move()
                    await ws.send_json(session.state_msg())
                    await _wait_engine(ws, session)
                else:
                    await ws.send_json(session.state_msg())
                continue
            await _handle_message(ws, session, data)
    except (WebSocketDisconnect, RuntimeError):
        pass   # 连接断开或推送失败
    finally:
        if session is not None:
            # 解绑但保留会话（刷新/重连窗口），由 reaper 兜底回收
            if session.ws is ws:
                session.ws = None


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("XQ_PORT", "8000")))
