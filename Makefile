SHELL := /bin/bash

run:
	source .venv/bin/activate && python3 manage.py runserver

makemigrations:
	source .venv/bin/activate && python3 manage.py makemigrations

migrate:
	source .venv/bin/activate && python3 manage.py migrate

shell:
	source .venv/bin/activate && python3 manage.py shell

createsuperuser:
	source .venv/bin/activate && python3 manage.py createsuperuser