[CmdletBinding()]
param(
    [ValidateRange(2, 99)]
    [int]$StartRound = 4,
    [Parameter(Mandatory = $true)]
    [string]$StartTeacherModel,
    [ValidateRange(2, 99)]
    [int]$MaxRound = 12,
    [int]$SeedBase = 150001,
    [int]$GameIdBase = 1000000,
    [ValidateRange(1, 64)]
    [int]$GenerateJobs = 12,
    [ValidateRange(1, 24)]
    [int]$MatchJobs = 6,
    [double]$MaxHours = 6.0
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$SingleIteration = Join-Path $PSScriptRoot "run_teacher_iteration.ps1"
$SummaryPath = Join-Path $PSScriptRoot "iteration_until_regression.local.json"
$teacherModel = (Resolve-Path $StartTeacherModel).Path
$previousRound = $StartRound - 1
$previousPstPath = Join-Path $PSScriptRoot (
    "iter{0}_vs_pst_192pairs.json" -f $previousRound)
if (-not (Test-Path -LiteralPath $previousPstPath)) {
    throw "previous PST match missing: $previousPstPath"
}
$previousPstScore = (Get-Content -Raw -LiteralPath $previousPstPath |
    ConvertFrom-Json).a_score_percent
$started = Get-Date
$history = [System.Collections.ArrayList]::new()

for ($round = $StartRound; $round -le $MaxRound; $round++) {
    if (((Get-Date) - $started).TotalHours -ge $MaxHours) {
        Write-Warning "time box reached before observing regression"
        break
    }
    $seed = $SeedBase + ($round - $StartRound) * 20000
    $gameOffset = $GameIdBase + ($round - $StartRound) * 100000
    $teacherName = "Iter$($round - 1)-NNUE-D3"
    Write-Host "=== iteration $round; teacher=$teacherName; prior PST=$previousPstScore% ==="
    & $SingleIteration -Round $round -TeacherModel $teacherModel `
        -InitModel $teacherModel -TeacherName $teacherName -Seed $seed `
        -GameIdBase $gameOffset -GenerateJobs $GenerateJobs -GamesPerShard 2250 `
        -MatchJobs $MatchJobs
    if ($LASTEXITCODE -ne 0) {
        throw "iteration $round failed with exit code $LASTEXITCODE"
    }

    $headPath = Join-Path $PSScriptRoot (
        "iter{0}_vs_iter{1}_192pairs.json" -f $round, ($round - 1))
    $pstPath = Join-Path $PSScriptRoot ("iter{0}_vs_pst_192pairs.json" -f $round)
    $head = Get-Content -Raw -LiteralPath $headPath | ConvertFrom-Json
    $pst = Get-Content -Raw -LiteralPath $pstPath | ConvertFrom-Json
    $model = Join-Path $PSScriptRoot (
        "iter{0}_nnued3_h16_fromiter{1}_gpu.nnue" -f $round, ($round - 1))
    $metadata = Get-Content -Raw -LiteralPath "$model.json" | ConvertFrom-Json
    $bestValidation = ($metadata.history |
        Measure-Object -Property validation_objective -Minimum).Minimum
    $record = [ordered]@{
        round = $round
        model = Split-Path -Leaf $model
        best_validation_objective = $bestValidation
        versus_previous_percent = $head.a_score_percent
        versus_previous_ci95_percent = $head.a_ci95_percent
        versus_pst_percent = $pst.a_score_percent
        versus_pst_ci95_percent = $pst.a_ci95_percent
        previous_pst_percent = $previousPstScore
        regression = (($head.a_score_percent -lt 50.0) -or
                      ($pst.a_score_percent -lt $previousPstScore))
    }
    [void]$history.Add([pscustomobject]$record)
    [ordered]@{
        stop_rule = "first point regression: vs previous < 50% or vs PST below prior round"
        started_at = $started.ToString("o")
        updated_at = (Get-Date).ToString("o")
        rounds = $history
    } | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 -LiteralPath $SummaryPath

    Write-Host ("round {0}: previous={1:F2}% PST={2:F2}% (prior {3:F2}%)" -f `
        $round, $head.a_score_percent, $pst.a_score_percent, $previousPstScore)
    if ($record.regression) {
        Write-Host "regression observed; stop at round $round"
        break
    }
    $teacherModel = $model
    $previousPstScore = $pst.a_score_percent
}

Write-Host "loop summary: $SummaryPath"
