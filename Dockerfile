FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 5000
# gunicorn (WSGI de producción) con 1 worker: el bloqueo por intentos vive en memoria del proceso
CMD ["sh", "-c", "python init_db.py && gunicorn -w 1 -b 0.0.0.0:5000 --access-logfile - app:app"]
