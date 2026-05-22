import os
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from src.config import PHOENIX_PORT


def init_tracing():
    try:
        import httpx
        response = httpx.get(f"http://localhost:{PHOENIX_PORT}/")
        phoenix_already_running = response.status_code == 200
    except Exception:
        phoenix_already_running = False

    if not phoenix_already_running:
        import phoenix as px
        os.environ["PHOENIX_PORT"] = str(PHOENIX_PORT)
        session = px.launch_app()
        print(f"Phoenix started at {session.url}")
    else:
        print(f"Phoenix already running at http://localhost:{PHOENIX_PORT}")

    otlp_exporter = OTLPSpanExporter(
        endpoint=f"http://localhost:{PHOENIX_PORT}/v1/traces"
    )

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)

    OpenAIInstrumentor().instrument()
    print("Tracing active.")