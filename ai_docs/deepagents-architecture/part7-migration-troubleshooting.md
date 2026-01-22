# DeepAgents CLI vs SDK Architecture - Part 7: Migration & Troubleshooting

> **Navigation**: [⬅️ Part 6: Comparison & Patterns](part6-comparison-patterns.md) | [Index](INDEX.md) | [Part 8: Reference ➡️](part8-reference.md)

**Sections**: 13-14 | Migration Guide, Troubleshooting

---

## 13. Migration Guide

This section covers migrating between CLI and SDK approaches.

### 13.1 CLI to SDK Migration

#### Step 1: Identify CLI Commands

Review your CLI-based workflow and identify bash commands:

**CLI Example**:
```python
# bash tool calls
bash("python analyze.py data.csv")
bash("cat results.txt")
bash("echo 'Done' > status.txt")
```

#### Step 2: Choose SDK Backend

Based on your requirements:

```
Need sandboxing? → DockerBackend
Need remote execution? → RemoteBackend
Only need file operations? → FilesystemBackend
```

**Example**: Choose DockerBackend for sandboxed execution.

#### Step 3: Set Up Backend

```python
from backends.docker_backend import DockerBackend
from deepagents.backends.composite import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from pathlib import Path

workspace_path = Path("./workspace").resolve()

docker_backend = DockerBackend(
    image="python:3.11",
    container_name="agent-sandbox",
    workdir="/workspace",
    volumes={
        str(workspace_path): "/workspace",
    },
    auto_start=True,
)

backend_factory = lambda rt: CompositeBackend(
    default=docker_backend,
    routes={
        "/workspace/": FilesystemBackend(
            root_dir=str(workspace_path),
            virtual_mode=True
        ),
    }
)
```

#### Step 4: Convert bash Calls to execute/file Tools

| CLI bash() | SDK Tool | Notes |
|-----------|---------|-------|
| `bash("python script.py")` | `execute("python /workspace/script.py")` | Specify full path |
| `bash("cat file.txt")` | `read_file("/workspace/file.txt")` | Use read_file instead |
| `bash("echo 'data' > file.txt")` | `write_file("/workspace/file.txt", "data")` | Use write_file instead |
| `bash("ls")` | `ls("/workspace/")` | Use ls tool |
| `bash("find . -name '*.py'")` | `glob("**/*.py")` | Use glob for patterns |

**CLI Code**:
```python
# CLI agent
bash("python analyze.py data.csv")
result = bash("cat results.txt")
```

**SDK Code**:
```python
# SDK agent with FilesystemMiddleware
execute("python /workspace/analyze.py /workspace/data.csv")
result = read_file("/workspace/results.txt")
```

#### Step 5: Update System Prompt

**CLI Prompt**:
```
You have access to bash commands. Use bash() to execute commands.
```

**SDK Prompt**:
```
You have access to:
- File tools: read_file, write_file, ls, glob, grep
- Execute tool: execute(command, workdir)

Files are in /workspace/. Use full paths.
```

#### Step 6: Create SDK Agent

```python
from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from deepagents.middleware.filesystem import FilesystemMiddleware

model = ChatAnthropic(model="claude-sonnet-4-5")

middleware = [
    FilesystemMiddleware(backend=backend_factory)
]

agent = create_agent(
    model=model,
    system_prompt=system_prompt,
    tools=[],
    middleware=middleware,
)
```

#### Step 7: Test and Iterate

Test your SDK agent with the same workflows as CLI:

```python
# Test
result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze the dataset"}]
})

print(result['messages'][-1]['content'])
```

### 13.2 SDK to CLI Integration

Sometimes you want to use SDK components in a CLI-like environment.

#### ShellMiddleware Pattern

Create custom middleware that provides bash-like execution:

```python
class ShellMiddleware:
    """Provides direct shell execution (CLI-like)."""

    def modify_tools(self, tools):
        def bash(command: str, description: str = "") -> str:
            """Execute bash command on host."""
            import subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            return result.stdout if result.returncode == 0 else result.stderr

        tools.append(bash)
        return tools

# Usage
from langchain.agents import create_agent

middleware = [
    ShellMiddleware(),  # Provides bash() tool
]

agent = create_agent(
    model=model,
    system_prompt="You have access to bash commands.",
    tools=[],
    middleware=middleware,
)

# Agent now has CLI-like bash() tool
```

### 13.3 Hybrid Approach

Combine CLI and SDK for optimal development workflow:

```
Development Phase: CLI
    ↓
    Fast iteration, learning
    ↓
Build SDK Version
    ↓
    Production-ready, sandboxed
    ↓
Deploy SDK to Production
    ↓
    Continue developing with CLI for new features
    ↓
Update SDK Version
    ↓
    Deploy updates
```

### 13.4 Migration Checklist

