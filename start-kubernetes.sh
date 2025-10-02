

docker build \
    -f Dockerfile-consumer \
    -t image/experiment-consumer .


cd pods
kubectl apply -f consumer-template.yml
for i in {1..5}
do
echo $i
sleep 1
done

kubectl apply -f producer-template.yml
kubectl logs -f deployment.apps/experiment-consumer



#sed 's/{{TOPIC}}/group5/g' < pods/producer-template.yml | kubectl apply -f -

#kubectl logs -f experiment-consumer