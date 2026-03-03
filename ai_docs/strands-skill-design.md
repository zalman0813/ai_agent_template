# Strands Agent Skill System Design

> Design spec for dynamic S3-based skill loading on Agent Strands.
> Based on analysis of aws-samples/sample-strands-agent-with-agentcore
> and LangChain DeepAgents patterns.

**References:**
- https://github.com/aws-samples/sample-strands-agent-with-agentcore/blob/main/chatbot-app/agentcore/src/local_tools/workspace.py
- https://github.com/aws-samples/sample-strands-agent-with-agentcore/blob/main/chatbot-app/agentcore/src/builtin_tools/code_interpreter_tool.py
- https://github.com/aws-samples/sample-strands-agent-with-agentcore/blob/main/chatbot-app/agentcore/src/builtin_tools/powerpoint_presentation_tool.py
- `ai_docs/strands-agents.md`
- `ai_docs/langchain-skills-middleware.md`

---

## Core Design Principle: WorkspaceManager as Backend

Analogous to LangChain's `FilesystemBackend` — all S3 ↔ sandbox I/O is
encapsulated inside a `WorkspaceManager` class. **The LLM never sees S3 keys,
sandbox file transfers, or pull/push operations.**

```
LANGCHAIN DeepAgents                 STRANDS (our design)
─────────────────────────────        ──────────────────────────────────
FilesystemBackend                    WorkspaceManager
  .download_files(path)  ──────────►   .pull_to_sandbox(paths, interp)
  .ls_info(path)         ──────────►   .list_s3(prefix)
  .upload_files(path)    ──────────►   .push_from_sandbox(paths, interp)

FilesystemMiddleware tools           Our tools (LLM-facing)
  read_file(path)        ──────────►   workspace_read(path)
  write_file(path)       ──────────►   workspace_write(path, content)
  execute(command)       ──────────►   execute_code(code,
                                         input_workspace_paths=[...],
                                         output_workspace_paths=[...])
                                       execute_command(command, ...)

# Internal only (NOT exposed to LLM):
ci_pull_from_workspace()             WorkspaceManager.pull_to_sandbox()
ci_push_to_workspace()               WorkspaceManager.push_from_sandbox()
```

---

## S3 Bucket Namespace

```
S3 BUCKET: s3://{AGENT_BUCKET}/
│
├── skills/                                   ← PROJECT-LEVEL (shared, no user/session)
│   ├── market-intel/
│   │   ├── SKILL.md                          ← frontmatter + instructions
│   │   └── market_intel.py                   ← executable script
│   └── web-search/
│       ├── SKILL.md
│       └── search.py
│
└── workspace/                                ← SESSION-LEVEL
    ├── code-interpreter-workspace/
    │   └── {user_id}/{session_id}/           ← sandbox output, pulled scripts
    ├── code-agent-workspace/
    │   └── {user_id}/{session_id}/
    └── documents/
        └── {user_id}/{session_id}/

Logical path → S3 key mapping:
  "skills/market-intel/SKILL.md"   →  "skills/market-intel/SKILL.md"         (no prefix)
  "code-interpreter/chart.png"     →  "code-interpreter-workspace/u/s/chart.png"
  "documents/report.pdf"           →  "documents/u/s/report.pdf"
```

---

## WorkspaceManager (Backend Class)

