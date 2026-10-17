# On-demand Hermes bot skeletons

These are profile identities, not extra skill entries or a delegate-agent registry. No real bot profiles, messaging connections, or schedules are created by this tree.

| Skeleton | One job | Suggested loaded skills |
|---|---|---|
| `poteto-agent/SOUL.md` | Complete one coordinator-scoped coding/helper task with proof. | `poteto-mode`, its referenced principles, `unslop` |
| `comment-sicko/SOUL.md` | Audit comments and remove only authorized, unjustified prose. | `no-comments`, `how`, `why`, `unslop` |

Each SOUL has One job, Anti-jobs, Voice, and Wake. Procedures live in skills, not duplicated profile config or model lists. Both wake on demand only.

## Create or clone, only when requested

First inspect the roster with `terminal(command="hermes profile list")` and `terminal(command="hermes profile show <approved-source>")`. Do not overwrite an existing profile or create a second bot for a job already covered. Pick an unused lowercase name. The table's names are suggestions, not permission to create them automatically.

Choose one supported mapping through `terminal`:

```text
hermes profile create <new-name> --clone-from <approved-source> --no-alias --description '<one job plus its sharpest anti-job>'
hermes profile create <new-name> --no-alias --description '<one job plus its sharpest anti-job>'
```

The first clones approved config, skill, persona, and identity state. Cloning can copy credential-bearing state and memories, so source approval is required. The second is fresh and needs provider authentication and model setup; do not claim it is ready for inference. `--clone` uses the active profile, so explicit `--clone-from` avoids an ambiguous source. `--no-alias` avoids changing the user's shell wrappers. Do not use `--clone-all` for these skeletons. Do not combine clone flags with `--no-skills`.

Read the created target back with `terminal(command="hermes profile show <new-name>")` and `terminal(command="hermes profile describe <new-name>")`. Resolve its exact home with `terminal(command="hermes -p <new-name> config path")`; the config's parent directory is `<profile-home>`. Never assemble a path under a guessed default home, derive the root by trimming a current profile path, or reuse another profile's `HERMES_HOME` for writes.

Use `read_file` on the new target's existing `SOUL.md`, then `write_file` to install the selected skeleton there. This replaces only the newly created bot's identity. Cloning also copies `memories/MEMORY.md` and `memories/USER.md`; with approval, remove only the new clone's `MEMORY.md` so it does not inherit the source bot's accumulated task memory. Retain `USER.md` only if it is appropriate for the intended user. Never delete or edit the source profile's memory. Do not print, copy into the repository, or add keys from any `.env` or auth file.

Normal config clones omit messaging channels on current Hermes, and schedules are not a substitute for on-demand wake. Verify the resulting target rather than assuming clone behavior, and leave it without routines or a gateway connection. Do not add channel credentials or `--clone-channels`.

## Install the whole adapted skill tree

Before merge, copy from this checked-out branch. A Hub/GitHub identifier normally resolves the default branch and cannot prove this unpublished tree is installed. After merge, individual skills can be installed with `hermes -p <new-name> skills install ThomsenDrake/agent-skills/skills/pstack-hermes/<skill>`; that installs one skill, not the whole adaptation. The local whole-tree mapping below remains the default.

Keep the entire `skills/pstack-hermes/` directory together so linked references, playbooks, and helpers survive. Resolve `<profile-home>` using the selected profile's `config path` output first. The destination is `<profile-home>/skills/pstack-hermes/`, never the source profile's skills directory. If a correct copy was inherited, inspect it instead of reinstalling. If the destination exists and differs, stop for an explicit update decision; do not overwrite it blindly or create a second copy with duplicate skill names.

Run this Python copy via `terminal` from the repository root after substituting the verified home:

```python
from pathlib import Path
import shutil

source = Path("skills/pstack-hermes").resolve()
home = Path("<profile-home>").resolve()
target = home / "skills" / "pstack-hermes"
assert source.is_dir() and (source / "poteto-mode" / "SKILL.md").is_file()
assert (home / "profile.yaml").is_file(), "Expected the newly created named profile"
assert not target.exists(), "Inspect an existing install before replacing it"
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target, ignore=shutil.ignore_patterns(
    "node_modules", "__pycache__", "*.pyc", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".cache", "coverage", ".coverage",
))
print(target)
```

This is installation into a new selected profile, not profile creation. Do not copy the vendored `skills/pstack/` tree over it. Inspect same-named skills at other precedence tiers before assuming this copy will load. Project-local `.hermes/skills/` can override profile skills in trusted repositories. Use the copy shown by actual discovery.

## Model and launch mapping

**One-shot launch gate.** Before any profile-process launch here, load `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`. `-z` bypasses command and hook approval gates. Require explicit authorization for that bypass, review inherited hooks, and verify restricted execution boundaries, scoped credentials, and minimal toolsets. Model-diversity or unattended-work requests are not bypass authorization. Otherwise use bounded parent-driven delegates, an approval-preserving interactive session, or report blocked.

A cloned profile starts from the approved source's model config. Load `/skill setup-pstack` within the new profile if it needs a different verified model/provider/effort. Use native `hermes -p <new-name> config set ...` and readback, not a bot-specific settings file. Ordinary `delegate_task(tasks=[{"goal": "<job>", "context": "<scope>"}, ...])` uses the inherited model unless configured otherwise. Model aliases do not change individual delegates and these SOUL filenames are not delegate type names.

A standalone on-demand run uses `terminal(command="hermes -p <new-name> -s poteto-mode -z '<bounded task with owned paths and done checks>'")` for the coding bot, or preloads `no-comments` for the comment bot. Pass a workdir and disjoint writes when another agent is working concurrently. In a chat, use `/skill <name>` or `skill_view(name="<name>")`. These do not start schedules. Do not start a process merely to install the skeleton.

## Verify before saying ready

- `profile show` and `profile describe` read back the new profile's identity and actual path.
- Its `SOUL.md` matches the selected skeleton, including all four headings and on-demand-only wake.
- `hermes -p <new-name> skills list` shows the required skills from the intended installed copy; a fresh session can load `skill_view(name="poteto-mode")` or `skill_view(name="no-comments")` and linked references.
- Model/provider/reasoning resolve as configured. Credentials were not printed or placed in skill files.
- `hermes -p <new-name> cron list` is read-only verification that no schedules were added. Verify no messaging channels were enabled for this bot.
- A harmless, explicitly authorized one-shot completes if readiness for inference is part of the request. Otherwise say that only the skeleton and installation were verified, not provider access.

## What was actually verified for these instructions

The installed CLI exposes `profile create --clone-from`, `--no-alias`, `--description`, `profile show`, `profile describe`, and `skills install <owner/repo/path>`. Fresh creation and cloning, profile-specific config-path resolution, local skill-copy discovery, and actual `skill_view` loading are checked in isolated scratch profiles without copying real credentials. This does not create either named bot, verify a public default-branch release, connect a channel, or prove an LLM provider call.
