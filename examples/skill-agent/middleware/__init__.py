"""Middleware exports for skill agent.

With DockerBackend as the default backend in CompositeBackend,
the original deepagents FilesystemMiddleware works correctly without patches.
"""

from deepagents import FilesystemMiddleware


__all__ = ["FilesystemMiddleware"]
