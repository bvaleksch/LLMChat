FROM python:3.12-slim

WORKDIR /app

# Копируем requirements.txt из корня проекта
COPY ../../requirements.txt /app/requirements.txt

# Копируем всё остальное (код сервиса)
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["python", "-m", "schemas.main"]