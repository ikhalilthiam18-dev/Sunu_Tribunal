FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fichiers statiques (Django Admin) intégrés à l'image, servis par whitenoise
RUN SECRET_KEY=construction-image DEBUG=False python manage.py collectstatic --noinput

EXPOSE 8000

# Au démarrage : création des tables manquantes, puis gunicorn sur le port fourni ($PORT sur Railway)
CMD ["sh", "start.sh"]
