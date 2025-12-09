"""Web search subagent configuration.

This module provides the configuration for the web search subagent
that can be delegated to by the primary agent.

Supports both Anthropic Claude and Google Gemini models.
"""

import os
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch

from src.middleware import SubAgentSpec

# Model provider type
ModelProvider = Literal["anthropic", "google", "azure_openai"]


def get_search_tool() -> TavilySearch:
    """Get the Tavily search tool instance."""
    return TavilySearch(
        max_results=5,
        topic="general",
        include_images=True,
        include_image_descriptions=True,
    )


def _create_model(provider: ModelProvider = "anthropic"):
    """Create chat model based on provider.

    Args:
        provider: Model provider - "anthropic" for Claude, "google" for Gemini,
                  "azure_openai" for Azure OpenAI

    Returns:
        Chat model instance
    """
    if provider == "google":
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
        return AzureChatOpenAI(
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5-mini"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
            # Note: temperature removed - gpt-5/reasoning models only support default (1)
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        )
    else:
        return init_chat_model(
            "claude-sonnet-4-5-20250929",
            model_provider="anthropic",
            temperature=0.7,
        )


def get_search_subagent_spec(
    model_provider: ModelProvider = "anthropic",
) -> SubAgentSpec:
    """Get the subagent specification for web search.

    Args:
        model_provider: Model provider - "anthropic" for Claude, "google" for Gemini

    Returns:
        SubAgentSpec compatible with CustomSubAgentMiddleware
    """
    return {
        "name": "web_search_agent",
        "description": "Search the web for current information, news, and real-time data",
        "system_prompt": """You are a web research specialist.
Your job is to search the web and find accurate, relevant information.

IMPORTANT: You MUST return your final response in the following JSON format:
```json
{
  "summary": "Brief summary of your findings",
  "text_results": [
    {
      "title": "Result title",
      "url": "https://...",
      "content": "Key content or snippet",
      "source": "Domain name"
    }
  ],
  "image_results": [
    {
      "image_url": "https://...",
      "title": "Image description or caption",
      "source": "Source website",
      "page_url": "https://..."
    }
  ]
}
```

Rules:
- Always include "summary" field with your analysis
- "text_results" for web page results (max 5)
- "image_results" for images found (max 6), only include if images are relevant
- If no images found or not relevant, set "image_results" to empty array []
- Return ONLY the JSON, no additional text""",
        "tools": [get_search_tool()],
        "model": _create_model(model_provider),
    }
