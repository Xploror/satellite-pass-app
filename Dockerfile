FROM python:3.12-slim AS base

ENV APP_HOST=0.0.0.0
ENV APP_PORT=80

WORKDIR /app

EXPOSE 80

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS development
USER root
COPY . .
RUN apt-get update && apt-get install -y build-essential curl git lsof gdb
RUN pip install --no-cache-dir pytest
ENTRYPOINT ["python", "main.py"]

FROM base AS production
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
ENTRYPOINT ["python", "main.py"]