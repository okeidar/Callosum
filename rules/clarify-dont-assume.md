# Clarify Don't Assume

## NEVER Make Assumptions About Requirements

When requirements are unclear or ambiguous, **ALWAYS ask for clarification** instead of guessing.

## Avoid Speculation

**DO NOT speculate, assume, or fabricate details that have not been explicitly agreed upon or documented:**

- ❌ Only reference features, details, or design elements that are explicitly documented
- ❌ Don't add new functionality that hasn't been previously discussed and approved
- ❌ Don't make assumptions about implementation details when requirements don't specify them
- ❌ When writing documentation files, DO NOT make assumptions about the project or write speculation/things that were not agreed upon
- ✅ If information is missing or unclear, ALWAYS ask for clarification
- ✅ When multiple interpretations are possible, present OPTIONS rather than selecting one arbitrarily

## Common Assumption Traps

### ❌ Don't Assume Implementation Details
**Instead of assuming:**
- "I'll add utility functions for completeness"
- "This probably needs configuration options"
- "Users might want this extra feature"

**Ask instead:**
- "Should this expose utility functions like `can_perform_action()` and `get_status()`?"
- "Do you want configuration options for this behavior?"
- "What specific functionality do you need beyond the core requirements?"

### ❌ Don't Assume Architecture Decisions
**Instead of assuming:**
- "This should follow pattern X"
- "Single vs multi should have separate functions"
- "This needs both sync and async implementations"

**Ask instead:**
- "Should this follow the same pattern as [existing system]?"
- "Would you prefer separate functions for single/multi, or a unified interface?"
- "Do you need async support, or should I keep it synchronous?"

### ❌ Don't Assume User Needs
**Instead of assuming:**
- "Users will probably want progress tracking"
- "This should have multiple configuration modes"
- "Better add debugging features just in case"

**Ask instead:**
- "Do you need progress tracking functionality?"
- "What configuration options are actually required?"
- "Should I include debug logging, or keep the implementation minimal?"

## Question Framework

When unclear about any aspect, ask:

1. **Scope:** "Should this handle X, or is that out of scope?"
2. **Interface:** "Do you prefer approach A or approach B for this interface?"
3. **Architecture:** "Should this follow the same pattern as [existing system]?"
4. **Requirements:** "Is [specific functionality] actually needed, or should I keep it minimal?"

## Red Flags - Stop and Ask

- Multiple ways to implement something exist
- Requirements don't specify implementation approach
- You're adding features not explicitly mentioned
- Your solution differs significantly from existing patterns
- You're uncertain about architectural decisions
- There's a term you don't understand - look it up in documentation, online, or ask for clarification

**When in doubt, present options and let the user choose rather than assuming the "best" approach.**
