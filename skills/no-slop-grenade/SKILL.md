---
name: no-slop-grenade
description: Size and shape anything written for other people so it is not a slop grenade (noslopgrenade.com), an AI-length wall of text where a person would write a few sentences. Use whenever you draft, rewrite, shorten or review text that someone other than the user will read, such as a chat message or reply, request, announcement, email, doc or wiki page, decision doc, slide deck, form or survey, PR description, issue, or status update, even if the user doesn't ask for brevity. Also use when the user says "slop grenade", links noslopgrenade.com, or says a draft is too long, too much detail, too minimal, or doesn't sound like them. It cuts to what the reader needs, keeps every fact, condition and real uncertainty, and keeps the human parts that people put back when rewrites go too far. For sentence-level AI tells alone (vocabulary, dashes), use an unslop-style skill.
license: MIT
metadata:
  author: ThomsenDrake
  version: "1.0"
  source: "https://noslopgrenade.com/"
---

# No slop grenade

A slop grenade is a long AI-written answer dropped where a person would write a few sentences. The reader has to dig out the one line they needed, and nothing is left to reply to. The goal is the text that a busy person who knows the subject would write for this reader, in this medium. That is usually much shorter than a first AI draft. It is not always the shortest possible version, and it never says more than the sender said.

These rules come from real rewrites of messages, requests, forms and a decision page, and from what the sender did next. The rewrites cut 34–70% of the words, and most of the cuts held. When a rewrite went too far, the sender put back the same few things: a greeting, paragraph breaks, real @mentions, the reason to act, and first-person promises. [references/examples.md](references/examples.md) has the before, over-cut and final versions.

## Workflow

1. **Name the reader, the medium and the one thing the reader must do or know.** If the draft has several asks for several people, write one ask per person. If you can't name the one thing, ask the user before you write.
2. **Pick the shape for the medium** from the table below. For anything longer than a chat message, read the matching section of [references/mediums.md](references/mediums.md).
3. **Cut** what the reader doesn't need in order to act.
4. **Keep** everything in the Keep list, even when it costs words.
5. **Write it as the sender would**, and add nothing the sender didn't say. Suggest additions after the text instead.
6. **Give each cut a home**, or drop it on purpose.
7. **Check truth, scope, voice and length** in the short version.
8. **Deliver** the text and an accurate list of what you cut.

## Shape by medium

