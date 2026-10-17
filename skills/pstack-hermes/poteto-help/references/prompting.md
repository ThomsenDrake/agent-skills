# Word the prompt

A prompt states intent and the check for done. The playbook supplies the steps, so a few plain sentences beat a speculative implementation spec. Load the task workflow with `/skill poteto-mode` or `skill_view(name="poteto-mode")`.

## Put in

- The goal: what is wrong or what should exist.
- A done check that can pass or fail. “Make it better” and a duration are not checks.
- The proof: actual command output, a captured user flow, a stored value, or a measured before/after.
- Known symptoms, reproduction steps, logs, and source links.
- Real constraints such as “repro first,” “do not change code yet,” “zero behavior change,” or “let me review the design first.”

## Leave out

- The implementation method when another approach could achieve the goal better.
- A hand-written chain of every skill. Name a skill only to override one choice; otherwise let the playbook order its steps.
- An untested theory presented as the cause. Label it a guess so it does not narrow the investigation prematurely.

## Load context first

- For a noisy report, ask for a plain restatement of the underlying issue before code.
- In a fresh chat, load `/skill recall` for prior work on the named topic. Keep the profile/project/time scope explicit.
- Before changing unfamiliar code, use the `how` and `why` skills for mechanics and reasons.
- Use `/skill teach` to explain why a proposed choice fixes the cause rather than the symptom.

## Design before the plan

- Prototype competing options, with real screenshots or videos when UI matters, then choose from the evidence.
- Let runnable prototypes settle uncertainty. Do not build an adversarial review around a design that has never existed.
- For a shared API, write the README or tutorial first and work back to code. The doc becomes the contract to verify.
- Plan only after the design is settled. Each step ends with an observable check.

## Follow up short

“Do it,” “continue,” and “keep going until done” are enough once the task is established. Say “new task” when the subject changes, or request an explanation-only turn when no implementation is intended. Reload the relevant skill in a fresh session rather than promising an editor-only persistent mode.

## Before stepping away

- State which decisions and actions are authorized while you are away. “I am stepping away” alone does not authorize publishing or destructive changes.
- Give a finish predicate the agent can actually run, with a retry cap and a concrete stop/report condition.
- Specify a fresh worktree and base if edits must be isolated.
- Pre-answer real blockers such as commit authority, but do not waive secret handling or safety scope.
- Ask for the `show-me-your-work` decision trail and an independent audit.
- A one-shot or delegate ends with its process; durable scheduling is a separate explicit request. Do not silently create cron or messaging delivery.

## Steer in one line

- “The goal is to reproduce it. I did not ask for a fix yet.”
- “Apply prove it works. Show the real app output, not just a successful build.”
- “Compare the independent attempts, but say they used the same inherited model.”
- “Name the concrete decision that principle changed.”
