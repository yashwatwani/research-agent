import phoenix as px
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from src.config import PHOENIX_PORT


def init_tracing():
    import os
    os.environ["PHOENIX_PORT"] = str(PHOENIX_PORT)
    
    session = px.launch_app()
    print(f"Phoenix UI running at {session.url}")

    otlp_exporter = OTLPSpanExporter(
        endpoint=f"http://localhost:{PHOENIX_PORT}/v1/traces"
    )

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)

    OpenAIInstrumentor().instrument()
    print("Tracing active. All OpenAI calls are now being recorded.")