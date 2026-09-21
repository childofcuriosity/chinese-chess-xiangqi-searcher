[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateRange(1, 99)]
    [int]$Round,

    [Parameter(Mandatory = $true)]
    [string]$TeacherModel,

    [string]$InitModel = $TeacherModel,
    [string]$TeacherName = "",
    [int]$Seed = 130001,
    [int]$GameIdBase = 1000000,
    [ValidateRange(0, 64)]
    [int]$GenerateJobs = 0,
    [ValidateRange(100, 10000)]
    [int]$GamesPerShard = 2250,
    [ValidateRange(1, 24)]
    [int]$MatchJobs = 6,
    [ValidateRange(1, 10)]
    [int]$Depth = 3,
    [double]$SecondsPerMove = 0.1,
    [int]$OpeningPairs = 192,
    [switch]$ForceTrain,
    [switch]$ForcePstMatch
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv-gpu\python.exe"
$Gxx = (Get-Command g++ -ErrorAction Stop).Source
$TeacherModel = (Resolve-Path $TeacherModel).Path
$InitModel = (Resolve-Path $InitModel).Path
$Openings = Join-Path $PSScriptRoot "openings_final2_192.fen"
$ShardDir = Join-Path $PSScriptRoot ("d3iter{0}_shards" -f $Round)
$MatchDir = Join-Path $PSScriptRoot ("iter{0}_matches" -f $Round)
$Dataset = Join-Path $PSScriptRoot ("train_iter{0}_nnue_d3_balanced_1m_v2.bin" -f $Round)
$Model = Join-Path $PSScriptRoot (
    "iter{0}_nnued3_h16_fromiter{1}_gpu.nnue" -f $Round, ($Round - 1))
$TrainLog = "$Model.train.log"
$VsPrevious = Join-Path $PSScriptRoot ("iter{0}_vs_iter{1}_192pairs.json" -f $Round, ($Round - 1))
$VsPst = Join-Path $PSScriptRoot ("iter{0}_vs_pst_192pairs.json" -f $Round)

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python 3.12 GPU environment not found: $Python"
}
if (-not $TeacherName) {
    $TeacherName = "Iter$($Round - 1)-NNUE-D3"
}
if ($OpeningPairs % $MatchJobs -ne 0) {
    throw "OpeningPairs must be divisible by MatchJobs"
}
if ($GenerateJobs -eq 0) {
    $GenerateJobs = [Environment]::ProcessorCount
}

New-Item -ItemType Directory -Force -Path $ShardDir, $MatchDir | Out-Null

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed with exit code $LASTEXITCODE"
    }
}

function Wait-Checked {
    param([System.Collections.ArrayList]$Processes, [string]$Stage)
    if ($Processes.Count -eq 0) { return }
    $Processes | Wait-Process
    foreach ($process in $Processes) { $process.Refresh() }
    $failed = @($Processes | Where-Object { $_.ExitCode -ne 0 })
    if ($failed.Count -gt 0) {
        throw "$Stage failed in process(es): $($failed.Id -join ',')"
    }
}

function Compile-Tools {
    $targets = @(
        @("nnue_engine.cpp", "nnue_engine_iteration.exe"),
        @("generate_data.cpp", "generate_data_iteration.exe"),
        @("augment_pst.cpp", "augment_pst_iteration.exe"),
        @("validate_quant.cpp", "validate_quant_iteration.exe"),
        @("verify_nnue.cpp", "verify_nnue_iteration.exe"),
        # teacher.cpp without XQ_LABEL_TEACHER is the production PST search,
        # with the nodes/depth diagnostics consumed by engine_match.py.
        @("teacher.cpp", "pst_iteration.exe")
    )
    foreach ($target in $targets) {
        $source = Join-Path $PSScriptRoot $target[0]
        $output = Join-Path $PSScriptRoot $target[1]
        Invoke-Checked $Gxx @("-std=c++17", "-O3", "-DNDEBUG", "-march=native", $source, "-o", $output)
    }
}

function Test-RawShardComplete {
    param([string]$Log, [int]$Games)
    if (-not (Test-Path -LiteralPath $Log)) { return $false }
    $last = Get-Content -LiteralPath $Log -Tail 1
    return $last -match ("games={0}/{0}" -f $Games)
}

