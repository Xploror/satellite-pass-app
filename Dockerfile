FROM python:3.12-slim AS base

ENV APP_HOST=0.0.0.0
ENV N2YO_APIKEY=P4PMZJ-ESGUNV-9F93DH-5T7S
ENV PYTHONUNBUFFERED=1

WORKDIR /app

EXPOSE 80
EXPOSE 60

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS development
ENV APP_PORT=80
USER root
RUN apt-get update && apt-get install -y build-essential curl git lsof gdb
RUN pip install --no-cache-dir pytest
COPY . .
ENTRYPOINT ["python", "main.py"]

FROM base AS production
ENV APP_PORT=60
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
ENTRYPOINT ["python", "main.py"]