```python
import os
import base64
import logging
import boto3
from strands import ToolContext
from strands_tools.code_interpreter.models import (
    WriteFilesAction, ReadFilesAction, FileContent, ExecuteCodeAction, LanguageType,
)

logger = logging.getLogger(__name__)

AGENT_BUCKET = os.environ["AGENT_BUCKET"]
AWS_REGION   = os.environ.get("AWS_REGION", "us-west-2")

_TEXT_EXTENSIONS = {
    ".txt", ".py", ".js", ".ts", ".json", ".csv", ".md",
    ".html", ".xml", ".yaml", ".yml", ".sh", ".sql", ".r", ".toml",
}

_NAMESPACE_MAP = [
    ("skills",           "skills/"),
    ("code-interpreter", "code-interpreter-workspace/{user_id}/{session_id}/"),
    ("code-agent",       "code-agent-workspace/{user_id}/{session_id}/"),
    ("documents",        "documents/{user_id}/{session_id}/"),
]


class WorkspaceManager:
    """
    S3 ↔ sandbox bridge. Equivalent to LangChain FilesystemBackend.
    All tools use this class; the LLM never touches S3 or sandbox directly.
    """

    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self._s3 = boto3.client("s3", region_name=AWS_REGION)

    @classmethod
    def from_context(cls, tool_context: ToolContext) -> "WorkspaceManager":
        state = tool_context.invocation_state
        return cls(
            user_id=state.get("user_id", "default_user"),
            session_id=state.get("session_id", "default_session"),
        )

    # ── Path resolution ──────────────────────────────────────────────────────

    def to_s3_key(self, logical_path: str) -> str:
        """Map logical workspace path to S3 key."""
        path = logical_path.lstrip("/")
        for prefix, template in _NAMESPACE_MAP:
            if path.startswith(prefix):
                suffix = path[len(prefix):].lstrip("/")
                base = template.format(
                    user_id=self.user_id, session_id=self.session_id
                )
                return base + suffix
        # default: documents namespace
        return f"documents/{self.user_id}/{self.session_id}/{path}"

    def to_logical_path(self, s3_key: str) -> str:
        """Map S3 key back to logical workspace path."""
        for prefix, template in _NAMESPACE_MAP:
            s3_base = template.format(
                user_id=self.user_id, session_id=self.session_id
            )
            if s3_key.startswith(s3_base):
                return prefix + "/" + s3_key[len(s3_base):]
        return s3_key

    # ── S3 operations ─────────────────────────────────────────────────────────

    def read_from_s3(self, logical_path: str) -> bytes:
        """Read file bytes from S3."""
        key = self.to_s3_key(logical_path)
        return self._s3.get_object(Bucket=AGENT_BUCKET, Key=key)["Body"].read()

    def write_to_s3(self, logical_path: str, data: bytes) -> str:
        """Write file bytes to S3. Returns resolved S3 key."""
        key = self.to_s3_key(logical_path)
        self._s3.put_object(Bucket=AGENT_BUCKET, Key=key, Body=data)
        logger.info(f"[workspace] wrote {len(data)} bytes → s3://{AGENT_BUCKET}/{key}")
        return key

    def list_s3(self, logical_prefix: str = "") -> list[dict]:
        """List files under a logical prefix. Returns [{path, size, last_modified}]."""
        if logical_prefix:
            s3_prefixes = [self.to_s3_key(logical_prefix.rstrip("/") + "/")]
        else:
            s3_prefixes = [
                f"code-interpreter-workspace/{self.user_id}/{self.session_id}/",
                f"code-agent-workspace/{self.user_id}/{self.session_id}/",
                f"documents/{self.user_id}/{self.session_id}/",
            ]
        files = []
        paginator = self._s3.get_paginator("list_objects_v2")
        for prefix in s3_prefixes:
            for page in paginator.paginate(Bucket=AGENT_BUCKET, Prefix=prefix):
                for obj in page.get("Contents", []):
                    if not obj["Key"].endswith("/"):
                        files.append({
                            "path": self.to_logical_path(obj["Key"]),
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                        })
        return files

    # ── Sandbox sync (internal, NOT exposed to LLM) ───────────────────────────

    def pull_to_sandbox(
        self, logical_paths: list[str], interpreter, session_name: str
    ) -> list[str]:
        """
        S3 → sandbox: download files and upload to code interpreter.
        Returns list of sandbox filenames successfully loaded.
        Equivalent to: LangChain FilesystemBackend.download_files()
        """
        text_entries = []
        uploaded = []

        for path in logical_paths:
            filename = os.path.basename(path)
            ext = os.path.splitext(filename)[1].lower()
            try:
                data = self.read_from_s3(path)
            except Exception as e:
                logger.warning(f"pull_to_sandbox: cannot read '{path}': {e}")
                continue

            if ext in _TEXT_EXTENSIONS:
                text_entries.append(
                    FileContent(path=filename, text=data.decode("utf-8", errors="replace"))
                )
            else:
                # Binary: inject via base64-decode script
                b64 = base64.b64encode(data).decode()
                decode_script = (
                    f"import base64\n"
                    f"with open('{filename}', 'wb') as _f:\n"
                    f"    _f.write(base64.b64decode('{b64}'))\n"
                    f"print('loaded:', '{filename}')\n"
                )
                interpreter.execute_code(ExecuteCodeAction(
                    type="executeCode", session_name=session_name,
                    code=decode_script, language=LanguageType.PYTHON,
                    clear_context=False,
                ))
            uploaded.append(filename)

        if text_entries:
            interpreter.write_files(WriteFilesAction(
                type="writeFiles", session_name=session_name, content=text_entries,
            ))

        logger.info(f"pull_to_sandbox: loaded {len(uploaded)} files")
        return uploaded

    def push_from_sandbox(
        self, sandbox_filenames: list[str], interpreter, session_name: str,
        target_prefix: str = "code-interpreter"
    ) -> list[str]:
        """
        sandbox → S3: read files from sandbox and upload to workspace.
        Returns list of logical paths saved.
        Equivalent to: LangChain FilesystemBackend.upload_files()
        """
        saved = []
        for filename in sandbox_filenames:
            try:
                result = interpreter.read_files(ReadFilesAction(
                    type="readFiles", session_name=session_name,
                    paths=[filename],
                ))
                for item in result.get("content", []):
                    if not isinstance(item, dict):
                        continue
                    blob = item.get("data") or item.get("resource", {}).get("blob")
                    text = item.get("text", "")
                    data = blob if blob else text.encode("utf-8") if text else None
                    if data:
                        logical_path = f"{target_prefix}/{filename}"
                        self.write_to_s3(logical_path, data if isinstance(data, bytes) else data)
                        saved.append(logical_path)
                        break
            except Exception as e:
                logger.warning(f"push_from_sandbox: could not save '{filename}': {e}")

        logger.info(f"push_from_sandbox: saved {len(saved)} files")
        return saved
```