function Generate-OneShard {
    param([string]$Stem, [int]$Games, [int]$ShardSeed, [int]$GameOffset, [int]$Cpu)
    if ($Stem -match '^shard_(\d+)$') {
        $suffix = $Matches[1]
        $raw = Join-Path $ShardDir "raw_$suffix.bin"
        $stdout = Join-Path $ShardDir "shard_$suffix.stdout.log"
        $stderr = Join-Path $ShardDir "shard_$suffix.stderr.log"
    } else {
        $raw = Join-Path $ShardDir "$Stem.raw.bin"
        $stdout = Join-Path $ShardDir "$Stem.generate.stdout.log"
        $stderr = Join-Path $ShardDir "$Stem.generate.stderr.log"
    }
    if (Test-RawShardComplete $stderr $Games) { return $null }
    $generator = Join-Path $PSScriptRoot "generate_data_iteration.exe"
    $arguments = @(
        $raw, $Games, $Depth, $ShardSeed, 120, 2, 6, 1, $GameOffset,
        "--teacher", "nnue", "--nnue", $TeacherModel
    )
    $process = Start-Process -FilePath $generator -ArgumentList $arguments `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
        -WindowStyle Hidden -PassThru
    try { $process.ProcessorAffinity = [intptr](1 -shl $Cpu) } catch {}
    return $process
}

function Augment-AllShards {
    $augmenter = Join-Path $PSScriptRoot "augment_pst_iteration.exe"
    $processes = [System.Collections.ArrayList]::new()
    $rawFiles = @(
        Get-ChildItem -LiteralPath $ShardDir -Filter "raw_*.bin"
        Get-ChildItem -LiteralPath $ShardDir -Filter "*.raw.bin"
    ) | Sort-Object FullName -Unique
    $index = 0
    foreach ($raw in $rawFiles) {
        if ($raw.Name -match '^raw_(\d+)\.bin$') {
            $suffix = $Matches[1]
            $v2 = Join-Path $ShardDir "v2_$suffix.bin"
            $stderr = Join-Path $ShardDir "augment_$suffix.stderr.log"
            $stdout = Join-Path $ShardDir "augment_$suffix.stdout.log"
        } else {
            $v2 = $raw.FullName -replace '\.raw\.bin$', '.v2.bin'
            $stderr = $raw.FullName -replace '\.raw\.bin$', '.augment.stderr.log'
            $stdout = $raw.FullName -replace '\.raw\.bin$', '.augment.stdout.log'
        }
        if ((Test-Path -LiteralPath $v2) -and (Test-Path -LiteralPath $stderr) -and
            ((Get-Content -LiteralPath $stderr -Tail 1) -match '^augmented records=')) {
            $index++
            continue
        }
        $process = Start-Process -FilePath $augmenter -ArgumentList @($raw.FullName, $v2) `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
            -WindowStyle Hidden -PassThru
        try { $process.ProcessorAffinity = [intptr](1 -shl ($index % $GenerateJobs)) } catch {}
        [void]$processes.Add($process)
        $index++
    }
    Wait-Checked $processes "PST augmentation"
}

function Build-Dataset {
    $builder = Join-Path $PSScriptRoot "build_balanced_dataset.py"
    for ($attempt = 0; $attempt -le 8; $attempt++) {
        $inputs = @(
            Get-ChildItem -LiteralPath $ShardDir -Filter "v2_*.bin"
            Get-ChildItem -LiteralPath $ShardDir -Filter "*.v2.bin"
        ) | Sort-Object FullName -Unique | ForEach-Object { $_.FullName }
        & $Python $builder $Dataset @inputs --per-side 500000 --seed ($Seed + 2)
        if ($LASTEXITCODE -eq 0) { return }
        if ($attempt -eq 8) { throw "dataset remained short after eight top-up shards" }
        $stem = "topup_{0:D2}" -f $attempt
        $games = 500
        $offset = $GameIdBase + $GenerateJobs * $GamesPerShard + $attempt * $games
        $process = Generate-OneShard $stem $games ($Seed + 50000 + $attempt * 1019) $offset 0
        if ($null -ne $process) {
            $list = [System.Collections.ArrayList]::new()
            [void]$list.Add($process)
            Wait-Checked $list "top-up generation"
        }
        Augment-AllShards
    }
}

