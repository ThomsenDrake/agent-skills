---
name: setup-pstack
description: "Use when choosing pstack models and reasoning."
compatibility: "Hermes CLI with named profiles, config set/get, and its Python reasoning resolver; provider credentials remain outside this skill."
---

# Setup pstack for Hermes

Choose a profile's model, provider, and per-model reasoning budget through the Hermes CLI. The default adaptation uses inherited same-model delegates with independent contexts. It does not create a per-role settings file, an always-applied rule, or a fabricated panel-model list.

## 1. Discover the target and available models

Load `skill_view(name="hermes-agent")` if installed, including its configuration and providers references. Check the installed CLI's help and the authoritative docs at https://hermes-agent.nousresearch.com/docs/user-guide/configuring-models. Treat source and runtime readback as the deciding evidence when a reference describes an older release.

Resolve the user's selected profile with `terminal(command="hermes profile list")` and `terminal(command="hermes -p <profile> config path")`. If no profile was named, identify the current profile before writing. Never assume `$HOME` or a hard-coded default home is the active profile. Do not configure another profile just because its name appears in history.

Read current values through `terminal`:

```text
hermes -p <profile> config get model.default
hermes -p <profile> config get model.provider
hermes -p <profile> config get agent.reasoning_overrides --json
hermes -p <profile> config get agent.reasoning_effort
hermes -p <profile> config get delegation --json
```

Do not print the entire config, credentials, or auth pools. When inspecting `delegation`, capture its JSON in a local process and print only the non-secret model/provider/base_url fields and whether any credential pin exists; redact keys or tokens. Use the same redaction on later delegation readbacks. Discover exact provider/model IDs from the account's live catalog, the Hermes model picker, or provider documentation plus an authenticated capability check. `terminal(command="hermes -p <profile> model --refresh")` is an interactive picker, not a read-only listing command. Do not open it unattended or treat its examples as entitlement proof. Ask for the user's supported choices only if discovery cannot establish them. Never append reasoning or speed words to a model ID.

## 2. Choose and confirm the budget

Ask only for choices not already given. Offer these budgets as reasoning targets, not model names:

| Budget | Target effort |
|---|---|
| unlimited | max |
| large | xhigh |
| medium | high |
| small | medium |

Hermes accepts these reasoning labels: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`, `ultra`. A provider/model may accept only a subset. Validate that subset, choose a supported level with the user, and never silently claim an unsupported effort will work.

Show the selected profile and resolved path, exact model ID, provider, effort, and any existing delegation pins. Existing choices remain the starting point, not values to overwrite with a hard-coded family. Confirm the actual changes before writing unless the user already specified them. If a custom endpoint is involved, verify its base URL and auth mechanism; do not let credentials flow to an old provider's endpoint.

## 3. Apply the selected profile configuration

Invoke these real commands with `terminal`, substituting only validated values and shell-quoting each argument:

```text
hermes -p <profile> config set model.default <model>
hermes -p <profile> config set model.provider <provider>
hermes -p <profile> config set agent.reasoning_overrides.<model> <level>
```

The final command is a leaf key path, not a role-to-model mapping. Escape every literal dot in the model portion as `\.` before passing the key, and quote the whole key so the shell preserves the backslash. Do not replace dots with dashes or otherwise alter a model ID. For example, a model portion `<family>.1` becomes the key argument `'agent.reasoning_overrides.<family>\.1'`. See `skill_view(name="setup-pstack", file_path="references/config-readback.md")` for the verified construction and resolver check.

Some CLI versions coerce a leaf value of `none` to YAML null. Null is not disabled reasoning. For `none`, or a CLI that cannot safely express a literal model key, read the existing overrides, merge this exact model key with a string level, and write the merged mapping using `hermes -p <profile> config set agent.reasoning_overrides <JSON-mapping>`. Current Hermes accepts mapping literals through `config set`. Preserve unrelated entries and verify that the chosen model resolves to `{"enabled": false}` for `none`. If this release rejects the mapping form, stop and check its live source/help; do not hand-edit an existing user's config or write a surrogate settings file.

For the selected inherited-delegate default, confirm removal of any existing `delegation.model`, `delegation.provider`, or endpoint pins that would override the parent, then remove only those approved pins with `hermes -p <profile> config unset <key>`. Read the delegation section back. Do not delete unrelated concurrency or iteration settings. Existing pinned delegates are not same-model inheritance until this is verified.

## 4. Read back and prove resolution

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

Run all of these through `terminal` after writes:

```text
hermes -p <profile> config get model.default
hermes -p <profile> config get model.provider
hermes -p <profile> config get agent.reasoning_overrides --json
hermes -p <profile> config get delegation --json
```

Also read the escaped leaf key back and use the installed Hermes Python interpreter to call `resolve_reasoning_config(load_config(), <exact-model>)` with `HERMES_HOME` set to the selected profile path. Inspect the post-load model/provider and compare the effective reasoning against the chosen level. A successful setter message is not verification. The reference gives a no-secret probe. Configuration resolution is not proof of provider entitlement; only after the launch gate above and separate permission for the inference cost, run a fresh `terminal(command="hermes -p <profile> -z 'Reply with READY only.'")` and check the actual provider/model metadata and successful completion. A model's self-reported identity is not routing evidence.

Report only the chosen profile, model/provider, resolved effort, delegate mode, and whether inference was tested. New sessions pick up the persistent values. A running session may retain its own overrides; do not mutate its past prompt or claim a current-session model switch from a config write.

## 5. Optional true model diversity

Normal `delegate_task(tasks=[{"goal": "<job>", "context": "<scope and evidence contract>"}, ...])` calls inherit the parent model when delegation is not pinned. The tool has no per-call `model`, provider, reasoning, or speed controls in this workflow. Multiple same-model workers are independent attempts, not different model families.

If the user explicitly wants actual diversity, create separate named profiles with `terminal(command="hermes profile create <new-profile> --clone-from <approved-source> --no-alias --description '<one job>'")`. Read each profile back and configure/verify its own model/provider/effort with this procedure. Run it as a separate `hermes -p <new-profile>` process with a bounded task and isolated write scope, not by inventing delegate overrides. Cloning copies credential-bearing state; do it only with explicit source approval and never print or commit that state. Prefer source config cloning, not a full-state clone.

`model_aliases` are session model-selection shortcuts. They do not route individual `delegate_task` calls. No alias, profile, or panel is created unless the user asked for it.

## 6. Offer app verification once

Check for an existing `verify-*` skill or real-app harness. If none exists, offer `/skill create-verification-skill` so future work can drive the app and show proof. On yes, load `skill_view(name="create-verification-skill")` and follow it. On no, move on.

## Pitfalls and completion

Keep secrets out of skills, examples, logs, and config values. Use Hermes's credential setup instead of requesting keys in chat. Never infer absence of setup from a missing rule file: the live profile config is the state. Completion requires exact config readback and resolver evidence; label missing credentials, unsupported levels, managed-config refusal, or an untested inference path plainly.