---

## LLM-Facing Tools

The LLM only ever calls these tools. S3 / sandbox mechanics are fully hidden.

### workspace_read / workspace_write / workspace_list

```python
import json
from strands import tool, ToolContext

@tool(context=True)
def workspace_read(path: str, tool_context: ToolContext = None) -> str:
    """Read a file from the workspace.

    Args:
        path: Logical path (e.g. 'code-interpreter/report.json',
              'documents/data.csv', 'skills/market-intel/SKILL.md').

    Returns:
        File content as text (binary files returned base64-encoded).
    """
    manager = WorkspaceManager.from_context(tool_context)
    try:
        data = manager.read_from_s3(path)
        ext = os.path.splitext(path)[1].lower()
        if ext in _TEXT_EXTENSIONS:
            return data.decode("utf-8", errors="replace")
        return base64.b64encode(data).decode()
    except Exception as e:
        return json.dumps({"error": str(e), "path": path, "status": "error"})


@tool(context=True)
def workspace_write(
    path: str,
    content: str,
    encoding: str = "text",
    tool_context: ToolContext = None,
) -> str:
    """Write a file to the workspace.

    Args:
        path: Logical path (e.g. 'code-interpreter/output.json').
        content: File content. Use encoding='base64' for binary files.
        encoding: 'text' (default) or 'base64'.

    Returns:
        Confirmation with resolved path.
    """
    manager = WorkspaceManager.from_context(tool_context)
    try:
        data = base64.b64decode(content) if encoding == "base64" else content.encode("utf-8")
        manager.write_to_s3(path, data)
        return json.dumps({"path": path, "size": len(data), "status": "ok"})
    except Exception as e:
        return json.dumps({"error": str(e), "status": "error"})


@tool(context=True)
def workspace_list(path: str = "", tool_context: ToolContext = None) -> str:
    """List files in the workspace.

    Args:
        path: Optional prefix to filter. '' = list all namespaces.
              e.g. 'code-interpreter/', 'documents/'

    Returns:
        JSON list of files with path, size, last_modified.
    """
    manager = WorkspaceManager.from_context(tool_context)
    try:
        files = manager.list_s3(path)
        return json.dumps({"files": files, "count": len(files)}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e), "status": "error"})
```

### execute_code

S3 sync is **transparent** — the LLM specifies logical paths; the tool handles pull/push.

