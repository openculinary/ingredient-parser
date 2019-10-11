SERVICE=$(basename `git rev-parse --show-toplevel`)
COMMIT=$(git rev-parse --short HEAD)

kubectl apply -f k8s
kubectl set image deployments -l app=${SERVICE} ${SERVICE}=registry.gitlab.com/openculinary/${SERVICE}:${COMMIT}
