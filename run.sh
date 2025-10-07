#!/bin/bash
echo "Running vagabond forum..."

export CONFIG_PATH="config.json"

echo y | pipenv run python wipe_tables.py

# export PGPASSWORD='root'
# already_initialized=`psql -h 127.0.0.1 -p 5432 -U admin -d forum -c "SELECT EXISTS (SELECT 1 FROM sessions_table WHERE TRUE);"`

# if [ "$already_initialized" = "1" ];
#     echo "Already initialized... wiping tables"
# fi 
pipenv run python init_db.py
mailpit &
pipenv run python -m vagabond.main