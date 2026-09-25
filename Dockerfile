FROM python:3.12-slim

WORKDIR /app

# Copiar solo lo necesario para instalar
COPY pyproject.toml .
COPY ruleforge ./ruleforge

# Instalar el paquete y uvicorn
RUN pip install --no-cache-dir -e . uvicorn

EXPOSE 8000

# Healthcheck usando Python nativo (evita instalar curl extra)
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "ruleforge.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
