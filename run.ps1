Write-Host "Running Flask App bootstrap"

$env:CONFIG_PATH = "config.json"

# if ($null -eq $anotherVariable) {
#     Write-Host "Venv is not activated... activating..."
    
# } else {
#     Write-Host "anotherVariable is not null."
# }

pipenv run python -m vagabond.main