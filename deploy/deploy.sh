#!/usr/bin/env bash
# ============================================================
# 一键部署脚本: 本地改完代码, 运行本脚本即可更新服务器
#
# 用法 (Windows Git Bash / macOS / Linux 均可):
#     bash deploy/deploy.sh
#
# 部署方式:
#   - 服务器信息在 deploy/secrets.env (已 gitignore, 不提交):
#       先 cp deploy/secrets.env.example deploy/secrets.env 并填真实值
#   - 走 ssh (别名见 secrets.env 的 SERVER), 不走 git
#   - 上传 python/前端文件到服务器 REMOTE_DIR/
#   - xiangqi_ai.cpp 用 md5 对比, 有变化才上传并 g++ 重编译
#   - 更新 systemd 服务 (SERVICE) 并重启, 验证 HTTP 200
#
# 常用命令 (把 <alias> 换成 secrets.env 里的 SERVER):
#   手动重启      ssh <alias> "sudo systemctl restart xiangqi-web"
#   看服务日志    ssh <alias> "journalctl -u xiangqi-web -n 50"
#   引擎单独重编  ssh <alias> "cd /opt/xq && g++ -O2 -std=c++17 -o xiangqi_ai xiangqi_ai.cpp"
# ============================================================
set -e

# 脚本所在目录的上一级 = 项目根目录 (从任意目录运行都行)
PROJECT_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$PROJECT_ROOT"

# 加载服务器配置 (含 IP 等敏感信息, 已 gitignore)
if [ -f deploy/secrets.env ]; then
  . deploy/secrets.env
else
  echo "缺少 deploy/secrets.env (含服务器信息, 已 gitignore)。"
  echo "请复制 deploy/secrets.env.example 为 deploy/secrets.env 并填好真实值。"
  exit 1
fi

# ---- 要上传的 python 文件 (加新文件往这里加一行) ----
FILES="common.py webapp.py"

echo "[1/4] 上传代码到 $SERVER:$REMOTE_DIR ..."
for f in $FILES; do
  scp "$f" "$SERVER:$REMOTE_DIR/"
done
scp -r static "$SERVER:$REMOTE_DIR/"
scp deploy/xiangqi-web.service "$SERVER:/tmp/"

# ---- 引擎源码有变化才重编译 ----
LOCAL_MD5=$(md5sum xiangqi_ai.cpp | awk '{print $1}')
REMOTE_MD5=$(ssh "$SERVER" "md5sum $REMOTE_DIR/xiangqi_ai.cpp 2>/dev/null | awk '{print \$1}' || echo missing")
if [ "$LOCAL_MD5" != "$REMOTE_MD5" ]; then
  echo "[2/4] 引擎源码有变化, 上传并重新编译 ..."
  scp xiangqi_ai.cpp "$SERVER:$REMOTE_DIR/"
  ssh "$SERVER" "cd $REMOTE_DIR && g++ -O2 -std=c++17 -o xiangqi_ai xiangqi_ai.cpp"
else
  echo "[2/4] 引擎源码无变化, 跳过编译"
fi

echo "[3/4] 更新 systemd 服务并重启 ..."
ssh "$SERVER" "sudo cp /tmp/xiangqi-web.service /etc/systemd/system/$SERVICE.service \
  && sudo systemctl daemon-reload \
  && sudo systemctl restart $SERVICE \
  && sleep 1 \
  && systemctl is-active $SERVICE"

echo "[4/4] 验证服务 ..."
ssh "$SERVER" "curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:$PORT/"

echo "完成! 朋友访问: ${PUBLIC_URL:-http://<服务器IP>:$PORT}"
