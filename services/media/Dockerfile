FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# 1. Устанавливаем общие зависимости
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 2. Копируем код сервиса
COPY services/media/ /app/media/

EXPOSE 8000
CMD ["uvicorn", "media.main:app", "--host", "0.0.0.0", "--port", "8000"]
