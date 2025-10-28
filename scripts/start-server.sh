#!/bin/sh

python manage.py runserver

exec "$@"