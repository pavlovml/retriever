.PHONY: all build push run dev

DOCKER_TAG ?= dsys/match:latest

export PORT ?= 8888
export ELASTICSEARCH_URL ?= elasticsearch:9200
export ELASTICSEARCH_INDEX ?= images
export ELASTICSEARCH_DOC_TYPE ?= images
export DISTANCE_CUTOFF ?= 0.45

all: run

build:
	docker build -t $(DOCKER_TAG) .

push: build
	docker push $(DOCKER_TAG)

run: build
	docker run \
		-e PORT \
		-e ELASTICSEARCH_URL \
		-e ELASTICSEARCH_INDEX \
		-e ELASTICSEARCH_DOC_TYPE \
		-e DISTANCE_CUTOFF \
		-p $(PORT):$(PORT) \
		-it $(DOCKER_TAG)

dev: build
	docker-compose up
