# Reading a report

A report is one assessment of one system on one date. This page goes through a report from top to bottom with an example, and says who each part is for.

The example below is made up, built on the demo system "Halo" from [Getting started](getting-started.md).

## The header: which system, when, and how final

```
Halo support assistant
2026-11-06 · final · assessed by A. Assessor <assessor@example.com> · took 1 h 25 min
```

- **Status** is `draft` or `final`. A draft is still being corrected; grades and wording may change. A final report is signed off and is the dated record of what was assessed that day. The published site shows only final reports unless told otherwise, and marks any draft with a banner.
- **Assessor** is the person accountable for the judgments, taken from their git identity. It is never the agent.
- **Took** is the time between the start and the end of the run, recorded by the agent.

If this is a re-assessment, a box under the header says **what changed since the last assessment**. Read that first: it tells you which findings moved and why.

## The findings table: what the risk owner reads

| Threat | Harm | Severity | Likelihood | Origin |
| --- | --- | --- | --- | --- |
| T-TOOL-ABUSE | Data integrity | high | medium | catalog |
| T-DATA-LEAK | Data exposed | high | low | catalog |

A **finding** is a threat that survived the analysis: it can happen in this system as it is built today. The table is sorted with the most severe first.

- **Harm** is what breaks, from a fixed list of six: wrong decision, data integrity, data exposed, code execution, downtime, reputation and legal.
- **Severity** and **likelihood** each use three levels: low, medium, high. There is no fourth level on purpose: your own risk policy turns a grade into an action, and policies are written against three bands.
- **Origin** says whether the threat came from the catalog or is new. A new one is something the catalog did not have; it is a candidate for your catalog (see [Authoring](authoring.md)).

## One finding, top to bottom

Each finding opens with a **scenario**: one story of who does what, through which channel, and what is lost.

> A customer uploads an attachment whose text tells the assistant to change the shipping address on another order. The model calls `update_shipping_address` with the attacker's address and the parcel goes there.

Under it, the chain the scenario is built from:

| Field | Example | What it answers |
| --- | --- | --- |
| Who or what drives it | External attacker: redirect a shipment. Access: any signed-in user can upload an attachment that gets indexed | Who has the motive and the access, or for a model error, what triggers it |
| Asset | Shipping addresses in the production database | What is lost |
| Reached over | Retrieved content | The channel the harmful text comes through |
| Vulnerability | The address write runs because the model produced the call; nothing outside the model ties it to the user | The condition in this system that lets it happen |
| Effort to exploit | low | How hard it is to pull off |
| Why this grade | The write changes real orders and any signed-in user can plant the text | A sentence that stands on its own, ready to paste into a ticket |
| What the AI integration changed | Before the assistant, an address change went through a form tied to the session user | The difference from the system before AI was added |

The last row matters most when you argue about priority. A threat that existed before the AI integration and is no worse now is a different conversation from one the integration created.

## Requirements: what the product team gets

| Control or ask | In place here? | In the hand-off |
| --- | --- | --- |
| CTRL-HUMAN-IN-LOOP | No, to be built | yes |
| Bind every write tool call to the order ids the signed-in user owns, checked in the tool | No, to be built | yes |
| CTRL-AUDIT-LOGGING | Yes: requests go to the SIEM, kept 90 days | no |

A requirement is either a catalog control (it links to the control's page, which says what it does and how to check it) or a plain-language ask for something the catalog has no card for yet.

- **In place here?** is the judgment about this deployment: yes, partly, or not yet. "Yes" and "partly" carry a note saying what covers it.
- **In the hand-off** says whether the requirement goes to the product team. By default everything not already in place does; the assessor can change that.

Below the requirements, **linked controls that do not apply here** lists controls the catalog suggests for this threat but that are wrong for this system, each with the reason.

## Ruled out, with the reason

| Threat | Why it does not apply |
| --- | --- |
| T-CODEGEN | Nothing downstream executes the output or renders it as active content |

Every candidate the assessment dropped is listed with the reason. This is what lets the next reviewer, or an auditor, see that a threat was considered and why it was dropped, rather than wonder whether it was missed. The rule behind it: a threat is dropped only on an established fact, never because a fact was missing.

## How this assessment ran

A collapsed section at the end records the questions the agent asked and what each answer changed, facts the specialist gave without being asked, and where the specialist said the agent's reasoning was wrong. It is there to improve the assessment process, not to describe the system, so the product team can skip it.

## Who reads what

| Reader | Read | Skip |
| --- | --- | --- |
| Risk owner | Header, what changed, the findings table, each scenario | The chain table, the run record |
| Product team | Requirements marked for hand-off, and the scenario of each finding they belong to | Ruled out, the run record |
| Security lead, auditor, next assessor | Everything, especially ruled out and what the AI integration changed | Nothing |

## Check yourself

A finding reads: severity **high**, likelihood **low**, "What the AI integration changed: nothing; staff could already do this through the admin panel."

Should this go to the top of the product team's list?

<details>
<summary>Answer</summary>

Not on the strength of this report alone. The harm is serious, but the AI integration did not create it or make it easier, and it is unlikely. The risk was already there before the assistant, so it belongs with whoever owns the admin panel's risk. The report gives the risk owner what they need to make that call; it does not make it for them.
</details>

The format of a report may gain fields as the assessment method develops. The published site shows any field it does not know yet under "Other fields", so nothing in a report is hidden from a reader.
