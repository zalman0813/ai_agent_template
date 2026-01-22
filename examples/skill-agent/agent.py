"""Agent creation with manual middleware configuration.

Architecture:
1. DockerBackend + CompositeBackend - Sandboxed execution with path routing
   Backend Configuration:
   - Default: DockerBackend (sandboxed execution in Docker container)
   - /skills/: FilesystemBackend(./skills) - Fast host reads for skill definitions
   - /workspace/: FilesystemBackend(./workspace) - Fast host reads for user files
   - Docker volumes ensure container can access both /skills and /workspace during execution
2. Manual middleware stack:
   - TodoListMiddleware - Provides todo management tools
   - SkillsMiddleware - Automatic skill discovery and documentation injection
   - FilesystemMiddleware - Provides file tools and execute support
   - CustomSubAgentMiddleware - Provides task delegation with event streaming
   - SummarizationMiddleware - Automatic conversation summarization
   - AnthropicPromptCachingMiddleware - Prompt caching for Claude models
   - PatchToolCallsMiddleware - Tool call patching for compatibility
3. create_agent - Assembles the LangGraph agent with custom middleware
"""

from pathlib import Path
import os
import sys
from typing import TYPE_CHECKING

# Add parent directory to path for src imports
parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware, SummarizationMiddleware
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from deepagents.backends import StateBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.composite import CompositeBackend
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.skills import SkillsMiddleware
from deepagents.middleware.filesystem import FilesystemMiddleware
from langchain_openai import AzureChatOpenAI

from backends import DockerBackend
from src.middleware import CustomSubAgentMiddleware

if TYPE_CHECKING:
    from src.observation.outputs import OutputHandler


def create_azure_model() -> AzureChatOpenAI:
    """Create Azure OpenAI model from environment.

    Required environment variables:
    - AZURE_OPENAI_API_KEY
    - AZURE_OPENAI_ENDPOINT
    - AZURE_OPENAI_DEPLOYMENT_NAME

    Optional:
    - AZURE_OPENAI_API_VERSION (default: 2024-08-01-preview)
    """
    return AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    )


