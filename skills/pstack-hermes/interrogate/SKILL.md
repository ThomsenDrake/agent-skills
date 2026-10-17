---
name: interrogate
description: "Use when adversarially reviewing code or designs."
compatibility: "Requires Hermes delegation and read tools; terminal with git for diff-based review."
---

# Interrogate

Run an adversarial panel, then apply lead judgment to produce a synthesized verdict. Do not auto-apply changes. Use for challenging code, designs, assumptions, or blind spots, not as a substitute for executing acceptance tests.

## Step 1: Scope

Identify the exact files or diff from the user's context. For branch review, discover the appropriate base and use `terminal(command="git diff <base>...HEAD")`; do not assume the branch is named main. Include authorized uncommitted changes when relevant, capturing them separately so the review does not miss the actual work.

Read surrounding callers, types, tests, and constraints with `read_file` and `search_files`. Package a stable snapshot, its revision/base, and enough context to understand the changes. If the target changes during review, refresh the affected findings before issuing a verdict.

## Step 2: Intent

State the intent in one paragraph from the user's request, commit messages, PR description, and code. Retrieve available context before asking. If materially uncertain, ask for clarification rather than having reviewers judge different goals.

## Step 3: Dispatch reviewers

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

Load the complete references through:

- `skill_view(name="interrogate", file_path="references/reviewer-prompt.md")`
- `skill_view(name="interrogate", file_path="references/rubric.md")`
- `skill_view(name="interrogate", file_path="references/code-quality-review.md")`

Default to two isolated reviewers with different emphasis: A traces correctness, security, and execution paths; B challenges structure, maintainability, and hidden assumptions. Both see the same intent, snapshot, rubric, and quality lens and may report any real issue. Distinct roles reduce duplicate searching without confining findings to artificial personas.

Use one real Hermes batch:

```python
delegate_task(tasks=[
    {"goal": "Adversarial review A: execution and security", "context": "<filled reviewer template, emphasis A, workspace, exact snapshot, no-write instruction>"},
    {"goal": "Adversarial review B: structure and assumptions", "context": "<same evidence and rubric, emphasis B, workspace, no-write instruction>"},
])
```

Children inherit the parent model unless global delegation settings override it. This default is a same-model role panel, not cross-model evidence. The tool has no per-call model selection; aliases do not retarget it. For optional true model diversity, load `arena` and use its explicit separate-process protocol with profiles configured by `setup-pstack`, isolated workdirs, and verified actual models. Never invent model entitlements or silently substitute defaults.

Specify no file edits, commits, or external writes in every context; this is a behavioral restriction, not a sandbox. Children do not recursively delegate. If the dispatch returns a background handle, finish independent reading and yield for completion messages between turns. Do not poll transcripts. Children are not durable after owner exit. If delegation is unavailable, disclose a sequential review instead of claiming a panel ran.

## Step 4: Synthesize

Parse every reviewer's findings and merge duplicates without losing locations, evidence, or attribution. Note which reviewer roles raised each issue. Same-model agreement can prioritize inspection, but it is not independent cross-model confirmation. A lone concrete security or correctness finding can outweigh unanimous style concerns.

Record explicit disagreements and missing/failed reviewers. A partial panel is not a clean review by all seats. Read the actual referenced paths and call chains, and reproduce decisive issues with safe tests where possible. Child conclusions and claimed checks are self-reports, not verified side effects.

## Step 5: Lead judgment

Load `skill_view(name="interrogate", file_path="references/lead-judgment.md")`. Be the pragmatic lead, not a neutral vote counter. Classify every distinct finding with its reviewers and a one-line evidence-backed rationale:

- **Act on:** a real correctness, security, or maintainability problem given the goals; would block a real PR.
- **Consider:** legitimate, but addressing it now has an unresolved cost/benefit tradeoff.
- **Noted:** valid context, premature optimization, or low impact, not actionable now.
- **Dismissed:** wrong, preference-only, nitpicky, or missing context; explain why.

No findings is valid. Do not inflate a tidy review into defects. Do not dismiss an uncomfortable issue without checking its execution path.

## Output and verification

### Intent

The stated intent paragraph.

### Reviewers

One row per planned reviewer: label, role, actual model/provider when verifiable or unknown, completion status, and parsed finding count. Distinguish same-model roles from any verified model diversity.

### Act on / Consider / Noted / Dismissed

For each finding, include location, concrete issue, evidence, attribution, judgment, and remaining uncertainty. Keep the four buckets separate.

### Agreement map

Where reviewers agreed or diverged, why it matters, and which claims the parent independently checked. Include gaps and the exact reviewed snapshot. No auto-fixes: the deliverable is a verdict, not unrequested changes.
