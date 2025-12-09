"""Content processor subagent configuration.

This module provides the configuration for the content processor subagent
that analyzes and processes text content from search results or other sources.

Supports both Anthropic Claude and Google Gemini models.
"""

import os
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI

from src.middleware import SubAgentSpec
from src.tools.content_tools import content_tools

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


def get_content_processor_subagent_spec(
    model_provider: ModelProvider = "anthropic",
) -> SubAgentSpec:
    """Get the subagent specification for content processing.

    Args:
        model_provider: Model provider - "anthropic" for Claude, "google" for Gemini

    Returns:
        SubAgentSpec compatible with CustomSubAgentMiddleware
    """
    return {
        "name": "content_processor_agent",
        "description": (
            "Process and analyze text content - extract keywords, summarize, "
            "and analyze sentiment. Use this after getting search results."
        ),
        "system_prompt": """You are a content processing specialist.
Your job is to analyze text and extract meaningful insights.

You have three tools available:
1. extract_keywords - Extract key terms and named entities from text
2. summarize - Create concise summaries of long content
3. analyze_sentiment - Analyze sentiment and classify content type

When processing content:
- Use the appropriate tool based on what's requested
- Always return structured, well-formatted results
- If the content is too short or unclear, explain what's missing
- For keywords and sentiment analysis, return valid JSON format

If you cannot process the content adequately, explain what additional information is needed.""",
        "tools": content_tools,
        "model": _create_model(model_provider),
    }