**CLI → SDK Migration**:
- [ ] Identify all bash() commands
- [ ] Choose appropriate backend (Docker/Remote/Filesystem)
- [ ] Set up backend with correct paths and volumes
- [ ] Convert bash() to execute() or file tools
- [ ] Update system prompt
- [ ] Create middleware stack
- [ ] Test all workflows
- [ ] Add error handling
- [ ] Configure resource limits (Docker)
- [ ] Set up monitoring/logging

**SDK → CLI Integration**:
- [ ] Identify why CLI approach is needed
- [ ] Create ShellMiddleware (if needed)
- [ ] Test on trusted environment only
- [ ] Document security implications
- [ ] Consider hybrid approach instead

---

## 14. Troubleshooting

Common issues and their solutions.

### 14.1 Backend Issues

#### Issue: "Container not found" or "Container failed to start"

**Symptoms**:
```
DockerBackend execute() fails with "Container agent-sandbox not found"
```

**Causes**:
1. Container doesn't exist
2. Container stopped/removed
3. Docker daemon not running

**Solutions**:

```python
# Solution 1: Enable auto_start
docker = DockerBackend(
    container_name="agent-sandbox",
    auto_start=True,  # Automatically create/start container
)

# Solution 2: Check Docker daemon
# Run in terminal:
docker ps  # Should list containers
docker images  # Should list images

# Solution 3: Manually create container
docker run -d --name agent-sandbox python:3.11 tail -f /dev/null
```

#### Issue: "Permission denied" when accessing files in container

**Symptoms**:
```
execute("python /workspace/script.py") fails with "Permission denied"
```

**Causes**:
1. Volume mount permissions mismatch
2. Container running as different user

**Solutions**:

```python
# Solution 1: Fix volume permissions
# On host:
chmod -R 755 /host/workspace/

# Solution 2: Run container as current user
docker = DockerBackend(
    user=f"{os.getuid()}:{os.getgid()}",  # Run as current user
    ...
)

# Solution 3: Use privileged mode (not recommended)
docker = DockerBackend(
    privileged=True,  # Security risk!
    ...
)
```

#### Issue: "No such file or directory" in container

**Symptoms**:
```
execute("python /skills/script.py") fails with "No such file or directory"
```

**Causes**:
1. Volume not mounted
2. Path mismatch between host and container

**Solutions**:

```python
# Solution: Ensure volume mounts
docker = DockerBackend(
    volumes={
        "/host/skills": "/skills",  # Must match paths used in execute()
    }
)

# Verify mount:
execute("ls /skills")  # Should show skills directory contents
```

#### Issue: StateBackend runtime error

**Symptoms**:
```
TypeError: StateBackend.__init__() missing 1 required positional argument: 'runtime'
```

**Cause**: Creating backend instance directly instead of using factory.

**Solution**:

```python
# ✗ Wrong:
backend = CompositeBackend(
    state_backend=StateBackend(runtime=???),  # No runtime available!
    ...
)

# ✓ Correct:
backend_factory = lambda rt: CompositeBackend(
    state_backend=StateBackend(runtime=rt),  # Runtime injected
    ...
)
```

### 14.2 Middleware Issues

#### Issue: Tools not generated

**Symptoms**:
- Agent doesn't have execute() tool
- Agent doesn't have file tools

**Causes**:
1. FilesystemMiddleware not in middleware stack
2. Backend doesn't support required operations

**Solutions**:

```python
# Solution 1: Add FilesystemMiddleware
middleware = [
    FilesystemMiddleware(backend=backend_factory),  # Add this
    # Other middleware...
]

# Solution 2: Check backend capabilities
# FilesystemBackend: read/write/ls/glob/grep (NO execute)
# DockerBackend: ALL operations including execute
# CompositeBackend: Depends on default backend
```

#### Issue: Skills not discovered

**Symptoms**:
- No <available_skills> in agent context
- Agent doesn't know about skills

**Causes**:
1. SkillsMiddleware not in stack
2. Wrong sources path
3. SKILL.md files missing or invalid

**Solutions**:

```python
# Solution 1: Add SkillsMiddleware
middleware = [
    SkillsMiddleware(
        backend=backend_factory,
        sources=["/skills/"]  # Correct path
    ),
    FilesystemMiddleware(backend=backend_factory),
]

# Solution 2: Verify skills directory structure
# /skills/skill-name/SKILL.md must exist

# Solution 3: Test manually
backend = backend_factory(None)
print(backend.ls("/skills/"))  # Should list skill directories
print(backend.read_file("/skills/file-hash/SKILL.md"))  # Should work
```

#### Issue: Middleware order causing problems

**Symptoms**:
- Sub-agents don't have skills
- Tools missing from sub-agents

**Cause**: Wrong middleware order.

**Solution**:

