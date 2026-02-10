import numpy as np
from sklearn.linear_model import HuberRegressor,LinearRegression
import os

# --- 配置 ---
DATA_FILE = "dataset_tree_score.txt"
OUTPUT_FILE = "my_symmetric_pst.py"

# 棋子索引 (只定义红方，黑方通过翻转映射)
PIECE_INDICES = {'R': 0, 'N': 1, 'B': 2, 'A': 3, 'K': 4, 'C': 5, 'P': 6}
PIECE_NAMES = ['R', 'N', 'B', 'A', 'K', 'C', 'P']
NAME_MAP = {
    'R': 'rook', 'N': 'knight', 'B': 'bishop', 
    'A': 'advisor', 'K': 'king', 'C': 'cannon', 'P': 'pawn'
}

# 因为我生成数据没有吃和差，所以子分数就用这个权宜之计人为定。如果设全0就是没有人为定的。
BASE_VALUES = {
    'R': 1000,  # 车
    'N': 450,   # 马
    'B': 120,   # 象
    'A': 120,   # 士
    'K': 20000,     # 帅 (由PST决定安全分，不需要基础材质分)
    'C': 450,   # 炮
    'P': 30     # 兵 (未过河基础分)
}
# 核心逻辑：将9列映射到5列 (0,1,2,3,4)
# Col 0(左边) 和 Col 8(右边) 视为同一个位置
def get_symmetric_col(col):
    if col <= 4:
        return col
    else:
        return 8 - col

# --- 特征提取 1: 纯子力数量差 (用于阶段一) ---
def get_material_counts(board_str):
    """
    返回一个长度为 7 的数组，表示 [车差, 马差, 象差, 士差, 帅差, 炮差, 兵差]
    """
    counts = np.zeros(7, dtype=np.int8)
    for char in board_str:
        if not char.isalpha(): continue
        upper = char.upper()
        if upper not in PIECE_INDICES: continue
        
        idx = PIECE_INDICES[upper]
        # 红方为正，黑方为负
        val = 1 if char.isupper() else -1
        counts[idx] += val
    return counts

def parse_fen_symmetric(fen):
    """
    将FEN转换为压缩后的特征向量 (利用左右对称)
    特征维度: 7种棋子 * 10行 * 5列 = 350个特征
    """
    
    board_str = fen.split()[0]
    
    # 350 = 7types * 50squares
    features = np.zeros(350, dtype=np.int8)
    
    row_idx = 0
    col_idx = 0
    
    for char in board_str:
        if char == '/':
            row_idx += 1
            col_idx = 0
        elif char.isdigit():
            col_idx += int(char)
        else:
            # 计算基础坐标
            # 无论红黑，都要映射到 "红方视角的左半边(0-4列)"
            
            p_type_idx = -1
            effective_row = -1
            sign = 0
            
            if char.isupper(): # 红棋
                p_type_idx = PIECE_INDICES[char]
                effective_row = row_idx  # 红方Row 0是上面
                sign = 1
            else: # 黑棋
                p_type_idx = PIECE_INDICES[char.upper()]
                effective_row = 9 - row_idx # 黑方翻转行：Row 0变成Row 9
                sign = -1 # 黑棋价值为负
            
            # --- 对称化核心 ---
            # 这里的 col_idx 是物理列号 (0-8)
            # 我们将其折叠到 (0-4)
            sym_col = get_symmetric_col(col_idx)
            
            # 计算在压缩特征向量中的索引
            # [Type 0...6] * [Row 0...9] * [Col 0...4]
            # 偏移量 = 类型偏移 + 行偏移 + 列
            feat_idx = (p_type_idx * 50) + (effective_row * 5) + sym_col
            
            features[feat_idx] += sign
            
            col_idx += 1
            
    return features

# --- 新增：翻转棋盘字符串函数 ---
def flip_board_fen(board_fen):
    """
    翻转 FEN 的棋盘部分：
    1. 行顺序颠倒 (Row 0 <-> Row 9)
    2. 大小写互换 (红变黑，黑变红)
    """
    rows = board_fen.split('/')
    # reversed(rows) 实现上下翻转
    # swapcase() 实现颜色互换 (r -> R, R -> r)
    new_rows = [row.swapcase() for row in reversed(rows)]
    return "/".join(new_rows)

