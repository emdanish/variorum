# Launches both the Variorum backend and frontend, each in its own PowerShell
# window. Run this after editing .env:   powershell -File scripts\start-all.ps1
Write-Host "Launching Variorum backend and frontend..."
Start-Process powershell -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$PSScriptRoot\start-backend.ps1"
)
Start-Process powershell -ArgumentList @(
    "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "$PSScriptRoot\start-frontend.ps1"
)
Write-Host ""
Write-Host "  Backend:  http://localhost:8000/docs"
Write-Host "  Frontend: http://localhost:3000"
Write-Host ""
Write-Host "Two windows opened. Close them to stop the servers."