```python
@tool(context=True)
def execute_code(
    code: str,
    language: str = "python",
    input_workspace_paths: list = None,
    output_workspace_paths: list = None,
    tool_context: ToolContext = None,
) -> str:
    """Execute code in the sandboxed Code Interpreter.

    Files listed in input_workspace_paths are automatically loaded from
    workspace into the sandbox before execution. Files listed in
    output_workspace_paths are automatically saved back to workspace after.

    Args:
        code: Python (default), JavaScript, or TypeScript code to run.
              Use print() for text output. Variables persist across calls.
        language: 'python' | 'javascript' | 'typescript'
        input_workspace_paths: Workspace files to make available in sandbox.
            e.g. ['skills/market-intel/market_intel.py', 'code-interpreter/data.csv']
        output_workspace_paths: Sandbox filenames to save back to workspace.
            e.g. ['report.json', 'chart.png']
            Saved under 'code-interpreter/{filename}' in workspace.

    Returns:
        Execution stdout. For saved files: confirmation + stdout.
    """
    from strands_tools.code_interpreter.models import ExecuteCodeAction, LanguageType

    interpreter, session_name = _get_interpreter(tool_context)
    if not interpreter:
        return json.dumps({"error": "Code Interpreter not available.", "status": "error"})

    manager = WorkspaceManager.from_context(tool_context)

    # ── Step 1: Pull input files from S3 → sandbox (transparent) ──
    if input_workspace_paths:
        manager.pull_to_sandbox(input_workspace_paths, interpreter, session_name)

    # ── Step 2: Execute ──
    lang_map = {"python": LanguageType.PYTHON, "javascript": LanguageType.JAVASCRIPT,
                "typescript": LanguageType.TYPESCRIPT}
    try:
        result = interpreter.execute_code(ExecuteCodeAction(
            type="executeCode", session_name=session_name,
            code=code, language=lang_map.get(language.lower(), LanguageType.PYTHON),
            clear_context=False,
        ))
        output = _extract_text(result)

        if result.get("status") == "error":
            return json.dumps({"error": output, "status": "error"})

        # ── Step 3: Push output files from sandbox → S3 (transparent) ──
        saved = []
        if output_workspace_paths:
            saved = manager.push_from_sandbox(
                output_workspace_paths, interpreter, session_name
            )

        if saved:
            return f"{output or '(no stdout)'}\n\nSaved to workspace: {saved}"
        return output or "(no output)"

    except Exception as e:
        logger.error(f"execute_code error: {e}")
        return json.dumps({"error": str(e), "status": "error"})
```

### execute_command

Same transparent sync pattern as `execute_code`.

```python
@tool(context=True)
def execute_command(
    command: str,
    input_workspace_paths: list = None,
    output_workspace_paths: list = None,
    tool_context: ToolContext = None,
) -> str:
    """Execute a shell command in the Code Interpreter sandbox.

    Args:
        command: Shell command (e.g. 'python market_intel.py --query AI').
        input_workspace_paths: Workspace files to load into sandbox before running.
        output_workspace_paths: Sandbox filenames to save back to workspace after.

    Returns:
        Command stdout/stderr.
    """
    from strands_tools.code_interpreter.models import ExecuteCommandAction

    interpreter, session_name = _get_interpreter(tool_context)
    if not interpreter:
        return json.dumps({"error": "Code Interpreter not available.", "status": "error"})

    manager = WorkspaceManager.from_context(tool_context)

    # ── Step 1: Pull ──
    if input_workspace_paths:
        manager.pull_to_sandbox(input_workspace_paths, interpreter, session_name)

    # ── Step 2: Execute ──
    try:
        result = interpreter.execute_command(ExecuteCommandAction(
            type="executeCommand", session_name=session_name, command=command,
        ))
        output = _extract_text(result)

        # ── Step 3: Push ──
        saved = []
        if output_workspace_paths:
            saved = manager.push_from_sandbox(
                output_workspace_paths, interpreter, session_name
            )

        if saved:
            return f"{output}\n\nSaved to workspace: {saved}"
        return output

    except Exception as e:
        logger.error(f"execute_command error: {e}")
        return json.dumps({"error": str(e), "status": "error"})
```

---

## Complete Flow: LLM Perspective vs Internal Reality