def get_mirror_board_fen(board_fen):
    """
    获取棋盘的左右水平镜像 FEN。
    原理：每一行字符串直接反转即可。
    例如: "R2c" (车,2空,炮) -> 反转为 "c2R" (炮,2空,车) -> 对应实际棋盘的左右翻转
    注意：这仅适用于FEN中数字只有1-9单字符的情况（中国象棋FEN标准如此）。
    """
    rows = board_fen.split('/')
    # 字符串反转 [::-1]
    new_rows = [row[::-1] for row in rows]
    return "/".join(new_rows)
def calculate_material_diff(board_str):
    """
    计算 (红方材质分 - 黑方材质分)
    """
    score = 0
    for char in board_str:
        if not char.isalpha():
            continue
        
        piece_type = char.upper()
        if piece_type not in BASE_VALUES:
            continue
            
        value = BASE_VALUES[piece_type]
        
        if char.isupper(): # 红方
            score += value
        else: # 黑方
            score -= value
    return score

def main():
    if not os.path.exists(DATA_FILE):
        print(f"错误：找不到数据文件 {DATA_FILE}")
        return

    print("正在加载数据并应用对称化处理...")
    X_material = [] # 阶段一特征
    y_raw = []      # 原始分数
    seen_positions = set()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 2: continue
            
            try:
                score = float(parts[0])
                raw_fen = parts[1]
                fen_parts = raw_fen.split()
                board_str = fen_parts[0]
                # 获取走棋方 (w/r=红, b=黑)，如果FEN不标准默认当红方处理
                turn = fen_parts[1] if len(fen_parts) > 1 else 'w'

                # 如果是黑方走棋 ('b')，我们需要将其翻转为“红方走棋”的等价局面
                if turn == 'b':
                    # 1. 翻转分数 (黑方优势变红方优势，或反之)
                    score = -score
                    # 2. 翻转棋盘 (黑棋变红棋，且位置倒置)
                    board_str = flip_board_fen(board_str)
                    
                    # 更新 fen 变量，因为 parse_fen_symmetric 只需要 board_str
                    # (我们不需要重组完整的FEN字符串，只要把 board_str 传给解析函数即可)
                    fen_to_process = board_str
                else:
                    # 红方走棋，直接用原串
                    fen_to_process = board_str
                mirror_fen = get_mirror_board_fen(fen_to_process)
                if (fen_to_process in seen_positions) or (mirror_fen in seen_positions):
                    continue
                seen_positions.add(fen_to_process)
                X_material.append(get_material_counts(fen_to_process))
                y_raw.append(score)
            except:
                continue
    X_material = np.array(X_material)
    y_raw = np.array(y_raw)
    print(f"加载完成，总样本数 (含丢子局): {len(y_raw)}")
    
    # =========================================================
    # 阶段一：学习全量子力价值 (Global Material Values)
    # =========================================================
    print("\n[阶段一] 正在全量数据上拟合基础子力价值...")
    
    # 用简单的线性回归，fit_intercept=False (没有子力时默认为0分)
    model_mat = LinearRegression(fit_intercept=False) 
    model_mat.fit(X_material, y_raw)
    
    learned_values = model_mat.coef_
    
    print(">>> 学习到的子力价值 (Global):")
    material_dict = {}
    for i, name in enumerate(PIECE_NAMES):
        val = int(learned_values[i])
        material_dict[name] = val
        print(f"    {name}: {val}")
        BASE_VALUES[name] = val  # 更新基础值为学习到的值
    # R: 702
    # N: 413
    # B: -36
    # A: 90
    # K: 0
    # C: 694
    # P: 178
    # 这不对，因为表达能力没法学先见之明，维度少了。就抄象眼就好，不要低维硬平均高维，数据量不能承受。
    X = []
    y = []
    seen_positions = set()
    count = 0
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 2: continue
            
            try:
                score = float(parts[0])
                raw_fen = parts[1]
                if abs(score) > 2000: # 过滤极端分数，因为平时可能在这个位置没事
                    continue 

                # --- 新增逻辑开始 ---
                fen_parts = raw_fen.split()
                board_str = fen_parts[0]
                # 获取走棋方 (w/r=红, b=黑)，如果FEN不标准默认当红方处理
                turn = fen_parts[1] if len(fen_parts) > 1 else 'w'

                # 如果是黑方走棋 ('b')，我们需要将其翻转为“红方走棋”的等价局面
                if turn == 'b':
                    # 1. 翻转分数 (黑方优势变红方优势，或反之)
                    score = -score
                    # 2. 翻转棋盘 (黑棋变红棋，且位置倒置)
                    board_str = flip_board_fen(board_str)
                    
                    # 更新 fen 变量，因为 parse_fen_symmetric 只需要 board_str
                    # (我们不需要重组完整的FEN字符串，只要把 board_str 传给解析函数即可)
                    fen_to_process = board_str
                else:
                    # 红方走棋，直接用原串
                    fen_to_process = board_str
                mirror_fen = get_mirror_board_fen(fen_to_process)
                if (fen_to_process in seen_positions) or (mirror_fen in seen_positions):
                    continue
                seen_positions.add(fen_to_process)
                X.append(parse_fen_symmetric(fen_to_process))
                material_diff = calculate_material_diff(board_str)
                target_residual = score - material_diff
                y.append(target_residual)
                count += 1
            except:
                continue
                
    print(f"加载完成，有效样本数: {count}")
    print("正在训练对称回归模型 ( Regression)...")
    
    # Alpha越大，PST数值越平滑，越不容易过拟合
    model = HuberRegressor(epsilon=1.2, max_iter=200, alpha=0.0001) 

    # 注意：HuberRegressor 的 fit 比较慢，如果数据量太大(几十万)，可能需要一点时间
    model.fit(X, y)
    
    print("训练完成！正在解压并导出完整 9x10 PST...")
    
    # 提取权重 (350个)
    weights = model.coef_
    
    output_lines = []
    output_lines.append("# Generated by Residual Learning")
    output_lines.append("# 这些值是【相对于】基础子力价值的加成/减分")
    output_lines.append("")
    
    # 打印基础分供参考
    output_lines.append("# 基础子力设定:")
    for k, v in BASE_VALUES.items():
        output_lines.append(f"# {k}: {v}")
    output_lines.append("")

    
    # 2. 输出 PST 表
    for i, p_char in enumerate(PIECE_NAMES):
        piece_name = NAME_MAP[p_char]
        var_name = f"pst_{piece_name}"
        base_val = BASE_VALUES[p_char]
        output_lines.append(f"{var_name} = [")
        
        # 获取该棋子的50个压缩权重
        w_packed = weights[i*50 : (i+1)*50]
        
        # 逐行还原为 9列
        for r in range(10):
            # 获取该行压缩后的5个值 (col 0,1,2,3,4)
            row_packed = w_packed[r*5 : (r+1)*5]
            
            # 解压逻辑：[0, 1, 2, 3, 4, 3, 2, 1, 0]
            # 左半边 + 中间 + 右半边(左边的镜像)
            full_row = []
            
            # 左边 (0-3)
            for c in range(4):
                full_row.append(int(row_packed[c]+ base_val))
            
            # 中间 (4)
            full_row.append(int(row_packed[4]+ base_val))
            
            # 右边 (5-8) -> 对应 (3,2,1,0)
            for c in range(3, -1, -1):
                full_row.append(int(row_packed[c]+ base_val))
            
            # 格式化输出
            row_str = ", ".join(f"{v:4d}" for v in full_row)
            output_lines.append(f"    [{row_str}], # Row {r}")
            
        output_lines.append("]\n")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(output_lines))
        
    print(f"文件已生成: {OUTPUT_FILE}")
    print("提示：你可以直接复制这些 pst_xxx 数组到你的引擎代码中。")

if __name__ == "__main__":
    main()