def create_skill_agent(
    skills_root: str | Path = "./skills",
    workspace_root: str | Path = "./workspace",
    output_handlers: list["OutputHandler"] | None = None,
):
    """Create agent with manual middleware configuration.

    Architecture:
    1. DockerBackend + CompositeBackend - Sandboxed execution with path routing
    2. Manual middleware stack with CustomSubAgentMiddleware for event visibility
    3. create_agent - Assembles the LangGraph agent

    Args:
        skills_root: Path to the skills directory.
        workspace_root: Path to the workspace directory for user files.
        output_handlers: Optional output handlers for streaming subagent events.
            When provided, enables visibility into subagent tool calls and lifecycle.

    Returns:
        CompiledStateGraph (LangGraph compatible)
    """
    skills_path = Path(skills_root).resolve()
    workspace_path = Path(workspace_root).resolve()
    project_root = Path(__file__).parent

    # Step 1: Azure OpenAI model
    model = create_azure_model()

    # Step 2: DockerBackend + CompositeBackend for sandboxed execution
    # Architecture:
    #   - DockerBackend: Provides sandboxed execution in Docker container
    #   - Routes: Optimize file reads by routing to host FilesystemBackend
    #     /skills/*    -> FilesystemBackend(./skills) - Fast host reads
    #     /workspace/* -> FilesystemBackend(./workspace) - Fast host reads
    #   - Volumes: Enable container access to host directories during execution
    #
    # Flow:
    #   1. read("/skills/script.py") → FilesystemBackend (host, fast)
    #   2. execute("python /skills/script.py") → DockerBackend (container, via volume)
    #   3. Volume ensures container can access /skills/script.py from host
    #
    # Note: Create backend with lambda factory for StateBackend (needs runtime)

    # Create DockerBackend with auto-start (will create/start container if needed)
    docker_backend = DockerBackend(
        image="skill-agent:latest",
        container_name="skill-agent-container",
        workdir="/workspace",
        volumes={
            str(workspace_path): "/workspace",
            str(skills_path): "/skills",
        },
        auto_start=True,
    )

    backend_factory = lambda rt: CompositeBackend(
        default=docker_backend,
        routes={
            "/skills/": FilesystemBackend(root_dir=str(skills_path), virtual_mode=True),
            "/workspace/": FilesystemBackend(root_dir=str(workspace_path), virtual_mode=True),
        },
    )

    # Step 3: Build middleware stack manually (replicating create_deep_agent behavior)
    middleware_stack = [
        # Todo management
        TodoListMiddleware(),
        # Skills discovery and documentation
        SkillsMiddleware(
            backend=backend_factory,  # Reuse same backend as FilesystemMiddleware
            sources=["/skills/"]  # Path will be routed to actual skills directory
        ),
        # File operations and command execution (sandboxed via DockerBackend)
        FilesystemMiddleware(backend=backend_factory),
        # Subagent delegation with event streaming
        CustomSubAgentMiddleware(
            default_model=model,
            default_tools=[],  # general-purpose subagent inherits all tools
            subagents=[],  # No custom subagents, only general-purpose
            include_general_purpose=True,
            stream_subagent_events=output_handlers is not None,
            output_handlers=output_handlers,
            # Default middleware for subagents (same as create_deep_agent)
            default_middleware=[
                TodoListMiddleware(),
                SkillsMiddleware(
                    backend=backend_factory,
                    sources=["/skills/"]
                ),
                FilesystemMiddleware(backend=backend_factory),
                SummarizationMiddleware(
                    model=model,
                    max_tokens_before_summary=170000,
                    messages_to_keep=6,
                ),
                AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
                PatchToolCallsMiddleware(),
            ],
        ),
        # Conversation summarization
        SummarizationMiddleware(
            model=model,
            max_tokens_before_summary=170000,
            messages_to_keep=6,
        ),
        # Prompt caching for Claude models
        AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
        # Tool call patching for compatibility
        PatchToolCallsMiddleware(),
    ]

    # Step 4: System prompt with file access and skill execution info
    system_prompt = """You are a helpful assistant with access to skills and file operations.

## Available Tools

You have access to:
- **File tools**: ls, read_file, write_file, edit_file, glob, grep
- **Execute tool**: Run Python scripts and commands
- **Task tool**: Delegate complex multi-step tasks to subagents (if enabled)

## Skills

Skills are automatically discovered and documented. Each skill provides specialized capabilities.

### How to Use Skills

1. **Read the skill documentation**: When you see a skill in <available_skills>, read its full documentation using read_file() to understand what it does and how to use it.

2. **Follow skill instructions**: Skills may include:
   - Python scripts in scripts/ directory
   - Step-by-step usage instructions
   - Example commands to execute

3. **Execute skill scripts**: Many skills require script execution. Use the execute() tool to run them:
   ```
   execute(command="python3 /skills/skill-name/scripts/script_name.py <args>")
   ```

4. **Check skill requirements**: Some skills REQUIRE script execution because the AI cannot perform the operation directly:
   - Cryptographic hash calculation (MD5, SHA256, SHA512)
   - Binary file processing
   - External API calls
   - Complex data transformations

### When to Execute vs Delegate

- **Use execute() tool directly** when:
  - A skill provides a script to run
  - The task requires cryptographic operations
  - The task involves binary file processing
  - The skill documentation says "requires script execution"

- **Use task() tool to delegate** when:
  - The task is complex and multi-step
  - No specific skill script is available
  - The task requires multiple tool calls and reasoning

### Important Notes

- **You CANNOT compute cryptographic hashes** - you must execute the hash script
- **Read skill documentation first** - don't assume how skills work
- **Follow the exact command format** provided in skill documentation
- **Check file paths** - use /skills/ and /workspace/ prefixes as documented
"""

    # Step 5: Create agent with manual middleware
    agent = create_agent(
        model,
        system_prompt=system_prompt,
        tools=[],  # Tools provided by middleware
        middleware=middleware_stack,
    )

    return agent
