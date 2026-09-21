[CmdletBinding()]
param(
    [ValidateRange(1, 64)] [int]$Jobs = 12,
    [ValidateRange(1, 192)] [int]$OpeningPairs = 12,
    [ValidateRange(0, 191)] [int]$OpeningStart = 0,
    [ValidateRange(0.01, 60.0)] [double]$XqSecondsPerMove = 0.31,
    [ValidateRange(0.01, 60.0)] [double]$TianqiSecondsPerMove = 0.10,
    [ValidateRange(20, 1000)] [int]$MaxPlies = 160,
    [string]$TianqiPath = "",
    [string]$Output = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = (Get-Command python -ErrorAction Stop).Source
$Engine = Join-Path $PSScriptRoot "nnue_engine_iteration.exe"
$Model = Join-Path $PSScriptRoot "iter2_nnued3_h16_fromiter1_gpu.nnue"
$Bridge = Join-Path $Root "tianqi_bridge.py"
$Openings = Join-Path $PSScriptRoot "openings_final2_192.fen"
$MatchScript = Join-Path $PSScriptRoot "engine_match.py"
$MergeScript = Join-Path $PSScriptRoot "merge_match_shards.py"
if (-not $TianqiPath) {
    $candidate = Get-ChildItem -LiteralPath $Root -Recurse -Filter "*.exe" -File |
        Where-Object { $_.Length -eq 776704 -and $_.DirectoryName -like "*1.1.8*" } |
        Select-Object -First 1
    if ($candidate) { $TianqiPath = $candidate.FullName }
}
$caseName = "start{0}_pairs{1}_a{2}_b{3}" -f $OpeningStart, $OpeningPairs,
    ([int][math]::Round($XqSecondsPerMove * 1000)),
    ([int][math]::Round($TianqiSecondsPerMove * 1000))
$WorkDir = Join-Path $PSScriptRoot ("tianqi_match_shards\" + $caseName)
if (-not $Output) {
    $Output = Join-Path $PSScriptRoot ("tianqi_{0}.json" -f $caseName)
} elseif (-not [System.IO.Path]::IsPathRooted($Output)) {
    $Output = Join-Path $Root $Output
}

if ($OpeningPairs % $Jobs -ne 0) { throw "OpeningPairs must be divisible by Jobs" }
if ($OpeningStart + $OpeningPairs -gt 192) { throw "opening slice exceeds suite" }
foreach ($path in @($Engine, $Model, $TianqiPath, $Bridge, $Openings,
                     $MatchScript, $MergeScript)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "missing input: $path" }
}

$env:TIANQI_PATH = (Resolve-Path -LiteralPath $TianqiPath).Path
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null
$perJob = [int]($OpeningPairs / $Jobs)
$processes = [System.Collections.ArrayList]::new()
$parts = [System.Collections.ArrayList]::new()
for ($index = 0; $index -lt $Jobs; $index++) {
    $part = Join-Path $WorkDir ("part{0:D2}.json" -f $index)
    [void]$parts.Add($part)
    if ((Test-Path -LiteralPath $part) -and -not $Force) { continue }
    $arguments = @(
        $MatchScript,
        "--a-exe", $Engine, "--a-model", $Model,
        "--a-name", "XQ-NNUE-Iter2",
        "--b-exe", $Python, "--b-arg", $Bridge,
        "--b-name", "Tianqi-1.1.8",
        "--openings", $Openings,
        "--opening-start", ($OpeningStart + $index * $perJob),
        "--limit", $perJob,
        "--a-seconds", $XqSecondsPerMove,
        "--b-seconds", $TianqiSecondsPerMove,
        "--max-plies", $MaxPlies,
        "--cpu-index", $index,
        "--output", $part
    )
    $process = Start-Process -FilePath $Python -ArgumentList $arguments `
        -RedirectStandardOutput (Join-Path $WorkDir "part$index.stdout.log") `
        -RedirectStandardError (Join-Path $WorkDir "part$index.stderr.log") `
        -WindowStyle Hidden -PassThru
    [void]$processes.Add($process)
}
if ($processes.Count -gt 0) {
    $processes | Wait-Process
    foreach ($process in $processes) { $process.Refresh() }
    $failed = @($processes | Where-Object { $_.ExitCode -ne 0 })
    if ($failed.Count -gt 0) { throw "Tianqi match shard failure: $($failed.Id -join ',')" }
}

& $Python $MergeScript $Output @parts
if ($LASTEXITCODE -ne 0) { throw "match merge failed" }
$result = Get-Content -Raw -Encoding UTF8 $Output | ConvertFrom-Json
$result | Add-Member -Force NoteProperty protocol ([ordered]@{
    opening_file = "trainnnue/openings_final2_192.fen"
    color_control = "each opening played twice with colors reversed"
    cpu = "both engines pinned to the same logical CPU; parallel pairs use disjoint CPUs"
    threads = 1
    time_control = "fixed movetime per move; actual wall time reported"
    tianqi_version = "Xiangqi Tianqi 1.1.8 64bit SSE4.2"
    tianqi_protocol = "UCI"
    tianqi_book = "disabled"
    tianqi_sha256 = (Get-FileHash $TianqiPath -Algorithm SHA256).Hash
    xq_nnue_sha256 = (Get-FileHash $Model -Algorithm SHA256).Hash
})
[System.IO.File]::WriteAllText(
    $Output, ($result | ConvertTo-Json -Depth 12),
    [System.Text.UTF8Encoding]::new($false))
Write-Host "Tianqi match: $Output"
