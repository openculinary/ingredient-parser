.PHONY: build deploy image lint tests

SERVICE=$(shell basename $(shell git rev-parse --show-toplevel))
REGISTRY=registry.openculinary.org
PROJECT=reciperadar

IMAGE_NAME=${REGISTRY}/${PROJECT}/${SERVICE}
IMAGE_COMMIT := $(shell git rev-parse --short HEAD)
IMAGE_TAG := $(strip $(if $(shell git status --porcelain --untracked-files=no), latest, ${IMAGE_COMMIT}))

build: image

deploy:
	kubectl apply -f k8s
	kubectl set image deployments -l app=${SERVICE} ${SERVICE}=${IMAGE_NAME}:${IMAGE_TAG}

image:
	$(eval container=$(shell buildah from docker.io/library/python:3.10-slim))
	buildah copy $(container) 'web' 'web'
	buildah copy $(container) 'requirements.txt'
	buildah run $(container) -- useradd --home-dir /srv/ --no-create-home gunicorn --shell /sbin/nologin --
	buildah run $(container) -- chown gunicorn /srv/ --
	buildah run --user gunicorn $(container) -- pip install --no-deps --no-warn-script-location --progress-bar off --requirement requirements.txt --user --
	# Begin: HACK: For rootless compatibility across podman and k8s environments, unset file ownership and grant read+exec to binaries
	buildah run $(container) -- chown -R nobody:nogroup /srv/ --
	buildah run $(container) -- chmod -R a+rx /srv/.local/bin/ --
	buildah run $(container) -- find /srv/ -type d -exec chmod a+rx {} \;
	# End: HACK
	buildah config --cmd '/srv/.local/bin/gunicorn web.app:app --bind :8000' --port 8000 --user gunicorn $(container)
	buildah commit --quiet --rm --squash $(container) ${IMAGE_NAME}:${IMAGE_TAG}

# Virtualenv Makefile pattern derived from https://github.com/bottlepy/bottle/
venv: venv/.installed requirements.txt requirements-dev.txt
	venv/bin/pip install --requirement requirements-dev.txt --quiet
	touch venv
venv/.installed:
	python3 -m venv venv
	venv/bin/pip install pip-tools
	touch venv/.installed

requirements.txt: requirements.in
	venv/bin/pip-compile --allow-unsafe --generate-hashes --no-header --quiet --resolver backtracking requirements.in

requirements-dev.txt: requirements.txt requirements-dev.in
	venv/bin/pip-compile --allow-unsafe --generate-hashes --no-header --quiet --resolver backtracking requirements-dev.in

lint: venv
	venv/bin/black --check --quiet tests
	venv/bin/black --check --quiet web
	venv/bin/flake8 tests
	venv/bin/flake8 web

tests: venv
	venv/bin/pytest tests
