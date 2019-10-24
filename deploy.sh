REGISTRY='registry.openculinary.org'
PROJECT='reciperadar'
SERVICE=$(basename `git rev-parse --show-toplevel`)

IMAGE_NAME=${REGISTRY}/${PROJECT}/${SERVICE}
IMAGE_COMMIT=$(git rev-parse --short HEAD)

kubectl apply -f k8s
kubectl set image deployments -l app=${SERVICE} ${SERVICE}=${IMAGE_NAME}:${IMAGE_COMMIT}
