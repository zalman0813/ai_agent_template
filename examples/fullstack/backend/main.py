"""FastAPI backend with SSE streaming for agent chat."""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from schemas import ChatRequest  # noqa: E402

from src.agents.primary_agent import ModelProvider, create_primary_agent  # noqa: E402
from src.errors import classify_error  # noqa: E402
from src.observation import AgentObserver, CallbackOutput  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

# Get model provider from env (default: anthropic)
def get_model_provider() -> ModelProvider:
    """Get model provider from MODEL_PROVIDER env var."""
    provider = os.getenv("MODEL_PROVIDER", "anthropic").lower()
    logger.info(f"MODEL_PROVIDER env var: '{provider}'")

    if provider in ["google", "gemini"]:
        result = "google"
    elif provider in ["azure", "azure_openai"]:
        result = "azure_openai"
    else:
        result = "anthropic"

    logger.info(f"Selected model provider: '{result}'")
    return result

app = FastAPI(title="AI Agent Chat API")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming endpoint for chat.

    Streams events:
    - llm_token: LLM output tokens
    - llm_end: LLM response complete
    - node_start/node_end: Graph node execution
    - tool_call: Tool invocation
    - tool_result: Tool response
    - subagent_start/subagent_end: SubAgent lifecycle
    - subagent_tool_call/subagent_tool_result: SubAgent internal tool calls
    - error: Error occurred
    - done: Stream complete
    """

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()

        def on_event(event_type: str, data: dict):
            """Callback to push events to the queue."""
            queue.put_nowait((event_type, data))

        # Create callback output handler
        callback_output = CallbackOutput(on_event)

        # Create agent with output handlers for subagent streaming
        agent = create_primary_agent(
            model_provider=get_model_provider(),
            output_handlers=[callback_output],
        )

        # Create observer with same callback output
        observer = AgentObserver([callback_output])

        # Run agent in background task with retry enabled
        task = asyncio.create_task(
            observer.arun(
                agent,
                {"messages": [{"role": "user", "content": request.message}]},
                max_retries=2,
                retry_delay=1.0,
            )
        )

        final_response = ""

        try:
            while not task.done() or not queue.empty():
                try:
                    event_type, data = await asyncio.wait_for(
                        queue.get(), timeout=0.1
                    )

                    # Send SSE event
                    event_data = json.dumps(data, ensure_ascii=False, default=str)
                    yield f"event: {event_type}\ndata: {event_data}\n\n"

                    # Track final response from llm_end
                    if event_type == "llm_end":
                        final_response = data.get("content", "")

                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"

            # Get result and extract final response
            result = task.result()

            # Check for error in result (graceful failure from retry exhaustion)
            if result and result.get("error"):
                error_info = result["error"]
                yield f"event: error\ndata: {json.dumps(error_info)}\n\n"
            elif result and "messages" in result:
                messages = result["messages"]
                if messages:
                    last_msg = messages[-1] if isinstance(messages, list) else messages
                    if hasattr(last_msg, "content"):
                        final_response = last_msg.content

            # Send done event
            yield f"event: done\ndata: {json.dumps({'final_response': final_response})}\n\n"

        except Exception as e:
            llm_error = classify_error(e)
            logger.exception(f"Stream error: {e}")
            yield f"event: error\ndata: {json.dumps(llm_error.to_dict())}\n\n"
            yield f"event: done\ndata: {json.dumps({'final_response': ''})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
