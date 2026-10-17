---
name: how
description: "Use when explaining subsystem architecture or flow."
compatibility: "Requires Hermes skill_view, delegation, read_file, search_files, and terminal for runtime checks."
---

# How

Answer how code works at the level of a senior engineer onboarding onto a subsystem. Build a useful mental model of architecture, runtime flow, ownership, and placement without turning the answer into annotated source. For historical motivation, load `why` instead.

## Delegation and prerequisites

The parent coordinates the stages with `delegate_task(tasks=[{"goal": "...", "context": "..."}, ...])`. Children inherit the parent model unless global delegation settings override it. Distinct explorer angles and a separate explainer are same-model roles by default, not cross-model evidence. Do not select models per call or ask children to delegate further.

Use `skill_view(name="how", file_path="references/explorer-prompt.md")` and `skill_view(name="how", file_path="references/explainer-prompt.md")` to load the full templates before filling them in. Each brief includes the question, repository/workspace path, revision when relevant, scope, required evidence, and a no-write instruction. This instruction is not a filesystem sandbox. Use `read_file` and `search_files` for investigation; use `terminal` only for authorized non-mutating checks. No code edits, commits, or external writes are part of this workflow.

Confirm access to the target first. If the question is ambiguous, state a reasonable interpretation and explore so the user can redirect.

## 1. Assess complexity

- **Simple:** one module, utility, or narrow question. Dispatch one explainer that explores and explains in one pass. Fill its template without the Explorer Findings section or claims that explorers already ran. Continue to step 4.
- **Complex:** a multi-file/service subsystem, cross-cutting feature, or broad architectural overview. Continue to step 2.

When in doubt, take the simple path. If delegation is unavailable, perform the same bounded exploration inline and say no subagent panel ran.

## 2. Explore (complex only)

Split the question into 2-4 distinct angles, such as state ownership, request flow, persistence, and integration boundaries. Dispatch all independent explorers together:

```python
delegate_task(tasks=[
    {"goal": "Trace angle A of the subsystem", "context": "<filled explorer template, workspace, question, angle A, no-write constraint>"},
    {"goal": "Trace angle B of the subsystem", "context": "<filled explorer template, workspace, question, angle B, no-write constraint>"},
])
```

Require concrete file/function evidence, data flow, files read, and explicit gaps. Do not give each explorer the whole system to rediscover.

When delegation returns a background handle, do independent parent work, then yield for completion messages between turns. Do not poll child transcripts or assume files are complete. The parent remains responsible for the investigation; children are not durable across owner exit.

## 3. Synthesize (complex only)

After every explorer has returned, dispatch one explainer using `delegate_task(tasks=[{"goal": "Explain the subsystem architecture", "context": "<filled explainer template, all findings, question, workspace, no-write constraint>"}])`.

Include every explorer's findings and gaps, not only summaries that fit one story. The explainer resolves contradictions by checking code, merges overlaps, and traces missing links. Independent contexts do not make contradictory claims equally valid.

## 4. Verify and present

The parent checks decisive file references and the central execution path directly before presenting the explanation. Read the cited functions and verify the boundary/ownership claims; child reports remain self-reports. Do not turn a static reading into a claim of runtime execution.

Present the explainer's output with light clarity edits and conversation context. Correct verified errors, but do not silently replace the result with an unsupported rewrite. If gaps remain, preserve them.

## Output

Use applicable sections from the explainer template: Overview, Key Concepts, How It Works, Where Things Live, Gotchas. Include a diagram only if it clarifies multi-component flow. Keep exact evidence locations and distinguish observed behavior from an inference about motivation.

Completion: the explanation answers the question, shows a traceable flow, identifies owners/boundaries, and names any unverified links.
