FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
COPY . .
RUN pip install --no-cache-dir .
CMD ["sh", "-c", "uvicorn flowbound.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
