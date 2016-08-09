.PHONY: all build push run devel kill

DOCKER_TAG ?= pavlov/match
ELASTICSEARCH_URL ?=
PORT ?= 8000
ELASTICSEARCH_PORT ?= 59200

all: run

build:
	docker build -t $(DOCKER_TAG) .

push: build
	docker push $(DOCKER_TAG)

run: build
	docker run \
		-e ELASTICSEARCH_URL \
		-p $(PORT):80 \
		-it $(DOCKER_TAG)

devel: build kill
	docker run -d \
	    --name pavlov_elasticsearch \
	    -p $(ELASTICSEARCH_PORT):9200 \
	    elasticsearch
	# Wait until elasticsearch is running
	wget --retry-connrefused --tries=10 -q --wait=1 --spider localhost:$(ELASTICSEARCH_PORT)
	docker run -d \
	    --name pavlov_match \
	    -p $(PORT):80 \
	    --link pavlov_elasticsearch:elasticsearch \
	    pavlov/match

kill:
	-docker kill pavlov_elasticsearch pavlov_match
	-docker rm pavlov_elasticsearch pavlov_match
