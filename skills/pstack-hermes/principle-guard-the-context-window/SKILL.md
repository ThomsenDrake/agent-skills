---
name: principle-guard-the-context-window
description: "Use when large outputs threaten the context window."
compatibility: Hermes Agent with bounded file reads; execute_code or delegate_task when available.
---

# Guard the Context Window

When context is filling up through large outputs, long files, repeated reads, or fan-out planning, keep summaries in the main thread rather than raw payloads.

**Why:** Context overflow degrades reasoning quality, creates compression artifacts, and halts progress.

**Pattern:**
- **Size phases and cap scope.** Limit files per phase, set turn budgets, account for mechanism costs.
- Bound retrieval with `read_file` offsets and limits or targeted `search_files` queries. Use `execute_code` when available to filter bulk tool results before they enter context.
- Route independent bulk analysis through `delegate_task(tasks=[{"goal": "...", "context": "..."}])` when available. Children have isolated context, so supply paths, the question, write fences, and a concise output contract. They inherit centrally configured model settings. Keep findings and evidence paths, not raw payloads.
