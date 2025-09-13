#!/bin/bash

# this script installs all the packages from the pipenv virtual environment, assuming it is installed
echo Must have 'pipenv' installed, 'pip install pipenv', 'sudo apt install pipenv' or from your package manager!
echo Installing packages...

pipenv install && pipenv run python init_db.py