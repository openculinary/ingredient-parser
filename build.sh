REGISTRY='registry.openculinary.org'
PROJECT='reciperadar'
SERVICE=$(basename `git rev-parse --show-toplevel`)

IMAGE_NAME=${REGISTRY}/${PROJECT}/${SERVICE}
IMAGE_COMMIT=$(git rev-parse --short HEAD)

container=$(buildah from docker.io/library/python:3.8-alpine)
buildah copy ${container} 'web' 'web'
buildah copy ${container} 'Pipfile'
buildah run ${container} -- pip install pipenv --
buildah run ${container} -- pipenv install --
buildah config --port 80 --entrypoint 'pipenv run gunicorn web.app:app --bind :80' ${container}
buildah commit --squash --rm ${container} ${IMAGE_NAME}:${IMAGE_COMMIT}
