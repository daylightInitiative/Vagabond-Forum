#!/bin/bash
set FLASK_APP = "./vagabond/main.py"

echo "Running Flask App bootstrap"

# Run Flask with pipenv
pipenv run python -m vagabond.main