```python
# ✗ Wrong order:
middleware = [
    SubAgentMiddleware(...),  # Sub-agents created before skills discovered
    SkillsMiddleware(...),
]

# ✓ Correct order:
middleware = [
    SkillsMiddleware(...),    # Discover skills first
    SubAgentMiddleware(...),  # Sub-agents inherit skills
]
```

### 14.3 Skills Issues

#### Issue: Skill script execution fails

**Symptoms**:
```
execute("python /skills/hash/scripts/hash_file.py ...") fails
```

**Causes**:
1. Script has syntax errors
2. Missing dependencies in container
3. Wrong Python version

**Solutions**:

```python
# Solution 1: Test script manually in container
docker exec agent-sandbox python /skills/hash/scripts/hash_file.py --help

# Solution 2: Install dependencies
# In Dockerfile:
RUN pip install requests numpy pandas

# Or at runtime:
execute("pip install requests")

# Solution 3: Check Python version
execute("python --version")  # Should match script requirements
```

#### Issue: Skill not visible to agent

**Symptoms**:
- Skill directory exists
- SKILL.md exists
- Agent doesn't see skill in <available_skills>

**Causes**:
1. SKILL.md missing required frontmatter
2. Syntax error in SKILL.md
3. Wrong sources path

**Solutions**:

```python
# Solution 1: Validate SKILL.md format
# Must have:
# ---
# name: skill-name
# description: Description here
# ---

# Solution 2: Check sources path
middleware = [
    SkillsMiddleware(
        sources=["/skills/"]  # Trailing slash important!
    )
]

# Solution 3: Debug skill discovery
# Add logging to see what's being discovered
```

### 14.4 Path Issues

#### Issue: "Path not found" errors

**Symptoms**:
```
read_file("/workspace/file.txt") fails with "Path not found"
```

**Causes**:
1. Virtual mode path mismatch
2. Route prefix mismatch
3. File doesn't exist

**Solutions**:

```python
# Solution 1: Check virtual_mode configuration
routes={
    "/workspace/": FilesystemBackend(
        root_dir="/host/workspace",
        virtual_mode=True,  # Agent uses /workspace/
        virtual_prefix="/workspace"  # Must match route key
    ),
}

# Solution 2: Verify file exists
# On host:
ls /host/workspace/file.txt

# Solution 3: Debug path resolution
# Add logging to see which backend handles the operation
```

#### Issue: CompositeBackend routing wrong

**Symptoms**:
- File reads go to wrong backend
- execute() fails to find files

**Causes**:
1. Route prefix doesn't match paths
2. Longest prefix matching issue

**Solutions**:

```python
# Solution: Check route prefixes
composite = CompositeBackend(
    routes={
        "/skills/": FilesystemBackend(...),  # Matches /skills/*
        "/workspace/": FilesystemBackend(...),  # Matches /workspace/*
    }
)

# Paths must start with route prefix:
read_file("/skills/file.txt")     # ✓ Routes to /skills/ backend
read_file("/workspace/file.txt")  # ✓ Routes to /workspace/ backend
read_file("/other/file.txt")      # ✓ Routes to default backend
```

### 14.5 Performance Issues

#### Issue: Slow file operations

**Symptoms**:
- read_file() takes seconds instead of milliseconds

**Cause**: Reading through DockerBackend instead of FilesystemBackend route.

**Solution**:

```python
# Add CompositeBackend routes for fast reads
backend = CompositeBackend(
    default=DockerBackend(...),
    routes={
        "/workspace/": FilesystemBackend(...),  # Fast host reads
    }
)
```

#### Issue: Container startup delays

**Symptoms**:
- First request takes 1-2 seconds
- Subsequent requests fast

**Cause**: Container creation overhead.

**Solution**:

```python
# Keep container running
docker = DockerBackend(
    auto_start=True,
    auto_remove=False,  # Don't remove container
)

# Or pre-create container:
docker run -d --name agent-sandbox python:3.11 tail -f /dev/null
```

### 14.6 Docker Issues

#### Issue: "Docker daemon not available"

**Symptoms**:
```
DockerBackend fails with connection error
```

**Solutions**:

```bash
# Check Docker is running
docker ps

# Start Docker daemon (macOS)
open -a Docker

# Start Docker daemon (Linux)
sudo systemctl start docker
```

#### Issue: Image pull fails

**Symptoms**:
```
DockerBackend fails with "Image not found"
```

**Solutions**:

```bash
# Pull image manually
docker pull python:3.11

# Or build custom image
cd /path/to/Dockerfile
docker build -t skill-agent:latest .
```

#### Issue: Out of disk space

**Symptoms**:
```
Docker operations fail with "no space left on device"
```

**Solutions**:

```bash
# Clean up Docker
docker system prune -a

# Check disk usage
docker system df
```

---


---

**Navigation**: [⬅️ Part 6: Comparison & Patterns](part6-comparison-patterns.md) | [Index](INDEX.md) | [Part 8: Reference ➡️](part8-reference.md)
