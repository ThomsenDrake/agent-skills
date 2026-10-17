# Explorer Prompt Template

Load with `skill_view(name="how", file_path="references/explorer-prompt.md")`. The parent fills in this template and includes it in one task's `context` in a `delegate_task(tasks=[...])` batch. Also supply the exact workspace/revision, allowed reads, and reporting scope.

---

Other explorers investigate different slices of the subsystem. Focus on your assigned angle and go deep. Use `read_file`, `search_files`, and authorized non-mutating `terminal` checks. Do not modify code, commit, write external records, or delegate again. Return findings in your final response. The default panel uses the same model in isolated conversations, not cross-model evidence. Distinguish code observations from checks actually executed.

## Question

> {QUESTION}

## Your Exploration Angle

{EXPLORATION_ANGLE}

## Output

### Components Found
The key types, services, classes, and abstractions. For each: name, exact file/line or symbol location, and a one-sentence description of what it does. Include the inspected revision when supplied.

### Flow
The execution flow step by step. For each step: what function/method runs, what file it's in, what it does, what it calls next. Include the data that flows between steps.

### Files Read
Every file you read during exploration, so the explainer can reference them.

### Boundaries
Where this subsystem connects to other parts of the codebase. The inputs and outputs.

### Non-Obvious Things
Anything surprising, historically motivated, or easy to get wrong. Things that look like they should work one way but work another.

### Open Questions
Anything you couldn't fully trace or understand. Be honest about gaps.
