# Shape by medium

Read the section for the medium you are writing. Each section says what the reader needs first, what to cut, and what to keep. Notes marked *(observed)* come from real rewrites and the sender's reactions. The rest applies the same principle to mediums with less data.

Contents:

- [Chat reply or DM](#chat-reply-or-dm)
- [Request to a person or team](#request-to-a-person-or-team)
- [Message to a few named people](#message-to-a-few-named-people)
- [Raising a problem or question with an owner](#raising-a-problem-or-question-with-an-owner)
- [Group announcement](#group-announcement)
- [Email](#email)
- [Doc, wiki or decision page](#doc-wiki-or-decision-page)
- [Slide deck](#slide-deck)
- [Form or survey](#form-or-survey)
- [PR description, issue or commit](#pr-description-issue-or-commit)
- [Status update or report](#status-update-or-report)
- [Calendar invite or event description](#calendar-invite-or-event-description)

## Chat reply or DM

Someone asked a question, so answer it. Put the decision first, then the one reason that decides it: "Redis. We need pub/sub for the notifications feature." Use one to three sentences.

- Cut: "Great question", a restated question, a survey of both options, and an "it depends" ending.
- Keep: the decision, the deciding reason, and the one number that matters. Keep the sender's position: if their draft ends in a suggestion ("might be worth a pilot"), lead with that suggestion. Don't upgrade it to a firmer call.
- Give each subject its own paragraph, and say why each point matters to the reader. An unexplained "also…" line at the end should go or be explained. *(observed)*
- Back an abstract distinction with one concrete example, and say how often it happens if you know. *(observed)*
- When the reader needs more than a few lines, link a doc and say what the link contains. *(observed)*
- If you honestly can't decide, say what would decide it and offer to check: "Probably Postgres. The only thing that would change that is if we need full-text search at scale. I can benchmark it by Friday."

## Request to a person or team

The reader owes you nothing, so make the ask easy to answer.

- Put one ask in the first two sentences, as a yes/no or either/or question. *(observed)*
- Give the numbers that the answer depends on, such as volume, dates or scope, in plain words.
- Context goes last, in one sentence, or nowhere if the reader knows you. In the data, the sender cut their own role sentence before sending. *(observed)*
- Keep everything else in an **"If they ask"** list under the draft. That list is for the sender only. *(observed)*
- Before sending, role-play the reader: if their reply would be a clarifying question ("which workspace?"), answer it in the message. *(observed)*
- About 40–100 words. *(observed: 39–94 for agent rewrites, 65 for what the sender sent)*
- Ask only for what you need now. Question each extra item before you add it. *(observed: "Is there a reason to ask for more than two?")*
- Keep the one concrete sentence that says how the thing works. Spell out internal abbreviations, say what a link contains, and give a real deadline. *(observed)*
- To reviewers: ask for the one check you need, and say what they don't need to review. *(observed)*
- To an expert or owning team, about your approach: first ask whether it's the right path, and invite alternatives. Ask them to act (review, grant, share) only after they say yes. *(observed)*
- To an outside vendor or consultant: lead with what blocks you now, include only what changed since your last message, and state the outcome you need, not how to build it. Put field names and values in code format. Drop apologies. *(observed)*
- To IT or a service desk: a few lines. The one-line ask, the exact identifiers, one line of why, and the earlier ticket number instead of repeated context. No Context/Ask/Details/Impact sections. *(observed: an IT specialist asked for exactly this)*
- Your role: add one line only when the reader doesn't know you and the ask would look odd from your team. Drop it when they know you. *(observed: the sender asked for the line, then cut it before sending to someone who knew them)*

## Message to a few named people

A small group DM or thread, such as a first post to six stakeholders. It is closer to a request than to an announcement.

- One line of context: who you are only if they don't know you, and what you're sharing. *(observed)*
- Then one ask or answer per person, with their @mention. Fold people with the same ask into one sentence. *(observed: the sender's version used 3 short paragraphs for 4 people)*
- Put the link where the context line mentions it. *(observed)*
- Answer a question that someone already asked first. Scope the answer if it covers less than it sounds ("In my prototype, yes"). *(observed)*
- About 60–100 words. *(observed: 289 → 87 by the agent, 85 sent)*

## Raising a problem or question with an owner

- Post one short question in business terms: what is happening, is it intended, and what should happen. Let the owner supply the technical cause. Don't post a thread of technical replies. *(observed: a 488-word, 5-message draft was replaced by one question)*
- When the owner's preference decides it, ask which option they prefer and list the options. Don't recommend one or settle it without them. Add the new question to any existing list of questions. *(observed)*
- Format nested options so they paste cleanly into the chat tool.

## Group announcement

Many readers, and most of them skim. They need to know what changes for them, what to do, and when.

- Order: greeting, what changes, what to do, timing, thanks, and where to ask. *(observed)*
- Say plainly what the thing does, with substance. Don't copy the template of thinner announcements. If the sender supplies an opening line, use it as written. *(observed)*
- Use short paragraphs with one idea each. Don't use one dense block. *(observed: the sender split a 1-block rewrite into 5 paragraphs)*
- Use real @mentions for the people you thank or address. Use @here or @channel only when everyone needs it today. *(observed)*
- Keep the reason that makes it worth doing, such as what it counts toward. *(observed)*
- End with where to ask. A first-person follow-up ("I'll post an update once…") works well, but only the sender can promise it, so suggest it after the text. *(observed: the sender added one themselves)*
- Cut mechanics that people learn by using the thing, reminder schedules, edge cases that affect few people, and pilot history. Those go in the thread. *(observed)*
- Length: about half of a long first draft, or most of a short one that was already tight. The sender rejected cuts to a third, and also cut a 305-word draft to 149 themselves. *(observed: 305 → 149 and 177 → 154 by the sender, against 99 and 60 by the agent)*

## Email

Email adds a subject line and a reader who may be outside your company.

- Subject: the ask or the news, specific enough to find later ("Invoice 2231 was charged twice, can you refund one?"), not "Following up".
- First line: the ask. Then the numbers and the deadline it depends on, then any condition you're attaching.
- Cut: "I hope this email finds you well", partnership recaps, "I completely understand", and offers to talk that don't name a time.
- Keep: every number, date and condition in a negotiation. A conditional offer ("we'll extend the contract only if the SLA credit applies") must stay conditional. Keep the sender's level of certainty too: "we believe we need" is not "we need".
- Keep the stance in one sentence: that you intend to continue, what you value, and that you're open to other options if the draft says so. These shape the reply. Without them the email reads as an ultimatum.
- If the draft offers a call, keep the offer, but put it in one line.
- To a customer: be diplomatic. Lead with what helps them, not with what you can't do ("the fastest way to get started is…", not "we aren't able to set up a call for every request"). Follow the channel's rules: a cold outbound email has no links. *(observed)*
- A sign-off is one line.

## Doc, wiki or decision page

A doc can be long. It becomes a slop grenade when the reader can't find the point, or when sections exist for the writer and not for any reader.

- On the first screen, put the ask or the decision, what happens if the answer is no, and each reader's part with a deadline. *(observed)*
- A title that states the ask ("Approve the partner sign-in pilot") beats a topic ("Partner sign-in proposal"). *(observed)*
- Then put only what a reviewer needs in order to decide: what it is, options with a one-line verdict each, risks with mitigations, and open questions per team. *(observed)*
- Put citations and long evidence in a collapsed section or an appendix. *(observed)*
- Cut restatements, a "Conclusion" that repeats the summary, and background that no reader asked for.
- After cutting, run a fact check. Compression drops qualifiers such as "draft", "low-priority" and "no review yet". *(observed)*
- Open a proposal with the problem, in the sender's words, before the solution. Put a short TL;DR at the top of a long spec or scope page. *(observed)*
- For a manager or decision-maker: separate your own reference detail from what they must decide. Give them the short version, with a very simple flowchart of what happens and when. *(observed)*
- Show the artifact, not a description of it: the message template with its merge fields, and a preview with them filled in. *(observed)*
- Keep out issues that belong in another doc, and "known limits" that aren't real problems in context. *(observed)*
- Report results per scenario, and say which scenarios weren't tested. Don't sum up with one headline number that the test doesn't support. *(observed)*
- On a page for business readers, leave out code-file paths, line numbers and change-history notes ("Changed on <date>"). Keep those in the repo copy. *(observed)*
- For non-technical readers, such as sales reps: organize by the job they want done, show each job end to end with real screenshots, and use plain words. Don't catalog tools, permissions or config. If some is needed, put it in a collapsed block. *(observed)*
- A README for a tool that people install starts with a copy-paste block that gets them going. *(observed)*
- Long internal reference pages for engineers or agents are fine. Don't trim verified reference content unless asked. *(observed)*

## Slide deck

Brevity is the wrong goal here. Each slide should be easy to read, and the deck should cover the topic.

- One idea per slide, with a headline that states the point ("Churn fell 12% after onboarding calls"), not a label ("Results").
- Keep the time constraints from the notes, such as the slot length and the Q&A time. Don't invent a structure that the notes don't give, such as which example illustrates which rule.
- Use enough slides to cover the material at a comfortable pace. Don't squeeze a talk into a few dense slides. As a rough guide, plan one slide for every 1–2 minutes of talk, and give each demo its own slide.
- On slides, use few words and let the speaker say the rest. Put detail in speaker notes, not in bullets.
- Keep numbers with their sources, and put each result next to the claim it supports. Keep the limits and caveats the audience must know.
- When the notes call for examples (sample prompts, before/after pairs), draft them and mark them for the speaker to check. Don't leave empty placeholders.
- If a slide-count limit forces cramming, offer a version with enough slides. *(observed: "we're trying to squeeze too much into four slides")*
- In training, explain what a term or label means. Don't tell the audience how to do their job unless that is the topic. *(observed)*
- Leave out features most of the audience doesn't have, or that are out of date. Don't center one segment of the audience. *(observed)*
- When there are several valid ways to do something, list them as equal options. *(observed)*

## Form or survey

The form must be easy to fill in, and it must still get detailed answers.

- Title: what it is for, in a few words. Description: why and the deadline, in 2–3 sentences. Give the time it takes only if the sender knows it.
- Ask few questions. Every field must be used for a decision. Word each field as a question that asks for detail, with a hint where it helps. Don't hand people a property schema to fill in. *(observed: "That's too complicated. It needs to be both easy to fill in while prompting them to give detailed answers")*
- Text for a field with limited space, such as a request dialog, must fit the field. Write the short version for the field. *(observed)*
- Ask for detail with a concrete prompt, not by adding more fields: "Walk us through the last time you did this, step by step" gets more than five separate fields do.
- Prefer one optional example field over many required fields. Make the required fields match the promises: if partial answers are fine, require only what you can't do without.
- Keep promises that the readers will see only here, such as "More than one submission is welcome". *(observed: this line was cut from both the message and the form)*

## PR description, issue or commit

The reviewer needs to know what changed, why, and what could break.

- First lines: the problem and the fix, both in the first one or two sentences.
- If the reviewer or deployer must do something in order, say so near the top ("Deploy in order: dedupe, migrate, then ship. Details below."), and give each step its reason.
- Then: how it was tested (one line, not pasted logs), and deploy steps or ordering, if any.
- Keep every ordering constraint and risk: "deploy the reader before the writer, otherwise old pods can't parse the new rows."
- Cut: file-by-file narration that the diff already shows, pasted test output, "This PR introduces a comprehensive…", and closing invitations to ask questions. Keep "as of yesterday" as written unless the sender gives the date. Don't guess it, and don't leave a placeholder.
- For an issue, the title states the problem or the ask, and the body gives the steps to reproduce or the decision needed.

## Status update or report

Readers want the outcome and what you need from them, not a diary.

- First: what you need from the readers, if anything, such as a decision with who decides and by when. Make it easy to spot. A bold "Decision needed:" lead is fine in a status channel.
- Then: the status in one line (on track, at risk, or slipped, and the new date). Say plainly whether each piece is planned, built or live. *(observed)*
- Then: the 2–3 numbers that show progress.
- Keep the assumptions that the dates depend on ("March 3 assumes the vendor ships the API fix by Feb 20"), and the current state of each one ("they're reviewing the fix now").
- Cut: a day-by-day log, finished minor tasks, and "productive week, team in good spirits".
- For a manager or leadership: neutral and forward-looking. Give the facts and the next action. Don't resurface past misses or blame individuals. *(observed)*

## Calendar invite or event description

The invite is where the details live that a message can leave out.

- Title: what the event is ("Working session: onboarding pilot kickoff").
- Body: what to bring or prepare, the link, and one line of purpose.
- The invite list can replace a cc list in the message. *(observed)*
