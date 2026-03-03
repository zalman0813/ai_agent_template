# Strands Agents — OpenTelemetry with AWS

> Observability guide for Strands Agents: traces, logs, and per-user token cost tracking
> using AWS X-Ray and CloudWatch without a separate collector.

**Sources:**
- https://strandsagents.com/latest/documentation/docs/user-guide/observability-evaluation/traces/
- https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLP-UsingADOT.html
- https://aws.amazon.com/otel/faqs/

---

## Overview

```
Strands Agent
    │ OTLP (http/protobuf)
    │
    ├──► https://xray.{region}.amazonaws.com/v1/traces   → AWS X-Ray
    └──► https://logs.{region}.amazonaws.com/v1/logs     → CloudWatch Logs

No separate collector process needed.
```

### Cost

| Component | Cost |
|-----------|------|
| ADOT SDK | Free |
| X-Ray Traces | Free first 100,000 traces/month, then $5/million |
| CloudWatch Logs | Free first 5 GB/month, then $0.50/GB |
| CloudWatch Metrics | Free first 10 metrics, then $0.30/metric/month |

Solo dev usage rarely exceeds free tier.

---

## Automatically Captured Token Attributes

Strands records these attributes on every model call span without extra code:

| Attribute | Description |
|-----------|-------------|
| `gen_ai.usage.input_tokens` | Input tokens per model call |
| `gen_ai.usage.output_tokens` | Output tokens per model call |
| `gen_ai.usage.total_tokens` | Total tokens |
| `gen_ai.usage.cache_read_input_tokens` | Prompt cache hits (0 if unsupported) |
| `gen_ai.usage.cache_write_input_tokens` | Prompt cache writes (0 if unsupported) |
| `gen_ai.request.model` | Model ID used |

---

## Installation

```bash
pip install 'strands-agents[otel]'
pip install aws-opentelemetry-distro
```

---

## IAM Permissions

Attach to your IAM role or user:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:*"
    }
  ]
}
```

---

## Environment Variables

```bash
# AWS credentials
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# ADOT Python distro (required)
OTEL_PYTHON_DISTRO=aws_distro
OTEL_PYTHON_CONFIGURATOR=aws_configurator

# Send traces directly to X-Ray (no collector)
OTEL_TRACES_EXPORTER=otlp
OTEL_EXPORTER_OTLP_TRACES_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://xray.ap-northeast-1.amazonaws.com/v1/traces

# Send logs to CloudWatch
OTEL_LOGS_EXPORTER=otlp
OTEL_EXPORTER_OTLP_LOGS_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=https://logs.ap-northeast-1.amazonaws.com/v1/logs
OTEL_EXPORTER_OTLP_LOGS_HEADERS=x-aws-log-group=/my-agent/logs,x-aws-log-stream=default
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true

# Service identity (shows in X-Ray service map)
OTEL_RESOURCE_ATTRIBUTES=service.name=my-agent,deployment.environment=production

# Disable metrics to avoid cost (enable if needed)
OTEL_METRICS_EXPORTER=none
```

---

## Basic Setup

```python
from dotenv import load_dotenv
from strands import Agent
from strands.telemetry import StrandsTelemetry

load_dotenv()

# Setup telemetry — reads OTEL_* env vars automatically
StrandsTelemetry().setup_otlp_exporter()

# Tag each agent invocation with user context
agent = Agent(
    model="us.anthropic.claude-sonnet-4-6-v1:0",
    system_prompt="You are a helpful assistant.",
    trace_attributes={
        "user.id": "user-123",        # enables per-user filtering in X-Ray
        "session.id": "sess-456",
        "tags": ["production", "my-agent"],
    },
)

response = agent("Research quantum computing trends")
```

### Startup Command

```bash
# Wrap with opentelemetry-instrument for auto-instrumentation
opentelemetry-instrument python main.py

# FastAPI
opentelemetry-instrument uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## Per-User Token Cost Tracking

### Option A: Query CloudWatch Logs Insights (post-hoc analysis)

Because `user.id` is attached to every span as a trace attribute, you can
aggregate token usage per user directly in CloudWatch Logs Insights:

```sql
-- Run in CloudWatch Logs Insights against log group: aws/spans
fields @timestamp, `user.id`,
       `gen_ai.usage.input_tokens`,
       `gen_ai.usage.output_tokens`
| filter ispresent(`user.id`)
| stats
    sum(`gen_ai.usage.input_tokens`)  as total_input,
    sum(`gen_ai.usage.output_tokens`) as total_output,
    count()                           as requests
  by `user.id`
| sort total_input desc
```

### Option B: Real-time Cost via Custom SpanProcessor

Use a custom `SpanProcessor` to capture token counts at span end and store
them in a database, enabling cost data to be returned in the same API response.