```
LLM CALL                              INTERNAL REALITY
─────────────────────────────────     ──────────────────────────────────────────

workspace_list("code-interpreter/")
                                      WorkspaceManager.list_s3(prefix)
                                        s3.list_objects_v2(Prefix="code-interpreter-workspace/u/s/")
                                      → returns [{path, size, ...}]
↓ returns file list


workspace_read("code-interpreter/data.csv")
                                      WorkspaceManager.read_from_s3(path)
                                        s3.get_object(Key="code-interpreter-workspace/u/s/data.csv")
                                      → returns file content as text
↓ returns CSV content


execute_command(
  command="python market_intel.py --query 'AI 2025'",
  input_workspace_paths=[
    "skills/market-intel/market_intel.py",   ← from skills/ (no user/session prefix)
    "code-interpreter/data.csv",             ← from workspace
  ],
  output_workspace_paths=["results.json"]
)
                                      ── Step 1: pull_to_sandbox() ──
                                        s3.get_object("skills/market-intel/market_intel.py")
                                          → interpreter.write_files([FileContent("market_intel.py", text)])
                                        s3.get_object("code-interpreter-workspace/u/s/data.csv")
                                          → interpreter.write_files([FileContent("data.csv", text)])

                                      ── Step 2: execute ──
                                        interpreter.execute_command("python market_intel.py ...")
                                        → stdout: "Analysis complete. Saved results.json"

                                      ── Step 3: push_from_sandbox() ──
                                        interpreter.read_files(["results.json"])
                                          → blob bytes
                                        s3.put_object(
                                          Key="code-interpreter-workspace/u/s/results.json",
                                          Body=blob
                                        )
↓ returns stdout + "Saved to workspace: ['code-interpreter/results.json']"


workspace_read("code-interpreter/results.json")
                                      WorkspaceManager.read_from_s3(path)
                                        s3.get_object("code-interpreter-workspace/u/s/results.json")
↓ returns JSON content
```

---

## SkillsHookProvider (unchanged from previous design)

```python
from strands.hooks import HookProvider, HookRegistry, AgentInitializedEvent, BeforeInvocationEvent

class SkillsHookProvider(HookProvider):
    """Load skill metadata from S3 once; inject catalog into system prompt every turn."""

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(AgentInitializedEvent, self._load_once)
        registry.add_callback(BeforeInvocationEvent, self._inject_prompt)

    def _load_once(self, event: AgentInitializedEvent) -> None:
        if event.agent.state.get("skills_metadata"):
            return                                   # guard: already loaded (0 IO)
        metadata = _load_skills_from_s3()            # scan skills/ prefix, frontmatter only
        event.agent.state.set("skills_metadata", metadata)

    def _inject_prompt(self, event: BeforeInvocationEvent) -> None:
        metadata = event.agent.state.get("skills_metadata") or []
        if not metadata:
            return
        catalog = _format_skill_catalog(metadata)    # 0 IO, in-memory
        if event.messages:
            content = event.messages[0].get("content", "")
            if isinstance(content, list):
                content.insert(0, {"text": catalog + "\n\n"})
            else:
                event.messages[0]["content"] = catalog + "\n\n" + content
```

```python
@tool(context=True)
def read_skill(skill_name: str, tool_context: ToolContext = None) -> str:
    """Read full instructions for a skill (Stage 2 progressive disclosure).

    Args:
        skill_name: Skill name from the Available Skills list.

    Returns:
        Complete SKILL.md with instructions and script path.
    """
    manager = WorkspaceManager.from_context(tool_context)
    try:
        data = manager.read_from_s3(f"skills/{skill_name}/SKILL.md")
        return data.decode("utf-8")
    except Exception as e:
        return f"Skill '{skill_name}' not found: {e}"
```

---

## Tool Inventory (LLM-facing only)

| Tool | S3 IO | Sandbox IO | Purpose |
|------|-------|------------|---------|
| `workspace_read` | `get_object` | none | Read file from S3 |
| `workspace_write` | `put_object` | none | Write file to S3 |
| `workspace_list` | `list_objects` | none | List files in S3 |
| `read_skill` | `get_object` | none | Fetch full SKILL.md (Stage 2) |
| `execute_code` | auto pull+push | execute | Run code; sync files transparently |
| `execute_command` | auto pull+push | execute | Run shell; sync files transparently |

