"""Docker-based sandboxed backend for skill execution."""

import subprocess
import time
from typing import Any

from deepagents.backends.sandbox import BaseSandbox
from deepagents.backends.protocol import (
    ExecuteResponse,
    FileUploadResponse,
    FileDownloadResponse,
)


class DockerBackend(BaseSandbox):
    """Docker-based sandbox backend that inherits from BaseSandbox.

    Provides sandboxed execution in a Docker container with automatic
    container lifecycle management.

    Features:
    - Auto-start: Automatically creates and starts container if needed
    - Auto-create: Creates container with configured volumes
    - Reuse: Reuses existing running containers
    - Cleanup: stop() method for container cleanup

    Args:
        image: Docker image name (default: "skill-agent:latest")
        container_name: Container name for identification
        workdir: Working directory inside container
        volumes: Host path -> container path mappings
        timeout: Command execution timeout in seconds
        auto_start: Automatically start container if not running
    """

    def __init__(
        self,
        image: str = "skill-agent:latest",
        container_name: str = "skill-agent-container",
        workdir: str = "/workspace",
        volumes: dict[str, str] | None = None,
        timeout: int = 60,
        auto_start: bool = True,
    ):
        self.image = image
        self.container_name = container_name
        self.workdir = workdir
        self.volumes = volumes or {}
        self.timeout = timeout

        if auto_start:
            self._ensure_container_running()
        else:
            self._verify_container()

    def _check_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _ensure_container_running(self):
        """Start container if not running, create if doesn't exist."""
        # Check if Docker is available
        if not self._check_docker_available():
            raise RuntimeError(
                "Docker is not available. Please install Docker and ensure it's running.\n"
                "Visit https://docs.docker.com/get-docker/ for installation instructions."
            )

        # Check if container exists
        if not self._container_exists():
            self._create_container()

        # Check if container is running
        if not self._container_is_running():
            self._start_container()

    def _verify_container(self):
        """Verify container exists and is running when auto_start=False."""
        if not self._check_docker_available():
            raise RuntimeError(
                "Docker is not available. Please install Docker and ensure it's running."
            )

        if not self._container_exists():
            raise RuntimeError(
                f"Container '{self.container_name}' does not exist. "
                "Set auto_start=True or create the container manually."
            )

        if not self._container_is_running():
            raise RuntimeError(
                f"Container '{self.container_name}' is not running. "
                "Set auto_start=True or start the container manually."
            )

    def _container_exists(self) -> bool:
        """Check if container exists."""
        try:
            result = subprocess.run(
                ["docker", "inspect", self.container_name],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker command timed out while checking container existence")

    def _container_is_running(self) -> bool:
        """Check if container is running."""
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self.container_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() == "true"
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker command timed out while checking container status")

    def _image_exists(self) -> bool:
        """Check if Docker image exists."""
        try:
            result = subprocess.run(
                ["docker", "inspect", self.image],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker command timed out while checking image existence")

    def _create_container(self):
        """Create new container with configured volumes."""
        # Check if image exists
        if not self._image_exists():
            raise RuntimeError(
                f"Docker image '{self.image}' not found.\n"
                f"Please build the image first:\n"
                f"  cd examples/skill-agent\n"
                f"  docker build -t {self.image} ."
            )

        cmd = ["docker", "run", "-d", "--name", self.container_name]

        # Add volume mounts
        for host_path, container_path in self.volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])

        # Set working directory and image
        cmd.extend(["-w", self.workdir, self.image, "tail", "-f", "/dev/null"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to create container '{self.container_name}':\n{e.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Docker container creation timed out after 30 seconds"
            )

    def _start_container(self):
        """Start stopped container."""
        try:
            subprocess.run(
                ["docker", "start", self.container_name],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to start container '{self.container_name}':\n{e.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker container start timed out after 10 seconds")

    def stop(self):
        """Stop and remove container (cleanup)."""
        try:
            # Stop container
            subprocess.run(
                ["docker", "stop", self.container_name],
                capture_output=True,
                timeout=10,
            )
            # Remove container
            subprocess.run(
                ["docker", "rm", self.container_name],
                capture_output=True,
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Docker cleanup timed out")

    def execute(self, command: str) -> ExecuteResponse:
        """Execute command in Docker container via docker exec.

        Args:
            command: Shell command to execute

        Returns:
            ExecuteResponse with combined output and exit code
        """
        docker_cmd = [
            "docker", "exec",
            "-w", self.workdir,
            self.container_name,
            "bash", "-c", command
        ]

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            # Combine stdout and stderr into single output
            output = result.stdout
            if result.stderr:
                if output:
                    output += "\n" + result.stderr
                else:
                    output = result.stderr

            return ExecuteResponse(
                output=output,
                exit_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return ExecuteResponse(
                output=f"Command timed out after {self.timeout} seconds",
                exit_code=-1,
            )
        except Exception as e:
            return ExecuteResponse(
                output=f"Execution error: {str(e)}",
                exit_code=-1,
            )

    def upload_files(self, files: list[Any]) -> list[FileUploadResponse]:
        """Not implemented - use Docker volumes for file access."""
        raise NotImplementedError(
            "DockerBackend does not support upload_files. "
            "Use Docker volumes to share files between host and container."
        )

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Not implemented - use Docker volumes for file access."""
        raise NotImplementedError(
            "DockerBackend does not support download_files. "
            "Use Docker volumes to share files between host and container."
        )

    @property
    def id(self) -> str:
        """Unique identifier for this sandbox."""
        return f"docker:{self.container_name}"
