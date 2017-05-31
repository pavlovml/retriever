<p align="center"><img src="https://raw.githubusercontent.com/pavlovml/match/master/resources/logo.png" alt="logo" width="220" /></p>

<p align="center"><strong>Scalable reverse image search</strong><br /><em>built on <a href="http://kubernetes.io/">Kubernetes</a> and <a href="https://www.elastic.co/">Elasticsearch</a></em></p>

<p align="center"><a href="https://github.com/pavlovml/match/stargazers"><img src="https://img.shields.io/github/stars/pavlovml/match.svg?style=flat" alt="GitHub stars" /></a> <a href="https://hub.docker.com/r/pavlov/match/"><img src="https://img.shields.io/docker/pulls/pavlov/match.svg" alt="Docker Pulls" /></a> <a href="http://kubernetes.io"><img src="https://img.shields.io/badge/kubernetes-ready-brightgreen.svg?style=flat" alt="Kubernetes shield" /></a> <a href="https://app.fossa.io/projects/git%2Bhttps%3A%2F%2Fgithub.com%2Fpavlovai%2Fmatch?ref=badge_shield" alt="FOSSA Status"><img src="https://app.fossa.io/api/projects/git%2Bhttps%3A%2F%2Fgithub.com%2Fpavlovai%2Fmatch.svg?type=shield"/></a></p>

