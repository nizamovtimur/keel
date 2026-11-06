# Evidence and open questions in assessment reports

Design, 2026-11-06. Status: agreed with the maintainer, built in this branch (schema, save and finalize checks, report page, both skills).

## The problem

An assessment can be complete-looking and wrong in two ways the record does not show.

1. **A question is asked and the run moves on.** Three places let it happen. The method's data-sufficiency gate lets independent branches continue, but nothing stops the dependent branch from being graded anyway. The library overlay says "if a gate paused the run, finish the assessment first, then polish". And the report schema requires a `risk` on every finding and an `answer` on every question, so "waiting for a fact" has nowhere to go. The result is a grade resting on an assumption, or a threat discarded because a fact was missing: exactly what the gate forbids.
2. **Claims carry no checkable pointer.** Evidence lives inside the prose of `scenario`, `vulnerability` and `risk.reasoning`. A reader cannot tell which sentence was checked against code and which was inferred, and a vague pointer ("the handler appears to…") looks the same as an exact one.

## Decisions

### Open questions block; they are not deferred

- Before asking, the assessor looks for the fact itself: code, configuration, running a test where the case is unclear.
- When it knows where the fact is but lacks access or a document, it asks for that access or that document, not for the fact.
- A question that decides a branch is never left open. The branch gets no grade, no discard and no requirements until it is answered; branches that do not depend on it are carried through.
- A branch depends on a fact only when it cannot be decided without it (can the source reach the surface at all, does the action exist). An unverified compensating control does not pause a grade: the grade is given from the established facts with that control uncounted, and the answer says what the grade becomes if the control holds. A first version of the rule without this line made models withhold grades the given facts already decided; with it, blind-judged runs on six method scenarios passed every required check.
- A report with an unanswered question cannot be finalized.
- In a fleet run on subagents, a subagent that needs an answer returns to the coordinating session with the question and waits; the coordinator asks the person. There is no separate "collect facts first, grade later" phase: assessment keeps needing new facts and rechecks, so the rule is about not moving past an open question, not about phases.

### Evidence as an addendum, referenced from the text

Adapted from lesslop (github.com/slovozaslovo/lesslop, MIT, commit e816f80): every claim about the system is either backed by something checked in this session, or marked unverified. Verify, don't defer.

- The report gets an `evidence` list. Each entry: a stable id, a permalink pinned to a commit and to the exact line range (not a file, not a branch), the path and lines, a verbatim quote, and how it was obtained (read, command run, test).
- The prose stays clean: a claim points to its entry with one marker, `[1]`, or an embedded link to the entry. The embedded link always targets the evidence entry inside the report, never an outside address directly, so the reader sees the full destination in the addendum before leaving the page.
- A claim that decides a grade and has no evidence entry is an open question (above), not an unverified footnote.

### Links are safe by construction

An evidence link is model output, so it can be steered: a planted address can carry data in its query or lead to a lookalike page, and a page that previews links leaks without a click.

- Save rejects a link whose host is not on the organisation's allowlist (configuration, empty by default) or that is not pinned to a commit.
- The quote is required, so the evidence survives for a reader without access to the source.
- The UI renders links as text with the domain shown, opens nothing by itself, and loads no images or previews.

## Also in this change

- `deployment` as its own field on a finding (live, off, pilot, not deployed); the grade describes the design as it will run.
- Discards only by the threat's `reachability` condition. A small consequence is a low grade, not a discard.
- `attack_surface` optional where the weakness has none.
- Save warns when a finding's `harm` or `source.who` is outside the catalog threat's values.
- A stable fingerprint per finding (system, root cause, threat).

## Out of this change

Catalog splits (credential borrowing by action, data leak by rule-out), the harm vocabulary, control cards, and cross-system calibration. Each is its own change after this one is checked.

## How we will know it worked

Re-run two or three systems on the new schema. Expected: no finding graded while its deciding question is open; every grade-deciding claim has an evidence entry with a pinned link and a quote; no paused branch among discards. If grades still rest on "not established" in the reasoning, the cause is the model or the skill text, and those are fixed before the catalog work starts.
