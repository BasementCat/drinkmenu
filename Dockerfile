# Separate stage, only need to update version once
FROM tiangolo/uwsgi-nginx-flask:python3.8-alpine AS base


FROM base AS build

RUN pip install --upgrade pip setuptools wheel
# COPY requirements.txt /tmp/

# RUN apk add --no-cache --virtual .build-deps \
#     # Build deps
#     alpine-sdk \
#     python3-dev \
#     jpeg-dev \
#     zlib-dev \
#     libxml2-dev \
#     libxslt-dev \
#     musl-dev
# RUN MAKEFLAGS="-j$(nproc)" pip install --no-cache-dir -r /tmp/requirements.txt
# RUN apk del .build-deps


FROM base

# COPY --from=build  /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages

RUN apk add \
    # Runtime deps
    libmagic \
    libxml2 \
    libxslt \
    libstdc++ \
    curl

COPY requirements/base.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENV STATIC_PATH /app/app/static

COPY . /app