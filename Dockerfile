
# Python
FROM python:3.12-slim

# Directorio
WORKDIR /app

# Copiar e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Puerto de Flask
EXPOSE 5000

# Iniciar aplicación
CMD ["python", "app.py"]
