"""ExecutableCompositeBackend: CompositeBackend with command execution support.

This backend extends CompositeBackend to support command execution with automatic
virtual path translation. It implements SandboxBackendProtocol, enabling the
FilesystemMiddleware to automatically provide an 'execute' tool to the agent.

Key Features:
- Automatic path translation: /skills/ → skills/, /workspace/ → workspace/
- Fully scalable: Works with any routes without code changes
- Route-based translation: Uses self.routes configuration as single source of truth
- SDK-compliant: Implements SandboxBackendProtocol as designed

Example:
    backend = ExecutableCompositeBackend(
        default=StateBackend(runtime),
        routes={
            "/skills/": FilesystemBackend(root_dir="./skills", virtual_mode=True),
            "/workspace/": FilesystemBackend(root_dir="./workspace", virtual_mode=True),
        },
        execution_cwd=Path.cwd(),
    )

    # Agent can now use: execute("python /skills/script.py /workspace/data.csv")
    # Backend translates to: python skills/script.py workspace/data.csv
"""

import re
import subprocess
from pathlib import Path
from typing import Dict

from deepagents.backends.composite import CompositeBackend
from deepagents.backends.protocol import BackendProtocol, ExecuteResponse, SandboxBackendProtocol


class ExecutableCompositeBackend(CompositeBackend, SandboxBackendProtocol):
    """CompositeBackend with command execution support.

    Extends CompositeBackend to implement SandboxBackendProtocol, enabling command
    execution with automatic virtual path translation based on route configuration.

    Path translation is fully automatic and scalable:
    - Iterates through all configured routes
    - Translates virtual paths to real filesystem paths
    - No hardcoding - works with unlimited routes
    - Add new route → translation works automatically

    Args:
        default: Default backend for unmatched paths
        routes: Mapping of virtual path prefixes to backends
        execution_cwd: Working directory for command execution (default: current directory)
    """

    def __init__(
        self,
        *,
        default: BackendProtocol,
        routes: Dict[str, BackendProtocol],
        execution_cwd: Path | None = None,
    ):
        """Initialize ExecutableCompositeBackend.

        Args:
            default: Default backend for unmatched paths
            routes: Mapping of virtual path prefixes to backends
            execution_cwd: Working directory for command execution
        """
        super().__init__(default=default, routes=routes)
        # Set execution directory (typically project root)
        self.execution_cwd = execution_cwd or Path.cwd()

    def execute(self, command: str) -> ExecuteResponse:
        """Execute command with automatic virtual path translation.

        Translates all virtual paths in the command based on route configuration,
        then executes the command in the configured working directory.

        Translation is fully scalable:
        - /skills/path → skills/path (based on routes["/skills/"])
        - /workspace/path → workspace/path (based on routes["/workspace/"])
        - /any-future-route/path → auto-translated (no code changes needed!)

        Args:
            command: Shell command to execute (may contain virtual paths)

        Returns:
            ExecuteResponse with output and exit code

        Example:
            >>> backend.execute("python /skills/script.py /workspace/data.csv")
            # Translates to: python skills/script.py workspace/data.csv
            # Then executes from execution_cwd
        """
        # Translate all virtual paths using route configuration
        translated_command = self._translate_all_virtual_paths(command)

        # Execute command with proper working directory
        try:
            result = subprocess.run(
                translated_command,
                shell=True,
                cwd=self.execution_cwd,
                capture_output=True,
                text=True,
                timeout=120,
            )

            return ExecuteResponse(
                output=result.stdout + result.stderr,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecuteResponse(
                output="Command execution timed out after 120 seconds",
                exit_code=124,
            )
        except Exception as e:
            return ExecuteResponse(
                output=f"Command execution failed: {str(e)}",
                exit_code=1,
            )

    def _translate_all_virtual_paths(self, command: str) -> str:
        """Translate all virtual paths in command based on route configuration.

        This method is fully scalable and requires zero configuration:
        1. Iterates through all routes in self.routes
        2. For each route, extracts the real filesystem path
        3. Replaces virtual path prefix with relative path
        4. Works with any number of routes without code changes

        Translation preserves:
        - System paths: /usr/bin/python3 → unchanged (not in routes)
        - Command names: python3 → unchanged (not a path)
        - Multiple paths: Handles multiple paths in one command
        - Quoted paths: Handles both quoted and unquoted paths

        Args:
            command: Original command with virtual paths

        Returns:
            Command with all virtual paths translated to relative paths

        Example:
            With routes = {"/skills/": "./skills", "/workspace/": "./workspace"}:

            "python /skills/a.py /workspace/b.csv"
            → "python skills/a.py workspace/b.csv"

            'cat "/workspace/data.json"'
            → 'cat "workspace/data.json"'

            "ls /skills/ /workspace/ /usr/bin"
            → "ls skills/ workspace/ /usr/bin"  (system path preserved)
        """
        translated = command

        # Iterate through all configured routes (scalable!)
        for route_prefix, backend in self.routes.items():
            # Only translate if backend has a real filesystem path
            if hasattr(backend, 'cwd'):
                # Get the real directory path for this route
                real_root = backend.cwd

                try:
                    # Make path relative to execution directory
                    rel_root = real_root.relative_to(self.execution_cwd)
                except ValueError:
                    # If paths are not relative, use absolute path
                    rel_root = real_root

                # Build replacement pattern
                # Example: /skills/ → skills/
                pattern = re.escape(route_prefix)
                replacement = str(rel_root) + '/'

                # Replace in multiple contexts:
                # - Start of string: /skills/path
                # - After whitespace: python /skills/path
                # - After quotes: "/skills/path" or '/skills/path'
                # - After parens: (/skills/path)
                translated = re.sub(
                    rf'(^|\s|["\'(])({pattern})',
                    rf'\1{replacement}',
                    translated
                )

        return translated
