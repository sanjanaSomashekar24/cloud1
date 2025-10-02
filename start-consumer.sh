

docker build -t image/consumer -f Dockerfile-consumer .

docker run \
	    --rm \
		-d \
		--name consumer \
		-v "$(pwd)/auth":/app/auth \
		image/consumer consumer.py "group5"
