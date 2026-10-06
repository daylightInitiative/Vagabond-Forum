
echo "Must have 'pipenv' installed, 'pip install pipenv' or from your package manager!"
echo "Installing packages..."


if ((wsl --list --verbose | Out-String) -match 'Stopped') {
    Write-Host "WSL is currently stopped. Running in the background..." -ForegroundColor Cyan
    # 'dbus-launch true' keeps WSL alive in the background
    wsl --exec dbus-launch true | Out-Null
    Start-Sleep -Seconds 3
}

Write-Host "--- PostgreSQL Status ---" -ForegroundColor Cyan
wsl systemctl status postgresql
Write-Host "--- Powershell Log Status ---" -ForegroundColor Cyan

Write-Host "Purging old secrets.env"
Remove-Item -Path "secrets.env"

# this script installs all the packages from the pipenv virtual environment, assuming it is installed
pipenv install
echo "yes" | pipenv run python -m scripts.wipe_tables
pipenv run python -m scripts.setup_creds
pipenv run python -m scripts.init_db