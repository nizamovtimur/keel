---
name: assess-genai-with-library
description: Use when assessing the GenAI/LLM security of a specific system, integration, agent, RAG, or feature ("assess security", "threat model", "security review", "risk assessment of an integration") and the in-house Keel threat-model MCP is available to draw on.
---

# Assessing a GenAI system against the threat library

## Overview
The library is the methodology **crystallized** into a catalog of threats, each a `harm` (the consequence) resting on `weaknesses` at owned components, each reached across a `surface` (the channel whose content that component treats as trustworthy), driven by a `source`, with a `reachability` carve-out and linked mitigations. It gives you **candidates and coverage**, but you must reason **FROM THE SYSTEM**: the catalog is a floor, not a ceiling, and not a substitute for analysis.

**REQUIRED, source of truth:** run the assessment strictly by the `assessing-genai-security` methodology and follow it verbatim, all its steps, the data-sufficiency gate, the output format. Nothing here overrides or paraphrases it: it is calibrated. This skill only points to where the library plugs into its steps.

## Note the time you started

Before anything else, record the current timestamp. It goes into the report as `meta.started_at`, and it is the one thing that cannot be reconstructed afterwards. An assessment that costs the specialist two hours is a different product from one that costs twenty minutes, and nobody remembers which it was a week later.

## Identify the system first (before the methodology's step 1)

Assessments are archived per system. Before analysing anything, call `list_reports` and read the `system_description` of each system's most recent assessment (`get_report`). If one plausibly describes the system in front of you, **propose the match and wait**, do not assume it. A specialist with fifty systems will not remember the slug, and two similar agents are easy to confuse.

On a confirmed match, read that report in full and assess **by delta**: what changed in the architecture since that date, which findings are affected, which are untouched. Re-derive nothing that has not moved, but do re-check each carried-forward finding rather than copying it, because a control that closed a gap can also have been removed. On no match, this is a first assessment: pick a new `system-id` (lowercase, hyphenated, stable, it is a folder name forever) and leave `delta_summary` null.

## Where the library plugs in (overlay, not a replacement)

- **Threat search (in that methodology step).** Don't pull the whole catalog with all fields in one call, a full `list_threats(brief=false, include=[all])` doesn't fit in one tool response. Query pattern: **(1)** a light index `mcp__keel__list_threats(brief=false, include=["harm","weaknesses"])` for a first-pass pattern match (the `weaknesses`, cause + where + defect, are the recognition anchor); **(2)** `mcp__keel__get_threat(id)` per relevant candidate, for `source`, `reachability`, and linked mitigations (`surface` already comes with the weaknesses in step 1). This does NOT override the methodology's rule "search from the system, not from a catalog": the catalog is a floor. After matching, walk the `harm` classes (wrong-decision, data-integrity, data-exposed, code-execution, downtime, reputation-legal - take them from `get_vocabulary` rather than this line, which is a reminder and not the source) and check whether an asset is under threat that the catalog misses, analyze such a threat from scratch by the methodology.
- **Harm / source / weakness (in those steps).** `harm` = the consequence class; `source` = who or what drives it, one catalog value per source the methodology's source step names (its injection is `external-attacker` arriving over a surface, since the model is only the channel there; the model as a source in its own right is `model-mistake`, `model-overeager` or `model-own-goal`); `weaknesses` = the architectural conditions (cause + where + defect), i.e. how the system is exploitable. Each weakness names the `component` it sits on (model / tool / downstream / memory / knowledge-base / identity-store) and, when something flows in, the `surface` it arrives through - check the system actually has that component, that the channel exists in this architecture, and that the condition holds there. A weakness with no `surface` is about the component's own authority, so it is reachable without anything crossing a boundary. Mind `nature`: a `targeted` weakness is an independent attack path (remove it and the attack fails); a `secondary` one only amplifies impact or likelihood, so it modulates severity, it is not itself the opening. The match is **advisory, not a checklist**: does the weakness fit THIS architecture.
- **Applicability decision.** After a match, apply `reachability` ("NOT applicable if…") on the **UN-mitigated** architecture. A carve-out that doesn't close it → the threat is live; carry it further down the methodology's chain. Missing a fact to decide → this is the methodology's data-sufficiency gate. Look for it in the code and configuration first; if you know where it is and lack the access, ask for the access. Otherwise record it in `open_questions`, put the candidate in `paused`, and wait for the answer. Never assess on an assumption, and never grade it now to fix later. **The gate is symmetric:** DROPPING a threat by taking a missing fact as "absent" (e.g. calling output inert text without confirming the render mode; assuming a tool is unreachable) is the same violation as confirming it on an assumption. No fact → ask, don't drop.
- **Risk reduction (in the mitigation step).** `mcp__keel__get_threat(id)` → linked mitigations; each link's `rationale` says why that control addresses this threat's specific weakness, use it as the starting map, but verify the mapping against the real architecture rather than trusting the prose. Keep the controls applicable to this system. Mind each link's `strength`: a `soft` link only lowers likelihood (by the methodology's cross-cutting rule it is not an architectural control and does not finalize the threat); a `gating` link is an architectural control that blocks the threat. Then judge whether the control is actually **in place in this deployment**: `mcp__keel__get_mitigation(id)` and read its `implementations`, a recorded implementation, especially one the platform or surrounding infrastructure provides, means the control already covers this system and genuinely reduces the threat; an empty `implementations` list means it is only a recommendation, not yet present, so do not credit it as covering the system, verify its presence from the architecture instead. Read `failure_behavior` too: a control that fails open (lets the threat through when it fails) is materially weaker than one that fails closed, weigh that in the residual risk.

