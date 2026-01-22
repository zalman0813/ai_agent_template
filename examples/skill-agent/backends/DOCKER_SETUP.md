# Docker Setup Guide for Skill-Agent

This guide explains how to set up and use the DockerBackend for sandboxed skill execution.

## Overview

The skill-agent uses a **DockerBackend** for sandboxed execution, providing:
- **Security**: Isolated execution environment for potentially untrusted code
- **Reproducibility**: Consistent container environment across systems
- **Auto-management**: Automatic container creation and startup
- **Performance**: Optimized file operations via CompositeBackend routes

## Architecture

### Backend Configuration

```
CompositeBackend
├── default: DockerBackend (sandboxed execution)
│   ├── Container: skill-agent-container
│   ├── Image: skill-agent:latest
│   └── Volumes: /skills, /workspace mounted from host
└── routes: FilesystemBackend (fast host file reads)
    ├── /skills/ → ./skills (host directory)
    └── /workspace/ → ./workspace (host directory)
```

### Execution Flow

1. **File reads** → FilesystemBackend (host, fast)
   - `read_file("/skills/script.py")` reads directly from host

2. **Command execution** → DockerBackend (container, sandboxed)
   - `execute("python /skills/script.py")` runs in container

3. **Volume access** → Host directories accessible in container
   - Container can access `/skills` and `/workspace` via Docker volumes

## Prerequisites

### 1. Install Docker

**macOS**:
```bash
# Install Docker Desktop for Mac
# Download from: https://www.docker.com/products/docker-desktop

# Or install via Homebrew
brew install --cask docker
```

**Linux**:
```bash
# Install Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (avoid sudo)
sudo usermod -aG docker $USER
newgrp docker
```

**Windows**:
```bash
# Install Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop
```

### 2. Verify Docker Installation

```bash
docker --version
# Should output: Docker version XX.X.X, build XXXXXXX

docker ps
# Should list running containers (empty if none running)
```

## Setup

### 1. Build the Custom Docker Image

The skill-agent uses a custom Docker image with pre-installed dependencies:

```bash
cd examples/skill-agent
docker build -t skill-agent:latest .
```

This builds an image with:
- Python 3.11-slim base
- Common packages: requests, curl, git
- Working directory: /workspace

**Customize the image**: Edit `Dockerfile` to add dependencies your skills need:
```dockerfile
RUN pip install --no-cache-dir \
    requests \
    pandas \
    numpy \
    your-package-here
```

### 2. Verify Image Build

```bash
docker images | grep skill-agent
# Should output: skill-agent   latest   XXXXXXXXX   X minutes ago   XXX MB
```

## Usage

### Basic Usage

The DockerBackend automatically manages the container lifecycle:

```python
from agent import create_skill_agent

# Create agent - container auto-created and started if needed
agent = create_skill_agent(
    skills_root="./skills",
    workspace_root="./workspace"
)

# Use agent - executes in Docker container
response = agent.invoke({"messages": [{"role": "user", "content": "Run file-hash skill"}]})

# Container persists after agent stops (reused on next run)
```

### Container Lifecycle

#### Auto-Start Mode (Default)

```python
from backends import DockerBackend

docker_backend = DockerBackend(
    image="skill-agent:latest",
    container_name="skill-agent-container",
    workdir="/workspace",
    volumes={
        "/host/path/workspace": "/workspace",
        "/host/path/skills": "/skills",
    },
    auto_start=True,  # Default: automatically manage container
)
```

**Behavior**:
1. **Container doesn't exist** → Creates new container with volumes
2. **Container exists but stopped** → Starts the container
3. **Container already running** → Reuses existing container

#### Manual Mode

```python
docker_backend = DockerBackend(
    auto_start=False,  # Manual mode: container must exist and be running
    ...
)
```

**Use case**: Pre-create container with custom configuration, then use it.

### Container Management

#### Check Container Status

```bash
# List all containers (including stopped)
docker ps -a | grep skill-agent-container

# Check if container is running
docker inspect -f '{{.State.Running}}' skill-agent-container
```

#### Manual Container Start/Stop

```bash
# Start stopped container
docker start skill-agent-container

# Stop running container
docker stop skill-agent-container

# Remove container (will be recreated on next agent run)
docker rm skill-agent-container
```

#### Cleanup Container

```python
from backends import DockerBackend

docker_backend = DockerBackend(...)
# ... use the backend ...
docker_backend.stop()  # Stops and removes container
```

Or manually:
```bash
docker stop skill-agent-container
docker rm skill-agent-container
```

## Configuration

### Volume Mounts

Volumes enable the container to access host directories during execution:

```python
volumes={
    "/absolute/host/path/workspace": "/workspace",  # Must be absolute paths
    "/absolute/host/path/skills": "/skills",
}
```

