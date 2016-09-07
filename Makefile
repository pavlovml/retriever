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

devel: build
	docker-compose up -d

kill:
	docker-compose down
