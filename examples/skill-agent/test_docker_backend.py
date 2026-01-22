"""Test suite for DockerBackend implementation.

Tests cover:
- Auto-start functionality (create, start, reuse)
- Container lifecycle management
- Command execution (basic, Python, skills)
- File operations via BaseSandbox
- Volume access verification
- Error handling (timeout, invalid commands, Docker not installed)
"""

import subprocess
import tempfile
import time
from pathlib import Path

import pytest

from backends import DockerBackend


# Fixtures

@pytest.fixture(scope="session")
def docker_available():
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
        pytest.skip("Docker not available")


@pytest.fixture(scope="session")
def image_available(docker_available):
    """Check if skill-agent:latest image exists."""
    result = subprocess.run(
        ["docker", "inspect", "skill-agent:latest"],
        capture_output=True,
        timeout=5,
    )
    if result.returncode != 0:
        pytest.skip(
            "Docker image 'skill-agent:latest' not found. "
            "Build it with: docker build -t skill-agent:latest ."
        )


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "workspace"
        workspace.mkdir()

        # Create test files
        (workspace / "test.txt").write_text("Hello, World!")
        (workspace / "test.py").write_text("print('Hello from Python')")

        yield workspace


@pytest.fixture
def temp_skills():
    """Create temporary skills directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills = Path(tmpdir) / "skills"
        skills.mkdir()

        # Create a simple test skill
        skill_dir = skills / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "script.py").write_text(
            "import sys; print(f'Args: {sys.argv[1:]}')"
        )

        yield skills


@pytest.fixture
def docker_backend(temp_workspace, temp_skills, image_available):
    """Create DockerBackend instance with auto-cleanup."""
    backend = None
    try:
        backend = DockerBackend(
            image="skill-agent:latest",
            container_name="test-skill-agent-container",
            workdir="/workspace",
            volumes={
                str(temp_workspace): "/workspace",
                str(temp_skills): "/skills",
            },
            timeout=30,
            auto_start=True,
        )
        yield backend
    finally:
        # Cleanup
        if backend:
            try:
                backend.stop()
            except Exception:
                pass  # Ignore cleanup errors


# Tests: Auto-Start Functionality

def test_auto_start_creates_container(temp_workspace, temp_skills, image_available):
    """Test that auto_start creates container if it doesn't exist."""
    container_name = "test-auto-create-container"

    # Ensure container doesn't exist
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
    )

    try:
        backend = DockerBackend(
            image="skill-agent:latest",
            container_name=container_name,
            workdir="/workspace",
            volumes={
                str(temp_workspace): "/workspace",
                str(temp_skills): "/skills",
            },
            auto_start=True,
        )

        # Verify container exists and is running
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "true"

    finally:
        # Cleanup
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


def test_auto_start_starts_stopped_container(temp_workspace, temp_skills, image_available):
    """Test that auto_start starts a stopped container."""
    container_name = "test-auto-start-container"

    # Create stopped container
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", container_name,
            "-v", f"{temp_workspace}:/workspace",
            "-v", f"{temp_skills}:/skills",
            "-w", "/workspace",
            "skill-agent:latest",
            "tail", "-f", "/dev/null"
        ],
        capture_output=True,
        check=True,
    )
    subprocess.run(["docker", "stop", container_name], capture_output=True, check=True)

    # Verify container is stopped
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "false"

    try:
        # Create backend with auto_start
        backend = DockerBackend(
            image="skill-agent:latest",
            container_name=container_name,
            workdir="/workspace",
            volumes={
                str(temp_workspace): "/workspace",
                str(temp_skills): "/skills",
            },
            auto_start=True,
        )

        # Verify container is now running
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "true"

    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


def test_auto_start_reuses_running_container(temp_workspace, temp_skills, image_available):
    """Test that auto_start reuses an existing running container."""
    container_name = "test-auto-reuse-container"

    # Create and start container
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
    subprocess.run(
        [
            "docker", "run", "-d",
            "--name", container_name,
            "-v", f"{temp_workspace}:/workspace",
            "-v", f"{temp_skills}:/skills",
            "-w", "/workspace",
            "skill-agent:latest",
            "tail", "-f", "/dev/null"
        ],
        capture_output=True,
        check=True,
    )

    try:
        # Get container ID
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.Id}}", container_name],
            capture_output=True,
            text=True,
        )
        original_id = result.stdout.strip()

        # Create backend with auto_start
        backend = DockerBackend(
            image="skill-agent:latest",
            container_name=container_name,
            workdir="/workspace",
            volumes={
                str(temp_workspace): "/workspace",
                str(temp_skills): "/skills",
            },
            auto_start=True,
        )

        # Verify same container (not recreated)
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.Id}}", container_name],
            capture_output=True,
            text=True,
        )
        new_id = result.stdout.strip()
        assert original_id == new_id

    finally:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


# Tests: Command Execution

def test_execute_basic_command(docker_backend):
    """Test executing a basic shell command."""
    response = docker_backend.execute("echo 'Hello, Docker!'")

    assert response.exit_code == 0
    assert "Hello, Docker!" in response.output


def test_execute_python_command(docker_backend):
    """Test executing a Python command."""
    response = docker_backend.execute("python -c \"print('Hello from Python')\"")

    assert response.exit_code == 0
    assert "Hello from Python" in response.output


