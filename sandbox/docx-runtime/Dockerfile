FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /workspace

RUN groupadd --system sandbox \
    && useradd --system --gid sandbox --home-dir /workspace sandbox \
    && mkdir -p /input /output \
    && chown -R sandbox:sandbox /workspace /output

RUN pip install --upgrade pip \
    && pip install python-docx==1.1.2

USER sandbox
