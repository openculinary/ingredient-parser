SERVICE=$(basename `git rev-parse --show-toplevel`)
COMMIT=$(git rev-parse --short HEAD)

for script in k8s/*.yml;
do
        kubectl apply -f ${script}
done;

kubectl set image deployment/${SERVICE}-deployment ${SERVICE}=registry.gitlab.com/openculinary/${SERVICE}:${COMMIT}

