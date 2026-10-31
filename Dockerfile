FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install --index-url https://download.pytorch.org/whl/cpu torch
RUN pip install -r requirements.txt \
    && pip install psycopg2-binary
COPY ai ./ai
COPY backend ./backend
COPY database ./database
COPY data ./data
EXPOSE 5000
CMD ["sh", "-c", "python -m database.initialize && exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --threads 4 --timeout 120 backend.app:app"]
