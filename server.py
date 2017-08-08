from botocore.credentials import get_credentials
from botocore.session import Session
from elasticsearch import Elasticsearch
from elasticsearch import RequestsHttpConnection
from flask import Flask, request
from flask import Response
from functools import wraps
from image_match.elasticsearch_driver import SignatureES
from image_match.goldberg import ImageSignature
from requests_aws4auth import AWS4Auth
import json
import os
import sys

# =============================================================================
# Globals

es_url = os.environ['ELASTICSEARCH_URL']
es_index = os.environ['ELASTICSEARCH_INDEX']
es_doc_type = os.environ['ELASTICSEARCH_DOC_TYPE']
all_orientations = os.environ['ALL_ORIENTATIONS']
AWS_CREDS = os.environ.get('AWS_CREDS', None) == 'true'

if os.environ.get('AUTH_USERNAME', None) and os.environ.get('AUTH_PASSWORD', None):
    auth_username = os.environ['AUTH_USERNAME']
    auth_password = os.environ['AUTH_PASSWORD']

distance_cutoff = float(os.environ.get('IMAGE_MATCH_DISTANCE_CUTOFF', 0.45))

can_update = os.environ.get('CAN_UPDATE', None) == 'true'
create_index = os.environ.get('CREATE_INDEX', None) == 'true'

if os.environ.get('USER_AGENT', None):
    import urllib.request

    opener = urllib.request.build_opener()
    opener.addheaders = [('User-agent', os.environ['USER_AGENT'])]

    urllib.request.install_opener(opener)

app = Flask(__name__)

if AWS_CREDS:

    aws_default_region = os.environ['AWS_DEFAULT_REGION']
    creds = get_credentials(Session())

    awsauth = AWS4Auth(
        creds.access_key,
        creds.secret_key,
        aws_default_region,
        'es',
        session_token=creds.token)

    es = Elasticsearch(
        hosts=[{'host': es_url, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=120)
else:
    es = Elasticsearch([es_url], verify_certs=True, timeout=60, max_retries=10, retry_on_timeout=True)


ses = SignatureES(es, distance_cutoff=distance_cutoff, index=es_index, doc_type=es_doc_type)
gis = ImageSignature()

# Try to create the index and ignore IndexAlreadyExistsException
# if the index already exists
if create_index:
    es.indices.create(index=es_index, ignore=400)

# =============================================================================
# Helpers

def ids_with_path(path):
    matches = es.search(index=es_index,
                        _source='_id',
                        q='path:' + json.dumps(path))
    return [m['_id'] for m in matches['hits']['hits']]

def paths_at_location(offset, limit):
    search = es.search(index=es_index,
                       from_=offset,
                       size=limit,
                       _source='path')
    return [h['_source']['path'] for h in search['hits']['hits']]

def count_images():
    return es.count(index=es_index)['count']

def delete_ids(ids):
    for i in ids:
        es.delete(index=es_index, doc_type=es_doc_type, id=i, ignore=404)

def dist_to_percent(dist):
    return (1 - dist) * 100

def get_image(url_field, file_field):
    if url_field in request.form:
        return request.form[url_field], False
    else:
        return request.files[file_field].read(), True

# =============================================================================
# Routes


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    if auth_username and auth_password:
        return username == auth_username and password == auth_password

    return True


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

if can_update:
    @app.route('/add', methods=['POST'])
    @requires_auth
    def add_handler():
        path = request.form['filepath']
        try:
            metadata = json.loads(request.form['metadata'])
        except KeyError:
            metadata = None
        img, bs = get_image('url', 'image')

        old_ids = ids_with_path(path)
        ses.add_image(path, img, bytestream=bs, metadata=metadata)
        delete_ids(old_ids)

        return json.dumps({
            'status': 'ok',
            'error': [],
            'method': 'add',
            'result': []
        })

    @app.route('/delete', methods=['DELETE'])
    @requires_auth
    def delete_handler():
        path = request.form['filepath']
        ids = ids_with_path(path)
        delete_ids(ids)
        return json.dumps({
            'status': 'ok',
            'error': [],
            'method': 'delete',
            'result': []
        })

@app.route('/search', methods=['POST'])
@requires_auth
def search_handler():
    img, bs = get_image('url', 'image')
    ao = request.form.get('all_orientations', all_orientations) == 'true'

    matches = ses.search_image(
            path=img,
            all_orientations=ao,
            bytestream=bs)

    return json.dumps({
        'status': 'ok',
        'error': [],
        'method': 'search',
        'result': [{
            'score': dist_to_percent(m['dist']),
            'filepath': m['path'],
            'metadata': m['metadata']
        } for m in matches]
    })

@app.route('/compare', methods=['POST'])
@requires_auth
def compare_handler():
    img1, bs1 = get_image('url1', 'image1')
    img2, bs2 = get_image('url2', 'image2')
    img1_sig = gis.generate_signature(img1, bytestream=bs1)
    img2_sig = gis.generate_signature(img2, bytestream=bs2)
    score = dist_to_percent(gis.normalized_distance(img1_sig, img2_sig))

    return json.dumps({
        'status': 'ok',
        'error': [],
        'method': 'compare',
        'result': [{ 'score': score }]
    })

@app.route('/count', methods=['GET'])
@requires_auth
def count_handler():
    count = count_images()
    return json.dumps({
        'status': 'ok',
        'error': [],
        'method': 'count',
        'result': [count]
    })

@app.route('/list', methods=['GET'])
@requires_auth
def list_handler():
    offset = max(int(request.form.get('offset', 0)), 0)
    limit = max(int(request.form.get('limit', 20)), 0)
    paths = paths_at_location(offset, limit)

    return json.dumps({
        'status': 'ok',
        'error': [],
        'method': 'list',
        'result': paths
    })

@app.route('/ping', methods=['GET'])
@requires_auth
def ping_handler():
    return json.dumps({
        'status': 'ok',
        'error': [],
        'method': 'ping',
        'result': []
    })

# =============================================================================
# Error Handling

@app.errorhandler(400)
def bad_request(e):
    return json.dumps({
        'status': 'fail',
        'error': ['bad request'],
        'method': '',
        'result': []
    }), 400

@app.errorhandler(404)
def page_not_found(e):
    return json.dumps({
        'status': 'fail',
        'error': ['not found'],
        'method': '',
        'result': []
    }), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return json.dumps({
        'status': 'fail',
        'error': ['method not allowed'],
        'method': '',
        'result': []
    }), 405

@app.errorhandler(500)
def server_error(e):
    return json.dumps({
        'status': 'fail',
        'error': [str(e)],
        'method': '',
        'result': []
    }), 500
