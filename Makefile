.PHONY: prebuild lint tests

prebuild: lint tests

lint:
	pipenv run flake8

tests:
	pipenv run pytest tests
