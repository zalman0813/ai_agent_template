import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { useSSEChat } from "./hooks/useSSEChat";
import type {
  StreamItem,
  TextStreamItem,
  ToolStreamItem,
  SubAgentStreamItem,
  TodoStreamItem,
  TodoItem,
  AssistantTurn,
  UserMessage,
  TavilyImage,
  TavilySearchResponse,
} from "./types";
import "./App.css";

// Format JSON for display
const formatJson = (obj: unknown) => {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
};

// Try to parse JSON string, return null if failed
const tryParseJson = (str: string): unknown | null => {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
};

// Check if parsed object is a Tavily search response
const isTavilyResponse = (obj: unknown): obj is TavilySearchResponse => {
  if (!obj || typeof obj !== "object") return false;
  const o = obj as Record<string, unknown>;
  return "query" in o && "results" in o && Array.isArray(o.results);
};

// Structured search result from SubAgent (for RESULT rendering)
interface StructuredSearchResult {
  summary: string;
  text_results?: Array<{
    title: string;
    url: string;
    content: string;
    source: string;
  }>;
  image_results?: Array<{
    image_url: string;
    title: string;
    source: string;
    page_url?: string;
  }>;
}

// Check if parsed object is a structured search result
const isStructuredSearchResult = (obj: unknown): obj is StructuredSearchResult => {
  if (!obj || typeof obj !== "object") return false;
  const o = obj as Record<string, unknown>;
  return "summary" in o && typeof o.summary === "string";
};

// Helper function to get image URL from TavilyImage (string or object)
const getImageUrl = (img: TavilyImage): string =>
  typeof img === "string" ? img : img.url;

// Helper function to get image description from TavilyImage
const getImageDescription = (img: TavilyImage): string | undefined =>
  typeof img === "string" ? undefined : img.description;

// Image Modal component for fullscreen preview
function ImageModal({
  image,
  onClose,
}: {
  image: TavilyImage;
  onClose: () => void;
}) {
  const imageUrl = getImageUrl(image);
  const description = getImageDescription(image);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="image-modal-overlay" onClick={onClose}>
      <div className="image-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="image-modal-close" onClick={onClose}>
          ✕
        </button>
        <img src={imageUrl} alt={description || ""} />
        {description && <p className="image-modal-desc">{description}</p>}
      </div>
    </div>
  );
}

// Image gallery component for Tavily results (max 5 images)
function TavilyImageGallery({
  images,
  onImageClick,
}: {
  images: TavilyImage[];
  onImageClick: (img: TavilyImage) => void;
}) {
  const displayImages = images.slice(0, 5);
  if (displayImages.length === 0) return null;

  return (
    <div className="tavily-images">
      {displayImages.map((img, idx) => (
        <div
          key={idx}
          className="tavily-image-item"
          onClick={() => onImageClick(img)}
        >
          <img src={getImageUrl(img)} alt={`Image ${idx + 1}`} />
        </div>
      ))}
    </div>
  );
}

// Helper to safely extract hostname from URL
const getHostname = (url: string): string => {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
};