| Medium | Aim for | Watch out for |
|---|---|---|
| Chat reply or DM | The answer first, in 1–3 sentences, with the reason that decides it | Restating the question, balanced essays that end in "it depends" |
| Request to a person or team | One ask, as a yes/no or either/or question, in about 40–100 words (the sender's real one was 65). Your context goes last, in one sentence | Several questions at once, the whole plan in the first message |
| Message to a few named people (a small group DM or thread) | One line of context, then one ask or answer per person, in 2–3 short paragraphs and about 60–100 words (the sender's real one was 85) | Treating it like a channel announcement, a paragraph per person |
| Group announcement (a channel or a large list) | What changes, what to do, when, thanks, where to ask, in short paragraphs. About half of a long first draft (the sender's real one went from 305 to 149 words) | One dense block, and cutting below what the sender would write |
| Email | The ask or the news in the subject and first line, then short paragraphs | Long preambles, and losing the stance in a negotiation |
| Doc, wiki or decision page | The ask or decision visible on the first screen. Length follows the content | Restating, and padding sections that no reader needs |
| Slide deck | One idea per slide, with enough slides to cover the topic in the time slot | Squeezing a topic into too few slides |
| Form or survey | A short title and description, and questions that are easy to answer but prompt detailed answers | Too many fields, and instructions that read like a doc |
| PR description, issue or commit | The problem and the fix in the first lines, and any deploy order or risk near the top. Link logs and long output | Pasted logs, file-by-file narration |
| Status update | What you need from the readers first, if anything, then the outcome, blockers and 2–3 numbers | A chronological diary, a decision buried in paragraph two |

## Cut

- **The background the reader doesn't act on**: how you got here, why you built it, program framing, the history of the decision.
- **Mechanics** that the reader will discover by using the thing, such as what each button does or a reminder schedule. Also cut lists, feature tours and examples that a linked page, video or form already shows.
- **Preambles and closers**, such as "Here's the plan:", "Great question", "On your question:", "Happy to help" and "Let me know if you have any questions".
- **Secondary asks.** Keep one ask per reader. Turn an open question into a yes/no or either/or question. Park the rest for later.
- **Filler hedges**: stacked qualifiers, "just", "basically", "it's worth noting". Keep every word that states real uncertainty or a condition, such as "may", "could", "we believe", "for now", "if" and "only if". "Could be disruptive" and "would be disruptive" are different claims.
- **Jargon the reader doesn't share.** Use plain words. Keep the shorthand that this audience uses, such as "opp" or "EOD" in a sales channel.
- **Bullets and bold**, unless the reader acts on each item or compares options.
- **Repeats.** Say each thing once.

## Keep

In every text:

- **The ask, and every date, time, deadline, link, number and name the reader needs to act.**
- **What the thing is.** "Kicking off Fri Nov 20, invite coming" never says what is kicking off. Name the event, product or change.
- **Every condition, and the one caveat that changes what a reader does.**
- **The reason that makes the reader act**, such as what it counts toward or why now. Cutting the "why" of your own process is fine. Cutting the reader's reason is not.
- **The sender's voice.** Use their "I" for their own commitments ("I'll send an invite shortly", not "invite coming"), their phrasing for their own role, and the emoji they already used. Don't add decorative emoji.
- **Structure that carries content in longer text**: headings, and a table where the reader compares options.

In posts to a group (a channel or a large list):

- A greeting or thanks, short paragraphs with one idea each, real @mentions for the people you address or thank, and where to ask, if the draft says where.

With someone outside your company, or in any negotiation:

- **The stance.** Keep one short sentence of the signals that shape the reply, such as "we plan to renew", "we value X" or "open to other options". Without them, a polite request reads as take-it-or-leave-it.

## Write as the sender

- **Learn their voice.** If you can see the sender's recent messages in this channel or to this reader, read a few and match them. In chat that usually means full sentences with normal capitalization, commas or periods instead of em dashes, reasoning in the first person, and no headers or bold. Sectioned structure (Why, Fix, Tests) belongs in PR descriptions and runbooks, not in chat. Don't copy typos.
- **Never stiff or controlled English.** Short declarative sentences with "Please…" on every line read as robotic, even when they're clear. One sender called that tone "atrocious".
- **Cut when asked to cut. Polish when asked to polish.** A request to shorten a draft, or to make it not a slop grenade, is a request to cut: apply the Cut list fully, and keep the sender's own phrases where they survive. A request to fix a draft the sender wrote themselves, or to fix one part of it, is a request to edit lightly. Keep their words and their meaning. Fix real errors, such as a wrong day, a wrong word or an unexplained abbreviation. When they name the part to fix, change only that part. Don't split a claim into finer precision than the reader needs; the sender will call it pedantic. Use any wording the sender supplies exactly as written, and build the rest around it.
- **Plain over compressed.** If a short line would need explaining to you, the reader needs the explanation too. Write the plain sentence that says what actually happens, and to whom.
- **Match the tone to the relationship.**
  - Asking a manager or peer for a decision: invite their input before you build. "Would love a yes/no by Friday" is too blunt.
  - Asking a colleague or vendor for something substantive: say what you need and what you'll do. Cut deferential padding such as "would really appreciate", "happy to hop on a call" and "no rush". Keep short warmth in acknowledgements, and keep hedges that mark real uncertainty, such as "as far as I can tell".
  - Conceding a correction: concede flatly ("Yeah, you're right.") and go straight to the substance. Don't write "good catch", an apology or praise.
  - Pushing back on a vendor: keep the substance, framed as what you believe, what their way costs, and what would change your mind.
  - Writing to a customer: be diplomatic. Lead with what helps them, not with what you can't do for them.
- **Say whose call it is.** If the draft assumes something that another person owns, say so and @mention them to confirm. If the choice is theirs, list the options and ask; don't recommend one.
- **State status plainly**: planned, built, or live. "Scoping" leaves readers guessing whether anything works yet.

## Add nothing the sender didn't say

A rewrite should only remove, merge, reorder or rephrase. Don't put new commitments, policies, estimates, deadlines or facts into the text. That includes the human parts above. "I'll post an update once it's out", "or DM me", "takes about 10 minutes" and "one task per response" are all promises the sender didn't make. Don't add asks or scope the sender never raised, and leave out dates the sender can't commit to yet.

When the shape would be better with an addition, suggest it after the text, in one line: "Consider adding: 'I'll post an update here once the first batch is out.'" Use a placeholder such as `[link]` only for something the sender must supply, and point it out. Keep a relative date ("yesterday") as written. Don't swap it for a placeholder or a date you worked out yourself. Don't invent structure that the source doesn't give, such as which example goes with which rule.

Writing from notes is different from rewriting a draft. When the notes call for illustrative material, such as example prompts for a slide or sample wording for a template, draft it and mark it as a draft for the sender to check. Empty placeholders leave the sender with the work. Still don't invent facts, numbers, results or commitments.

## Give each cut a home

Cut detail goes to one of these places:

- An **"If they ask"** list under the draft. This list is for the sender and is not sent. Order it by how likely each question is, and raise items one at a time in the conversation.
- **The thread**, or a follow-up message.
- **A linked doc, video or form**, or a collapsed section of a page.
- **Nowhere, on purpose.** Say so in the cut list.

Don't move a promise or a condition to a place that doesn't exist yet. In one rewrite, "more than one card is welcome" left the message because "the form can say that", then left the form in the next pass. No text that the readers saw said it anymore.

## Check the short version

- **Truth.** Reread every sentence whose condition you cut. In one announcement, "Yes gets you a follow-up card" was true only for meetings that hadn't happened yet. Without "if you say Yes before the meeting", it was false for most of the first batch.
- **Certainty.** Compare each claim with the original. "We believe we need 130" must not become "we need 130", and "may object" must not become "object".
- **Scope.** A short "yes" can claim more than the sender means. Add the qualifier the sender would use, as in "In my prototype, yes". When you merge clauses, keep each qualifier attached to what it qualified. A size that applied only to month 1 must not become "each", and "X, so Y" must not become "Y because X".
- **Additions.** Nothing in the text is new, except placeholders and marked drafts of example material.
- **Standalone.** A reader who sees only this text can tell what it is about and what to do.
- **Voice.** It reads as if the sender typed it. Subjectless fragments and missing greetings in a group post mean you over-cut.
- **Length, both ways.** If you removed more than about two-thirds of an announcement or a reply to a group, compare it against the Keep list again. The sender rejected a 66% cut ("That might be too minimal") and rewrote a 68% cut back to about half the original. If you kept more than about two-thirds of a long draft, you probably kept mechanics or background: cut again. If a request or a message to a few people is still over about 100 words, find the second ask or the explanation that can wait.

## Deliver

1. Put the text in a paste-ready block, so the sender can copy it with its formatting.
2. After the block, write one or two lines that name every cut and where it went, then any suggested additions. Name all the cuts, not a sample, and claim only what you checked. "The video covers the features" is a guess unless you saw the video.
3. Hand the text back in the conversation so the sender can paste and send it. Don't post, send or publish it for them unless they ask. Don't explain these rules back to them.

For sentence-level cleanup (AI vocabulary, dashes, filler), use an unslop-style pass after this one. Keep the sender's own emoji, quote style and shorthand.
