# Repository updater

Data shapes:

- `../UPSTREAM.json`: accepted source commit and tree, schema 1. The commit belongs to `agent-skills`.
- `plan.json`: immutable source/basis bindings, exact Markdown destinations, mode, and the pre-model publication probe.
- `candidate.json`: schema 2. The protected plan, hashed text updates, one writer gateway receipt, and bounded writer run metrics. No approval verdict, Git patch, or executable archive.
- `verified.json`: the same packet plus successful protected checks. Only this artifact may reach the publisher.

The path is **detect → Vibe writer → protected checks → one human-reviewed PR**. Human review owns semantic acceptance. The updater never approves or merges a PR. It never changes installed Hermes profiles. The accepted checkpoint advances only when a human merges the proposal.

## Execution

`.github/workflows/update-pstack-hermes.yml` runs on GitHub-hosted Ubuntu runners after the existing upstream-sync workflow succeeds. Daily reconciliation at 14:35 UTC and manual dispatch cover missed runs. It does not rely on a default-token push triggering another push workflow.

| Job | Authority and work |
| --- | --- |
| `plan` | Read-only checkout. Compare immutable old/new source trees. Map destinations, reject unsupported changes, and deduplicate pending proposals. |
| `adapt` | Build pinned Vibe. Run offline policy tests and one restricted writer using `mistral-large-4`. Only the gateway holds the real provider credential. |
| `verify` | Fresh runner. Reconstruct validated text edits. Run protected contracts, updater tests, Bun tests/typechecking, and the pinned native Hermes loader. No model or publishing credential. |
| `publish` | Fresh runner with repository/PR write permission. Recheck main, source, original probe, scope, and bot branch. Append normally and read back the exact PR head. No model credential. |

The writer compares old upstream, new upstream, and the current Hermes adaptation. It translates the delta, not a fresh upstream copy. Agent documents map to the shipped bot SOUL skeletons, not live profiles.

There is no automated AI reviewer or model-generated approval. Old audited packets are rejected, not converted into successful reviews. Every changed source file needs an actual edit to its mapped adaptation. If the existing adaptation already represents a change, the automatic path stops for human reconciliation rather than silently advancing the checkpoint or inventing a diff. An unchanged source tree is a no-op without a model call.

## Boundaries

- Only known existing Markdown counterparts and the package index may change automatically.
- New/deleted/renamed files, executable changes, links, modes, invalid text, and unmapped scope stop before adaptation.
- Frontmatter stays byte-identical. Output cannot introduce or alter inline shell templates.
- Tests, automation, workflows, evidence, the checkpoint, and unrelated content are not model-writable publication targets.
- The writer receives no real provider key, repository token, Git checkout, live home, messaging config, or Docker socket.
- Docker enforces read-only inputs, a bounded writable candidate, non-root execution, dropped capabilities, resource limits, and internal-only networking.
- The gateway exposes only the exact pinned model route. It injects authentication and records usage outside the AI mounts.
- Raw transcripts, journals, and provider errors are not artifacts. Logs expose only bounded closed tool-effect metadata, never arguments, paths, output, messages, or reasoning.
- Publishing consumes the verifier's exact artifact ID from the current workflow. A model's claim that tests passed is not authority.
- Fixture source changes exist only in disposable runner checkouts. Fixture mode cannot publish.

## Pins and limits

`runtime.json`, `vibe-config.toml`, and `Dockerfile.worker` hold the pins. Vibe is `2.26.1` with a checked wheel hash. Hermes uses an immutable Git revision. Bun is `1.4.3`. Actions use commit SHAs. The base-image tag and transitive dependencies are not a complete reproducible-image lock.

The writer gets one attempt: 40 turns, 150,000 cumulative tokens, an estimated $2 limit, and a 900-second Vibe deadline. The gateway separately caps attempts, request/response bytes, generation, and elapsed time. Each completion is at most 8,192 tokens. These client limits are not a provider-enforced account billing ceiling. Use a provider project budget for that ceiling.

Pinned Unified Vibe maps `thinking="low"` to explicit Mistral `reasoning_effort="none"`; `off` omits it. An offline SDK assertion checks the mapping. The gateway independently sets `none` and clamps completion length. Unknown aliases, fallback warnings, unavailable models, limited/failed exports, and zero usage stop the run.

Successful pending proposals are deduplicated. Failed adaptations retry on later reconciliation. Disable the workflow to stop repeated spending while repairing a failure.

## Configuration

- Actions secret `MISTRAL_API_KEY`. Use GitHub Secrets or the credential store. Never commit or print its value.
- Actions variable `PSTACK_VIBE_MODEL=mistral-large-4`. Another value blocks the run.
- Actions may create PRs. GitHub combines creation and approval in one repository setting; the updater never approves. Workflow permissions default to read-only. Only `publish` requests write authority.

No profile configuration, credential file, bot routine, or installed skill is modified.

## Run and inspect

After merging the setup into the default branch:

```bash
gh workflow run update-pstack-hermes.yml --repo ThomsenDrake/agent-skills -f mode=reconcile
gh workflow run update-pstack-hermes.yml --repo ThomsenDrake/agent-skills -f mode=fixture
```

To test the unmerged branch without running the vendor sync:

```bash
gh workflow run update-pstack.yml --repo ThomsenDrake/agent-skills --ref pstack-hermes-updater -f verify_updater=true
```

The registered workflow calls the new workflow at that revision. Its `sync` job is skipped. The controlled source rule contains `PSTACK_UPDATER_SMOKE`. Both adaptation and verification require the actual Vibe-produced file to preserve the rule. No canned candidate substitutes for the model edit. Fixture publishing is blocked in both workflow and controller.

Inspect the exact commit, job conclusions, logs, and normalized artifacts. A dispatch, configured model, authentication result, or local test pass is not hosted proof. The native Hermes check lists and loads the shipping skills and support files without inference. It proves loader compatibility, not every skill's behavior or semantic correctness.

## Recovery

One append-only branch, `automation/pstack-hermes-update`, holds proposals. Stale main/source/basis, an unexpected bot head, or a human-closed unmerged PR stops publication. The publisher never force-pushes, deletes branches, or replaces manual edits.

A retry after push-success/PR-write-failure must use the original verified artifact and protected pre-model probe. Exact-tree recovery repairs only missing or stale PR metadata. It cannot make another commit or push. Main must remain unchanged. Fresh reconciliation deliberately rejects ambiguous stale-body state.

Review source/base hashes again before merging if main moved. Merging never updates installed profiles. Expand eligible scope only through a separate human-reviewed policy change to the protocol, inventory, integrity checks, loader, and fixtures.
