FROM python:3.12-slim

ARG HELM_VERSION=4.1.1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL "https://get.helm.sh/helm-v${HELM_VERSION}-linux-amd64.tar.gz" \
    | tar -C /tmp -xzf - \
    && mv /tmp/linux-amd64/helm /usr/local/bin/helm \
    && rm -rf /tmp/linux-amd64

COPY entrypoint.py /entrypoint.py

ENTRYPOINT ["python", "/entrypoint.py"]
