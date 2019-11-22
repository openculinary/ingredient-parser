.PHONY: prebuild lint tests

prebuild: lint tests

lint:
	flake8

tests:
	pytest tests
