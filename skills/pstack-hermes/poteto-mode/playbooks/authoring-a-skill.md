### Authoring or modifying a skill

**You own the skill's voice and its executable contract.** No separate skill-authoring tool or plugin is required.

1. Discover the target with `search_files` and read its full text and linked files with `read_file`. For an installed skill, use `skill_view(name='<name>')`. Keep the requested scope. Do not edit a different Hermes profile or the vendored upstream copy.
2. For a repository skill, use `patch` for a targeted edit or `write_file` for a new file or full rewrite after reading the existing file. For a user-local skill, use `skill_manage` only when that profile and change are authorized. Write YAML frontmatter with a lowercase `name`, a concise trigger in `description`, and explicit compatibility or optional dependencies. Put long procedures in linked references, not an index of nonexistent tools.
3. Validate the skill. Parse the frontmatter, confirm a nonempty body, check that referenced files exist and named skills are installed or explicitly optional, and check every command against the real tool schema or CLI help. Address skills as `skill_view(name='<skill-name>')` or `/skill <skill-name>`. Load a playbook as `skill_view(name='poteto-mode', file_path='playbooks/<selected-playbook>.md')`, not through a sibling skill file path.
4. Add or update tests for structural contracts and run them through `terminal`. Exercise bundled scripts on safe fixtures. A subjective wording edit may skip a new test with a reason, but not link, metadata, or command validation. Include actual output and unresolved dependencies in the report.
5. If publishing a PR is in scope, load `skill_view(name='poteto-mode', file_path='playbooks/opening-a-pr.md')`. Otherwise stop at the verified files. Editing a skill does not itself authorize a push or PR.

When in doubt, delete. Keep prose that changes a decision. Explain a rule only when the rule is confusing without its reason. Match tone to scope. Point at structural sources such as types, READMEs, and config. Load `skill_view(name='principle-encode-lessons-in-structure')` when encoding a repeated lesson. Do not restate another skill. Propose a missing reusable workflow rather than silently changing runtime configuration.

**Reply:** summary of the skill, key design decisions, validation output, files changed, and any remaining dependency or publication gate.
