FROM python:3
MAINTAINER Alex Kern <alex@pavlov.ai>

RUN apt-get update && \
    apt-get install -y libopenblas-dev gfortran && \
    pip install numpy==1.12.1 && \
    pip install scipy==0.19.0 && \
    pip install gevent==1.2.1 && \
    pip install flask==0.12.2 && \
    pip install image-match==1.1.2 && \
    rm -rf /var/lib/apt/lists/*

COPY server.py wait-for-it.sh /

EXPOSE 80
ENV PORT=80 \
    ELASTICSEARCH_URL=elasticsearch:9200 \
    ELASTICSEARCH_INDEX=images \
    ELASTICSEARCH_DOC_TYPE=images
CMD python /server.py
