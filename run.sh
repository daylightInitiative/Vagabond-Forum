#!/bin/bash
set FLASK_APP = "./vagabond/main.py"

echo "Running Flask App bootstrap"

# Run Flask with pipenv
pipenv run flask --debug run -h 0.0.0.0