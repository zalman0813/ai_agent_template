---
allowed-tools: Read, Grep, Glob, Edit, WebSearch, WebFetch
description: Reflect on spec implementation process and generate improvement lessons
argument-hint: [spec-file-path]
model: sonnet
---

# Spec Implementation Reflection

You are tasked with conducting a comprehensive post-implementation reflection (PIR) for a spec implementation session. This reflection will generate actionable lessons learned to evolve the spec-implement system.

## Variables

SPEC_FILE_PATH: $1
SLASH_COMMANDS_DIR: .claude/commands/
AGENTS_DIR: .claude/agents/

## Workflow

1. **Gather Implementation Context**
   - Read the spec file at `SPEC_FILE_PATH`
   - Search for any related discussion files, notes, or logs in the project
   - Identify which slash commands were used during the implementation process
   - List all deviations, blockers, and clarifications that occurred

2. **Analyze the Spec Document Quality**
   - Evaluate the spec's completeness: Were all necessary details provided?
   - Check for ambiguity: Which sections caused confusion or required clarification?
   - Assess technical accuracy: Were the API references, library versions, and code examples correct?
   - Review structure: Did the format help or hinder implementation?

3. **Identify Root Causes of Friction**
   For each issue encountered, determine if it was caused by:
   - **User's Requirement Clarity**: Was the original high-level prompt too vague?
   - **Spec Document Gaps**: Missing edge cases, error handling, or integration details?
   - **Documentation Currency**: Outdated API references or deprecated patterns?
   - **Agent Capability Limits**: Things the AI couldn't infer or needed to ask about?
   - **Workflow Design**: Is the spec-implement process itself flawed?

4. **Generate Improvement Recommendations**
   Categorize recommendations by:

   **A. User Prompt Improvements**
   - What questions should users answer upfront?
   - Template or checklist for better requirement gathering

   **B. Spec Template Enhancements**
   - Sections that should be mandatory
   - Better structure for complex implementations

   **C. Slash Command Modifications**
   - Changes needed to existing commands in `SLASH_COMMANDS_DIR`
   - New commands that would help

   **D. Agent Behavior Improvements**
   - When should the agent ask clarifying questions?
   - What validation steps should be automatic?

5. **Propose Specific File Changes**
   - Draft concrete edits for slash command files
   - Suggest new sections for spec templates
   - Recommend agent configuration changes

## Report

Generate a structured reflection report in the following format:

```markdown
# Spec Implementation Reflection Report

## Overview
- **Spec File**: [path]
- **Implementation Date**: [date]
- **Success Rate**: [% of spec completed without issues]
- **Total Blockers Encountered**: [number]

## Issue Analysis

### Issue 1: [Title]
- **Category**: [User Prompt | Spec Gap | Outdated Docs | Agent Limit | Workflow]
- **Description**: What happened
- **Root Cause**: Why it happened
- **Impact**: How it affected implementation
- **Proposed Fix**: Specific recommendation

[Repeat for each issue]

## Recommended System Improvements

### User Experience
1. [Recommendation with rationale]

### Spec Template Changes
```diff
+ [lines to add]
- [lines to remove]
```

### Slash Command Updates

#### [command-name.md]
```diff
[proposed changes]
```

### Agent Clarification Triggers
- When user says X, agent should ask Y
- Before implementing Z, verify A, B, C

## Lessons Learned Summary

| Category | Issue Count | Key Insight |
|----------|-------------|-------------|
| User Prompt | N | ... |
| Spec Quality | N | ... |
| Documentation | N | ... |
| Agent Behavior | N | ... |
| Workflow | N | ... |

## Action Items
- [ ] [Specific, actionable task]
- [ ] [Specific, actionable task]

## Questions for Future Specs
1. [Question the user should answer next time]
2. [Question the user should answer next time]
```

After generating the report, ask the user:
1. Which improvements should be implemented immediately?
2. Are there any additional issues not captured in this reflection?
3. Should this lesson be saved for future reference?
