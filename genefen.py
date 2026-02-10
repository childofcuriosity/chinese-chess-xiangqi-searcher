import subprocess
import random
import os
import re
import multiprocessing
import time
from queue import Empty

# ENGINE_PATH: 指向皮卡鱼可执行文件的路径
ENGINE_PATH = r"E:\copyofxhy\after2024\2025-1\xq\pikafish\pikafish-bmi2.exe"
# DATA_FILE: 生成的数据保存在这个文本里
DATA_FILE = "dataset_tree_score.txt"
TOTAL_TARGET = 500000        # 总共想采集的数据条数
TREE_DEPTH_LIMIT = 50        # 搜索树的最大深度（防止开局后走太深）
MULTIPV = 4                  # 重点：让引擎同时输出排名前4的好走法，这样分支多，采集快
EVAL_DEPTH = 6              # 引擎搜索的深度——太太平了
NODES_LIMIT = 30000          # 限制每个局面搜索的计算量（节点数），平衡速度与质量
PROCESSES = max(1, multiprocessing.cpu_count() - 2) # 并行进程数

class EngineTreeWorker:
    def __init__(self, path):
        self.path = path
        startupinfo = None# startupinfo: 在 Windows 下防止每开一个引擎就弹出一个黑窗口
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        # 启动子进程执行引擎
        self.proc = subprocess.Popen(
            self.path, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0, startupinfo=startupinfo,
            shell=False
        )
        # --- UCI 握手环节 ---
        self.send("uci")          # 告诉引擎：我们要用 UCI 模式交流
        self.wait_for("uciok")    # 等待引擎确认
        self.send(f"setoption name MultiPV value {MULTIPV}") # 设置：请给多个最佳走法
        self.send("isready")      # 询问：准备好了吗？
        self.wait_for("readyok")  # 等待回复：准备好了

    def send(self, cmd):
        self.proc.stdin.write(f"{cmd}\n".encode())
        self.proc.stdin.flush()

    def wait_for(self, target):
        while True:
            line = self.proc.stdout.readline().decode('utf-8', errors='ignore').strip()
            if target in line: return line
    def get_eval_and_next_fens(self, current_fen):
        self.send(f"position fen {current_fen}")
        self.send(f"go depth {EVAL_DEPTH} nodes {NODES_LIMIT}")
        
        pv_map = {} 
        current_max_depth = 0
        
        while True:
            line = self.proc.stdout.readline().decode('utf-8', errors='ignore').strip()
            if not line: continue
            
            if "info" in line and "multipv" in line and " pv " in line:
                # 1. 提取当前这一行的深度
                depth_match = re.search(r"depth (\d+)", line)
                if not depth_match: continue
                depth = int(depth_match.group(1))
                
                # 2. 如果这行信息的深度比之前看到的高，说明进入了新的一层
                # 我们清空旧的（低深度）数据，只保留当前最高深度的
                if depth > current_max_depth:
                    pv_map = {}
                    current_max_depth = depth
                
                # 只有当这行数据的深度等于我们记录的最高深度时，才存入
                if depth == current_max_depth:
                    try:
                        idx_match = re.search(r"multipv (\d+)", line)
                        score = 0
                        if "cp " in line:
                            score = int(re.search(r"cp (-?\d+)", line).group(1))
                        elif "mate " in line:
                            score = 10000 if "cp" not in line else 20000 # 简化处理绝杀
                        
                        move = re.search(r" pv (\w+)", line).group(1)
                        idx = int(idx_match.group(1))
                        
                        pv_map[idx] = {'move': move, 'score': score}
                    except:
                        continue
            
            if "bestmove" in line:
                break

        results = []
        side = current_fen.split()[1]
        
        # 对每一个找到的 PV 分支，获取它的新 FEN
        for idx in pv_map:
            move = pv_map[idx]['move']
            score = pv_map[idx]['score']
            # 统一转换成分数：如果是黑方走，引擎给的 cp 是对黑方而言的，
            # 这里转换成“对红方的利好程度”
            score_red = score if side == 'w' else -score
            
            # 快速获取执行 move 后的 FEN
            # --- 重点技巧：如何获取走完这一步后的新 FEN？ ---
            # 再次发送 position 命令，带上 moves 参数
            self.send(f"position fen {current_fen} moves {move}")
            self.send("d")
            # Pikafish 的 d 命令输出包含 "Fen: <fen>"
            fen_line = self.wait_for("Fen:")
            new_fen = fen_line.split("Fen:")[1].strip()
            
            results.append({
                'score_red': score_red,
                'new_fen': new_fen,
                'original_fen': current_fen
            })
            
        return results

    def close(self):
        try:
            self.send("quit")
            self.proc.terminate()
        except: pass

def worker_main(worker_id, shared_queue, shared_seen, target):
    # 每个进程启动一个独立的引擎实例
    engine = None
    try:
        engine = EngineTreeWorker(ENGINE_PATH)
        local_batch = []
        count = 0
        
        while count < target:
            try:
                # 从共享队列中拿出一个待分析的局面
                # 稍微加长等待时间，并增加队列为空的处理
                fen, depth = shared_queue.get(timeout=10)
            except Empty:
                print(f"⚠️ 进程 {worker_id} 队列为空，等待中...")
                time.sleep(2)
                continue
            # 归一化 FEN：去掉最后的回合计数，只保留棋盘分布和走子方
            norm_fen = " ".join(fen.split()[:2])
            if norm_fen in shared_seen:
                continue
            shared_seen[norm_fen] = True

            # 获取分支
            branches = engine.get_eval_and_next_fens(fen)
            
            for b in branches:
                # 保存红方视角分数和当前局面
                local_batch.append(f"{b['score_red']}\t{" ".join(b['new_fen'].split()[:2])}")
                count += 1
                
                # 将新局面加入队列
                if depth < TREE_DEPTH_LIMIT:
                    if abs(b['score_red']) < 2000: # 过滤极端杀棋分数，避免干扰PST的平滑度
                        shared_queue.put((b['new_fen'], depth + 1))

                if len(local_batch) >= 20:
                    with open(DATA_FILE, "a", encoding="utf-8") as f:
                        f.write("\n".join(local_batch) + "\n")
                    local_batch = []
                    if count % 100 == 0:
                        print(f"📊 进程 {worker_id}: 已采集 {count}/{target}")

    except Exception as e:
        print(f"❌ 进程 {worker_id} 崩溃: {e}")
    finally:
        if engine: engine.close()

def main():
    # 必须在 Windows 下使用的多进程写法
    multiprocessing.freeze_support()
    
    manager = multiprocessing.Manager()
    shared_queue = manager.Queue()
    shared_seen = manager.dict()
    
    # 初始种子：开局位置
    start_fen = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
    shared_queue.put((start_fen, 0))
    
    # 增加种子多样性：随机走几步产生不同的起点
    # 也可以手动加入几十个不同的常见开局 FEN
    print("🌱 正在初始化种子局面...")
    
    target_per_worker = TOTAL_TARGET // PROCESSES
    
    print(f"🚀 启动并行引擎任务 | 进程数: {PROCESSES} | 深度限制: {TREE_DEPTH_LIMIT}")
    
    processes = []
    for i in range(PROCESSES):
        p = multiprocessing.Process(target=worker_main, args=(i, shared_queue, shared_seen, target_per_worker))
        p.daemon = True
        p.start()
        processes.append(p)
        
    for p in processes:
        p.join()

if __name__ == "__main__":
    main()