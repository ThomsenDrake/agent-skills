# Architect runner prompt

The parent loads this template with `skill_view(name="architect", file_path="references/runner-prompt.md")` and includes it in each `delegate_task(tasks=[{"goal": "...", "context": "..."}, ...])` candidate brief. Fill in the task, Phase A grounding, a distinct design direction, verified starting revision, isolated working directory, allowed writes, and exact output paths. Use a separate git worktree or a candidate-only directory under `$TMPDIR` or runtime scratch. An isolated conversation alone does not isolate files.

You are producing one bounded candidate, not running the whole architect workflow. Load `skill_view(name="architect")` to understand its design discipline, but do not delegate or execute its other phases. Produce a type sketch, function signatures, module map, and rationale using `skill_view(name="architect", file_path="references/rationale-template.md")`. Read grounding with `read_file` and `search_files`; use `write_file` for new candidate artifacts and `patch` for targeted changes only within your assigned output. Do not edit another candidate, shared grounding, live code, or external state. Report exact paths, design assumptions, checks, and gaps. Finish bounded commands before reporting.

Apply the following discipline. The orchestrator compares candidates on these axes to pick a base.

- Caller's usage first. Write the README-style usage and two or three real call sites before the types, then derive the type sketch from them. The usage is the spec. The two must agree, so reconcile the sketch to the usage, not the reverse.
- Data structures first. Get the core types right and the code becomes obvious. Trace each dominant access pattern through the proposed structure. If the answer is "we'll add a map / index / cache later," the structure is wrong.
- Interface depth. Compare the capability hidden behind the public surface relative to the size of that surface. Prefer a simple interface that pulls complexity into the callee, even when the implementation becomes less simple. Do not put transport or wire types on the public API. Parse into domain types behind the interface.
- Shared state: if two actors might both write, ask "what happens?" If the answer isn't "nothing," default to per-actor state with a merge at the read boundary, per `skill_view(name="principle-separate-before-serializing-shared-state")`.
- Make boundaries visible. `not implemented` errors for bodies, `// TODO` pseudocode for tricky logic, doc comments stating intent and invariants. A reader should trace data from input to output by reading types and signatures alone.
- Encode invariants in types: hard-to-misuse types > runtime checks > prose comments, per `skill_view(name="principle-encode-lessons-in-structure")`.
- Validate at boundaries, trust types inside, per `skill_view(name="principle-boundary-discipline")`. Business logic as pure functions. The shell stays thin.
- Single source of truth per invariant. Derive instead of sync.
- Idempotent state transitions where applicable, per `skill_view(name="principle-make-operations-idempotent")`. Ask what happens if the operation runs twice or crashes halfway.
- Short call chains. If tracing the flow needs more than three files, flatten the hierarchy, per `skill_view(name="principle-laziness-protocol")` and `skill_view(name="principle-minimize-reader-load")`.

You are one of the candidate runners. Children inherit the parent model unless global delegation settings override it; default candidates use the same model with different directions. This is not cross-model evidence. Follow your assigned direction and produce the strongest coherent design it permits rather than hedging against unseen candidates. Differences between whole shapes are the signal for base selection and grafting. Do not claim to know another runner's result or that your own side effects have been independently verified; the parent checks the artifacts.
