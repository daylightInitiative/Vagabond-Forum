Write-Host "Running Flask App bootstrap"

$env:CONFIG_PATH = "config.json"

# if ($null -eq $anotherVariable) {
#     Write-Host "Venv is not activated... activating..."
    
# } else {
#     Write-Host "anotherVariable is not null."
# }
$env:CONFIG_PATH = "config.json"

# Use WSL to run everything in one shot
pipenv run python -m vagabond.main