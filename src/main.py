"""Main entry point for the multi-agent system."""

import logging
import os
import sys

from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from src.agents.primary_agent import ModelProvider, create_primary_agent
from src.observation import AgentObserver, ConsoleOutput, JsonFileOutput


def main():
    """Run the interactive multi-agent system with observation."""
    # Load environment variables
    load_dotenv()

    # Get model provider: CLI arg > env var > default (anthropic)
    model_provider: ModelProvider = "anthropic"
    env_provider_raw = os.getenv("MODEL_PROVIDER", "anthropic")
    logger.info(f"MODEL_PROVIDER env var (raw): '{env_provider_raw}'")

    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        logger.info(f"CLI argument provided: '{arg}'")
        if arg in ["google", "gemini"]:
            model_provider = "google"
        elif arg in ["azure", "azure_openai"]:
            model_provider = "azure_openai"
        elif arg in ["anthropic", "claude"]:
            model_provider = "anthropic"
    else:
        # Fallback to env var
        env_provider = env_provider_raw.lower()
        if env_provider in ["google", "gemini"]:
            model_provider = "google"
        elif env_provider in ["azure", "azure_openai"]:
            model_provider = "azure_openai"

    logger.info(f"Selected model provider: '{model_provider}'")

    # Verify API keys based on provider
    if model_provider == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("GOOGLE_API_KEY not set")
    elif model_provider == "azure_openai":
        if not os.getenv("AZURE_OPENAI_API_KEY"):
            raise ValueError("AZURE_OPENAI_API_KEY not set")
        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            raise ValueError("AZURE_OPENAI_ENDPOINT not set")
    else:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY not set")

    if not os.getenv("TAVILY_API_KEY"):
        raise ValueError("TAVILY_API_KEY not set")

    # Create agent with selected provider
    agent = create_primary_agent(model_provider=model_provider)

    # Create observer with multiple outputs
    observer = AgentObserver([
        ConsoleOutput(verbose=True, show_tokens=True),
        JsonFileOutput(),  # Auto-generates filename in logs/
    ])

    # Interactive loop
    provider_names = {"google": "Gemini", "azure_openai": "Azure OpenAI", "anthropic": "Claude"}
    provider_name = provider_names.get(model_provider, "Claude")
    print(f"Multi-Agent System Ready! (using {provider_name})")
    print("Commands: 'quit' to exit\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ["quit", "exit", "q"]:
            break

        if not user_input:
            continue

        # Use observer.run() instead of agent.invoke()
        result = observer.run(
            agent,
            {"messages": [{"role": "user", "content": user_input}]}
        )

        # Get final response
        if result and "messages" in result:
            messages = result["messages"]
            if messages:
                last_msg = messages[-1] if isinstance(messages, list) else messages
                if hasattr(last_msg, "content"):
                    print(f"\nAgent: {last_msg.content}\n")


if __name__ == "__main__":
    main()
