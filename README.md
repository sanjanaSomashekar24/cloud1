# cc2023-g5
Working folder

# Commands to run the service:
kubectl apply -f <_.yml>

you need to do this for the files in /pods:

NB! start the consumer.yml file first, then producer

When you are done:
kubectl delete -f <_.yml>

# Important commands
kubectl get pods -> get the currently active pods and the pod_name
kubectl logs -f <'pod_name'> -> get the logs of the pod

How you open a interactive shell for the database:
kubectl run -it mongo-shell --image=mongo:4.0.17 --rm -- /bin/bash

And when you in the shell (mongodb-0 is the name of our database):
mongo mongodb-0.mongodb

db.records.deleteMany({})
db.experiments.deleteMany({})

kubectl scale --replicas 3 deployment.apps/experiment-consumer

kubectl create configmap kafka-auth --from-file=../auth/group5

for updating images:
eval $(minikube docker-env)

kubectl delete -f consumer-template.yml
kubectl delete -f producer-template.yml

#PROMETHEUS
1. Start node exporter: 
wget -O local-setup/node_exporter.tar.gz https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
mkdir local-setup/node-exporter
tar xvfz local-setup/node_exporter.tar.gz --directory local-setup/node-exporter --strip-components=1
./local-setup/node-exporter/node_exporter "--web.listen-address=[0.0.0.0]:9100" &

2. to start prometheus and grafana:
cd local-setup && docker compose up -d && cd -  (call this command from cc2023-g5)

3. Go to the web: 34.251.148.96:3009/login
Password, username: admin, admin
Go to dashboards


#establish container registry at port 5000. This is needed to build api, but not necessary for it to run
docker run -d --rm -it --network=host alpine ash -c "apk add socat && socat TCP-LISTEN:5000,reuseaddr,fork TCP:$(minikube ip):5000"

#establish gateway between openfaas 8080 and machine 8080
kubectl rollout status -n openfaas deploy/gateway
kubectl port-forward -n openfaas svc/gateway 8080:8080 &

#Password required
PASSWORD=$(kubectl get secret -n openfaas basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode; echo)
echo -n $PASSWORD | faas-cli login --username admin --password-stdin
#route incoming traffic from 3005 to 8080
docker run -d --rm -it --network=host alpine ash -c "apk add socat && socat TCP-LISTEN:3005,reuseaddr,fork TCP:127.0.0.1:8080"

#reverse proxy from 3003 to 3005. Change /temperature?data into /function/request-api/temperature?data
docker run     --rm -d     --name nginx-proxy     -v $(pwd)/reverseproxy/conf.d:/etc/nginx/conf.d       --network=host   nginx:alpine


docker build 
docker run -d -p 3003:5000 --network minikube  image/request-api

db.records.find({exp_id : "d6fc2d6d-d9df-4d07-b984-810a5582eab9"})
"http://127.0.0.1:3003/temperature/experiment-id=b574f455-3c4b-416e-990f-ff990c6b479d&start-time=1698857589.776&end-time=1698857605.8"

curl  "http://127.0.0.1:3003/temperature?experiment-id=1682eef4-5302-4c70-9aa8-e422b8d72f68"

#Test locally
curl "http://127.0.0.1:8080/function/request-api/temperature/out-of-range?experiment_id=4d7de6ce-3e2c-44d8-a05a-2c22d8f679da"

#Test externally
curl  "http://34.244.133.228:3003/temperature/out-of-range?experiment_id=4d7de6ce-3e2c-44d8-a05a-2c22d8f679da"

4d10cb73-ef46-4dc7-9c1b-303232f5c301
4d10cb73-ef46-4dc7-9c1b-303232f5c301&start-time=0.0&end-time=1000000000000.0