FROM python:3.10-alpine as base

ARG BUILD_DATE
ARG VERSION
ARG LIBRD_VER=2.10.0

LABEL version=$VERSION maintainer="CTO2B data team" \
      eu.cto2b.build_date=$BUILD_DATE \
      eu.cto2b.project="MAGICFLOW"

RUN mkdir -p /magicflow/libs
COPY magicflow/ /magicflow/
COPY magicflow/libs /magicflow/libs/
RUN apk update &&\
    apk upgrade &&\ 
    apk add --no-cache --virtual .make-static libpq openssl gcc ca-certificates libc-dev zstd-dev\
    && apk add --no-cache --virtual .make-deps bash make wget git g++ musl-dev zlib-dev openssl-dev pkgconfig musl-dev \
    && wget https://github.com/edenhill/librdkafka/archive/v${LIBRD_VER}.tar.gz \
    && tar -xvf v${LIBRD_VER}.tar.gz \
    && cd librdkafka-${LIBRD_VER} \
    && ./configure --prefix /usr --enable-ssl\
    && make && make install && make clean
      
RUN  rm -rf /librdkafka-${LIBRD_VER} &&\
    rm -f /v${LIBRD_VER}.tar.gz &&\
    mkdir /magicflow/ssl &&\
    apk del .make-deps &&\
    rm -rf /tmp/*.apk /var/cache/apk/*

RUN addgroup workflow && adduser -h /magicflow -s /bin/bash -G workflow -u 1001 -D workflow &&\
    chown -R workflow /magicflow

COPY magicflow/ /magicflow/

FROM base AS python-deps
RUN python -m pip install --upgrade pip
RUN pip install pipenv

COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv --python /usr/local/bin/python3.10  install --deploy

FROM base AS runtime
# Copy virtual env from python-deps stage
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

RUN chown -R workflow:workflow /magicflow

USER workflow
WORKDIR /
ENTRYPOINT ["python", "-m", "magicflow.app"]
