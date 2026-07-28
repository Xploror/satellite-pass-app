FROM python:3.12-slim

ENV APP_HOST=0.0.0.0
ENV APP_PORT=80

WORKDIR /app

EXPOSE 80

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "main.py"]