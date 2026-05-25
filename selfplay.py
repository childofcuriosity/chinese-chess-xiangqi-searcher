"""
自对弈仲裁: 让两个引擎对局, 检测吃王 / 长将 / 步数上限结束.
用法:
  python selfplay.py <red.exe> <black.exe> [max_plies=200]
"""
import subprocess, sys, time, os

INITIAL = [
    list("rnbakabnr"),
    list("........."),
    list(".c.....c."),
    list("p.p.p.p.p"),
    list("........."),
    list("........."),
    list("P.P.P.P.P"),
    list(".C.....C."),
    list("........."),
    list("RNBAKABNR"),
]

def new_board():
    return [row[:] for row in INITIAL]

def apply_move(b, mv):
    r1, c1, r2, c2 = mv
    captured = b[r2][c2]
    b[r2][c2] = b[r1][c1]
    b[r1][c1] = '.'
    return captured

def print_board(b):
    for r, row in enumerate(b):
        print(f"{r} " + " ".join(row))
    print("  " + " ".join(str(i) for i in range(9)))

class Engine:
    def __init__(self, exe_path, plays_red):
        self.exe = exe_path
        self.plays_red = plays_red
        # 引擎里 player_side 是 "人类方", AI 取反
        human_side = "black" if plays_red else "red"
        exe_abs = os.path.abspath(exe_path)
        self.p = subprocess.Popen(
            [exe_abs], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, bufsize=1, text=True, encoding='utf-8',
            errors='replace'
        )
        self._send("ready")
        self._wait_for("readyok")
        self._send(f"side {human_side}")

    def _send(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()

    def _wait_for(self, token):
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError(f"{self.exe} died")
            if token in line:
                return line.strip()

    def play_move(self, mv):
        r1, c1, r2, c2 = mv
        self._send(f"move {r1} {c1} {r2} {c2}")

    def search(self):
        self._send("search")
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError(f"{self.exe} died during search")
            line = line.strip()
            if line.startswith("move "):
                _, r1, c1, r2, c2 = line.split()
                return (int(r1), int(c1), int(r2), int(c2))
            if line == "resign":
                return None

    def quit(self):
        try:
            self._send("quit")
            self.p.wait(timeout=3)
        except Exception:
            self.p.kill()

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    red_exe, black_exe = sys.argv[1], sys.argv[2]
    max_plies = int(sys.argv[3]) if len(sys.argv) > 3 else 200

    red = Engine(red_exe, plays_red=True)
    black = Engine(black_exe, plays_red=False)
    engines = [red, black]   # 0 = red to move, 1 = black

    board = new_board()
    side = 0  # red 先
    move_history = []
    start = time.time()
    result = None

    for ply in range(max_plies):
        eng = engines[side]
        other = engines[1 - side]
        t0 = time.time()
        mv = eng.search()
        elapsed = time.time() - t0
        if mv is None:
            result = ("black" if side == 0 else "red") + " wins (opponent resigned)"
            break
        captured = apply_move(board, mv)
        side_name = "red  " if side == 0 else "black"
        cap_note = f" x{captured}" if captured != '.' else ""
        print(f"ply {ply+1:3d} {side_name} {mv[0]}{mv[1]}->{mv[2]}{mv[3]}{cap_note}  ({elapsed:.1f}s)")
        sys.stdout.flush()
        move_history.append((side, mv, captured))
        if captured in ('k', 'K'):
            winner = "red" if captured == 'k' else "black"
            result = f"{winner} wins (king captured)"
            break
        other.play_move(mv)
        side = 1 - side
    else:
        result = "draw (max plies)"

    total = time.time() - start
    print("=" * 50)
    print_board(board)
    print(f"Result: {result}")
    print(f"Total time: {total:.1f}s ({len(move_history)} plies)")
    print(f"  Red  ({red_exe})")
    print(f"  Black({black_exe})")
    red.quit(); black.quit()

if __name__ == "__main__":
    main()