## Common mistakes (library-specific; methodological ones live in the methodology)
- **Dropping on an assumption**, killing a threat by taking a missing fact as "absent" (e.g. calling output inert without confirming the render mode). A drop needs the same gate as a confirmation.
- **Catalog as a checklist**, skipping `reachability` carve-outs → over-applying threats the system doesn't have.
- **Catalog as a ceiling**, not walking `harm` coverage, missing a threat outside the catalog.
- **Copying the prose** of `weaknesses`/`reachability` instead of tying the wording to the specific system.
- **SOFT taken as a guarantee**, a `soft` mitigation link does not close the threat.
- **Crediting an unimplemented control**, a mitigation with no `implementations` recorded here is a recommendation, not evidence the threat is already covered in this deployment; confirm the control's presence from the architecture.
- **Per-item grading of a set on intuition (flip-flop)**, when the recommendation grades a SET of homogeneous items (tools, endpoints, actions), don't judge each by gut. First state one **risk frame** (impact if abused → reachability IN THIS system → residual risk after controls → gate/allow) and run every item through it in context, showing the reasoning per item. This is NOT a static matrix: verdicts legitimately differ across systems, context decides (e.g. an irreversible action with an unreachable surface or strong controls may be allowed), not the action class by itself. On a challenge to one item, test whether the FRAME holds (and re-derive it as a whole), don't flip a single verdict; a point flip IS the flip-flop. Flag genuinely borderline ones; the output is a **justified recommendation**, and the final decision is the owner's.

## Final polish (second to last step)
Once the assessment is complete, polish the **final assessment** (part 2 of the output) through two skills via the Skill tool, in order: **`tighten-text`** (concision + de-bullet, tuned for security prose), then **`humanizer`** (remove AI-tells, natural expert voice). Both are substance-preserving and MUST NOT drop or alter risk levels, HARD/SOFT tags, GATE ITEMS / stated uncertainty, the delta, mitigations, or any domain specifics, they tighten wording and voice only. Keep the two-part structure and the analysis trail intact; don't polish the audit trail's reasoning away. Polish only once nothing is paused: an open question is answered before the polish, not after it.

## Write the report and hand back a link (last step)

An assessment that lives only in this conversation is lost. Write it through the Keel MCP tools, `create_report` for the empty draft, then `save_report` with the whole document, and give the user a link to it. **The link is the deliverable**, not a wall of YAML pasted back into chat.

Do not write the YAML file directly. The tools check what a plain file write cannot: that the report parses, that its grades are on the allowed scale, and that every `mitigation_id` and catalog threat id it names actually exists. A file written round the side of those checks lands broken and nobody finds out until someone opens it.

**The record is a draft, and stays one.** The specialist corrects grades and wording, then finalizes it themselves in the UI. Finalizing is not exposed to you: signing off on someone else's judgment is not yours to do.

`assessor` comes from `git config user.name` and `user.email`, written as `Name <email>`, the person accountable for the judgments, never the agent. `date` is today. `system_id` and `system_description` come from the identification step above.

Per finding: `id` (the catalog threat id, or a new `T-*` id you coin for something the catalog lacks), `from_catalog`, `scenario`, `source` (`who` / `motive` / `access`), `asset`, `attack_surface`, `vulnerability`, `exploitation_complexity`, `harm`, `risk` (`likelihood` / `severity` / `reasoning`), `delta`, `deployment`, `root_cause`, `evidence`, `requirements`, `ignored_mitigations`. `attack_surface` stays empty only when the weakness has no channel (a standing credential); never name one the path does not cross. `deployment` says what is switched on today (`live`, `pilot`, `off`, `not_deployed`); grade the design as it will run, not today's switch. `root_cause` is a short stable slug for the defect, the same across re-assessments and across systems that share it. `harm`, `attack_surface` and `source.who` are the catalog's own vocabularies, quote them verbatim. `source.motive` and `source.access` answer the methodology's source step for either kind of source: for an attacker, the goal and the real access to the surface; for a source without one (`model-mistake`, `model-overeager`, `error`, `accident`), what triggers it in this system and the permissions it acts with. A source without an attacker still has a trigger, so `motive` is never just "none". `likelihood`, `severity` and `exploitation_complexity` are each **low | medium | high**; there is no fourth level.

