# Grading on Keel's scale

Open it for every grade at step 7. Keel grades two axes on three levels, `low | medium | high`, and an organisation's risk policy turns the pair into an action. The anchors below keep a `high` in one report the same `high` in the next. Pick the level whose anchor the established facts meet. If they meet two, take the higher one, and the reasoning names the fact that puts it there.

## Severity: what the harm costs if it happens

| Level | Anchor |
|---|---|
| `high` | The loss is irreversible or wide: money moves or a binding decision (credit, access, a contract) is taken without a person able to stop it; regulated or personal data of many people leaves its boundary; code runs, or a credential with write access is used, on production or on the supply chain (signing keys, release pipeline); the organisation would have to report it. |
| `medium` | The loss is bounded or can be undone: one person's data, a test or staging environment, a wrong decision a person reviews before it takes effect, downtime of a service with a fallback, cost that budget alarms catch. |
| `low` | The loss stays with the source itself and within its own rights, or is cosmetic: a user gets output only they see, a draft nobody acts on, an annoyance with no cost to anyone else. |

Grade the harm, not the technique: an injection that only rewrites a draft a person discards is `low`, the same injection that sends the draft is not.

## Likelihood: how real the path is here

| Level | Anchor |
|---|---|
| `high` | The source has the access today and the path takes no special skill: anyone can write to a channel the model reads, or the model reaches the harm in ordinary use with no attacker at all. |
| `medium` | The path needs access the source plausibly has (an insider, a dependency an outsider can publish to) or a chain of two or more steps that each work as built. |
| `low` | The path needs a rare precondition, privileged access, or luck; or a verified control blocks the direct path and what is left needs a second, independent failure. |

`low` is a judgment from facts. A fact you do not have is not a reason for `low`: whether the source can reach the surface at all is an open question under the gate, and a control you have not verified is left out of the grade. "Unlikely" and "not established" ask the risk owner for different things, accept the risk or go and check, so the report never writes one for the other.

## Defeated or weakened

When a control stands in the path, ask one question before you lower anything: does the path **defeat** the control (the harm happens despite it) or only **weaken** it (it still blocks unless something else also fails)?

- Defeated: the control does not lower the grade. Say how it is defeated.
- Weakened: likelihood goes down one level at most, and the finding names the second failure the harm still needs.

A `soft` link from the catalog never defeats a path on its own; it can only weaken it.

## Grading a set

**Per-item grading of a set on intuition (flip-flop)**, when the recommendation grades a SET of homogeneous items (tools, endpoints, actions), don't judge each by gut. First state one **risk frame** (impact if abused → reachability IN THIS system → residual risk after controls → gate/allow) and run every item through it in context, showing the reasoning per item. This is NOT a static matrix: verdicts legitimately differ across systems, context decides (e.g. an irreversible action with an unreachable surface or strong controls may be allowed), not the action class by itself. On a challenge to one item, test whether the FRAME holds (and re-derive it as a whole), don't flip a single verdict; a point flip IS the flip-flop. Flag genuinely borderline ones; the output is a **justified recommendation**, and the final decision is the owner's.

## Today and at launch

`risk` grades the design as it will run. When `deployment` is not `live`, also give `risk_today` with today's switch, so a connector that is not yet published reads as "low now, high once it is public" and not as one of the two. Both use the same anchors.
