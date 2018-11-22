FROM python:3.6
MAINTAINER Alex Kern <alex@distributedsystems.com>

RUN apt-get update && \
    apt-get install -y libopenblas-dev gfortran && \
    pip install numpy==1.12.1 && \
    pip install scipy==0.19.0 && \
    pip install gunicorn==19.7.1 && \
    pip install flask==0.12.2 && \
    pip install image-match==1.1.2 && \
    pip install 'elasticsearch>=6.0.0,<7.0.0' && \
    rm -rf /var/lib/apt/lists/*

COPY server.py wait-for-it.sh /

EXPOSE 80
ENV PORT=80 \
    WORKER_COUNT=4 \
    ELASTICSEARCH_URL=elasticsearch:9200 \
    ELASTICSEARCH_INDEX=images \
    ELASTICSEARCH_DOC_TYPE=images \
    ALL_ORIENTATIONS=true

CMD gunicorn \
    -t 60 \
    --access-logfile - \
    --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" - %(D)s' \
    -b 0.0.0.0:${PORT} \
    -w ${WORKER_COUNT} \
    server:app
