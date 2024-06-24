#!/bin/bash
source /home/ubuntu/appBackend/venv/bin/activate
exec gunicorn --workers 3 --bind 0.0.0.0:8000 project_backend.wsgi:application