// Tavily search result view component - Professional UI
function TavilyResultView({
  data,
  onImageClick,
}: {
  data: TavilySearchResponse;
  onImageClick: (img: TavilyImage) => void;
}) {
  const hasImages = data.images && data.images.length > 0;
  const hasResults = data.results && data.results.length > 0;

  return (
    <div className="tavily-result-view">
      {/* Query header */}
      <div className="tavily-query-header">
        <span className="tavily-query-icon">🔍</span>
        <span className="tavily-query-text">{data.query}</span>
      </div>

      {/* Images section */}
      {hasImages && (
        <div className="tavily-section">
          <div className="tavily-section-header">
            <span className="tavily-section-icon">🖼️</span>
            <span className="tavily-section-label">
              Images ({data.images!.length})
            </span>
          </div>
          <TavilyImageGallery images={data.images!} onImageClick={onImageClick} />
        </div>
      )}

      {/* Results section */}
      {hasResults && (
        <div className="tavily-section">
          <div className="tavily-section-header">
            <span className="tavily-section-icon">📄</span>
            <span className="tavily-section-label">
              Sources ({data.results.length})
            </span>
          </div>
          <div className="tavily-results-list">
            {data.results.slice(0, 5).map((result, idx) => (
              <div key={idx} className="tavily-result-item">
                <a
                  href={result.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="tavily-result-title"
                >
                  {result.title}
                </a>
                <p className="tavily-result-content">{result.content}</p>
                <span className="tavily-result-url">
                  {getHostname(result.url)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Structured search result view component - for SubAgent RESULT
function StructuredResultView({
  data,
  onImageClick,
}: {
  data: StructuredSearchResult;
  onImageClick: (img: TavilyImage) => void;
}) {
  const hasImages = data.image_results && data.image_results.length > 0;
  const hasTextResults = data.text_results && data.text_results.length > 0;

  return (
    <div className="structured-result-view">
      {/* Summary with Markdown rendering */}
      <div className="result-summary markdown-content">
        <ReactMarkdown>{data.summary}</ReactMarkdown>
      </div>

      {/* Images Grid */}
      {hasImages && (
        <div className="result-images-section">
          <div className="result-section-label">Images</div>
          <div className="result-images-grid">
            {data.image_results!.slice(0, 6).map((img, idx) => (
              <div
                key={idx}
                className="result-image-card"
                onClick={() => onImageClick(img.image_url)}
              >
                <img src={img.image_url} alt={img.title || `Image ${idx + 1}`} />
                {img.title && <div className="result-image-title">{img.title}</div>}
                {img.source && <div className="result-image-source">{img.source}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Text Results */}
      {hasTextResults && (
        <div className="result-text-section">
          <div className="result-section-label">Sources</div>
          {data.text_results!.slice(0, 5).map((item, idx) => (
            <div key={idx} className="result-text-item">
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                {item.title}
              </a>
              <p>{item.content}</p>
              <span className="result-source">{item.source}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Component to display a nested tool within side panel
function NestedToolCard({
  tool,
}: {
  tool: ToolStreamItem;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isRunning = tool.status === "running";

  // Always show raw JSON for tool output (no special rendering)
  const parsedResult = tool.result ? tryParseJson(tool.result) : null;

  return (
    <div className={`nested-tool-card ${tool.status}`}>
      <div className="nested-tool-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="nested-tool-title">
          {isRunning && <span className="spinner small" />}
          {!isRunning && <span className="check-icon small">✓</span>}
          <span className="nested-tool-icon">🔧</span>
          <span className="nested-tool-name">{tool.name}</span>
        </div>
        <span className="expand-icon small">{isExpanded ? "▼" : "▶"}</span>
      </div>

      {isExpanded && (
        <div className="nested-tool-details">
          {tool.args && (
            <div className="activity-section">
              <div className="activity-label">Input:</div>
              <pre className="activity-content small">{formatJson(tool.args)}</pre>
            </div>
          )}
          {tool.result && (
            <div className="activity-section">
              <div className="activity-label">Output:</div>
              <pre className="activity-content small">
                {parsedResult ? formatJson(parsedResult) : tool.result}
              </pre>
            </div>
          )}
          {isRunning && !tool.result && (
            <div className="activity-section">
              <span className="waiting-text small">Executing...</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Component to display nested subagent details
function NestedSubAgentCard({
  subagent,
  onImageClick,
}: {
  subagent: SubAgentStreamItem;
  onImageClick: (img: TavilyImage) => void;
}) {
  const isRunning = subagent.status === "running";
  const hasNestedTools = subagent.nestedTools && subagent.nestedTools.length > 0;

  return (
    <div className={`nested-subagent-card ${subagent.status}`}>
      <div className="nested-subagent-header">
        <div className="nested-subagent-title">
          {isRunning && <span className="spinner small" />}
          {!isRunning && <span className="check-icon small">✓</span>}
          <span className="nested-subagent-icon">🤖</span>
          <span className="nested-subagent-name">{subagent.name}</span>
          {hasNestedTools && (
            <span className="nested-count">({subagent.nestedTools!.length} tools)</span>
          )}
        </div>
      </div>

      <div className="nested-subagent-content">
        {/* Task description */}
        {subagent.description && (
          <div className="activity-section">
            <div className="activity-label">Task:</div>
            <pre className="activity-content small">{subagent.description}</pre>
          </div>
        )}

        {/* Nested tool calls */}
        {hasNestedTools && (
          <div className="activity-section">
            <div className="activity-label">Tool Calls:</div>
            <div className="nested-tools-container">
              {subagent.nestedTools!.map((nestedTool) => (
                <NestedToolCard
                  key={nestedTool.id}
                  tool={nestedTool}
                />
              ))}
            </div>
          </div>
        )}

        {/* Result - render structured result if available */}
        {subagent.result && (
          <div className="activity-section">
            <div className="activity-label">Result:</div>
            {(() => {
              const parsed = tryParseJson(subagent.result);
              if (isStructuredSearchResult(parsed)) {
                return <StructuredResultView data={parsed} onImageClick={onImageClick} />;
              }
              return (
                <pre className="activity-content small">
                  {parsed ? formatJson(parsed) : subagent.result}
                </pre>
              );
            })()}
          </div>
        )}

        {/* Loading state */}
        {isRunning && !hasNestedTools && (
          <div className="activity-section">
            <span className="waiting-text small">SubAgent working...</span>
          </div>
        )}
      </div>
    </div>
  );
}

// Side Panel component to display activity details
function SidePanel({
  activity,
  onClose,
  onImageClick,
}: {
  activity: StreamItem | null;
  onClose: () => void;
  onImageClick: (img: TavilyImage) => void;
}) {
  if (!activity) return null;

  const isToolCall = activity.type === "tool_call";
  const isSubAgent = activity.type === "subagent";
  const isRunning = isToolCall || isSubAgent ? (activity as ToolStreamItem | SubAgentStreamItem).status === "running" : false;

  // Tool call specific
  const toolItem = isToolCall ? (activity as ToolStreamItem) : null;
  const hasNestedSubAgent = toolItem?.nestedSubAgent !== undefined;

  // SubAgent specific
  const subagentItem = isSubAgent ? (activity as SubAgentStreamItem) : null;
  const hasNestedTools = subagentItem?.nestedTools && subagentItem.nestedTools.length > 0;

  // Try to parse tool result as Tavily response
  const parsedToolResult = toolItem?.result ? tryParseJson(toolItem.result) : null;
  const isTavilyResult = isTavilyResponse(parsedToolResult);

  // Calculate total tool count
  const getTotalToolCount = () => {
    if (toolItem?.nestedSubAgent?.nestedTools) {
      return toolItem.nestedSubAgent.nestedTools.length;
    }
    if (subagentItem?.nestedTools) {
      return subagentItem.nestedTools.length;
    }
    return 0;
  };

  const totalTools = getTotalToolCount();

  return (
    <div className="side-panel">
      <div className="side-panel-header">
        <div className="side-panel-title">
          {isRunning && <span className="spinner" />}
          {!isRunning && <span className="check-icon">✓</span>}
          <span className="activity-type">{isToolCall ? "🔧" : "🤖"}</span>
          <span>{isToolCall || isSubAgent ? (activity as ToolStreamItem | SubAgentStreamItem).name : ""}</span>
          {totalTools > 0 && <span className="nested-count">({totalTools} tools)</span>}
        </div>
        <button className="side-panel-close" onClick={onClose}>
          ✕
        </button>
      </div>

      <div className="side-panel-content">
        {/* Tool call input */}
        {toolItem && !hasNestedSubAgent && toolItem.args && (
          <div className="activity-section">
            <div className="activity-label">INPUT:</div>
            <pre className="activity-content">{formatJson(toolItem.args)}</pre>
          </div>
        )}

        {/* Nested SubAgent (for "task" tool) */}
        {hasNestedSubAgent && (
          <div className="activity-section">
            <NestedSubAgentCard
              subagent={toolItem!.nestedSubAgent!}
              onImageClick={onImageClick}
            />
          </div>
        )}

        {/* Tool call result */}
        {toolItem && !hasNestedSubAgent && toolItem.result && (
          <div className="activity-section">
            <div className="activity-label">OUTPUT:</div>
            {isTavilyResult ? (
              <TavilyResultView data={parsedToolResult} onImageClick={onImageClick} />
            ) : (
              <pre className="activity-content">
                {parsedToolResult ? formatJson(parsedToolResult) : toolItem.result}
              </pre>
            )}
          </div>
        )}

        {/* Standalone SubAgent - description */}
        {subagentItem && subagentItem.description && (
          <div className="activity-section">
            <div className="activity-label">TASK:</div>
            <pre className="activity-content">{subagentItem.description}</pre>
          </div>
        )}

        {/* Standalone SubAgent - nested tools */}
        {hasNestedTools && (
          <div className="activity-section">
            <div className="activity-label">TOOL CALLS:</div>
            <div className="nested-tools-container">
              {subagentItem!.nestedTools!.map((nestedTool) => (
                <NestedToolCard
                  key={nestedTool.id}
                  tool={nestedTool}
                />
              ))}
            </div>
          </div>
        )}

        {/* Standalone SubAgent - result with structured rendering */}
        {subagentItem && subagentItem.result && (
          <div className="activity-section">
            <div className="activity-label">RESULT:</div>
            {(() => {
              const parsed = tryParseJson(subagentItem.result);
              if (isStructuredSearchResult(parsed)) {
                return <StructuredResultView data={parsed} onImageClick={onImageClick} />;
              }
              return (
                <pre className="activity-content">
                  {parsed ? formatJson(parsed) : subagentItem.result}
                </pre>
              );
            })()}
          </div>
        )}

        {/* Loading state */}
        {isRunning && !hasNestedSubAgent && !hasNestedTools && (
          <div className="activity-section">
            <span className="waiting-text">
              {isSubAgent ? "SubAgent working..." : "Waiting for result..."}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// Text segment component - displays AI text
function TextSegment({ item }: { item: TextStreamItem }) {
  if (!item.content && !item.isStreaming) return null;

  return (
    <div className="message assistant">
      <div className="message-content">
        {item.content || (item.isStreaming && <span className="thinking">Thinking...</span>)}
        {item.isStreaming && item.content && <span className="cursor">|</span>}
      </div>
    </div>
  );
}

// Tool call card component - compact card in chat flow
function ToolCallCard({
  item,
  isSelected,
  onSelect,
}: {
  item: ToolStreamItem;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const hasNestedSubAgent = item.nestedSubAgent !== undefined;

  // Get nested subagent info for display
  const nestedSubAgent = item.nestedSubAgent;

  // For task tool with nested subagent, show subagent status
  const displayStatus = hasNestedSubAgent ? nestedSubAgent!.status : item.status;
  const displayRunning = displayStatus === "running";

  return (
    <div
      className={`activity-card compact tool_call ${displayStatus} ${isSelected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <div className="activity-header">
        <div className="activity-title">
          {displayRunning && <span className="spinner" />}
          {!displayRunning && <span className="check-icon">✓</span>}
          <span className="activity-type">🔧</span>
          <span className="activity-name">{item.name}</span>
        </div>
        <span className="expand-icon">▶</span>
      </div>

      {/* Show nested subagent and its tools inline */}
      {hasNestedSubAgent && (
        <div className="nested-inline">
          <div className="nested-inline-item">
            {nestedSubAgent!.status === "running" && <span className="spinner small" />}
            {nestedSubAgent!.status !== "running" && <span className="check-icon small">✓</span>}
            <span className="nested-icon">🤖</span>
            <span className="nested-name">{nestedSubAgent!.name}</span>
          </div>
          {nestedSubAgent!.nestedTools?.map((nt) => (
            <div key={nt.id} className="nested-inline-item nested-tool">
              {nt.status === "running" && <span className="spinner small" />}
              {nt.status !== "running" && <span className="check-icon small">✓</span>}
              <span className="nested-icon">🔧</span>
              <span className="nested-name">{nt.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// SubAgent card component - for standalone subagent
function SubAgentCard({
  item,
  isSelected,
  onSelect,
}: {
  item: SubAgentStreamItem;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const isRunning = item.status === "running";
  const nestedToolCount = item.nestedTools?.length || 0;

  return (
    <div
      className={`activity-card compact subagent ${item.status} ${isSelected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <div className="activity-header">
        <div className="activity-title">
          {isRunning && <span className="spinner" />}
          {!isRunning && <span className="check-icon">✓</span>}
          <span className="activity-type">🤖</span>
          <span className="activity-name">{item.name}</span>
          {nestedToolCount > 0 && (
            <span className="nested-count">({nestedToolCount} tools)</span>
          )}
        </div>
        <span className="expand-icon">▶</span>
      </div>

      {/* Show nested tools inline */}
      {item.nestedTools && item.nestedTools.length > 0 && (
        <div className="nested-inline">
          {item.nestedTools.map((nt) => (
            <div key={nt.id} className="nested-inline-item nested-tool">
              {nt.status === "running" && <span className="spinner small" />}
              {nt.status !== "running" && <span className="check-icon small">✓</span>}
              <span className="nested-icon">🔧</span>
              <span className="nested-name">{nt.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// TodoChecklist component - displays todos inline with professional checklist UI
function TodoChecklist({ item }: { item: TodoStreamItem }) {
  const { todos } = item;

  if (!todos || todos.length === 0) return null;

  // Calculate progress stats
  const completed = todos.filter((t) => t.status === "completed").length;
  const inProgress = todos.filter((t) => t.status === "in_progress").length;
  const total = todos.length;
  const progressPercent = total > 0 ? Math.round((completed / total) * 100) : 0;

  // Get status icon
  const getStatusIcon = (status: TodoItem["status"]) => {
    switch (status) {
      case "completed":
        return <span className="todo-icon completed">✓</span>;
      case "in_progress":
        return <span className="todo-icon in-progress spinner small" />;
      case "pending":
        return <span className="todo-icon pending">○</span>;
    }
  };

  return (
    <div className="todo-checklist">
      <div className="todo-header">
        <div className="todo-title">
          <svg className="todo-title-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M3 2.5A1.5 1.5 0 014.5 1h7A1.5 1.5 0 0113 2.5v11a1.5 1.5 0 01-1.5 1.5h-7A1.5 1.5 0 013 13.5v-11z" stroke="currentColor" strokeWidth="1.2"/>
            <path d="M5.5 5h5M5.5 8h5M5.5 11h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
          </svg>
          <span>Tasks</span>
        </div>
        <div className="todo-stats">
          <span className="todo-stat completed">{completed} done</span>
          {inProgress > 0 && <span className="todo-stat in-progress">{inProgress} active</span>}
          <span className="todo-stat total">{total} total</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="todo-progress-container">
        <div className="todo-progress-bar">
          <div
            className="todo-progress-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <span className="todo-progress-text">{progressPercent}%</span>
      </div>

      {/* Todo items */}
      <div className="todo-items">
        {todos.map((todo, index) => (
          <div key={index} className={`todo-item ${todo.status}`}>
            {getStatusIcon(todo.status)}
            <span className="todo-content">
              {todo.status === "in_progress" ? todo.activeForm : todo.content}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Assistant turn view - renders all stream items interleaved
function AssistantTurnView({
  turn,
  selectedActivity,
  onSelectActivity,
}: {
  turn: AssistantTurn;
  selectedActivity: StreamItem | null;
  onSelectActivity: (item: StreamItem) => void;
}) {
  // Show thinking if no items yet and still streaming
  if (turn.streamItems.length === 0 && turn.isStreaming) {
    return (
      <div className="assistant-turn">
        <div className="message assistant">
          <div className="message-content">
            <span className="thinking">Thinking...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="assistant-turn">
      {turn.streamItems.map((item) => {
        switch (item.type) {
          case "text":
            return <TextSegment key={item.id} item={item as TextStreamItem} />;

          case "tool_call":
            // Hide write_todos tool calls since we show TodoChecklist instead
            if ((item as ToolStreamItem).name === "write_todos") {
              return null;
            }
            return (
              <ToolCallCard
                key={item.id}
                item={item as ToolStreamItem}
                isSelected={selectedActivity?.id === item.id}
                onSelect={() => onSelectActivity(item)}
              />
            );

          case "subagent":
            return (
              <SubAgentCard
                key={item.id}
                item={item as SubAgentStreamItem}
                isSelected={selectedActivity?.id === item.id}
                onSelect={() => onSelectActivity(item)}
              />
            );

          case "todo":
            return <TodoChecklist key={item.id} item={item as TodoStreamItem} />;

          default:
            return null;
        }
      })}
    </div>
  );
}

// User message view
function UserMessageView({ message }: { message: UserMessage }) {
  return (
    <div className="message user">
      <div className="message-content">{message.content}</div>
    </div>
  );
}

function App() {
  const {
    conversation,
    isLoading,
    activeTools,
    activeSubAgents,
    error,
    sendMessage,
    clearMessages,
    stopGeneration,
  } = useSSEChat();

  const [input, setInput] = useState("");
  const [selectedActivity, setSelectedActivity] = useState<StreamItem | null>(null);
  const [modalImage, setModalImage] = useState<TavilyImage | null>(null);
  const [isDark, setIsDark] = useState(() => {
    // Check localStorage or system preference
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("theme");
      if (saved) return saved === "dark";
      return window.matchMedia("(prefers-color-scheme: dark)").matches;
    }
    return false;
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
    localStorage.setItem("theme", isDark ? "dark" : "light");
  }, [isDark]);

  // Auto-scroll to bottom when conversation updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation]);

  // Auto-select running task/subagent for side panel
  useEffect(() => {
    if (!isLoading) return;

    const lastTurn = conversation.filter((c) => c.role === "assistant").pop() as
      | AssistantTurn
      | undefined;
    if (!lastTurn) return;

    // Find running task with nested subagent or running standalone subagent
    for (const item of lastTurn.streamItems) {
      if (
        item.type === "tool_call" &&
        (item as ToolStreamItem).nestedSubAgent?.status === "running"
      ) {
        if (!selectedActivity || selectedActivity.id !== item.id) {
          setSelectedActivity(item);
        }
        return;
      }
      if (item.type === "subagent" && item.status === "running") {
        if (!selectedActivity || selectedActivity.id !== item.id) {
          setSelectedActivity(item);
        }
        return;
      }
    }
  }, [conversation, isLoading, selectedActivity]);

  // Update selected activity when it changes in conversation
  useEffect(() => {
    if (!selectedActivity) return;

    const lastTurn = conversation.filter((c) => c.role === "assistant").pop() as
      | AssistantTurn
      | undefined;
    if (!lastTurn) return;

    const updated = lastTurn.streamItems.find((si) => si.id === selectedActivity.id);
    if (updated && updated !== selectedActivity) {
      setSelectedActivity(updated);
    }
  }, [conversation, selectedActivity]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(input);
      setInput("");
      setSelectedActivity(null);
    }
  };

  const handleClear = () => {
    clearMessages();
    setSelectedActivity(null);
  };

  const hasSidePanel = selectedActivity !== null;

  return (
    <div className={`app-container ${hasSidePanel ? "with-panel" : ""}`}>
      <div className="chat-container">
        <header className="chat-header">
          <h1>AI Agent Chat</h1>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              onClick={() => setIsDark(!isDark)}
              className="theme-toggle"
              title={isDark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {isDark ? "☀️" : "🌙"}
            </button>
            <button onClick={handleClear} className="clear-btn">
              Clear
            </button>
          </div>
        </header>

        {/* Status indicators */}
        <div className="status-bar">
          {activeSubAgents.map((agent) => (
            <div key={agent.name} className="status-item subagent">
              <span className="spinner" />
              <span>SubAgent: {agent.name}</span>
            </div>
          ))}
          {activeTools.map((tool) => (
            <div key={tool.id} className="status-item tool">
              <span className="spinner" />
              <span>Tool: {tool.name}</span>
            </div>
          ))}
        </div>

        {/* Messages - Interleaved display */}
        <div className="messages">
          {conversation.length === 0 && (
            <div className="empty-state">
              <p>Start a conversation with the AI agent.</p>
              <p className="hint">Try asking about the weather, or request a task!</p>
            </div>
          )}
          {conversation.map((item) => {
            if (item.role === "user") {
              return <UserMessageView key={item.id} message={item as UserMessage} />;
            }
            return (
              <AssistantTurnView
                key={item.id}
                turn={item as AssistantTurn}
                selectedActivity={selectedActivity}
                onSelectActivity={setSelectedActivity}
              />
            );
          })}
          {error && <div className="error-message">Error: {error}</div>}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            disabled={isLoading}
          />
          {isLoading ? (
            <button type="button" onClick={stopGeneration} className="stop-btn">
              Stop
            </button>
          ) : (
            <button type="submit" disabled={!input.trim()}>
              Send
            </button>
          )}
        </form>
      </div>

      {/* Side Panel */}
      <SidePanel
        activity={selectedActivity}
        onClose={() => setSelectedActivity(null)}
        onImageClick={setModalImage}
      />

      {/* Image Modal */}
      {modalImage && (
        <ImageModal image={modalImage} onClose={() => setModalImage(null)} />
      )}
    </div>
  );
}

export default App;
