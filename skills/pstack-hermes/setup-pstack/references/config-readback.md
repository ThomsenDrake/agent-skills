# Model keys and reasoning readback

Use these probes through `terminal` after loading `skill_view(name="setup-pstack")`. They operate only on the profile the user selected. Resolve its home with `hermes -p <profile> config path`; the parent directory is the home used for the Python resolver. Use the Hermes installation's own interpreter and source path, not a random system Python without `ruamel.yaml`.

## Literal dots in model keys

Current `hermes_cli.config._split_key_path` recognizes backslash-escaped literal dots. Construct the leaf key without modifying the model ID:

```python
import subprocess

key = "agent.reasoning_overrides." + model.replace(".", "\\.")
subprocess.run([hermes, "-p", profile, "config", "set", key, level], check=True)
subprocess.run([hermes, "-p", profile, "config", "get", key, "--json"], check=True)
```

This uses argument lists, so a shell cannot eat the backslash. For a shell invocation, single-quote the entire key. Inspect the whole `agent.reasoning_overrides` mapping afterward. A nested fragment where the exact model string should be a key fails verification even if the leaf getter echoes the chosen value.

## Preserve the string `none`

A leaf setter may parse `none` as null because the arbitrary model key has no string-typed schema default. A null override does not disable reasoning. For this case, preserve existing entries and write a typed JSON mapping through the CLI:

```python
import json
import subprocess

base = [hermes, "-p", profile, "config"]
raw = subprocess.check_output(base + ["get", "agent.reasoning_overrides", "--json"], text=True)
overrides = json.loads(raw)
if not isinstance(overrides, dict):
    raise RuntimeError("Expected a mapping; inspect the config before writing")
overrides[model] = level  # validated string; e.g. "none", never Python None
subprocess.run(base + ["set", "agent.reasoning_overrides", json.dumps(overrides)], check=True)
actual = json.loads(subprocess.check_output(base + ["get", "agent.reasoning_overrides", "--json"], text=True))
assert actual == overrides
assert actual[model] == level
```

Do not replace the whole map with only the selected model. This method also avoids ambiguous dot-path parsing on releases without escaping support, provided their CLI supports typed mapping values. If it does not, stop and use that release's supported configuration procedure rather than fabricating success.

## Verify the runtime resolver

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

Run the following as a Python probe via `terminal` with `HERMES_HOME` explicitly bound to the selected profile home. The installation's Python must be able to import `hermes_cli` and `hermes_constants`.

```python
from hermes_cli.config import load_config
from hermes_constants import resolve_reasoning_config

cfg = load_config()
model_cfg = cfg.get("model", {})
assert model_cfg.get("default") == expected_model
assert model_cfg.get("provider") == expected_provider
resolved = resolve_reasoning_config(cfg, expected_model)
expected = {"enabled": False} if level == "none" else {"enabled": True, "effort": level}
assert resolved == expected, (resolved, expected)
print({"model": expected_model, "provider": expected_provider, "reasoning": resolved})
```

Print only those non-secret fields, not the whole model section: a custom endpoint configuration can contain credential references. Verify absence of delegation pins separately through `config get delegation --json`. Check provider support or a paid one-shot separately; the resolver proves how Hermes interprets settings, not whether the provider will accept them.

## Evidence behind this guidance

The literal-dot leaf setter, typed-map setter, getters, and reasoning resolver were exercised against the installed Hermes CLI in an isolated scratch home with a synthetic model identifier. The synthetic identifier tested parsing only; it was not a claim that a provider serves a model. No existing profile or provider credential was changed. Live provider capability must still be verified for the user's actual selection.
