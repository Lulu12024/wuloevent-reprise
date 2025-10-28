#!/bin/bash

# Stop execution if we have an error
set -e

# Try to connect to PostgreSQL
until PGPASSWORD="wuloevents_pw#&@!" psql -h "wuloevents.db" -U "wuloevents" -d "wuloevents_db" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing command"

# Execute given other parameters (commands)
exec "$@"