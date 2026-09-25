FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY ruleforge ./ruleforge

RUN pip install --no-cache-dir -e . uvicorn

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "ruleforge.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
