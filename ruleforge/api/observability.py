import logging
import json
import time
import sys
import os
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        if hasattr(record, 'extra_data'):
            log_record.update(record.extra_data)
        return json.dumps(log_record)

def setup_logging():
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

REQUESTS = Counter("ruleforge_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_DURATION = Histogram("ruleforge_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])
EVALUATIONS = Counter("ruleforge_evaluations_total", "Total rule evaluations", ["success"])
EVALUATION_DURATION = Histogram("ruleforge_evaluation_duration_seconds", "Time spent inside RuleForge Engine")

def setup_tracing(app):
    trace.set_tracer_provider(TracerProvider())
    # Solo usar ConsoleSpanExporter si la variable de entorno está activa
    if os.getenv("RULEFORGE_OTEL_CONSOLE", "false").lower() == "true":
        trace.get_tracer_provider().add_span_processor(
            SimpleSpanProcessor(ConsoleSpanExporter()) # SimpleSpanProcessor es síncrono y no deja hilos vivos
        )
    FastAPIInstrumentor.instrument_app(app)

async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    endpoint = request.url.path
    method = request.method
    status = response.status_code
    REQUESTS.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
    return response
