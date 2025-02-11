FROM python:3.13-slim-bookworm
LABEL version="0.1" description="Dockerfile for IOU app"

RUN apt-get update \
    && apt-get -y install libpq-dev gcc curl procps net-tools tini \
    && apt-get -y clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install gunicorn

ENV POETRY_HOME=/tmp/poetry
RUN curl -sSL https://install.python-poetry.org/ | python3 -
ENV PATH=$POETRY_HOME/bin:$PATH
ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . /app

RUN poetry config virtualenvs.create false \
  && poetry install --only main

EXPOSE 8000
ENTRYPOINT ["bash", "-c", "uvicorn iou_app.main:app --host 0.0.0.0 --port 8000"]