**Pavlov Match** makes it easy to search for images that look similar to each other. Using a state-of-the-art perceptual hash, it is invariant to scaling and 90 degree rotations. Its HTTP API is quick to integrate and flexible for a number of reverse image search applications. Kubernetes and Elasticsearch allow Match to scale to billions of images with ease while giving you full control over where your data is stored. Match uses the awesome [ascribe/image-match](https://github.com/ascribe/image-match) under the hood for most of the image search legwork.

1. [Getting Started](#getting-started)
  * [Setting up Elasticsearch](#setting-up-elasticsearch)
  * [One-command deployment with spread](#one-command-deployment-with-spread)
  * [Using in your own Kubernetes cluster](#using-in-your-own-kubernetes-cluster)
2. [API](#api)
3. [Development](#development)
4. [License and Acknowledgements](#license-and-acknowledgements)

## Getting Started

If you already have ElasticSearch running:
```
$ docker run -e ELASTICSEARCH_URL=https://daisy.us-west-1.es.amazonaws.com -it pavlov/match
```

If you want to run ElasticSearch in another docker container and link it to our `pavlov/match` container (use the `-p` option to export the ports from the containers to the host):
```
$ docker run --name my_elasticsearch_db -p 59200:9200 elasticsearch
$ docker run --link my_elasticsearch_db:elasticsearch -p 8888:80 pavlov/match
```

or, if you have [`docker-compose`](https://docs.docker.com/compose/) installed on your system, type:
```
$ docker-compose up
```

(All the commands can be run using `make`. Take a look to the `Makefile` to check the options.)

Match is packaged as a Docker container ([pavlov/match](https://hub.docker.com/r/pavlov/match/) on Docker Hub), making it highly portable and scalable to billions of images. You can configure a few options using environment variables:

* **ELASTICSEARCH_URL** *(default: `http://elasticsearch`)*

  A URL pointing to the Elasticsearch database where image signatures are to be stored. If you don't want to host your own Elasticsearch cluster, consider using [AWS Elasticsearch Service](https://aws.amazon.com/elasticsearch-service/). That's what we use.
  Note: in order to allow containers linking, the default value is set to `http://elasticsearch`

* **ELASTICSEARCH_INDEX** *(default: images)*

  The index in the Elasticsearch database where image signatures are to be stored.

* **ELASTICSEARCH_DOC_TYPE** *(default: images)*

  The doc type used for storing image signatures.

* **WORKER_COUNT** *(default: 4)*

  The number of gunicorn worker forks to maintain in each Docker container.


### One-command deployment with spread

Match is particularly awesomesauce when integrated into the Kubernetes container orchestration architecture. [`spread`](https://github.com/redspread/spread) makes it easy to get Match up and running quickly:

    $ go get rsprd.com/spread/cmd/spread
    $ git clone https://github.com/pavlovml/match
    $ vim .k2e/secret.yml # configure me
    $ spread deploy .

### Using in your own Kubernetes cluster

You can configure the service, replication controller, and secret like so:

```yaml
# match-service.yml
apiVersion: v1
kind: Service
metadata:
  namespace: default
  name: match
spec:
  ports:
  - name: http
    port: 80
    protocol: TCP
  selector:
    app: match
```

```yaml
# match-rc.yml
apiVersion: v1
kind: ReplicationController
metadata:
  namespace: default
  name: match
spec:
  replicas: 2
  selector:
    app: match
  template:
    metadata:
      labels:
        app: match
    spec:
      containers:
      - name: match
        image: pavlov/match:latest
        ports:
        - containerPort: 80
        env:
        - name: WORKER_COUNT
          valueFrom:
            secretKeyRef:
              name: match
              key: worker-count
        - name: ELASTICSEARCH_URL
          valueFrom:
            secretKeyRef:
              name: match
              key: elasticsearch.url
        - name: ELASTICSEARCH_INDEX
          valueFrom:
            secretKeyRef:
              name: match
              key: elasticsearch.index
        - name: ELASTICSEARCH_DOC_TYPE
          valueFrom:
            secretKeyRef:
              name: match
              key: elasticsearch.doc-type
```

```yaml
# match-secret.yml
apiVersion: v1
kind: Secret
metadata:
  namespace: default
  name: match
data:
  # 4, base64 encoded
  worker-count: NA==

  # https://daisy.us-west-1.es.amazonaws.com (change me)
  elasticsearch.url: aHR0cHM6Ly9kYWlzeS51cy13ZXN0LTEuZXMuYW1hem9uYXdzLmNvbQ==

  # images
  elasticsearch.index: aW1hZ2Vz

  # images
  elasticsearch.doc-type: aW1hZ2Vz
```

## API

Match has a simple HTTP API. All request parameters are specified via `application/x-www-form-urlencoded` or `multipart/form-data`.

* [POST `/add`](#post-add)
* [DELETE `/delete`](#delete-delete)
* [POST `/search`](#post-search)
* [POST `/compare`](#post-compare)
* [GET `/count`](#get-count)
* [GET `/list`](#get-list)
* [GET `/ping`](#get-ping)

---

### POST `/add`

Adds an image signature to the database.

#### Parameters

* **url** or **image** *(required)*

  The image to add to the database. It may be provided as a URL via `url` or as a `multipart/form-data` file upload via `image`.

* **filepath** *(required)*

  The path to save the image to in the database. If another image already exists at the given path, it will be overwritten.

* **metadata** *(default: None)*

  An arbitrary JSON object featuring meta data to attach to the image.

#### Example Response

```json
{
  "status": "ok",
  "error": [],
  "method": "add",
  "result": []
}
```

---

### DELETE `/delete`

Deletes an image signature from the database.

#### Parameters

* **filepath** *(required)*

  The path of the image signature in the database.

#### Example Response

```json
{
  "status": "ok",
  "error": [],
  "method": "delete",
  "result": []
}
```

---

### POST `/search`

Searches for a similar image in the database. Scores range from 0 to 100, with 100 being a perfect match.

#### Parameters

* **url** or **image** *(required)*

  The image to add to the database. It may be provided as a URL via `url` or as a `multipart/form-data` file upload via `image`.

* **all_orientations** *(default: true)*

  Whether or not to search for similar 90 degree rotations of the image.

#### Example Response

```json
{
  "status": "ok",
  "error": [],
  "method": "search",
  "result": [
    {
      "score": 99.0,
      "filepath": "http://static.wixstatic.com/media/0149b5_345c8f862e914a80bcfcc98fcd432e97.jpg_srz_614_709_85_22_0.50_1.20_0.00_jpg_srz"
    }
  ]
}
```

---

### POST `/compare`

Compares two images, returning a score for their similarity. Scores range from 0 to 100, with 100 being a perfect match.

#### Parameters

* **url1** or **image1**, **url2** or **image2** *(required)*

  The images to compare. They may be provided as a URL via `url1`/`url2` or as a `multipart/form-data` file upload via `image1`/`image2`.

#### Example Response

```json
{
  "status": "ok",
  "error": [],
  "method": "compare",
  "result": [
    {
      "score": 99.0
    }
  ]
}
```

---

### GET `/count`

Count the number of image signatures in the database.

#### Example Response

```json
{
  "status": "ok",
  "error": [],
  "method": "list",
  "result": [420]
}
```

---

### GET `/list`

Lists the file paths for the image signatures in the database.

#### Parameters

* **offset** *(default: 0)*

  The location in the database to begin listing image paths.

* **limit** *(default: 20)*

  The number of image paths to retrieve.

#### Example Response

```json
{
  "status": "ok",
  "error": [],
  "method": "list",
  "result": [
    "http://img.youtube.com/vi/iqPqylKy-bY/0.jpg",
    "https://i.ytimg.com/vi/zbjIwBggt2k/hqdefault.jpg",
    "https://s-media-cache-ak0.pinimg.com/736x/3d/67/6d/3d676d3f7f3031c9fd91c10b17d56afe.jpg"
  ]
}
```

---

### GET `/ping`

Check for the health of the server.

#### Example Response

```json
{
  "status": "ok",
  "error": [],
  "method": "ping",
  "result": []
}
```

## Development

    $ export ELASTICSEARCH_URL=https://daisy.us-west-1.es.amazonaws.com
    $ make build
    $ make run
    $ make push

## License and Acknowledgements

Match is based on [ascribe/image-match](https://github.com/ascribe/image-match), which is in turn based on the paper [_An image signature for any kind of image_, Goldberg et al](http://www.cs.cmu.edu/~hcwong/Pdfs/icip02.ps). There is an existing [reference implementation](https://www.pureftpd.org/project/libpuzzle) which may be more suited to your needs.

Match itself is released under the [BSD 3-Clause license](https://github.com/pavlovml/match/blob/master/LICENSE). `ascribe/image-match` is released under the Apache 2.0 license.
