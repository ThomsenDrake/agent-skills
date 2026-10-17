# Prompts worth copying

Replace placeholders with real paths, scopes, and done checks. These are chat prompts, not shell commands. Load each named skill through `/skill <name>` or `skill_view(name="<name>")`; a supporting file uses `skill_view(name, file_path)`. Informal wording works.

## Understand

- `/skill poteto-mode` then: “Read <thread>. Restate the underlying issue in your own words, in plain English.”
- `/skill in-your-own-words` then the long or messy ask.
- `/skill sharpen` then the proposed task.
- `/skill poteto-mode` then: “Investigate why <symptom>. Give what we know, the evidence, and hypotheses. Do not change code yet.”
- “Use the how skill for <subsystem>, then the why skill to investigate the recent break.”
- `/skill recall` then: “My work on <topic> in <project> last week, then read <issue>.”
- `/skill teach` then: “Why this implementation instead of <alternative>? What did it trade off?”
- `/skill poteto-mode` then: “Take over this branch. Read the decision log and continue from the verified state, without redoing finished work.”

## Build

- Bug: `/skill poteto-mode` then: “<Symptom>. Reproduce first, then fix and verify.”
- App bug: “Use poteto-mode and the installed verify-<app> skill. Reproduce on <base>, then fix only if it reproduces. Show a real captured flow as proof.”
- Cheap test: “Use poteto-mode. Reproduce <bug> first. If a cheap test path exists, follow the tdd skill and rerun after fixing.”
- Feature: “Use poteto-mode to add <behavior>. <Current output> must stay byte-identical. Verify both.”
- Refactor: “Use poteto-mode to move <code> into one module with zero behavior change. Record and compare the actual output.”
- Performance: “Use poteto-mode. <Operation> takes <measured time> on <fixture>. Trace it, fix the measured cause, and show before/after on the same fixture.”

## Design and plan

- “Use poteto-mode to prototype options for <feature>. Capture real screenshots or videos to compare.”
- “We need <feature>. Load the architect skill, answer open questions in prototypes, and stop at the design checkpoint before implementation.”
- “Use poteto-mode to write a tutorial for <new package> first. Then use teach to explain why it beats the current one.”
- “Use arena for independent attempts at this approach. Keep worker scopes explicit and report the actual model/profile used, without claiming fake model diversity.”
- “Use poteto-mode to turn this settled design into small verifiable PR units. Planning only for now.”
- “Plan migration of <library> to <target> with poteto-mode. Preserve original output exactly, including existing bugs unless separately authorized.”

## Review and ship

- `/skill interrogate` then: “Review the whole branch skeptically. No edits yet. Only real bugs or regressions, not nitpicks.” Read its dismissals too.
- `/skill swarm` then: “Check every package under <dir> with its actual check script. One read-only worker per package and one report.”
- “Use poteto-mode to open a PR with small ordered commits and measured evidence in its description.”
- “Use poteto-mode to babysit PR <number> to merge-ready. Do not merge.” For status only: “Check PR <number>. What is outstanding? No edits.”
- “Use poteto-mode to land the stack, after its required checks.” Only send this when landing is intended and authorized.

## Away and back

- “Use poteto-mode. I am stepping away. <Goal> in a fresh worktree off <base>. Done means <checks>. Keep a decision log. Committing is authorized, publishing and merging are not. Retry at most <limit>; if blocked, stop and report evidence. Do not create a schedule or messaging connection.”
- `/skill show-me-your-work` then: “Audit the decision trail from this run and summarize what needs attention.” Read the Attention section first.
- “Use poteto-mode for full autopilot on this queue. Items are independent. <Explicit authority and stop checks>.”
- “Use poteto-mode to stack these independent changes without shipping. I will land the stack.”
- `/skill reflect` then: “Capture what this completed task taught so the next run does not repeat it.” Approve edits only when they change a future decision.
- `/skill bro` restates the previous answer plainly.
- `/skill ketchup` catches up only on this chat since the last user message.
