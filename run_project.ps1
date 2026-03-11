param(
    [switch]$Dev
)

Write-Host "Using virtual environment Python..." -ForegroundColor Yellow
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$python = $venvPython
if (-not (Test-Path $venvPython)) {
    Write-Warning "Virtual environment not found at $venvPython. Falling back to system Python."
    $python = "python"
}

Write-Host "Starting Smart Healthcare Analytics Server..." -ForegroundColor Green
if ($Dev) {
    Write-Host "Dev mode: enabling --reload." -ForegroundColor Magenta
    & $python .\run_project.py --dev
} else {
    & $python .\run_project.py
}

