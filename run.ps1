Write-Host "Running Flask App bootstrap"

# $venv_activated = Get-ChildItem Env:VIRTUAL_ENV

# if ($null -eq $anotherVariable) {
#     Write-Host "Venv is not activated... activating..."
    
# } else {
#     Write-Host "anotherVariable is not null."
# }

pipenv run python -m vagabond.main