**`risk.reasoning` must be a sentence that stands on its own.** It is pasted straight into a ticket with no label in front of it, so "irreversible money movement, reachable anonymously" fails and "The money movement is irreversible and the path is reachable anonymously" works.

Each requirement is either a catalog control (`mitigation_id` set, `description` omitted) or an ad hoc ask (`mitigation_id: null`, `description` required). **Never invent a `mitigation_id`.** If the library has no card for a control this system clearly needs, that is a wanted outcome, not a gap in your answer: leave `mitigation_id` empty and write the ask in `description`, in one or two sentences, as if proposing it to the library, those are collected on the Overview as what the library is missing. A plausible-looking id that resolves to nothing reads as a cataloged control and is refused on save. `coverage_status` is `needs_implementation`, `already_covered` or `partial`; the last two **require** a `coverage_note` saying what covers it here, and `needs_implementation` must not carry one. Leave `included` out, it defaults to shipping everything except what is already covered, and the specialist decides the rest. A control linked in the catalog but wrong for this system goes in `ignored_mitigations` with the reason, not into `requirements`.

`discarded` is id + reason (+ the `evidence` ids it rests on), never the full chain. The reason is the threat's `reachability` condition holding here, shown by a fact. A small consequence is not a discard: that threat is live and graded low.

### Open questions and paused branches

A question is not a note for later. Each one goes into `open_questions`: `id` (`Q1`, `Q2`…), `question`, `asks_for` (`fact`, or `access` when you know where the fact is and lack the right or the document), `looked_in` (where you looked first and why it did not settle it), `needed_for` (the branch and the step). A candidate whose grade or discard depends on it goes into `paused` with `waiting_on` and a `note` of what is established so far: no grade, no requirements, no discard.

When `save_report` returns `open`, the assessment is not done. Get the answers: ask the specialist, or, if you run as a subagent, return the questions to the session that started you and wait. Write the answer into the question, turn each paused branch into a finding or a discard, and save again. A paused branch left waiting on an answered question is refused on save.

### Evidence

Adapted from lesslop (github.com/slovozaslovo/lesslop, MIT): every claim about the system is either backed by something you checked in this session, or it is not a claim you may grade on. Recalled, "standard", "obvious" and "the code probably" are not checked. If checking is cheap, check now; do not offer to check later.

The proof goes in the report's `evidence` list, not into the prose. Each entry: `id` (1, 2…), `kind` (`read`, `command`, `test`), a verbatim `quote` of the lines or the output, and for a read the `commit`, `path` and `lines` of the exact place (not a file, not a branch); for a command or test, the `command`. A `url` is optional and strict: https, on a host in `evidence_hosts`, containing the commit, anchored at the lines, no query string. Anything else is refused on save, because a link is model output and a planted one can carry data out.

In the prose, a claim carries one marker, `[3]`, and the finding lists the ids it rests on in `evidence`. Keep the sentence readable: one marker per claim, no paths or quotes inline. A finding with no evidence cannot be finalized. A grade-deciding claim you could not check is an open question, not an unmarked sentence.

### `meta`, how the run went

This block does not describe the system; it exists so the assessor itself can be improved, and it is the only feedback anyone will get. Fill it honestly, including the parts that make you look bad, a flattering `meta` is worthless.

- `started_at` from the first step above, `finished_at` at write time.
- `questions`, the exchanges that actually moved the analysis: what you asked, what came back, what it changed. Not a transcript, and not questions whose answers changed nothing.
- `volunteered`, **facts the specialist gave you that you never asked for.** This is the most valuable line in the report. A question you asked is one the skill already knows to ask; a fact you had to be handed is a hole in the skill, and writing it down is what closes it. If the specialist said "by the way, X" and X mattered, it goes here. Say what would have been wrong without it.
- `critique`, where the specialist told you your reasoning was wrong, in their words, not softened. If a grade moved because you were pushed, that belongs here as well as in `questions`.

Leave a list empty rather than padding it. An empty `volunteered` on a run where the specialist genuinely volunteered nothing is a real signal; an invented entry destroys the only measurement there is.

Then hand back the link, using the host and port Keel is served on (`keel up` serves `127.0.0.1:8420` and prints the address; `ui_port` in `keel/config.py` holds the port):

```
http://127.0.0.1:8420/reports/<system-id>/<YYYY-MM-DD>
```

Say in one line what the reader will find there and what is left to do, e.g. "3 findings, 5 requirements, review the grades and finalize." Do not print the YAML. Hand the link back as finished only when `open` is empty; until then what you hand back is the open questions.
