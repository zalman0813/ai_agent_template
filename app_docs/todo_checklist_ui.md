# Todo Checklist UI in Chat

**Date:** 2025-12-01
**Specification:** N/A

## Overview

Implemented a professional checklist UI component that displays `write_todos` tool output directly in the chat flow instead of the sidebar. The checklist automatically expands inline when the agent updates its task list, providing real-time visibility into task progress with a modern, Linear/Notion-inspired design.

## What Was Built

- `TodoChecklist` React component with progress bar and status indicators
- `TodoStreamItem` type for handling todo data in the conversation stream
- Special handling in `useSSEChat` hook to intercept `write_todos` tool results
- Professional CSS styling with dark/light mode support

## Technical Implementation

### Files Modified

- `examples/fullstack/frontend/src/types.ts`: Added `TodoItem` and `TodoStreamItem` interfaces, updated `StreamItem` union type
- `examples/fullstack/frontend/src/hooks/useSSEChat.ts`: Added special handling for `write_todos` tool to create `TodoStreamItem` from tool args
- `examples/fullstack/frontend/src/App.tsx`: Added `TodoChecklist` component and integrated it into `AssistantTurnView`
- `examples/fullstack/frontend/src/App.css`: Added comprehensive styling for the checklist component

### Key Changes

- When `tool_result` event is received for `write_todos`, the hook extracts todos from the tool call args instead of just storing the result string
- `TodoStreamItem` is appended to the assistant turn's `streamItems` array, appearing inline in the chat
- The `write_todos` tool card itself is hidden (`return null`) since the checklist provides a better visualization
- Progress calculation shows percentage complete with animated progress bar
- Status-specific styling: completed items are struck through, in_progress items have purple highlight

### Data Flow

```
Backend (write_todos tool)
    -> SSE: tool_call event (contains todos in args)
    -> SSE: tool_result event (triggers TodoStreamItem creation)
    -> useSSEChat extracts todos from tool_call args
    -> Creates TodoStreamItem with parsed todos array
    -> TodoChecklist renders in chat flow
```

### TodoItem Structure

```typescript
interface TodoItem {
  content: string;           // Task description (imperative form)
  status: "pending" | "in_progress" | "completed";
  activeForm: string;        // Present continuous form for in_progress display
}
```

## How to Use

1. Start the backend server: `uv run python examples/fullstack/backend/main.py`
2. Start the frontend: `cd examples/fullstack/frontend && npm run dev`
3. Ask the agent to perform a multi-step task (e.g., "Help me refactor the authentication module")
4. When the agent calls `write_todos`, the checklist will appear inline in the chat
5. The checklist updates each time the agent calls `write_todos` with new task states

## Configuration

No additional configuration required. The component uses existing CSS variables for theming:
- Light mode: White background with subtle borders
- Dark mode: Dark gray background with adjusted colors
- Progress bar uses `--success` color variable

## Testing

1. Trigger a `write_todos` tool call by asking the agent to plan a complex task
2. Verify the checklist appears inline (not in sidebar)
3. Verify progress bar reflects completion percentage
4. Verify `in_progress` items show `activeForm` text with purple highlight
5. Verify `completed` items show strikethrough styling
6. Test both light and dark modes

## Notes

- The `write_todos` tool card is intentionally hidden since the checklist provides superior UX
- Each `write_todos` call creates a new `TodoStreamItem`, so multiple checklist snapshots may appear in a single conversation turn
- The component handles empty todos arrays gracefully (returns null)
- Future consideration: Could add collapsible/expandable behavior if todo lists become very long
