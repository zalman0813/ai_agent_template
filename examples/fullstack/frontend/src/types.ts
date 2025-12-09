/**
 * Event types from the backend streaming API.
 * Reference: app_docs/streaming_api_contract.md
 */

export type EventType =
  | "llm_token"
  | "llm_end"
  | "node_start"
  | "node_end"
  | "tool_call"
  | "tool_result"
  | "subagent_start"
  | "subagent_end"
  | "error"
  | "done";

/**
 * Anthropic content block format.
 * LLM tokens can be either a string (OpenAI) or an array of these blocks (Anthropic).
 */
export interface ContentBlock {
  type: "text" | "input_json_delta";
  text?: string;
  partial_json?: string;
  index: number;
}

// Event data types

export interface LlmTokenData {
  token: string | ContentBlock[];
}

export interface LlmEndData {
  content: string;
}

export interface NodeData {
  node: "model" | "tools";
}

export interface ToolCallData {
  tool: string;
  args: Record<string, unknown>;
  id: string;
}

export interface ToolResultData {
  tool: string;
  result: string;
  tool_call_id: string;
}

export interface SubAgentStartData {
  name: string;
  description: string;
}

export interface SubAgentEndData {
  name: string;
  result: string;  // Full result for structured rendering
}

export interface ErrorData {
  message: string;
  code?: string;
}

export interface DoneData {
  final_response: string;
}

// UI state types

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ActiveTool {
  id: string;
  name: string;
  args?: Record<string, unknown>;
}

export interface ActiveSubAgent {
  name: string;
  description: string;
}

// Tool activity for inline display in chat
export interface ToolActivity {
  id: string;
  type: "tool" | "subagent";
  name: string;
  status: "running" | "completed" | "error";
  input?: Record<string, unknown>;
  output?: string;
  startTime: Date;
  endTime?: Date;
  // Nested tool calls within this subagent
  nestedTools?: ToolActivity[];
  // Nested subagent within this tool (for "task" tool)
  nestedSubAgent?: ToolActivity;
}

// Event for subagent's internal tool calls
export interface SubAgentToolCallData {
  subagent_name: string;
  tool: string;
  args: Record<string, unknown>;
  id: string;
}

export interface SubAgentToolResultData {
  subagent_name: string;
  tool: string;
  result: string;
  tool_call_id: string;
}

// Extended message that can include tool activities
export interface ChatMessageWithActivities extends ChatMessage {
  activities?: ToolActivity[];
}

// ============================================
// New types for interleaved message display
// ============================================

/**
 * Text segment - represents a chunk of AI text response
 */
export interface TextStreamItem {
  id: string;
  type: "text";
  content: string;
  isStreaming: boolean;
  timestamp: Date;
}

/**
 * Tool call item - represents a tool invocation in the stream
 */
export interface ToolStreamItem {
  id: string;
  type: "tool_call";
  name: string;
  args: Record<string, unknown>;
  status: "running" | "completed" | "error";
  result?: string;
  startTime: Date;
  endTime?: Date;
  // For nested subagent within "task" tool
  nestedSubAgent?: SubAgentStreamItem;
}

/**
 * SubAgent item - represents a sub-agent execution
 */
export interface SubAgentStreamItem {
  id: string;
  type: "subagent";
  name: string;
  description: string;
  status: "running" | "completed" | "error";
  result?: string;
  startTime: Date;
  endTime?: Date;
  // Nested tool calls within this subagent
  nestedTools?: ToolStreamItem[];
}

/**
 * Union type for all stream items
 */
export type StreamItem = TextStreamItem | ToolStreamItem | SubAgentStreamItem | TodoStreamItem;

/**
 * Assistant Turn - contains all stream items for one AI response
 */
export interface AssistantTurn {
  id: string;
  role: "assistant";
  timestamp: Date;
  isStreaming: boolean;
  streamItems: StreamItem[];
}

/**
 * User message
 */
export interface UserMessage {
  id: string;
  role: "user";
  content: string;
  timestamp: Date;
}

/**
 * Conversation item - can be user message or assistant turn
 */
export type ConversationItem = UserMessage | AssistantTurn;

// ============================================
// Todo types for inline checklist display
// ============================================

/**
 * Single todo item structure from write_todos tool
 */
export interface TodoItem {
  content: string;
  status: "pending" | "in_progress" | "completed";
  activeForm: string;
}

/**
 * Todo stream item - represents a todo list update in the stream
 */
export interface TodoStreamItem {
  id: string;
  type: "todo";
  todos: TodoItem[];
  timestamp: Date;
}

// ============================================
// Tavily types for image rendering
// ============================================

/**
 * Tavily image from search results
 * Can be either a string URL or an object with url and description
 */
export type TavilyImage = string | { url: string; description?: string };

/**
 * Tavily search result item
 */
export interface TavilyResult {
  title: string;
  url: string;
  content: string;
  score: number;
  raw_content?: string | null;
}

/**
 * Tavily search response structure
 */
export interface TavilySearchResponse {
  query: string;
  images?: TavilyImage[];
  results: TavilyResult[];
  response_time?: number;
  answer?: string;
}
