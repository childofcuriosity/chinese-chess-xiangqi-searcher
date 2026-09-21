[CmdletBinding()]
param(
    [ValidateRange(1, 64)]
    [int]$Jobs = 12,
    [ValidateRange(1, 192)]
    [int]$OpeningPairs = 192,
    [ValidateRange(0, 191)]
    [int]$OpeningStart = 0,
    [ValidateRange(0.01, 60.0)]
    [double]$XqSecondsPerMove = 0.10,
    [ValidateRange(0.01, 60.0)]
    [double]$PikafishSecondsPerMove = 0.10,
    [ValidateRange(0, 3133)]
    [int]$PikafishElo = 0,
    [ValidateRange(20, 1000)]
    [int]$MaxPlies = 160,
    [string]$Output = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = (Get-Command python -ErrorAction Stop).Source
$Engine = Join-Path $PSScriptRoot "nnue_engine_iteration.exe"
$Model = Join-Path $PSScriptRoot "iter2_nnued3_h16_fromiter1_gpu.nnue"
$Pikafish = Join-Path $Root "pikafish.exe"
$PikafishNetwork = Join-Path $Root "pikafish.nnue"
$Bridge = Join-Path $Root "pikafish_bridge.py"
$Openings = Join-Path $PSScriptRoot "openings_final2_192.fen"
$MatchScript = Join-Path $PSScriptRoot "engine_match.py"
$MergeScript = Join-Path $PSScriptRoot "merge_match_shards.py"
$strength = if ($PikafishElo -eq 0) { "full" } else { "elo$PikafishElo" }
$caseName = "start{0}_pairs{1}_a{2}_b{3}_{4}" -f $OpeningStart, $OpeningPairs,
    ([int][math]::Round($XqSecondsPerMove * 1000)),
    ([int][math]::Round($PikafishSecondsPerMove * 1000)), $strength
$WorkDir = Join-Path $PSScriptRoot ("external_match_shards\" + $caseName)
if (-not $Output) {
    $Output = Join-Path $PSScriptRoot ("external_{0}.json" -f $caseName)
} elseif (-not [System.IO.Path]::IsPathRooted($Output)) {
    $Output = Join-Path $Root $Output
}

if ($OpeningPairs % $Jobs -ne 0) {
    throw "OpeningPairs must be divisible by Jobs"
}
if ($OpeningStart + $OpeningPairs -gt 192) {
    throw "opening slice exceeds the 192-opening suite"
}
if ($PikafishElo -ne 0 -and $PikafishElo -lt 1280) {
    throw "PikafishElo must be 0 (full strength) or 1280..3133"
}
foreach ($path in @($Engine, $Model, $Pikafish, $PikafishNetwork,
                     $Bridge, $Openings, $MatchScript, $MergeScript)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "missing input: $path" }
}

$env:PIKAFISH_PATH = $Pikafish
if ($PikafishElo -eq 0) {
    Remove-Item Env:PIKAFISH_ELO -ErrorAction SilentlyContinue
} else {
    $env:PIKAFISH_ELO = "$PikafishElo"
}
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
        "--a-exe", $Engine,
        "--a-model", $Model,
        "--a-name", "XQ-NNUE-Iter2",
        "--b-exe", $Python,
        "--b-arg", $Bridge,
        "--b-name", $(if ($PikafishElo -eq 0) {
            "Pikafish-2026-01-31-NNUE"
        } else {
            "Pikafish-2026-01-31-Elo$PikafishElo"
        }),
        "--openings", $Openings,
        "--opening-start", ($OpeningStart + $index * $perJob),
        "--limit", $perJob,
        "--seconds", $PikafishSecondsPerMove,
        "--a-seconds", $XqSecondsPerMove,
        "--b-seconds", $PikafishSecondsPerMove,
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
    if ($failed.Count -gt 0) {
        throw "external match shard failure: $($failed.Id -join ',')"
    }
}

& $Python $MergeScript $Output @parts
if ($LASTEXITCODE -ne 0) { throw "match merge failed" }

$result = Get-Content -Raw -Encoding UTF8 $Output | ConvertFrom-Json
$result | Add-Member -Force NoteProperty protocol ([ordered]@{
    opening_file = "trainnnue/openings_final2_192.fen"
    color_control = "each opening played twice with colors reversed"
    cpu = "both engines pinned to the same logical CPU; parallel pairs use disjoint CPUs"
    threads = 1
    time_control = "fixed movetime per move"
    pikafish_version = "Pikafish 2026-01-31"
    pikafish_uci_elo = if ($PikafishElo -eq 0) { "full strength" } else { $PikafishElo }
    pikafish_sha256 = (Get-FileHash $Pikafish -Algorithm SHA256).Hash
    pikafish_nnue_sha256 = (Get-FileHash $PikafishNetwork -Algorithm SHA256).Hash
    xq_nnue_sha256 = (Get-FileHash $Model -Algorithm SHA256).Hash
})
$json = $result | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText($Output, $json, [System.Text.UTF8Encoding]::new($false))
Write-Host "external match: $Output"