```python
from opentelemetry.sdk.trace import SpanProcessor, ReadableSpan

# Claude pricing (USD per token, update as needed)
PRICING = {
    "claude-sonnet-4-6": {
        "input":       3.00 / 1_000_000,   # $3.00 per 1M input tokens
        "output":     15.00 / 1_000_000,   # $15.00 per 1M output tokens
        "cache_read":  0.30 / 1_000_000,   # $0.30 per 1M cache read tokens
        "cache_write": 3.75 / 1_000_000,   # $3.75 per 1M cache write tokens
    },
    "claude-haiku-4-5": {
        "input":       0.80 / 1_000_000,
        "output":       4.0 / 1_000_000,
        "cache_read":  0.08 / 1_000_000,
        "cache_write": 1.00 / 1_000_000,
    },
}

class CostTrackingProcessor(SpanProcessor):
    """Intercept span end to calculate and persist per-user token cost."""

    def __init__(self, db):
        self.db = db

    def on_end(self, span: ReadableSpan) -> None:
        attrs = span.attributes or {}

        input_tokens  = attrs.get("gen_ai.usage.input_tokens", 0)
        output_tokens = attrs.get("gen_ai.usage.output_tokens", 0)
        cache_read    = attrs.get("gen_ai.usage.cache_read_input_tokens", 0)
        cache_write   = attrs.get("gen_ai.usage.cache_write_input_tokens", 0)
        user_id       = attrs.get("user.id")
        model         = attrs.get("gen_ai.request.model", "claude-sonnet-4-6")

        # Skip spans that are not model call spans
        if not input_tokens or not user_id:
            return

        pricing = PRICING.get(model, PRICING["claude-sonnet-4-6"])
        cost_usd = (
            input_tokens  * pricing["input"]  +
            output_tokens * pricing["output"] +
            cache_read    * pricing["cache_read"] +
            cache_write   * pricing["cache_write"]
        )

        self.db.upsert_user_usage(
            user_id=user_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

    def on_start(self, span, parent_context=None) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
```

### Wiring the Custom Processor

```python
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanExporter
from strands.telemetry import StrandsTelemetry

def setup_telemetry(db) -> None:
    provider = TracerProvider()

    # Add cost tracking processor (runs on every span end)
    provider.add_span_processor(CostTrackingProcessor(db=db))

    # Set as global provider before creating the agent
    otel_trace.set_tracer_provider(provider)

    # Strands reads the global provider automatically
    StrandsTelemetry(tracer_provider=provider).setup_otlp_exporter()
```

### FastAPI Endpoint Example

```python
from fastapi import FastAPI, Depends
from strands import Agent
from strands.telemetry import StrandsTelemetry

app = FastAPI()

@app.on_event("startup")
async def startup():
    setup_telemetry(db=my_db)

@app.post("/chat")
async def chat(body: ChatRequest, user: User = Depends(get_current_user)):
    agent = Agent(
        model="us.anthropic.claude-sonnet-4-6-v1:0",
        system_prompt="You are a helpful assistant.",
        trace_attributes={
            "user.id": user.id,
            "session.id": body.session_id,
        },
    )

    result = agent(body.message)

    # CostTrackingProcessor already wrote usage to DB during agent.invoke()
    usage = my_db.get_last_usage(user.id)

    return {
        "message": str(result),
        "usage": {
            "input_tokens":  usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cost_usd":      round(usage.cost_usd, 6),
        },
    }
```

---

## Option Comparison

| | Option A (CloudWatch Insights) | Option B (SpanProcessor) |
|---|---|---|
| **Setup complexity** | Low | Medium |
| **Real-time cost in API response** | No | Yes |
| **Persist to database** | No | Yes |
| **CloudWatch dashboard** | Yes (built-in) | Yes (still sends to OTEL) |
| **Best for** | Monitoring, billing analysis | Per-request cost, frontend display |

Recommended: use both together — OTEL sends to CloudWatch for dashboards,
SpanProcessor writes to DB for real-time API responses.

---

## Local Development (No AWS)

Use Jaeger locally instead of AWS endpoints:

```bash
# Start Jaeger
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest
```

Override only the endpoint env var:

```bash
# .env.local
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4318
# Remove AWS-specific vars
```

Open `http://localhost:16686` to browse traces.

---

## What You See in CloudWatch X-Ray

```
Service Map:
  [my-agent] → [Claude API] → [Tool: search_web]
                             → [Tool: read_file]

Trace Detail (example):
  Agent Invocation          312ms
  ├─ model_call             254ms
  │    gen_ai.usage.input_tokens:  1,842
  │    gen_ai.usage.output_tokens:   318
  │    user.id: user-123
  ├─ tool: search_web        48ms
  └─ tool: read_file          10ms

CloudWatch Logs (/my-agent/logs):
  [INFO] Agent started  session=sess-456 user=user-123
  [INFO] Tool called: search_web  query="quantum computing"
  [INFO] Agent completed  duration=312ms cost_usd=0.000008
```

---

## Reference Links

- https://strandsagents.com/latest/documentation/docs/user-guide/observability-evaluation/traces/
- https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-OTLP-UsingADOT.html
- https://aws-otel.github.io/
- https://aws.amazon.com/otel/faqs/
- https://docs.aws.amazon.com/xray/latest/devguide/xray-services-adot.html
