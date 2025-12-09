import { useState, useCallback, useRef } from "react";
import type {
  ActiveTool,
  ActiveSubAgent,
  ContentBlock,
  LlmTokenData,
  LlmEndData,
  ToolCallData,
  ToolResultData,
  SubAgentStartData,
  SubAgentEndData,
  SubAgentToolCallData,
  SubAgentToolResultData,
  ErrorData,
  DoneData,
  // New types for interleaved display
  ConversationItem,
  UserMessage,
  AssistantTurn,
  StreamItem,
  TextStreamItem,
  ToolStreamItem,
  SubAgentStreamItem,
  // Todo types
  TodoItem,
  TodoStreamItem,
} from "../types";

const API_URL = "http://localhost:8000";

/**
 * Extract text from token data.
 * Handles both OpenAI (string) and Anthropic (ContentBlock[]) formats.
 */
function extractToken(token: string | ContentBlock[]): string {
  if (typeof token === "string") return token;
  return token
    .filter((b) => b.type === "text" && b.text)
    .map((b) => b.text!)
    .join("");
}

/**
 * Custom hook for SSE-based chat with the AI agent.
 * Uses interleaved display for text segments and tool calls.
 */
export function useSSEChat() {
  const [conversation, setConversation] = useState<ConversationItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTools, setActiveTools] = useState<ActiveTool[]>([]);
  const [activeSubAgents, setActiveSubAgents] = useState<ActiveSubAgent[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Token buffering for smoother UI updates
  const bufferRef = useRef("");
  const flushTimeoutRef = useRef<number | null>(null);
  const currentTurnIdRef = useRef<string | null>(null);
  const currentTextItemIdRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Flush buffered tokens to the current text stream item.
   * Creates a new TextStreamItem if none exists.
   */
  const flushBuffer = useCallback(() => {
    if (!bufferRef.current || !currentTurnIdRef.current) return;

    const bufferedText = bufferRef.current;
    bufferRef.current = "";

    setConversation((prev) =>
      prev.map((item) => {
        if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
          return item;
        }

        const turn = item as AssistantTurn;
        let newItems = [...turn.streamItems];

        if (currentTextItemIdRef.current) {
          // Append to existing text item
          newItems = newItems.map((si) => {
            if (si.type === "text" && si.id === currentTextItemIdRef.current) {
              return { ...si, content: si.content + bufferedText };
            }
            return si;
          });
        } else {
          // Create new text item
          const newTextItem: TextStreamItem = {
            id: `text-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
            type: "text",
            content: bufferedText,
            isStreaming: true,
            timestamp: new Date(),
          };
          currentTextItemIdRef.current = newTextItem.id;
          newItems.push(newTextItem);
        }

        return { ...turn, streamItems: newItems };
      })
    );
  }, []);

  /**
   * Buffer a token and schedule flush.
   */
  const bufferToken = useCallback(
    (text: string) => {
      bufferRef.current += text;

      if (flushTimeoutRef.current) {
        clearTimeout(flushTimeoutRef.current);
      }

      // Flush buffer every 50ms for smooth UI
      flushTimeoutRef.current = window.setTimeout(flushBuffer, 50);
    },
    [flushBuffer]
  );

  /**
   * Finalize the current text stream item (set isStreaming to false).
   */
  const finalizeCurrentTextItem = useCallback(() => {
    if (!currentTurnIdRef.current || !currentTextItemIdRef.current) return;

    setConversation((prev) =>
      prev.map((item) => {
        if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
          return item;
        }

        const turn = item as AssistantTurn;
        return {
          ...turn,
          streamItems: turn.streamItems.map((si) => {
            if (si.type === "text" && si.id === currentTextItemIdRef.current) {
              return { ...si, isStreaming: false };
            }
            return si;
          }),
        };
      })
    );

    currentTextItemIdRef.current = null;
  }, []);

  /**
   * Handle SSE events and update conversation state.
   */
  const handleEvent = useCallback(
    (eventType: string, data: unknown) => {
      switch (eventType) {
        case "llm_token": {
          const { token } = data as LlmTokenData;
          bufferToken(extractToken(token));
          break;
        }

        case "tool_call": {
          const toolData = data as ToolCallData;

          // Flush any buffered text first
          flushBuffer();

          // Finalize current text item
          finalizeCurrentTextItem();

          // Add to active tools for status display
          setActiveTools((prev) => [
            ...prev,
            { id: toolData.id, name: toolData.tool, args: toolData.args },
          ]);

          // Add tool call to stream items
          setConversation((prev) =>
            prev.map((item) => {
              if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
                return item;
              }

              const turn = item as AssistantTurn;
              const toolItem: ToolStreamItem = {
                id: toolData.id,
                type: "tool_call",
                name: toolData.tool,
                args: toolData.args,
                status: "running",
                startTime: new Date(),
              };

              return {
                ...turn,
                streamItems: [...turn.streamItems, toolItem],
              };
            })
          );
          break;
        }

        case "tool_result": {
          const resultData = data as ToolResultData;

          // Remove from active tools
          setActiveTools((prev) =>
            prev.filter((t) => t.id !== resultData.tool_call_id)
          );

          // Special handling for write_todos: add TodoStreamItem to conversation
          if (resultData.tool === "write_todos") {
            // Find the tool call args to get the todos list
            setConversation((prev) =>
              prev.map((item) => {
                if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
                  return item;
                }

                const turn = item as AssistantTurn;

                // Find the write_todos tool call to get the args
                const toolCall = turn.streamItems.find(
                  (si) => si.type === "tool_call" && si.id === resultData.tool_call_id
                ) as ToolStreamItem | undefined;

                let todos: TodoItem[] = [];
                if (toolCall?.args?.todos && Array.isArray(toolCall.args.todos)) {
                  todos = toolCall.args.todos as TodoItem[];
                }

                // Create TodoStreamItem
                const todoItem: TodoStreamItem = {
                  id: `todo-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
                  type: "todo",
                  todos,
                  timestamp: new Date(),
                };

                // Update the tool call status and add todo item
                return {
                  ...turn,
                  streamItems: [
                    ...turn.streamItems.map((si) => {
                      if (si.type === "tool_call" && si.id === resultData.tool_call_id) {
                        return {
                          ...si,
                          status: "completed" as const,
                          result: resultData.result,
                          endTime: new Date(),
                        };
                      }
                      return si;
                    }),
                    todoItem,
                  ],
                };
              })
            );
            break;
          }

          // Update tool stream item with result
          setConversation((prev) =>
            prev.map((item) => {
              if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
                return item;
              }

              const turn = item as AssistantTurn;
              return {
                ...turn,
                streamItems: turn.streamItems.map((si) => {
                  if (si.type === "tool_call" && si.id === resultData.tool_call_id) {
                    return {
                      ...si,
                      status: "completed" as const,
                      result: resultData.result,
                      endTime: new Date(),
                    };
                  }
                  return si;
                }),
              };
            })
          );
          break;
        }

        case "subagent_start": {
          const startData = data as SubAgentStartData;

          // Add to active subagents
          setActiveSubAgents((prev) => [
            ...prev,
            { name: startData.name, description: startData.description },
          ]);

          // Find the most recent running "task" tool and nest subagent inside it
          setConversation((prev) =>
            prev.map((item) => {
              if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
                return item;
              }

              const turn = item as AssistantTurn;
              let foundTask = false;

              // Look for running task tool to nest into
              const newItems = turn.streamItems.map((si) => {
                if (
                  si.type === "tool_call" &&
                  si.name === "task" &&
                  si.status === "running" &&
                  !si.nestedSubAgent &&
                  !foundTask
                ) {
                  foundTask = true;
                  return {
                    ...si,
                    nestedSubAgent: {
                      id: `subagent-${startData.name}-${Date.now()}`,
                      type: "subagent" as const,
                      name: startData.name,
                      description: startData.description,
                      status: "running" as const,
                      startTime: new Date(),
                    },
                  };
                }
                return si;
              });

              // If no task tool found, add as standalone subagent
              if (!foundTask) {
                const subagentItem: SubAgentStreamItem = {
                  id: `subagent-${startData.name}-${Date.now()}`,
                  type: "subagent",
                  name: startData.name,
                  description: startData.description,
                  status: "running",
                  startTime: new Date(),
                };
                newItems.push(subagentItem);
              }

              return { ...turn, streamItems: newItems };
            })
          );
          break;
        }

        case "subagent_end": {
          const endData = data as SubAgentEndData;

          // Remove from active subagents
          setActiveSubAgents((prev) =>
            prev.filter((a) => a.name !== endData.name)
          );

          // Update subagent status (either nested or standalone)
          setConversation((prev) =>
            prev.map((item) => {
              if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
                return item;
              }

              const turn = item as AssistantTurn;
              return {
                ...turn,
                streamItems: turn.streamItems.map((si) => {
                  // Check if nested in task tool
                  if (
                    si.type === "tool_call" &&
                    si.nestedSubAgent &&
                    si.nestedSubAgent.name === endData.name &&
                    si.nestedSubAgent.status === "running"
                  ) {
                    return {
                      ...si,
                      nestedSubAgent: {
                        ...si.nestedSubAgent,
                        status: "completed" as const,
                        result: endData.result,
                        endTime: new Date(),
                      },
                    };
                  }
                  // Check if standalone subagent
                  if (
                    si.type === "subagent" &&
                    si.name === endData.name &&
                    si.status === "running"
                  ) {
                    return {
                      ...si,
                      status: "completed" as const,
                      result: endData.result,
                      endTime: new Date(),
                    };
                  }
                  return si;
                }),
              };
            })
          );
          break;
        }

        case "subagent_tool_call": {
          const nestedData = data as SubAgentToolCallData;

          // Add nested tool to subagent
          setConversation((prev) =>
            prev.map((item) => {
              if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
                return item;
              }

              const turn = item as AssistantTurn;
              return {
                ...turn,
                streamItems: turn.streamItems.map((si) => {
                  // Check if nested in task tool
                  if (
                    si.type === "tool_call" &&
                    si.nestedSubAgent &&
                    si.nestedSubAgent.name === nestedData.subagent_name &&
                    si.nestedSubAgent.status === "running"
                  ) {
                    const nestedTool: ToolStreamItem = {
                      id: nestedData.id,
                      type: "tool_call",
                      name: nestedData.tool,
                      args: nestedData.args,
                      status: "running",
                      startTime: new Date(),
                    };
                    return {
                      ...si,
                      nestedSubAgent: {
                        ...si.nestedSubAgent,
                        nestedTools: [...(si.nestedSubAgent.nestedTools || []), nestedTool],
                      },
                    };
                  }
                  // Check if standalone subagent
                  if (
                    si.type === "subagent" &&
                    si.name === nestedData.subagent_name &&
                    si.status === "running"
                  ) {
                    const nestedTool: ToolStreamItem = {
                      id: nestedData.id,
                      type: "tool_call",
                      name: nestedData.tool,
                      args: nestedData.args,
                      status: "running",
                      startTime: new Date(),
                    };
                    return {
                      ...si,
                      nestedTools: [...(si.nestedTools || []), nestedTool],
                    };
                  }
                  return si;
                }),
              };
            })
          );
          break;
        }

        case "subagent_tool_result": {
          const nestedResult = data as SubAgentToolResultData;

          // Update nested tool result
          setConversation((prev) =>
            prev.map((item) => {
              if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
                return item;
              }

              const turn = item as AssistantTurn;
              return {
                ...turn,
                streamItems: turn.streamItems.map((si) => {
                  // Check if nested in task tool
                  if (
                    si.type === "tool_call" &&
                    si.nestedSubAgent &&
                    si.nestedSubAgent.name === nestedResult.subagent_name
                  ) {
                    return {
                      ...si,
                      nestedSubAgent: {
                        ...si.nestedSubAgent,
                        nestedTools: (si.nestedSubAgent.nestedTools || []).map((nt) =>
                          nt.id === nestedResult.tool_call_id
                            ? {
                                ...nt,
                                status: "completed" as const,
                                result: nestedResult.result,
                                endTime: new Date(),
                              }
                            : nt
                        ),
                      },
                    };
                  }
                  // Check if standalone subagent
                  if (
                    si.type === "subagent" &&
                    si.name === nestedResult.subagent_name
                  ) {
                    return {
                      ...si,
                      nestedTools: (si.nestedTools || []).map((nt) =>
                        nt.id === nestedResult.tool_call_id
                          ? {
                              ...nt,
                              status: "completed" as const,
                              result: nestedResult.result,
                              endTime: new Date(),
                            }
                          : nt
                      ),
                    };
                  }
                  return si;
                }),
              };
            })
          );
          break;
        }

        case "llm_end": {
          const endData = data as LlmEndData;

          // Flush any remaining buffer
          flushBuffer();

          // If there's content and no text items were created from tokens,
          // use llm_end content as fallback
          if (endData.content && currentTurnIdRef.current) {
            setConversation((prev) =>
              prev.map((item) => {
                if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
                  return item;
                }

                const turn = item as AssistantTurn;

                // Calculate total text content from stream items
                const existingText = turn.streamItems
                  .filter((si): si is TextStreamItem => si.type === "text")
                  .map((si) => si.content)
                  .join("");

                // If existing text is significantly shorter than llm_end content,
                // we might have missed some tokens - use the complete content
                if (existingText.length < endData.content.length * 0.5) {
                  // Create text item with full content
                  const newTextItem: TextStreamItem = {
                    id: `text-llm-end-${Date.now()}`,
                    type: "text",
                    content: endData.content,
                    isStreaming: false,
                    timestamp: new Date(),
                  };

                  // Remove any existing text items and add the complete one
                  const nonTextItems = turn.streamItems.filter((si) => si.type !== "text");
                  return {
                    ...turn,
                    streamItems: [...nonTextItems, newTextItem],
                  };
                }

                return turn;
              })
            );
          }

          finalizeCurrentTextItem();
          break;
        }

        case "error": {
          const errorData = data as ErrorData;
          setError(errorData.message);
          break;
        }

        case "done": {
          const doneData = data as DoneData;

          // Final flush
          flushBuffer();

          // Use final_response as last resort if no text content
          if (doneData.final_response && currentTurnIdRef.current) {
            setConversation((prev) =>
              prev.map((item) => {
                if (item.role !== "assistant" || item.id !== currentTurnIdRef.current) {
                  return item;
                }

                const turn = item as AssistantTurn;
                const hasTextContent = turn.streamItems.some(
                  (si) => si.type === "text" && (si as TextStreamItem).content
                );

                if (!hasTextContent && doneData.final_response) {
                  const textItem: TextStreamItem = {
                    id: `text-final-${Date.now()}`,
                    type: "text",
                    content: doneData.final_response,
                    isStreaming: false,
                    timestamp: new Date(),
                  };
                  return {
                    ...turn,
                    streamItems: [...turn.streamItems, textItem],
                  };
                }

                return turn;
              })
            );
          }

          finalizeCurrentTextItem();
          break;
        }
      }
    },
    [bufferToken, flushBuffer, finalizeCurrentTextItem]
  );

  /**
   * Send a message to the chat API.
   */
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isLoading) return;

      setError(null);
      setIsLoading(true);

      // Add user message
      const userMessage: UserMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content,
        timestamp: new Date(),
      };

      // Add empty assistant turn
      const assistantTurnId = `assistant-${Date.now()}`;
      currentTurnIdRef.current = assistantTurnId;
      currentTextItemIdRef.current = null;

      const assistantTurn: AssistantTurn = {
        id: assistantTurnId,
        role: "assistant",
        timestamp: new Date(),
        isStreaming: true,
        streamItems: [],
      };

      setConversation((prev) => [...prev, userMessage, assistantTurn]);

      // Create abort controller for this request
      abortControllerRef.current = new AbortController();

      try {
        const response = await fetch(`${API_URL}/api/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: content }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) throw new Error("No response body");

        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let currentEvent = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              currentEvent = line.slice(7);
            } else if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                handleEvent(currentEvent, data);
              } catch {
                // Skip malformed JSON
              }
            }
          }
        }
      } catch (err) {
        // Don't show error if it was aborted by user
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        // Final flush
        flushBuffer();
        finalizeCurrentTextItem();

        // Mark turn as not streaming
        setConversation((prev) =>
          prev.map((item) =>
            item.role === "assistant" && item.id === currentTurnIdRef.current
              ? { ...item, isStreaming: false }
              : item
          )
        );

        currentTurnIdRef.current = null;
        currentTextItemIdRef.current = null;
        abortControllerRef.current = null;
        setIsLoading(false);
        setActiveTools([]);
        setActiveSubAgents([]);
      }
    },
    [isLoading, handleEvent, flushBuffer, finalizeCurrentTextItem]
  );

  /**
   * Stop the current generation.
   */
  const stopGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  /**
   * Clear all messages.
   */
  const clearMessages = useCallback(() => {
    setConversation([]);
    setError(null);
  }, []);

  /**
   * Get all tool activities from the current assistant turn (for side panel).
   */
  const getToolActivities = useCallback((): StreamItem[] => {
    const lastTurn = conversation.filter((c) => c.role === "assistant").pop() as AssistantTurn | undefined;
    if (!lastTurn) return [];
    return lastTurn.streamItems.filter((si) => si.type === "tool_call" || si.type === "subagent");
  }, [conversation]);

  return {
    conversation,
    isLoading,
    activeTools,
    activeSubAgents,
    error,
    sendMessage,
    clearMessages,
    stopGeneration,
    getToolActivities,
  };
}
