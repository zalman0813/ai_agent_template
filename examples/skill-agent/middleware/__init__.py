"""Custom middleware with fixed execution detection for ExecutableCompositeBackend.

This module patches deepagents' _supports_execution function to fix a bug where
ExecutableCompositeBackend's execution support isn't detected properly.
"""

from collections.abc import Awaitable, Callable
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from deepagents import FilesystemMiddleware
from deepagents.backends.composite import CompositeBackend
from deepagents.backends.protocol import BackendProtocol, SandboxBackendProtocol


def _supports_execution_fixed(backend: BackendProtocol) -> bool:
    """Fixed version: Check if CompositeBackend itself implements SandboxBackendProtocol first.

    Original bug: deepagents only checks backend.default for CompositeBackend,
    ignoring when the CompositeBackend itself implements SandboxBackendProtocol.

    Fix: Check if CompositeBackend itself implements SandboxBackendProtocol before
    checking its default backend.
    """
    if isinstance(backend, CompositeBackend):
        # First check if the CompositeBackend itself implements SandboxBackendProtocol
        if isinstance(backend, SandboxBackendProtocol):
            return True
        # Fall back to checking default backend
        return isinstance(backend.default, SandboxBackendProtocol)

    return isinstance(backend, SandboxBackendProtocol)


# Monkey patch: Replace deepagents' _supports_execution with our fixed version
# This is necessary because the execute tool also calls _supports_execution at runtime,
# and we need to ensure it uses our fixed logic instead of the buggy original.
import deepagents.middleware.filesystem as filesystem_module
filesystem_module._supports_execution = _supports_execution_fixed


class FixedFilesystemMiddleware(FilesystemMiddleware):
    """FilesystemMiddleware with fixed execution detection.

    Fixes the bug where ExecutableCompositeBackend's execute support isn't detected
    because the original _supports_execution() only checks backend.default instead of
    checking if the CompositeBackend itself implements SandboxBackendProtocol.

    Implementation: Completely overrides wrap_model_call and awrap_model_call to use
    the fixed _supports_execution_fixed() function instead of calling the parent's buggy version.
    """

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Update the system prompt and filter tools based on backend capabilities.

        This is a complete copy of the parent's wrap_model_call but uses _supports_execution_fixed
        instead of _supports_execution.
        """
        # Import constants from parent module
        from deepagents.middleware.filesystem import FILESYSTEM_SYSTEM_PROMPT, EXECUTION_SYSTEM_PROMPT

        # Check if execute tool is present and if backend supports it
        has_execute_tool = any(
            (tool.name if hasattr(tool, "name") else tool.get("name")) == "execute"
            for tool in request.tools
        )

        backend_supports_execution = False
        if has_execute_tool:
            # Resolve backend to check execution support
            backend = self._get_backend(request.runtime)
            backend_supports_execution = _supports_execution_fixed(backend)  # ✓ Use fixed version

            # If execute tool exists but backend doesn't support it, filter it out
            if not backend_supports_execution:
                filtered_tools = [
                    tool for tool in request.tools
                    if (tool.name if hasattr(tool, "name") else tool.get("name")) != "execute"
                ]
                request = request.override(tools=filtered_tools)
                has_execute_tool = False

        # Use custom system prompt if provided, otherwise generate dynamically
        if self._custom_system_prompt is not None:
            system_prompt = self._custom_system_prompt
        else:
            # Build dynamic system prompt based on available tools
            prompt_parts = [FILESYSTEM_SYSTEM_PROMPT]

            # Add execution instructions if execute tool is available
            if has_execute_tool and backend_supports_execution:
                prompt_parts.append(EXECUTION_SYSTEM_PROMPT)

            system_prompt = "\n\n".join(prompt_parts)

        if system_prompt:
            request = request.override(
                system_prompt=request.system_prompt + "\n\n" + system_prompt
                if request.system_prompt
                else system_prompt
            )

        return handler(request)  # ✓ Don't call super().wrap_model_call()

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """(async) Update the system prompt and filter tools based on backend capabilities.

        This is a complete copy of the parent's awrap_model_call but uses _supports_execution_fixed
        instead of _supports_execution.
        """
        # Import constants from parent module
        from deepagents.middleware.filesystem import FILESYSTEM_SYSTEM_PROMPT, EXECUTION_SYSTEM_PROMPT

        # Check if execute tool is present and if backend supports it
        has_execute_tool = any(
            (tool.name if hasattr(tool, "name") else tool.get("name")) == "execute"
            for tool in request.tools
        )

        backend_supports_execution = False
        if has_execute_tool:
            # Resolve backend to check execution support
            backend = self._get_backend(request.runtime)
            backend_supports_execution = _supports_execution_fixed(backend)  # ✓ Use fixed version

            # If execute tool exists but backend doesn't support it, filter it out
            if not backend_supports_execution:
                filtered_tools = [
                    tool for tool in request.tools
                    if (tool.name if hasattr(tool, "name") else tool.get("name")) != "execute"
                ]
                request = request.override(tools=filtered_tools)
                has_execute_tool = False

        # Use custom system prompt if provided, otherwise generate dynamically
        if self._custom_system_prompt is not None:
            system_prompt = self._custom_system_prompt
        else:
            # Build dynamic system prompt based on available tools
            prompt_parts = [FILESYSTEM_SYSTEM_PROMPT]

            # Add execution instructions if execute tool is available
            if has_execute_tool and backend_supports_execution:
                prompt_parts.append(EXECUTION_SYSTEM_PROMPT)

            system_prompt = "\n\n".join(prompt_parts)

        if system_prompt:
            request = request.override(
                system_prompt=request.system_prompt + "\n\n" + system_prompt
                if request.system_prompt
                else system_prompt
            )

        return await handler(request)  # ✓ Don't call super().awrap_model_call()
