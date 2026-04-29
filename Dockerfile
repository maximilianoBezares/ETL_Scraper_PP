# Imagen base oficial de Playwright (Python + Drivers de Navegador)
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

# Evita que Python retenga los logs en el buffer. Fundamental para monitorear el scraper en vivo.
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY . /app

# Instalacion de Librerias
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Instalacion de Navegadores
RUN playwright install chromium
RUN playwright install-deps

EXPOSE 8000

CMD ["uvicorn", "wrapper_http.main:app", "--host", "0.0.0.0", "--port", "8000"]