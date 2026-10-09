FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Safety net: strip Windows line endings so the script runs on Linux
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# $PORT is set by hosts like Render; falls back to 8000 locally
CMD ["sh", "-c", "gunicorn masar_backend.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]