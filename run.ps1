Write-Host "Running Flask App bootstrap"

$env:CONFIG_PATH = "config.json"

# if ($null -eq $anotherVariable) {
#     Write-Host "Venv is not activated... activating..."
    
# } else {
#     Write-Host "anotherVariable is not null."
# }
$env:CONFIG_PATH = "config.json"

# for normal runs on windows, remove the need to manually start wsl
if ((wsl --list --verbose | Out-String) -match 'Stopped') {
    Write-Host "WSL is currently stopped. Running in the background..." -ForegroundColor Cyan
    # 'dbus-launch true' keeps WSL alive in the background
    wsl --exec dbus-launch true | Out-Null
    Start-Sleep -Seconds 3
}

# if secrets.env isn't generated then we need to proceed with setup again


Write-Host "--- PostgreSQL Status ---" -ForegroundColor Cyan
wsl systemctl status postgresql
Write-Host "--- Powershell Log Status ---" -ForegroundColor Cyan

# Use WSL to run everything in one shot
pipenv run python -m vagabond.main