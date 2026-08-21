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
#   - 自研引擎与 Pikafish PST 桥接引擎同时部署，网页可按局选择
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
$Files = @("common.py", "webapp.py", "pikafish_bridge.py")

Write-Host "[1/5] 上传代码到 ${SERVER}:${REMOTE_DIR} ..."
foreach ($f in $Files) {
  scp $f "${SERVER}:${REMOTE_DIR}/"
  Check "上传 $f"
}
scp -r static "${SERVER}:${REMOTE_DIR}/"
Check "上传 static/"
scp deploy/xiangqi-web.service "${SERVER}:/tmp/"
Check "上传 service 文件"
scp deploy/pikafish_pst_bridge "${SERVER}:${REMOTE_DIR}/"
Check "上传 Pikafish 桥接入口"
ssh $SERVER "chmod +x ${REMOTE_DIR}/pikafish_pst_bridge"
Check "设置桥接入口权限"

# ---- 引擎源码有变化才重编译 ----
$LocalMd5  = (Get-FileHash "xiangqi_ai.cpp" -Algorithm MD5).Hash.ToLower()
$RemoteMd5 = (ssh $SERVER "md5sum ${REMOTE_DIR}/xiangqi_ai.cpp 2>/dev/null | awk '{print `$1}'").Trim()
if ($RemoteMd5 -eq "") { $RemoteMd5 = "missing" }
if ($LocalMd5 -ne $RemoteMd5) {
  Write-Host "[2/5] 自研引擎源码有变化, 上传并重新编译 ..."
  scp xiangqi_ai.cpp "${SERVER}:${REMOTE_DIR}/"
  Check "上传 xiangqi_ai.cpp"
  ssh $SERVER "cd ${REMOTE_DIR} && g++ -O2 -std=c++17 -o xiangqi_ai xiangqi_ai.cpp"
  Check "编译引擎"
} else {
  Write-Host "[2/5] 自研引擎源码无变化, 跳过编译"
}

# ---- Pikafish 源码与 PST evaluate.cpp 变化时重编译 ----
$LocalPstMd5 = (Get-FileHash "pikafish-pst/src/evaluate.cpp" -Algorithm MD5).Hash.ToLower()
$RemotePstMd5Output = ssh $SERVER "test -x ${REMOTE_DIR}/pikafish_pst && md5sum ${REMOTE_DIR}/pikafish-pst/src/evaluate.cpp 2>/dev/null | awk '{print `$1}'"
$RemotePstMd5 = if ($null -eq $RemotePstMd5Output) { "missing" } else { "$RemotePstMd5Output".Trim() }
if ($RemotePstMd5 -eq "") { $RemotePstMd5 = "missing" }
if ($LocalPstMd5 -ne $RemotePstMd5) {
  Write-Host "[3/5] 上传源码并构建 Pikafish PST 引擎 ..."
  $PikafishArchive = Join-Path $PSScriptRoot "pikafish-source.tar"
  git -C pikafish-pst archive --format=tar --output=$PikafishArchive HEAD
  Check "打包 Pikafish 源码"
  scp $PikafishArchive "${SERVER}:/tmp/pikafish-source.tar"
  Check "上传 Pikafish 源码包"
  Remove-Item -LiteralPath $PikafishArchive
  ssh $SERVER "mkdir -p ${REMOTE_DIR}/pikafish-pst && tar -xf /tmp/pikafish-source.tar -C ${REMOTE_DIR}/pikafish-pst"
  Check "解压 Pikafish 源码"
  scp pikafish-pst/src/evaluate.cpp "${SERVER}:${REMOTE_DIR}/pikafish-pst/src/"
  Check "上传 PST 评估源码"
  scp pikafish-pst/src/pikafish.nnue "${SERVER}:${REMOTE_DIR}/pikafish-pst/src/"
  Check "上传 Pikafish 网络文件"
  ssh $SERVER "cd ${REMOTE_DIR}/pikafish-pst/src && make -j build ARCH=x86-64-avx2 COMP=gcc EXTRACXXFLAGS=-DUSE_PST_EVAL && cp pikafish ${REMOTE_DIR}/pikafish_pst && cp pikafish.nnue ${REMOTE_DIR}/"
  Check "编译 Pikafish PST 引擎"
} else {
  Write-Host "[3/5] Pikafish PST 源码无变化, 跳过编译"
}

Write-Host "[4/5] 更新 systemd 服务并重启 ..."
ssh $SERVER "sudo cp /tmp/xiangqi-web.service /etc/systemd/system/${SERVICE}.service && sudo systemctl daemon-reload && sudo systemctl restart ${SERVICE} && sleep 1 && systemctl is-active ${SERVICE}"
Check "重启服务"

Write-Host "[5/5] 验证服务 ..."
ssh $SERVER "curl -s -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:${PORT}/"
Check "HTTP 验证"

Write-Host "完成! 朋友访问: $PUBLIC_URL" -ForegroundColor Green