def test_execute_pwd(docker_backend):
    """Test that working directory is correct."""
    response = docker_backend.execute("pwd")

    assert response.exit_code == 0
    assert response.output.strip() == "/workspace"


def test_execute_with_error(docker_backend):
    """Test executing a command that fails."""
    response = docker_backend.execute("exit 42")

    assert response.exit_code == 42


def test_execute_invalid_command(docker_backend):
    """Test executing a command that doesn't exist."""
    response = docker_backend.execute("nonexistent_command_12345")

    assert response.exit_code != 0
    assert "not found" in response.output or "nonexistent_command_12345" in response.output


# Tests: File Access via Volumes

def test_volume_access_workspace(docker_backend, temp_workspace):
    """Test that container can access workspace files via volumes."""
    # Read file created in fixture
    response = docker_backend.execute("cat /workspace/test.txt")

    assert response.exit_code == 0
    assert "Hello, World!" in response.output


def test_volume_access_skills(docker_backend, temp_skills):
    """Test that container can access skills files via volumes."""
    # List skills directory
    response = docker_backend.execute("ls /skills")

    assert response.exit_code == 0
    assert "test-skill" in response.output


def test_volume_write_access(docker_backend, temp_workspace):
    """Test that container can write to workspace via volumes."""
    # Write to workspace
    response = docker_backend.execute("echo 'Written from Docker' > /workspace/output.txt")
    assert response.exit_code == 0

    # Verify file exists on host
    output_file = temp_workspace / "output.txt"
    assert output_file.exists()
    assert output_file.read_text().strip() == "Written from Docker"


def test_execute_skill_script(docker_backend, temp_skills):
    """Test executing a skill script with arguments."""
    response = docker_backend.execute("python /skills/test-skill/script.py arg1 arg2")

    assert response.exit_code == 0
    assert "Args: ['arg1', 'arg2']" in response.output


# Tests: Timeout Handling

def test_execute_timeout(docker_backend):
    """Test that long-running commands timeout."""
    # Create backend with short timeout
    backend = DockerBackend(
        image="skill-agent:latest",
        container_name="test-timeout-container",
        workdir="/workspace",
        volumes={},
        timeout=2,  # 2 second timeout
        auto_start=True,
    )

    try:
        response = backend.execute("sleep 10")

        assert response.exit_code == -1
        assert "timed out" in response.output.lower()
    finally:
        backend.stop()


# Tests: Container Lifecycle

def test_stop_removes_container(temp_workspace, temp_skills, image_available):
    """Test that stop() removes the container."""
    container_name = "test-stop-container"

    backend = DockerBackend(
        image="skill-agent:latest",
        container_name=container_name,
        workdir="/workspace",
        volumes={
            str(temp_workspace): "/workspace",
            str(temp_skills): "/skills",
        },
        auto_start=True,
    )

    # Verify container exists
    result = subprocess.run(
        ["docker", "inspect", container_name],
        capture_output=True,
    )
    assert result.returncode == 0

    # Stop backend
    backend.stop()

    # Verify container is removed
    result = subprocess.run(
        ["docker", "inspect", container_name],
        capture_output=True,
    )
    assert result.returncode != 0


def test_backend_id_property(docker_backend):
    """Test that id property returns correct format."""
    assert docker_backend.id == "docker:test-skill-agent-container"


# Tests: Error Handling

def test_image_not_found():
    """Test error when Docker image doesn't exist."""
    with pytest.raises(RuntimeError, match="Docker image.*not found"):
        DockerBackend(
            image="nonexistent-image:latest",
            container_name="test-no-image",
            auto_start=True,
        )


def test_upload_files_not_implemented(docker_backend):
    """Test that upload_files raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Use Docker volumes"):
        docker_backend.upload_files([])


def test_download_files_not_implemented(docker_backend):
    """Test that download_files raises NotImplementedError."""
    with pytest.raises(NotImplementedError, match="Use Docker volumes"):
        docker_backend.download_files([])


# Tests: Integration with CompositeBackend

def test_composite_backend_integration(temp_workspace, temp_skills, image_available):
    """Test DockerBackend works with CompositeBackend."""
    from deepagents.backends.composite import CompositeBackend
    from deepagents.backends.filesystem import FilesystemBackend

    docker_backend = DockerBackend(
        image="skill-agent:latest",
        container_name="test-composite-container",
        workdir="/workspace",
        volumes={
            str(temp_workspace): "/workspace",
            str(temp_skills): "/skills",
        },
        auto_start=True,
    )

    try:
        composite = CompositeBackend(
            default=docker_backend,
            routes={
                "/skills/": FilesystemBackend(root_dir=str(temp_skills), virtual_mode=True),
                "/workspace/": FilesystemBackend(root_dir=str(temp_workspace), virtual_mode=True),
            },
        )

        # Test file read via route (should use FilesystemBackend)
        content = composite.read_file("/workspace/test.txt")
        assert "Hello, World!" in content

        # Test execution (should use DockerBackend)
        response = composite.execute("echo 'Composite test'")
        assert response.exit_code == 0
        assert "Composite test" in response.output

    finally:
        docker_backend.stop()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
