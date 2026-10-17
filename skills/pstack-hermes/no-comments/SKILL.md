---
name: no-comments
description: "Use when auditing comments and workaround code."
compatibility: Hermes Agent with delegate_task, repository file tools, terminal, and the comment-sicko bot instructions.
---

# No comments

Spawn Comment Sicko. Act on accepted findings.

Defer to Comment Sicko's fresh perspective.

## Scope

Use the caller's files or diff. Otherwise use the current diff against the verified repository base, including the working tree. Audit-only is the default unless the user requested edits. Keep legal headers, public contracts, and directives required for a successful build. A comment-only pass does not authorize application-code changes.

## Steps

1. Load `skill_view(name="pstack-hermes", file_path="bots/comment-sicko/SOUL.md")`. Delegate a fresh comment-only pass with `delegate_task(tasks=[{"goal": "Review the supplied scope as Comment Sicko. Follow the authorized audit or comment-edit mode and return the role's report.", "context": "<full Comment Sicko instructions, explicit audit-only or edit authorization, exact scope, baseline, and write fence>"}])`. The child has isolated context, so supply the full role text rather than assuming a registered role or shared conversation. It inherits centrally configured model settings. If delegation or the role file is unavailable, report the blocker rather than claiming an independent review.
2. Inspect its report and diff. Reject application-code edits, scope escapes, exception-protected deletions, misstated `MUST KILL` reasons, and flags that treat kept intentional code as guilty. Reshape flags on our-code surprises stay actionable. Do not restore those comments. A keep survives only when it matches the role's exception list and has supporting evidence. Audit missed scoped lint and TypeScript suppressions. Correctness or safety suppressions stay actionable `MUST KILL`s. Restore deletions only with exact exceptions and scoped proof. Before accepting thin `IMPORTANT` or `do not remove` kills or keeps, load `skill_view(name='how')` or `skill_view(name='why')` and follow it on their symbol. Resolve ambiguous legal, build, or safety directives before deletion. Unresolved evidence is an open finding, not permission to remove a required directive. In audit-only mode, report all proposed changes without edits. Revert and rerun one rejected report with the failure named. Reject a second, report it open, and mark `no-comments` incomplete.
3. In authorized implementation mode, fix trivial accepted flags by deleting a dead path, dropping a parameter, or using the real API. Otherwise report the proposed fix without editing. If any fix needs a shape, load `skill_view(name='architect')` and follow it once for the accepted set and surrounding code. Stop at the sketch. Architect shapes. Step 4 implements.
4. In authorized implementation mode, make the smallest root-cause fix in scope and remove the resolved workaround. In audit-only mode, report the proposed fix without editing. If the root cause is out of scope, report it open. Preserve any suppression needed for a successful build until an authorized implementer fixes its cause. The **principle-fix-root-causes** and **principle-redesign-from-first-principles** skills guide intent only. Neither authorizes widening the fence nor fixing instances outside it. Never bolt on symptom guards.
5. Constraint comments say `do not remove`, `do not change wording`, or `talk to X before changing`. Leave keeps about things we cannot change. Offer the cheapest in-scope type, runtime, test, or CI lint. Wait for interactive approval. Unattended and eval require caller pre-approval. If approved, encode and verify the constraint before deleting its comment. Otherwise retain an evidenced external constraint or build-required directive, report the unresolved constraint, and propose the smallest follow-up. Do not remove a safety requirement merely because enforcement is out of scope.
6. Verify the final diff and rerun scoped checks through `terminal`. Report the deletion count, restored comments, reruns, architect sketch, fixes, encoding offers, encodings, unenforced constraints, and other open work.
