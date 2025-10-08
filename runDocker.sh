#!/bin/bash

cat <<EOF > .env
POSTGRES_USER="admin"
POSTGRES_PASSWORD="root"
POSTGRES_DB="forum"
EOF

sudo docker compose build && sudo docker compose up