# MEH screen launcher: one brief, one GPU job, then verify the top candidates.
#
# Usage:
#   .\tools\meh\run_screen.ps1 -Tag t2 -Config examples\typologies\meh_2026-10-30\meh_t2a_search.yaml -Budget 40
#
# It clears stray solver hosts, runs the CMA screen, finds the run directory it created, and re-solves the
# top N at verify fidelity. Logs land in runs\nights\meh_<tag>_<mode>.log; one summary line goes to stdout
# and to runs\nights\meh_<tag>_summary.txt. Assumes the repo venv at .venv (see docs/meh/MEH_QUICKSTART.md).

param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$Config,
    [int]$Budget = 40,
    [ValidateSet("screen", "verify", "final")][string]$Mode = "screen",
    [int]$Top = 2
)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repo
$exe = Join-Path $repo ".venv\Scripts\hornlab-search.exe"
if (-not (Test-Path $exe)) { throw "no venv at $repo\.venv - see docs/meh/MEH_QUICKSTART.md" }
$logdir = Join-Path $repo "runs\nights"
New-Item -ItemType Directory -Force -Path $logdir | Out-Null
$summary = Join-Path $logdir ("meh_" + $Tag + "_summary.txt")

function Newest-ScreenRun {
    Get-ChildItem (Join-Path $repo "runs") -Directory |
        Where-Object { $_.Name -match "-screen-" } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
}

# one GPU job at a time: clear stale hosts before anything starts (CLAUDE.md GPU hygiene)
& $exe gpu-clean 2>&1 | Out-Null

$before = (Newest-ScreenRun).Name
$log = Join-Path $logdir ("meh_" + $Tag + "_" + $Mode + ".log")
"=== $Tag $Mode start $(Get-Date -Format o) config=$Config budget=$Budget" | Out-File -Encoding utf8 $log

& $exe search --config $Config --budget $Budget --mode $Mode *>&1 | Tee-Object -FilePath $log -Append
$code = $LASTEXITCODE
$run = Newest-ScreenRun
$line = "search tag=$Tag mode=$Mode exit=$code"
if ($run -and $run.Name -ne $before) {
    $line += " run=$($run.Name)"
    $best = Join-Path $run.FullName "best.json"
    if (Test-Path $best) {
        $b = Get-Content $best -Raw | ConvertFrom-Json
        $line += " best=$($b.design_hash) J=$($b.objective)"
    }
    $vlog = Join-Path $logdir ("meh_" + $Tag + "_verify.log")
    "=== $Tag verify run=$($run.Name) $(Get-Date -Format o)" | Out-File -Encoding utf8 $vlog
    & $exe verify --run $run.FullName --top $Top *>&1 | Tee-Object -FilePath $vlog -Append
    $line += " verify_exit=$LASTEXITCODE verify_log=$vlog"
}
else {
    $line += " NO_NEW_RUN (before=$before)"
}
$line | Tee-Object -FilePath $summary -Append
