# ============================================================
# 一键部署脚本 (PowerShell 版): 本地改完代码, 运行本脚本即可更新服务器
#
# 用法:
#   1. 在项目目录打开 PowerShell, 运行:
#        powershell -ExecutionPolicy Bypass -File deploy\deploy.ps1
#      (或者先放开执行策略, 以后直接 .\deploy\deploy.ps1 :
#        Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
#   2. 或者资源管理器右键 deploy.ps1 -> "使用 PowerShell 运行"
#
# 部署方式:
#   - 服务器信息在 deploy\secrets.env (已 gitignore, 不提交):
#       先 Copy-Item deploy\secrets.env.example deploy\secrets.env 并填真实值
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
$ErrorActionPreference = "Stop"

# 脚本所在目录的上一级 = 项目根目录 (从任意目录运行都行)
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

# 加载服务器配置 (含 IP 等敏感信息, 已 gitignore, 不提交)
$EnvFile = Join-Path $PSScriptRoot "secrets.env"
if (-not (Test-Path $EnvFile)) {
  Write-Host "缺少 deploy\secrets.env (含服务器信息, 已 gitignore)。" -ForegroundColor Red
  Write-Host "请复制 deploy\secrets.env.example 为 deploy\secrets.env 并填好真实值。"
  exit 1
}
Get-Content $EnvFile | ForEach-Object {
  if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
    Set-Variable -Name $Matches[1] -Value $Matches[2] -Scope Script
  }
}

function Check($msg) {
  if ($LASTEXITCODE -ne 0) {
    Write-Host "失败: $msg" -ForegroundColor Red
    exit 1
  }
}

# ---- 要上传的 python 文件 (加新文件往这里加一行) ----
$Files = @("common.py", "webapp.py")

Write-Host "[1/4] 上传代码到 ${SERVER}:${REMOTE_DIR} ..."
foreach ($f in $Files) {
  scp $f "${SERVER}:${REMOTE_DIR}/"
  Check "上传 $f"
}
scp -r static "${SERVER}:${REMOTE_DIR}/"
Check "上传 static/"
scp deploy/xiangqi-web.service "${SERVER}:/tmp/"
Check "上传 service 文件"

# ---- 引擎源码有变化才重编译 ----
$LocalMd5  = (Get-FileHash "xiangqi_ai.cpp" -Algorithm MD5).Hash.ToLower()
$RemoteMd5 = (ssh $SERVER "md5sum ${REMOTE_DIR}/xiangqi_ai.cpp 2>/dev/null | awk '{print `$1}'").Trim()
if ($RemoteMd5 -eq "") { $RemoteMd5 = "missing" }
if ($LocalMd5 -ne $RemoteMd5) {
  Write-Host "[2/4] 引擎源码有变化, 上传并重新编译 ..."
  scp xiangqi_ai.cpp "${SERVER}:${REMOTE_DIR}/"
  Check "上传 xiangqi_ai.cpp"
  ssh $SERVER "cd ${REMOTE_DIR} && g++ -O2 -std=c++17 -o xiangqi_ai xiangqi_ai.cpp"
  Check "编译引擎"
} else {
  Write-Host "[2/4] 引擎源码无变化, 跳过编译"
}

Write-Host "[3/4] 更新 systemd 服务并重启 ..."
ssh $SERVER "sudo cp /tmp/xiangqi-web.service /etc/systemd/system/${SERVICE}.service && sudo systemctl daemon-reload && sudo systemctl restart ${SERVICE} && sleep 1 && systemctl is-active ${SERVICE}"
Check "重启服务"

Write-Host "[4/4] 验证服务 ..."
ssh $SERVER "curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:${PORT}/"
Check "HTTP 验证"

Write-Host "完成! 朋友访问: $PUBLIC_URL" -ForegroundColor Green
