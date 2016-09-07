FROM python:3.5
MAINTAINER Alex Kern <alex@pavlovml.com>

# deps
RUN apt-get update && \
    apt-get install -y libopenblas-dev gfortran && \
    pip install numpy && \
    pip install scipy && \
    pip install flask gunicorn && \
    pip install image-match

# install
RUN mkdir -p /app
WORKDIR /app
COPY src .

# run
EXPOSE 80
ENV PORT 80
CMD wget --retry-connrefused --tries=100 -q --wait=1 --spider elasticsearch:9200 && gunicorn -w ${WORKER_COUNT:-4} wsgi:app
