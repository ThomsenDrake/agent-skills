# Verification record

Claims below are measured unless labeled otherwise.
These checks apply to this adaptation, not future upstream versions.

## Package checks

- The source is agent-skills commit `4150dd0f96115204d4527f7a1adf88c90bc2d9eb`, pstack v0.15.25.
- The adapted layout has the same 54 leaf directories and 55 total `SKILL.md` files, including its index.
- All 12 offline contract tests pass. The original five checks remain, with regressions for one-shot approval bypass, copied-plan launch gates, SHA-pinned merges, mandatory parent-owned reviews, honest panel labels, helper forge support, filtered installation, and retained-source tamper detection.
- After the review fixes, the parent refreshed the dedicated profile copy and reran native frontmatter validation, catalog comparison, and actual `skill_view` loads. All 55 entries load from the intended final tree, and all 62 supporting Markdown files load through the native file interface.
- The captured live `unslop` content is byte-identical to the final `unslop/SKILL.md`. Its SHA-256 is `46249fe55922c112a5f45ff2621fb7c97ffbc2ade339b04601364ed0090ca34d`. The earlier live swarm smoke remains evidence for its recorded version, not a live test of revised safety instructions.
- All 23 retained non-Markdown source files match the vendored bytes and executable bits. No upstream source code was rewritten.
- The retained Bun suite reports `68 pass`, `0 fail`, and `246 expect() calls`. Strict TypeScript checking passes.
- The real orchestrator and watcher entry points print help. The watcher entry point is `watch-pr/watch-pr`, not its `cli.ts` module.

Run the offline checks from the repository root with Hermes's Python environment:

```text
python -m unittest discover -s skills/pstack-hermes/tests -v
```

Run the script checks through `terminal` from `poteto-mode/scripts/`:

```text
bun install --frozen-lockfile
bun run test
bun run typecheck
bun run orch/orch.ts --help
bun run watch-pr/watch-pr --help
```

## Review-fix regression evidence

Each behavior regression was run before its corresponding documentation fix. The observed failures were assertions about the missing contract, not interpreter or import errors.

| Regression | Observed RED | Observed GREEN |
| --- | --- | --- |
| One-shot approval and launch preconditions | `Ran 6 tests`, `FAILED (failures=1)` | `Ran 6 tests`, `OK` |
| SHA-bound immediate merge recipes | `Ran 7 tests`, `FAILED (failures=1)` | `Ran 7 tests`, `OK` |
| Parent-owned mandatory delegated-PR reviews | `Ran 8 tests`, `FAILED (failures=1)` | `Ran 8 tests`, `OK` |
| Honest default-panel label | `Ran 1 test`, `FAILED (failures=1)` | `Ran 1 test`, `OK` |
| Actual helper forge support | `Ran 1 test`, `FAILED (failures=1)` | `Ran 1 test`, `OK` |
| Dependency and cache exclusions in bot copy recipe | `Ran 1 test`, `FAILED (failures=1)` | `Ran 1 test`, `OK` |
| Retained-byte and executable-bit drift in scratch copies | `Ran 1 test`, `FAILED (failures=2)` | `Ran 1 test`, `OK` |
| Launch gate survives copying the plan template | `Ran 1 test`, `FAILED (failures=1)` | `Ran 1 test`, `OK` |

The source-integrity regression mutates disposable copies, never the retained source. The original existence-only check failed to raise for either mutation; the strengthened check rejects both.

Final full-suite output from this round:

```text
Ran 12 tests in 0.125s

OK
```

The retained helper rerun returned `68 pass`, `0 fail`, `246 expect() calls`, followed by successful strict TypeScript checking with exit zero. Bun was initially absent from PATH; the existing scratch-tooling binary ran both commands without a new install. The installed GitHub CLI help confirms expected-head matching support. No live merge was attempted.

## Profile installation and real inference

A dedicated profile named `pstack-forge-test` received a complete copy of the adapted package.
`hermes -p pstack-forge-test skills list` lists this index and all 54 leaves as enabled.
The profile is a test identity, not either shipped bot skeleton. It was not deleted.

The recorded one-shot path bypasses command and hook approval gates. These were dedicated-profile/workspace fixture tests, not an OS containment test. No OS sandbox was verified, and the traces do not establish a separate approval-bypass grant or a complete inherited-hook audit. Their observed scope was the named input/output fixture and two read-only child checks. Do not infer broader safety or authorization from that limited result. Any future launch must first satisfy `skill_view(name='pstack-hermes', file_path='references/one-shot-safety.md')`.

The smoke prompt required a real `skill_view(name="unslop")` call, a rewrite, a file write, and a readback.
The one-shot run completed on `gpt-6.1-sol` through `openai-codex`.
The exported session proves the loaded path was `pstack-hermes/unslop/SKILL.md`, followed by reading the input, writing the output, and reading the output back.
No preload was used as a substitute for loading evidence.

Actual output:

```text
The export now takes 2 seconds instead of 5 seconds.
```

The input contained filler and marketing language before that exact timing sentence.
The rewrite removed the filler without changing either timing value.
See `smoke/unslop-input.txt`, `smoke/unslop-output.txt`, and `smoke/unslop-trace.json` for the captured evidence.
The trace is a reduced export of actual tool calls. It omits system prompts, credentials, and unrelated state.

## Live delegation smoke

A second one-shot loaded `pstack-hermes/swarm/SKILL.md` through a real `skill_view` call.
It invoked `delegate_task` once with two task entries containing only `goal` and `context`.
Both children completed on `gpt-6.1-sol` and used `read_file` successfully.
One checked the timing facts. The other checked all six prohibited phrases.
The parent reread both files, reran the phrase search, and wrote a two-row report.
The exported tool trace confirms joined completion in one-shot mode, not detached polling.
See `smoke/swarm-trace.json` for the reduced actual results and report.

## Configuration checks

The test profile's model/provider setter and getter commands completed successfully.
The literal model key `gpt-6.1-sol` was written through an escaped dot-path key, then read back as `low`.
The one-shot usage metadata confirms the actual model and provider, rather than relying on the model's self-report.
See `setup-pstack/references/config-readback.md` for resolver probes and the string-`none` pitfall.

## Independent review

The final independent re-review returned `passed: true`, with empty security concerns, logic errors, and suggestions.
The earlier blockers led to explicit one-shot safety gates, atomic accepted-head merge guards, and parent-owned mandatory delegated-PR reviews.
The retained helper source remains unchanged. No live landing or approval-bypass experiment was needed to validate these documentation contracts.

## Limits

The default parallel panels use inherited-model contexts. True cross-model profile panels were not live-tested.
The package installer identifier targets the repository's default branch. This branch was tested by whole-tree copy, not by pretending it was already merged.
Neither `poteto-agent` nor `comment-sicko` was created as a live bot profile. Their committed skeletons and creation workflow are the deliverable.
The editor-specific `worktree-audit.sh` is retained but skipped. Its transcript heuristic is not Hermes evidence.
Helper tests do not prove live PR merging, deployed webhooks, browser journeys, or every possible playbook.
The plan checker is lexical. The playbook still requires a manual media-gate audit.
No schedules, messaging connections, deployments, or merges were performed for this adaptation.
