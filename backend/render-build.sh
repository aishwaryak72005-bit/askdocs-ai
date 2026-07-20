#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

if [ -f "backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt
fi

if [ -f "manage.py" ]; then
    python manage.py collectstatic --noinput
    python manage.py migrate
elif [ -f "backend/manage.py" ]; then
    python backend/manage.py collectstatic --noinput
    python backend/manage.py migrate
else
    echo "Could not find manage.py!"
    exit 1
fi
