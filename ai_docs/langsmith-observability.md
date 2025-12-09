# LangSmith 可觀測性與追蹤最佳實踐指南

> LangChain v1.0 + LangSmith 完整 Observability 設計參考

## 目錄

1. [簡介](#簡介)
2. [環境配置](#環境配置)
3. [LangSmith 追蹤設置](#langsmith-追蹤設置)
4. [自定義元資料、標籤與註釋](#自定義元資料標籤與註釋)
5. [全面可觀測性設計最佳實踐](#全面可觀測性設計最佳實踐)
6. [錯誤處理與日誌記錄](#錯誤處理與日誌記錄)
7. [巢狀 Spans 與子執行](#巢狀-spans-與子執行)
8. [反饋與評分](#反饋與評分)
9. [敏感資料保護](#敏感資料保護)
10. [生產環境最佳實踐](#生產環境最佳實踐)
11. [完整程式碼範例](#完整程式碼範例)

---

## 簡介

LangSmith 是 LangChain 官方的可觀測性平台，提供全面的追蹤、監控和評估功能。

### 核心概念

| 概念 | 說明 |
|------|------|
| **Run** | 單一工作單元，類似 OpenTelemetry 的 span |
| **Trace** | 多個 runs 組成的完整操作序列 |
| **Project** | 組織容器，將所有 traces 分組 |
| **Metadata** | 附加到 runs 的鍵值對 |
| **Tags** | 字串集合，用於分類和過濾 |

---

## 環境配置

### 必要環境變數

```bash
# Enable LangSmith tracing
export LANGSMITH_TRACING=true

# Your LangSmith API key (required)
export LANGSMITH_API_KEY=<your-api-key>

# Optional: Specify project name
export LANGSMITH_PROJECT=my-project

# Optional: Sampling rate (0.0 to 1.0)
export LANGSMITH_TRACING_SAMPLING_RATE=0.5

# Optional: Hide sensitive data
export LANGSMITH_HIDE_INPUTS=true
export LANGSMITH_HIDE_OUTPUTS=true
```

### Python 程式化配置

```python
import langsmith as ls

# Create client with custom configuration
client = ls.Client(
    api_key="YOUR_API_KEY",
    api_url="https://api.smith.langchain.com",
    tracing_sampling_rate=0.5  # 50% sampling
)

# Use with tracing context
with ls.tracing_context(
    client=client,
    project_name="my-project",
    enabled=True
):
    # Your code here
    pass
```

---

## LangSmith 追蹤設置

### 方法一：LangChain 自動追蹤

```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os

os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = "your-api-key"
os.environ["LANGSMITH_PROJECT"] = "my-project"

# Automatically traced
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    ("user", "{question}")
])

model = ChatOpenAI(model="gpt-4o-mini")
chain = prompt | model | StrOutputParser()

result = chain.invoke({"question": "What is LangSmith?"})
```

### 方法二：@traceable 裝飾器

```python
from langsmith import traceable
from openai import OpenAI

client = OpenAI()

@traceable(run_type="llm")
def call_openai(messages: list, model: str = "gpt-4o-mini") -> str:
    """Call OpenAI API with tracing"""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content

@traceable(run_type="chain")
def process_query(query: str) -> str:
    """Process user query - creates nested trace"""
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": query}
    ]
    return call_openai(messages)
```

### 方法三：wrap_openai 包裝器

```python
from openai import OpenAI
from langsmith import wrappers, traceable

# Wrap the OpenAI client
client = wrappers.wrap_openai(OpenAI())

# All calls automatically traced
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)

@traceable(name="My AI Function")
def my_function(text: str):
    """Nested traces with wrapped client"""
    return client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Process: {text}"}]
    )
```

### 方法四：trace 上下文管理器

```python
import langsmith as ls

with ls.trace(
    name="Chat Pipeline",
    run_type="chain",
    project_name="my-project",
    inputs={"question": "What is AI?"}
) as rt:
    output = process_pipeline("What is AI?")

    # Add metadata during execution
    rt.metadata["version"] = "1.0"
    rt.metadata["user_id"] = "user-123"

    rt.end(outputs={"answer": output})
```

### 方法五：RunTree API（最大控制）

```python
from langsmith import RunTree

pipeline = RunTree(
    name="Chat Pipeline",
    run_type="chain",
    inputs={"question": "What is quantum computing?"},
    project_name="my-project"
)
pipeline.post()

# Create child run
child_run = pipeline.create_child(
    name="OpenAI Call",
    run_type="llm",
    inputs={"messages": [...]}
)
child_run.post()

try:
    result = process_llm_call()
    child_run.end(outputs={"response": result})
except Exception as e:
    child_run.end(error=str(e))
finally:
    child_run.patch()

pipeline.end(outputs={"final_result": result})
pipeline.patch()
```

---

## 自定義元資料、標籤與註釋

### 添加標籤

```python
from langsmith import traceable

# At decoration time
@traceable(
    tags=["production", "gpt-4", "customer-service"],
    run_type="chain"
)
def customer_service_chain(query: str):
    pass

# At invocation time
result = chain.invoke(
    {"input": "What is AI?"},
    {"tags": ["user-query", "high-priority"]}
)

# With @traceable at runtime
@traceable
def process_data(data: str):
    return data.upper()

process_data(
    "hello",
    langsmith_extra={"tags": ["runtime-tag"]}
)
```

### 添加元資料

```python
@traceable(
    metadata={
        "version": "1.2.3",
        "environment": "production",
        "git_hash": "e38f04c83"
    }
)
def my_function(x: int):
    return x * 2

# At invocation time
process_request(
    "user-123",
    "Hello",
    langsmith_extra={
        "metadata": {
            "user_id": "user-123",
            "session_id": "session-456",
            "region": "us-west-2"
        }
    }
)
```

### 標籤策略範例

```python
class TracingTags:
    """Standardized tagging system"""

    # Environment
    ENV_DEV = "env:dev"
    ENV_STAGING = "env:staging"
    ENV_PROD = "env:production"

    # Component
    COMPONENT_RAG = "component:rag"
    COMPONENT_AGENT = "component:agent"

    # Priority
    PRIORITY_HIGH = "priority:high"
    PRIORITY_LOW = "priority:low"

@traceable(
    tags=[
        TracingTags.ENV_PROD,
        TracingTags.COMPONENT_RAG,
        TracingTags.PRIORITY_HIGH
    ]
)
def rag_pipeline(query: str):
    pass
```

---

## 全面可觀測性設計最佳實踐

### 1. 結構化輸入/輸出

```python
from langsmith import traceable
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

@dataclass
class RetrievalResult:
    document_id: str
    score: float
    content: str
    metadata: Dict[str, Any]

@traceable(run_type="retriever")
def structured_retrieval(query: str) -> List[Dict[str, Any]]:
    results = [
        RetrievalResult(
            document_id="doc-1",
            score=0.95,
            content="...",
            metadata={"source": "kb"}
        )
    ]
    return [asdict(r) for r in results]
```

### 2. 效能追蹤

```python
from langsmith import traceable
import time
from datetime import datetime

@traceable(run_type="chain")
def monitored_pipeline(user_input: str):
    start_time = time.time()

    @traceable
    def step_with_timing(step_name: str, data: str, *, run_tree):
        step_start = time.time()
        result = process_step(data)
        step_duration = time.time() - step_start

        run_tree.metadata.update({
            "duration_ms": step_duration * 1000,
            "timestamp": datetime.utcnow().isoformat()
        })
        return result

    result1 = step_with_timing("preprocessing", user_input)
    result2 = step_with_timing("llm_call", result1)

    return {"result": result2}
```

---

## 錯誤處理與日誌記錄

### 自動錯誤捕獲

```python
from langsmith import traceable

@traceable(run_type="chain")
def pipeline_with_error_handling(input_data: str):
    try:
        result = risky_operation(input_data)
        return {"status": "success", "result": result}
    except Exception as e:
        # Error automatically logged to LangSmith
        return {
            "status": "error",
            "error_message": str(e),
            "error_type": type(e).__name__
        }
```

### 使用 trace 上下文管理器

```python
import langsmith as ls

with ls.trace(name="Robust Operation", run_type="chain") as run:
    try:
        result = risky_operation()
        run.end(outputs={"result": result})
    except ValueError as e:
        run.end(error=f"ValueError: {str(e)}")
    except Exception as e:
        run.end(error=f"Unexpected error: {str(e)}")
        raise
```

---

## 巢狀 Spans 與子執行

### 自動巢狀（函數呼叫）

```python
from langsmith import traceable

@traceable(run_type="tool")
def retrieve_documents(query: str, top_k: int = 3):
    # Child span
    return [{"id": "doc1", "content": "..."}]

@traceable(run_type="llm")
def generate_with_context(query: str, context: list):
    # Child span
    return "Generated answer"

@traceable(run_type="chain", name="RAG Pipeline")
def rag_pipeline(user_query: str):
    """
    Creates hierarchy:
    - RAG Pipeline (parent)
      - retrieve_documents (child 1)
      - generate_with_context (child 2)
    """
    documents = retrieve_documents(user_query)
    answer = generate_with_context(user_query, documents)
    return {"answer": answer}
```

### 存取 RunTree 物件

```python
from langsmith import traceable, RunTree
from uuid import UUID

@traceable(run_type="chain")
def function_with_run_access(
    query: str,
    *,
    run_tree: RunTree  # Injected by @traceable
):
    current_run_id = run_tree.id

    # Add metadata dynamically
    run_tree.metadata["custom_field"] = "value"

    result = process_query(query)
    return result, current_run_id
```

---

## 反饋與評分

### 添加反饋

```python
from langsmith import Client, traceable

client = Client()

@traceable(run_type="chain")
def my_function(x: int):
    return {"result": x * 2}

with traceable(name="My Operation") as run:
    result = my_function(5)
    run_id = run.id

# Add feedback
client.create_feedback(
    run_id=run_id,
    key="user_feedback",
    score=1.0,
    comment="Accurate and helpful."
)

# Multiple feedback types
client.create_feedback(
    run_id=run_id,
    key="correctness",
    score=1,  # Binary: 1 = correct
)

client.create_feedback(
    run_id=run_id,
    key="helpfulness",
    score=0.85,  # Continuous: 0.0 to 1.0
)
```

### 收集使用者反饋

```python
class FeedbackCollector:
    def __init__(self):
        self.client = Client()

    def thumbs_up_down(self, run_id: str, is_positive: bool, comment: str = None):
        self.client.create_feedback(
            run_id=run_id,
            key="user_satisfaction",
            score=1 if is_positive else 0,
            comment=comment
        )

    def rating(self, run_id: str, rating: int, aspect: str = "overall"):
        # Normalize 1-5 to 0-1
        normalized = (rating - 1) / 4
        self.client.create_feedback(
            run_id=run_id,
            key=f"rating_{aspect}",
            score=normalized
        )
```

---

## 敏感資料保護

### 使用 Anonymizer

```python
from langsmith import Client
from langsmith.anonymizer import create_anonymizer

patterns = [
    {"pattern": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "replace": "<EMAIL>"},
    {"pattern": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "replace": "<PHONE>"},
    {"pattern": r"sk-[a-zA-Z0-9]{32,}", "replace": "<API_KEY>"},
]

anonymizer = create_anonymizer(patterns)
client = Client(anonymizer=anonymizer)
```

### 函數層級處理

```python
from langsmith import traceable

def mask_sensitive_fields(data: dict) -> dict:
    masked = data.copy()
    if "password" in masked:
        masked["password"] = "***REDACTED***"
    if "api_key" in masked:
        masked["api_key"] = "***REDACTED***"
    return masked

@traceable(
    process_inputs=mask_sensitive_fields,
    process_outputs=mask_sensitive_fields
)
def handle_user_data(user_info: dict):
    return {"status": "processed"}
```

---

## 生產環境最佳實踐

### 1. 採樣率配置

```python
import os
from langsmith import Client

# 10% sampling for production
os.environ["LANGSMITH_TRACING_SAMPLING_RATE"] = "0.1"

# Or programmatic
client = Client(tracing_sampling_rate=0.1)
```

### 2. 環境別策略

```python
ENV = os.getenv("ENVIRONMENT", "development")

CONFIG = {
    "development": {"project": "dev-app", "sampling": 1.0},
    "staging": {"project": "staging-app", "sampling": 0.5},
    "production": {"project": "prod-app", "sampling": 0.1},
}

config = CONFIG[ENV]
```

### 3. 確保追蹤提交（Serverless）

```python
from langchain_core.tracers.langchain import wait_for_all_tracers

try:
    result = chain.invoke({"input": "question"})
finally:
    wait_for_all_tracers()
```

### 4. 成本追蹤

```python
TOKEN_COSTS = {
    "gpt-4o": {"input": 0.00003, "output": 0.00006},
    "gpt-4o-mini": {"input": 0.000015, "output": 0.00006},
}

@traceable(run_type="llm")
def llm_with_cost_tracking(messages: list, model: str, *, run_tree):
    response = client.chat.completions.create(model=model, messages=messages)

    usage = response.usage
    cost = (
        usage.prompt_tokens * TOKEN_COSTS[model]["input"] +
        usage.completion_tokens * TOKEN_COSTS[model]["output"]
    )

    run_tree.metadata.update({
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "estimated_cost_usd": cost
    })

    return response.choices[0].message.content
```

---

## 完整程式碼範例

### RAG 系統完整追蹤

```python
from langsmith import traceable, Client
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any
import uuid
from datetime import datetime

client = Client()
llm = ChatOpenAI(model="gpt-4o-mini")

@traceable(run_type="retriever", tags=["retrieval"])
def retrieve_documents(query: str, top_k: int = 5, *, run_tree):
    run_tree.metadata["top_k"] = top_k

    docs = [
        {"id": f"doc_{i}", "content": f"Content about {query}", "score": 0.95 - i*0.05}
        for i in range(top_k)
    ]

    run_tree.metadata["documents_found"] = len(docs)
    return docs

@traceable(run_type="llm", tags=["generation"])
def generate_answer(query: str, context_docs: List[Dict], *, run_tree):
    context = "\n".join([d["content"] for d in context_docs])

    response = llm.invoke(f"Context:\n{context}\n\nQuestion: {query}")

    run_tree.metadata["context_docs_count"] = len(context_docs)
    return {"answer": response.content, "sources": [d["id"] for d in context_docs]}

@traceable(
    run_type="chain",
    name="RAG Pipeline",
    tags=["rag", "production"],
    metadata={"version": "2.0"}
)
def rag_pipeline(query: str, user_id: str, *, run_tree):
    session_id = str(uuid.uuid4())

    run_tree.metadata.update({
        "user_id": user_id,
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    })

    try:
        documents = retrieve_documents(query, top_k=5)
        result = generate_answer(query, documents)

        run_tree.metadata["status"] = "success"

        client.create_feedback(
            run_id=run_tree.id,
            key="auto_confidence",
            score=0.9
        )

        return {
            "query": query,
            "answer": result["answer"],
            "sources": result["sources"],
            "session_id": session_id
        }

    except Exception as e:
        run_tree.metadata.update({
            "status": "error",
            "error_type": type(e).__name__
        })
        raise

# Usage
result = rag_pipeline("What is quantum computing?", user_id="user-123")
```

---

## 配置檢查清單

```
Production LangSmith Configuration:

Environment Variables:
[x] LANGSMITH_TRACING=true
[x] LANGSMITH_API_KEY=<your-key>
[x] LANGSMITH_PROJECT=<prod-project-name>
[x] LANGSMITH_TRACING_SAMPLING_RATE=0.1

Best Practices:
[x] Use sampling in high-traffic production
[x] Add comprehensive metadata
[x] Use consistent tagging strategy
[x] Implement error handling
[x] Flush traces in serverless environments
[x] Set up anonymization for PII
[x] Monitor costs with token tracking
[x] Separate projects for different environments
```

---

## Sources

### 官方文檔
- [LangSmith Annotate Code](https://docs.smith.langchain.com/observability/how_to_guides/annotate_code)
- [LangSmith Trace with LangChain](https://docs.smith.langchain.com/observability/how_to_guides/trace_with_langchain)
- [LangSmith Observability Concepts](https://docs.smith.langchain.com/observability/concepts)
- [LangSmith Add Metadata and Tags](https://docs.smith.langchain.com/observability/how_to_guides/add_metadata_tags)
- [LangSmith Set Sampling Rate](https://docs.smith.langchain.com/observability/how_to_guides/sample_traces)
- [LangSmith Mask Inputs Outputs](https://docs.smith.langchain.com/observability/how_to_guides/mask_inputs_outputs)
- [LangSmith Feedback Data Format](https://docs.smith.langchain.com/evaluation/concepts#feedback)

### SDK 參考
- [LangSmith Python SDK](https://docs.smith.langchain.com/reference/python/)
- [LangSmith traceable](https://docs.smith.langchain.com/reference/python/run_helpers/langsmith.run_helpers.traceable)
- [LangSmith RunTree](https://docs.smith.langchain.com/reference/python/run_trees/langsmith.run_trees.RunTree)

### 進階資源
- [LangSmith Cookbook](https://github.com/langchain-ai/langsmith-cookbook)
- [LangSmith SDK GitHub](https://github.com/langchain-ai/langsmith-sdk)

---

**文檔版本**: 1.0
**最後更新**: 2025-01-15
**適用於**: LangChain v1.0+, LangSmith SDK v0.1.81+
