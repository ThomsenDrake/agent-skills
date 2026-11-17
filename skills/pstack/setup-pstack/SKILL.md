---
name: setup-pstack
description: Configure which models pstack uses per role and at what reasoning budget. Detects your available models and writes the pstack models file, which overrides the skill defaults. Use for /setup-pstack, "configure pstack models", "pstack budget", or changing pstack's model choices.
---

# Setup pstack

Write `~/.config/pstack/pstack-models.md`, the pstack models file that sets pstack's model per role.

## Steps

### 1. Detect available models

Enumerate the models you can pass to a subagent in this session, and the efforts each one accepts. That is the dependable source. If your agent also has a models API or CLI that lists the user's entitled models, prefer it for completeness. If you cannot detect any, ask the user to paste the model IDs they have access to. Never write a real model you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid even though they are not detected models.

### 2. Load current state

The default role-to-model mapping is the file shape shown in step 5 below. If `~/.config/pstack/pstack-models.md` already exists, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `hardest tasks`, `architect runners`, `reflect tooling`, or `why investigators`, is from a retired role. Drop it.

A file without the `# defaults: 3` line comes from an older setup. That setup wrote a line for every role, so some of its values are old defaults, not choices. Before step 3, replace these values:

- An `arena cross-judge pool` list of exactly one `claude-fable-*` entry, one `claude-opus-*` entry, and one `gemini-*` entry, in any order, takes the role's step 5 list. Fable and Opus are one vendor, so the Fable entry could judge only where the Opus entry also could.
- A `# budget: unlimited` line becomes `large`, because no role runs above `xhigh`.
- If the file has no `# defaults: 2` line either, an old model is one that matches `grok-*`. An old model in `feature, refactoring`, `bug-fix`, `perf-issue`, `hillclimb`, or `swarm workers` takes the role's step 5 default. In a panel role (`arena runners`, `arena cross-judge pool`, `interrogate reviewers`), a list of exactly one `claude-opus-*` entry and one old model, in either order, takes the role's step 5 list. In any other list, each old model becomes `claude-opus-5-5 high`.

Every other value is the user's choice and stays, including an old model in any other role and every `inherit-parent` or `auto` value. Tell the user which values you replaced.

### 3. Budget, map, and confirm

**(a) Ask for a budget.** Prefer a multiple-choice question over free text when your agent supports one. Offer these three options with these exact labels, and name the current budget when the file records one. With no file, say that `large` matches the skill defaults.

- `large — xhigh reasoning`
- `medium — high reasoning`
- `small — medium reasoning`

**(b) Apply it.** Build the working table from the skill defaults, and on a re-run keep any role you changed by family, list, or alias (`inherit-parent`, `auto`). Families are the ones Phase A of the **arena** skill defines, so Fable is its own family. Each role has a target effort, which is its default's effort moved by the budget. `large` keeps it, `medium` lowers it one step, and `small` lowers it two steps, on the ladder `xhigh` > `high` > `medium` > `low`. No role runs above `xhigh`, and a target at the bottom of the ladder stays there. Most defaults are at `xhigh`, and each budget label names where those land. Set the effort of every real model in the role, panel entries included, to the role's target. The effort is the last token. If the result is not a detected model, use the same family's detected model with the highest effort at or below the target, else mark the role as needing a choice. `inherit-parent` and `auto` do not change. So `medium` turns `claude-opus-5-5 xhigh` into `claude-opus-5-5 high` and `claude-opus-5-5 high` into `claude-opus-5-5 medium`, and `small` turns them into `claude-opus-5-5 medium` and `claude-opus-5-5 low`. Gemini tops out at `high`, so a Gemini entry runs at `high` when its role's target is `xhigh`.

**(c) Show the roles and confirm.** Show every role with its model, marking any real model not in the detected set as needing a choice. Also list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected models at `xhigh` or below plus `inherit-parent` and `auto` (both mean: this role runs on the parent chat model, which is how users on automatic model selection stay on it) as the options. Prefer a multiple-choice question over free text when your agent supports one. For panel roles (arena runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena runs one judge. It tries only values from a vendor other than the parent's, in list order, so order it by preference. Fable and the other Claude models are one vendor. An `inherit-parent` or `auto` value never judges. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

### 4. Validate

Every real model written must be in the detected set and at `xhigh` or below. `inherit-parent` and `auto` always pass. If a chosen real model is not available, stop and ask again.

### 5. Write the file

Write `~/.config/pstack/pstack-models.md` with the `# defaults: 3` line, a `# budget` line with the chosen label and the effort that label names, and one line per role, using the same labels poteto-mode uses. Overwrite the whole file so re-runs stay idempotent. Shape:

```
# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit the subagent's model and spawn a general-purpose subagent). Alias entries in a panel list still count toward its fan-out.
# defaults: 3
# budget: large (xhigh)
feature, refactoring: claude-opus-5-5 xhigh
bug-fix: claude-opus-5-5 xhigh
perf-issue: claude-opus-5-5 xhigh
hillclimb: claude-opus-5-5 xhigh
judgment and prose: claude-opus-5-5 xhigh
arena runners: claude-fable-5-2 high, claude-opus-5-5 high, gemini-4-carbon high
arena cross-judge pool: claude-opus-5-5 high, gemini-4-carbon high
swarm workers: claude-opus-5-5 high
interrogate reviewers: claude-fable-5-2 high, claude-opus-5-5 high, gemini-4-carbon high
```

### 6. Confirm

Tell the user the file was written and that skills read it the next time they need a role. Re-running this skill updates it.

### 7. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill` (resolves wherever pstack is installed: workspace, user, or plugin). On no, move on without pushing.

### 8. Offer a formal verification skill (optional)

Check whether the project already has a formal verification skill (a project skill that runs a model checker, a proof, or another verifier against the code). If not, offer once: "want a formal verification skill, so agents can prove a key property of your code holds in every case in scope, not only the cases tests reach? I can generate one with /create-formal-verification-skill." On yes, invoke `/create-formal-verification-skill` (resolves wherever pstack is installed: workspace, user, or plugin). On no, move on without pushing.