**Removed from LLM tool list** (now internal only):
- `ci_pull_from_workspace` → `WorkspaceManager.pull_to_sandbox()`
- `ci_push_to_workspace` → `WorkspaceManager.push_from_sandbox()`
- `file_operations` → internal sandbox use only (not needed by LLM)

---

## Agent Assembly

```python
agent = Agent(
    model="us.anthropic.claude-sonnet-4-6-v1",
    system_prompt=(
        "You are an assistant with access to a workspace (S3) and a code execution sandbox.\n\n"
        "File access:\n"
        "  workspace_read/write/list — read and write files in the workspace.\n\n"
        "Code execution:\n"
        "  execute_code / execute_command — run Python or shell commands.\n"
        "  Specify input_workspace_paths to load files before execution.\n"
        "  Specify output_workspace_paths to save results after execution.\n\n"
        "Skills:\n"
        "  Available skills are listed in your context. Call read_skill('<name>') "
        "for full instructions, then execute_command to run the skill script."
    ),
    tools=[
        workspace_read,
        workspace_write,
        workspace_list,
        read_skill,
        execute_code,
        execute_command,
    ],
    hooks=[SkillsHookProvider()],
    session_manager=S3SessionManager(
        session_id=f"{user_id}-{session_id}",
        bucket=AGENT_BUCKET,
        prefix="sessions/",
        region_name=AWS_REGION,
    ),
)

result = agent(
    "Analyze AI market trends and save a report.",
    invocation_state={"user_id": "user-123", "session_id": "sess-456"},
)
```

---

## Progressive Disclosure: Three Stages

```
STAGE 1: Skill Catalog (every turn, 0 IO)
─────────────────────────────────────────
BeforeInvocationEvent injects into system prompt:
  "## Available Skills
   - market-intel: Gather market intelligence
   - web-search: Search the web
   Call read_skill('<name>') for full instructions."

STAGE 2: Full Instructions (on demand, 1 S3 read)
──────────────────────────────────────────────────
LLM: read_skill("market-intel")
     → WorkspaceManager.read_from_s3("skills/market-intel/SKILL.md")
     → returns: instructions + "Run: market_intel.py --query <q>"

STAGE 3: Execution (on demand, sandbox + S3 sync)
──────────────────────────────────────────────────
LLM: execute_command(
       command="python market_intel.py --query 'AI 2025'",
       input_workspace_paths=["skills/market-intel/market_intel.py"],
       output_workspace_paths=["results.json"]
     )
     → pull_to_sandbox(["skills/market-intel/market_intel.py"])  ← S3 → sandbox
     → interpreter.execute_command("python market_intel.py ...")  ← run
     → push_from_sandbox(["results.json"])                        ← sandbox → S3
     → returns stdout + saved paths
```

---

## Caching: Equivalent to LangChain SkillsMiddleware

```
LangChain                              Strands
──────────────────────────────         ─────────────────────────────────
before_agent():                        AgentInitializedEvent:
  if "skills_metadata" in state:         if agent.state.get("skills_metadata"):
      return None  # skip IO               return  # skip IO
  load frontmatter from filesystem       load frontmatter from S3
  AgentState["skills_metadata"] = [...]  agent.state.set("skills_metadata", [...])

wrap_model_call() every turn:          BeforeInvocationEvent every turn:
  read AgentState (0 IO)                 read agent.state (0 IO)
  inject into system prompt              inject into messages

S3SessionManager restore:
  agent.state restored from S3
  → AgentInitializedEvent guard fires
  → skills already in state → 0 IO
```

---

## SKILL.md Format

```markdown
---
name: market-intel
description: Gather market intelligence and competitor analysis
version: "1.0"
---

## Instructions

1. Pull the skill script into your sandbox and run it:

   execute_command(
     command="python market_intel.py --query '<your query>'",
     input_workspace_paths=["skills/market-intel/market_intel.py"],
     output_workspace_paths=["results.json"]
   )

2. Read the results:

   workspace_read("code-interpreter/results.json")

## Output

results.json: { "query": "...", "findings": [...], "sources": [...] }
```
