FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DB_PATH=/data/expenses.db PORT=5000
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

COPY . .
RUN mkdir -p /data
VOLUME /data
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request as u; u.urlopen('http://localhost:5000/health')" || exit 1

CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "2", "app:app"]