function Run-Matches {
    $engine = Join-Path $PSScriptRoot "nnue_engine_iteration.exe"
    $pst = Join-Path $PSScriptRoot "pst_iteration.exe"
    $matchScript = Join-Path $PSScriptRoot "engine_match.py"
    $perJob = [int]($OpeningPairs / $MatchJobs)
    $processes = [System.Collections.ArrayList]::new()
    for ($index = 0; $index -lt $MatchJobs; $index++) {
        $start = $index * $perJob
        $out = Join-Path $MatchDir ("vs_previous_part{0}.json" -f $index)
        if (-not (Test-Path -LiteralPath $out)) {
            $args = @(
                $matchScript, "--a-exe", $engine, "--a-model", $Model,
                "--b-exe", $engine, "--b-model", $TeacherModel,
                "--a-name", "Iter$Round-NNUE-D3", "--b-name", $TeacherName,
                "--openings", $Openings, "--opening-start", $start,
                "--limit", $perJob, "--seconds", $SecondsPerMove,
                "--max-plies", 160, "--cpu-index", $index, "--output", $out
            )
            $p = Start-Process -FilePath $Python -ArgumentList $args `
                -RedirectStandardOutput (Join-Path $MatchDir "vs_previous_part$index.stdout.log") `
                -RedirectStandardError (Join-Path $MatchDir "vs_previous_part$index.stderr.log") `
                -WindowStyle Hidden -PassThru
            [void]$processes.Add($p)
        }
        $out = Join-Path $MatchDir ("vs_pst_part{0}.json" -f $index)
        if ($ForcePstMatch -or -not (Test-Path -LiteralPath $out)) {
            $cpu = $index + $MatchJobs
            $args = @(
                $matchScript, "--a-exe", $engine, "--a-model", $Model,
                "--b-exe", $pst, "--a-name", "Iter$Round-NNUE-D3", "--b-name", "PST",
                "--openings", $Openings, "--opening-start", $start,
                "--limit", $perJob, "--seconds", $SecondsPerMove,
                "--max-plies", 160, "--cpu-index", $cpu, "--output", $out
            )
            $p = Start-Process -FilePath $Python -ArgumentList $args `
                -RedirectStandardOutput (Join-Path $MatchDir "vs_pst_part$index.stdout.log") `
                -RedirectStandardError (Join-Path $MatchDir "vs_pst_part$index.stderr.log") `
                -WindowStyle Hidden -PassThru
            [void]$processes.Add($p)
        }
    }
    Wait-Checked $processes "paired matches"
    $merger = Join-Path $PSScriptRoot "merge_match_shards.py"
    $previousParts = @(Get-ChildItem -LiteralPath $MatchDir -Filter "vs_previous_part*.json" |
        Sort-Object Name | ForEach-Object { $_.FullName })
    $pstParts = @(Get-ChildItem -LiteralPath $MatchDir -Filter "vs_pst_part*.json" |
        Sort-Object Name | ForEach-Object { $_.FullName })
    $previousMergeArgs = @($merger, $VsPrevious) + $previousParts
    $pstMergeArgs = @($merger, $VsPst) + $pstParts
    Invoke-Checked $Python $previousMergeArgs
    Invoke-Checked $Python $pstMergeArgs
}

Write-Host "[1/7] compile reproducible tools"
Compile-Tools

Write-Host "[2/7] generate NNUE+D$Depth labels on $GenerateJobs CPU cores"
$generation = [System.Collections.ArrayList]::new()
for ($index = 0; $index -lt $GenerateJobs; $index++) {
    $stem = "shard_{0:D2}" -f $index
    $process = Generate-OneShard $stem $GamesPerShard `
        ($Seed + $index * 1013) ($GameIdBase + $index * $GamesPerShard) $index
    if ($null -ne $process) { [void]$generation.Add($process) }
}
Wait-Checked $generation "label generation"

Write-Host "[3/7] augment PST values and build balanced deduplicated dataset"
Augment-AllShards
Build-Dataset

Write-Host "[4/7] independently calibrate K and train H16 on CUDA"
if ($ForceTrain -or -not ((Test-Path -LiteralPath $Model) -and (Test-Path -LiteralPath "$Model.json"))) {
    $train = Join-Path $PSScriptRoot "train.py"
    & $Python $train $Dataset --output $Model --width 16 --hidden 0 `
        --activation crelu --phase-heads --epochs 150 --batch-size 8192 `
        --learning-rate 0.003 --lambda 0.95 --seed ($Seed + 6) --residual `
        --delta-weight 0.25 --delta-clip 250 --delta-beta 25 --device cuda `
        --init-nnue $InitModel --early-stop-patience 15 `
        --early-stop-min-delta 0.00001 --min-epochs 25 2>&1 |
        Tee-Object -FilePath $TrainLog
    if ($LASTEXITCODE -ne 0) { throw "training failed with exit code $LASTEXITCODE" }
}

Write-Host "[5/7] validate quantization and incremental accumulators"
Invoke-Checked (Join-Path $PSScriptRoot "validate_quant_iteration.exe") @($Model, $Dataset, 30000)
Invoke-Checked (Join-Path $PSScriptRoot "verify_nnue_iteration.exe") @($Model)

Write-Host "[6/7] play paired equal-time matches against previous model and PST"
Run-Matches

Write-Host "[7/7] done"
Write-Host "dataset: $Dataset"
Write-Host "model:   $Model"
Write-Host "match:   $VsPrevious"
Write-Host "match:   $VsPst"
