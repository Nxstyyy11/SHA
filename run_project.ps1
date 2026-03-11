param(
    [switch]$Dev
)

Write-Host "Using virtual environment Python..." -ForegroundColor Yellow
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found at $venvPython"
    exit 1
}

Write-Host "Cleaning up old processes..." -ForegroundColor Cyan
taskkill /F /IM python.exe 2>$null
Start-Sleep -Seconds 1

Write-Host "Starting Smart Healthcare Analytics Server..." -ForegroundColor Green
cd backend
if ($Dev) {
    Write-Host "Dev mode: enabling --reload." -ForegroundColor Magenta
    & $venvPython -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
} else {
    # Disable reload to avoid Windows named pipe permission errors under this environment.
    & $venvPython -m uvicorn main:app --host 0.0.0.0 --port 8000
}


