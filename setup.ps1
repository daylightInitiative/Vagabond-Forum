
echo "Must have 'pipenv' installed, 'pip install pipenv' or from your package manager!"
echo "Installing packages..."
# this script installs all the packages from the pipenv virtual environment, assuming it is installed
pipenv install && pipenv run python init_db.py