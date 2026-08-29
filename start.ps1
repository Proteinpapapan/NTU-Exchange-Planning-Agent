$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path "backend\.env")) {
  Copy-Item "backend\.env.example" "backend\.env"
  Write-Host "Created backend/.env — add your GROQ_API_KEY before chatting."
}

if (-not (Test-Path "backend\.venv")) {
  python -m venv backend\.venv
}
& backend\.venv\Scripts\python -m pip install -r backend\requirements.txt

Set-Location frontend
if (-not (Test-Path "node_modules")) {
  npm install
}
Set-Location $root

Write-Host "Starting API on :8000 and UI on :3000"
Start-Process -FilePath (Join-Path $root "backend\.venv\Scripts\python.exe") -ArgumentList "-m","uvicorn","api.chat:app","--app-dir","src","--port","8000" -WorkingDirectory (Join-Path $root "backend")
Start-Process -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory (Join-Path $root "frontend")
Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"
