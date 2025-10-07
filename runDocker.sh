#!/bin/bash

cat <<EOF > .env
POSTGRES_USER="admin"
POSTGRES_PASSWORD="root"
POSTGRES_DB="forum"
POSTFIX_HOSTNAME=$(hostname)
ALLOWED_SENDER_DOMAINS=example.com
POSTFIX_MYNETWORKS="127.0.0.0/8 172.16.0.0/12"
EOF

sudo docker compose build && sudo docker compose up