**Important**:
- Use absolute paths for host directories
- Container paths should match routes in CompositeBackend
- Volumes are configured at container creation (can't change without recreating)

### Working Directory

The working directory inside the container:

```python
docker_backend = DockerBackend(
    workdir="/workspace",  # Commands execute from this directory
    ...
)
```

Commands like `execute("python script.py")` run from `/workspace`.

### Execution Timeout

Configure timeout for command execution:

```python
docker_backend = DockerBackend(
    timeout=60,  # Default: 60 seconds
    ...
)
```

Commands exceeding this timeout return with exit code -1.

### Custom Container Name

Use a custom container name for identification:

```python
docker_backend = DockerBackend(
    container_name="my-custom-agent-container",
    ...
)
```

Useful when running multiple skill-agent instances.

## Troubleshooting

### Docker Not Found

**Error**: `RuntimeError: Docker is not available`

**Solution**:
1. Install Docker (see Prerequisites)
2. Ensure Docker daemon is running: `docker ps`
3. On Linux, add user to docker group: `sudo usermod -aG docker $USER`

### Image Not Found

**Error**: `RuntimeError: Docker image 'skill-agent:latest' not found`

**Solution**: Build the image:
```bash
cd examples/skill-agent
docker build -t skill-agent:latest .
```

### Container Creation Failed

**Error**: `RuntimeError: Failed to create container`

**Possible causes**:
1. Port conflicts (if exposing ports)
2. Invalid volume paths (must be absolute)
3. Insufficient Docker resources

**Solution**:
1. Check Docker logs: `docker logs skill-agent-container`
2. Verify volume paths exist: `ls /host/path/workspace`
3. Try manual creation: `docker run -d --name skill-agent-container -v ...`

### Permission Denied (Linux)

**Error**: `permission denied while trying to connect to the Docker daemon socket`

**Solution**: Add user to docker group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Container Timeout

**Error**: Commands timing out

**Solution**:
1. Increase timeout: `DockerBackend(timeout=120)`
2. Check container health: `docker exec skill-agent-container echo "test"`
3. Check container logs: `docker logs skill-agent-container`

### Volume Access Issues

**Error**: Container cannot access files in `/skills` or `/workspace`

**Solution**:
1. Verify volume mounts: `docker inspect skill-agent-container | grep Mounts -A 10`
2. Check file permissions on host
3. Ensure absolute paths in volume configuration
4. Recreate container: `docker rm skill-agent-container` (will auto-recreate on next run)

## Advanced Topics

### Multiple Agent Instances

Run multiple skill-agent instances with separate containers:

```python
# Agent 1
agent1 = create_skill_agent(...)  # Uses default container name

# Agent 2 - requires custom container name
from backends import DockerBackend
docker_backend2 = DockerBackend(
    container_name="skill-agent-container-2",
    ...
)
# ... configure agent2 with docker_backend2 ...
```

### Custom Image Dependencies

Add dependencies to `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /workspace

# Add Python packages
RUN pip install --no-cache-dir \
    requests \
    pandas \
    numpy \
    scikit-learn \
    pillow

# Add system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

CMD ["tail", "-f", "/dev/null"]
```

Rebuild image:
```bash
docker build -t skill-agent:latest .
```

### Pre-Creating Container

Create container manually before running agent:

```bash
docker run -d \
  --name skill-agent-container \
  -v /host/path/workspace:/workspace \
  -v /host/path/skills:/skills \
  -w /workspace \
  skill-agent:latest \
  tail -f /dev/null
```

Then use with `auto_start=False`:
```python
docker_backend = DockerBackend(auto_start=False, ...)
```

### Container Logs

View container logs for debugging:

```bash
# View all logs
docker logs skill-agent-container

# Follow logs in real-time
docker logs -f skill-agent-container

# View last 50 lines
docker logs --tail 50 skill-agent-container
```

## Security Considerations

### Sandboxing Benefits

- **Isolation**: Code runs in isolated container, not on host
- **Resource limits**: Docker can limit CPU, memory, network
- **Read-only volumes**: Mount volumes as read-only when possible

### Best Practices

1. **Minimal image**: Only install necessary dependencies
2. **Non-root user**: Run container as non-root user (add to Dockerfile)
3. **Resource limits**: Set CPU and memory limits (via Docker)
4. **Network isolation**: Disable network if not needed
5. **Read-only volumes**: Mount volumes as read-only when appropriate

### Example: Enhanced Security Configuration

```python
# For maximum security, configure container manually:
docker_cmd = """
docker run -d \
  --name skill-agent-container \
  --user 1000:1000 \
  --memory=512m \
  --cpus=1.0 \
  --network=none \
  -v /host/path/workspace:/workspace \
  -v /host/path/skills:/skills:ro \
  -w /workspace \
  skill-agent:latest \
  tail -f /dev/null
"""

# Then use with auto_start=False
docker_backend = DockerBackend(auto_start=False, ...)
```

## Migration from ExecutableCompositeBackend

This is a **breaking change** from the previous `ExecutableCompositeBackend`.

### Key Differences

| Feature | ExecutableCompositeBackend | DockerBackend |
|---------|---------------------------|---------------|
| Execution | Host subprocess | Docker container |
| Security | No isolation | Sandboxed |
| Setup | No setup | Docker + image build |
| Path translation | Automatic | Via volumes |
| Monkey patch | Required | Not needed |

### Migration Steps

1. **Install Docker** (see Prerequisites)
2. **Build image**: `docker build -t skill-agent:latest .`
3. **Update code**: No changes needed in agent usage
4. **Test skills**: Verify skills work in container

### Known Issues

- **Slower startup**: Container creation adds ~1-2 seconds
- **Volume performance**: May be slower on macOS (use `:delegated` flag)
- **Path changes**: All paths must be absolute in volume configuration

## Support

For issues or questions:
- Check troubleshooting section above
- Review Docker documentation: https://docs.docker.com/
- Check skill-agent issues/documentation
