Write-Host "Running Flask App bootstrap"

$env:CONFIG_PATH = "config.json"

# if ($null -eq $anotherVariable) {
#     Write-Host "Venv is not activated... activating..."
    
# } else {
#     Write-Host "anotherVariable is not null."
# }
$env:CONFIG_PATH = "config.json"

# for normal runs on windows, remove the need to manually start wsl
if ((wsl --list --verbose | Out-String) -match "Stopped") { 
    Write-Host "WSL is currently stopped. Running background process..." -ForegroundColor Cyan 
    
    Start-Process -FilePath "wsl" -ArgumentList "--exec sleep infinity" -NoNewWindow
    
    Start-Sleep -Seconds 3 
}

Write-Host "--- PostgreSQL Status ---" -ForegroundColor Cyan
Write-Host "Waiting for PostgreSQL to start..." -ForegroundColor Cyan

while (-not (Test-NetConnection -ComputerName "localhost" -Port 5432 -InformationAction SilentlyContinue).TcpTestSucceeded) {
    Start-Sleep -Seconds 1
}

Write-Host "PostgreSQL is running" -ForegroundColor Green

# if secrets.env isn't generated then we need to proceed with setup again


wsl systemctl status postgresql
Write-Host "--- Powershell Log Status ---" -ForegroundColor Cyan

# Use WSL to run everything in one shot
pipenv run python -m vagabond.main