"""Agent creation with Deep Agents SDK.

Architecture:
1. CompositeBackend - Routes paths to appropriate backends
2. FilesystemMiddleware - Provides file tools (ls, read_file, write_file, etc.) [auto-added by SDK]
3. SkillsMiddleware - Discovers SKILL.md, injects into system prompt [auto-added by SDK]
4. create_deep_agent - Assembles the LangGraph agent
"""

from pathlib import Path
import os

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend
from deepagents.backends.filesystem import FilesystemBackend
from langchain_openai import AzureChatOpenAI

from tools.bash_tool import bash_tool


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
):
    """Create agent with Deep Agents SDK.

    Architecture:
    1. CompositeBackend - Routes paths to appropriate backends
    2. FilesystemMiddleware - Provides file tools (auto-added by SDK)
    3. SkillsMiddleware - Discovers SKILL.md (auto-added by SDK when skills param provided)
    4. create_deep_agent - Assembles the LangGraph agent

    Args:
        skills_root: Path to the skills directory.
        workspace_root: Path to the workspace directory for user files.

    Returns:
        CompiledStateGraph (LangGraph compatible)
    """
    skills_path = Path(skills_root).resolve()
    workspace_path = Path(workspace_root).resolve()

    # Step 1: CompositeBackend with route-based path resolution
    # Routes:
    #   /skills/*    -> FilesystemBackend(./skills)
    #   /workspace/* -> FilesystemBackend(./workspace)
    #   default      -> StateBackend (temporary storage)
    backend = lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={
            "/skills/": FilesystemBackend(root_dir=str(skills_path), virtual_mode=True),
            "/workspace/": FilesystemBackend(root_dir=str(workspace_path), virtual_mode=True),
        },
    )

    # Step 2: Azure OpenAI model
    model = create_azure_model()

    # Step 3: System prompt with file access info
    system_prompt = """You are a helpful assistant that can execute skills.

## File Access
- Skills are at: /skills/
- User files are at: /workspace/
- Use read_file/write_file tools to access files
- Use bash_tool to execute skill scripts

Example: "analyze sample.csv" means:
1. read_file("/workspace/sample.csv") to check the file
2. bash_tool("python skills/data-analysis/scripts/analyze.py workspace/sample.csv")
"""

    # Step 4: Create agent with SDK
    # SDK auto-adds: FilesystemMiddleware, SkillsMiddleware (when skills param provided)
    # Returns CompiledStateGraph (LangGraph compatible)
    agent = create_deep_agent(
        model=model,
        tools=[bash_tool],
        backend=backend,
        skills=["/skills/"],  # SDK auto-creates SkillsMiddleware
        system_prompt=system_prompt,
    )

    return agent
