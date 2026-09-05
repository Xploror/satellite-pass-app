FROM python:3.12-slim AS base

ENV APP_HOST=0.0.0.0
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
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
CMD ["python", "main.py"]

FROM base AS production
ENV APP_PORT=60
COPY . .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
ENTRYPOINT ["python", "main.py"]