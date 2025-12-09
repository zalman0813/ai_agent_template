"""Primary agent with TODO tools and search subagent delegation.

This module creates the main agent that manages tasks and can delegate
web search to a specialized subagent using custom middleware.

Supports both Anthropic Claude and Google Gemini models.
"""

import logging
import os
from typing import TYPE_CHECKING, Literal

logger = logging.getLogger(__name__)

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from src.agents.content_processor_agent import get_content_processor_subagent_spec
from src.agents.search_agent import get_search_subagent_spec
from src.middleware import CustomSubAgentMiddleware, TodoMiddleware

if TYPE_CHECKING:
    from src.observation.outputs import OutputHandler

# Model provider type
ModelProvider = Literal["anthropic", "google", "azure_openai"]


def _create_model(provider: ModelProvider = "anthropic"):
    """Create chat model based on provider.

    Args:
        provider: Model provider - "anthropic" for Claude, "google" for Gemini,
                  "azure_openai" for Azure OpenAI

    Returns:
        Chat model instance
    """
    logger.info(f"Creating model with provider: '{provider}'")

    if provider == "google":
        # Lazy import to avoid requiring google dependency when not used
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "langchain_google_genai is required for Google models. "
                "Install with: pip install langchain-google-genai"
            )
        logger.info("Initializing Google Gemini model: gemini-2.0-flash")
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.7,
            api_key=os.getenv("GOOGLE_API_KEY"),
        )
    elif provider == "azure_openai":
        # Lazy import to avoid requiring azure dependency when not used
        try:
            from langchain_openai import AzureChatOpenAI
        except ImportError:
            raise ImportError(
                "langchain_openai is required for Azure OpenAI models. "
                "Install with: pip install langchain-openai"
            )
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-mini")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        logger.info(f"Initializing Azure OpenAI model: deployment='{deployment}', endpoint='{endpoint}', api_version='{api_version}'")
        return AzureChatOpenAI(
            azure_deployment=deployment,
            api_version=api_version,
            # Note: temperature removed - gpt-5/reasoning models only support default (1)
            azure_endpoint=endpoint,
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        )
    else:
        logger.info("Initializing Anthropic Claude model: claude-sonnet-4-5-20250929")
        return init_chat_model(
            "claude-sonnet-4-5-20250929",
            model_provider="anthropic",
            temperature=0.7,
        )


def create_primary_agent(
    model_provider: ModelProvider = "anthropic",
    output_handlers: list["OutputHandler"] | None = None,
):
    """Create primary agent with TODO tools and search subagent.

    Uses create_agent with custom middleware instead of create_deep_agent.

    Args:
        model_provider: Model provider - "anthropic" for Claude, "google" for Gemini
        output_handlers: Optional output handlers for streaming subagent events.
            When provided, enables streaming of internal subagent tool calls.

    Returns:
        A compiled LangGraph agent ready for invocation
    """
    model = _create_model(model_provider)

    # Get subagent specs with same model provider
    search_subagent = get_search_subagent_spec(model_provider=model_provider)
    content_processor_subagent = get_content_processor_subagent_spec(
        model_provider=model_provider
    )

    # TodoMiddleware provides: write_todo, list_todos, complete_todo
    todo_middleware = TodoMiddleware()

    # Build middleware stack
    middleware = [
        todo_middleware,
        CustomSubAgentMiddleware(
            default_model=model,
            default_tools=todo_middleware.tools,  # Pass todo tools to subagents
            subagents=[search_subagent, content_processor_subagent],
            include_general_purpose=True,
            stream_subagent_events=output_handlers is not None,
            output_handlers=output_handlers,
        ),
    ]

    return create_agent(
        model,
        system_prompt="""You are an intelligent task manager and research assistant.

Your capabilities:
1. Manage TODO lists - add, list, and complete tasks
2. Delegate web research to your web_search_agent subagent
3. Process and analyze content with your content_processor_agent subagent

Workflow for complex research tasks:
1. First, break down the task into TODOs using write_todo
2. Delegate web search to web_search_agent
3. After getting search results, use content_processor_agent to:
   - Extract keywords and key entities
   - Summarize long content
   - Analyze sentiment if relevant
4. Mark TODOs as complete after each step
5. If processing fails or results are inadequate, ask the user for guidance

Guidelines:
- When user asks to remember or track something, use write_todo
- When user needs current information from the web, delegate to web_search_agent
- When user needs content analysis (keywords, summary, sentiment), use content_processor_agent
- Break complex tasks into smaller, manageable todos
- Always complete todos after finishing each subtask
- Always confirm actions taken""",
        tools=[],  # Tools are now provided by middleware
        middleware=middleware,
    )
