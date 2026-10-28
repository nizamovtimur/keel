# Crediting a model-based measure

Reached from step 11 of [../SKILL.md](../SKILL.md) when a model-based measure is proposed, credited, or about to be banned: safety training or alignment of the acting model, a prompt instruction, an action classifier, a guardrail filter, a monitor model.

A model-based measure is a *layer*, never a *boundary*. Ask the questions below for each pair of measure and source of harm (step 3). A "no" before (f) means zero credit against that source; the boundary for it is built outside the model.

## The test

**(a) Counterfactual.** First: can an architectural restriction remove this class of decision altogether (no production credentials, no write access)? If so, that restriction is the measure and the model-based one is optional. For the decisions that remain, name what stands in its place if it is removed: a human who approves most prompts and tires, bypass mode, nothing, an unsanctioned tool. Compare against that, using this organisation's own approval and bypass data where it exists. An ideal boundary is the wrong comparison.

**(b) Pressure.** Does anyone *adapt* against it: an attacker, the model's own goal, training that uses it as a signal, or the agent itself when a refusal is returned and it tries another path? An attacker adapts whenever it can test against this measure or a surrogate: a public product, open weights, a model the attack transfers from. Against injection that covers nearly every deployed classifier, so mass and targeted injection are treated alike unless the measure is private and its outputs are unobservable to the attacker. Overeagerness and honest mistakes have no adversary; if refusals feed back into the session, credit only a miss rate measured with the retries included, or a hard retry cap that ends the session. With no adaptation, go to (d).

**(c) Holding under pressure.** One of two must hold. Either its rate was measured under adaptive attack of this class, including attacks on the measure itself (injection into the monitor, best-of-n resampling). Or both: whoever fixes the measure sees its uses across every system that deploys it, and in each system harm needs a long session that outlasts the fix. The second branch needs published evidence of the response loop (red-team or contest results, time from found bypass to fix) and this system's own logging and alerting on refusals. A found bypass transfers to every system with the same measure: the attacker pays discovery once, and each system faces one attempt. If each system sees only itself, or harm follows the first success, credit is zero. A static-benchmark score answers neither branch.

**(d) Measurement.** Miss and false-positive rates with sample size, on traffic like this system's, for the current model and measure versions. A vendor's number on its own traffic is credited only against sources with no adversary, at the pessimistic end of its interval, with a date by which this system's logs re-measure it; past that date the credit is zero.

**(e) Position.** Inside an architectural boundary, as detection. Never the boundary for an irreversible action or an outbound channel.

**(f) Independence.** Does it see different input from the actor, is it a different model, can the actor's text address it? With shared blind spots its catch rate is not multiplied with other model-based layers.

## How credit enters the assessment

- A credited layer lowers likelihood (step 9) for its source by its measured catch rate, stated with its interval. Risk stays above zero, and the boundary is still required.
- Its false positives are priced like any requirement at step 11: a refusal that pushes people to bypass mode or a personal tool is a gap with the bypass named.
- Safety training and alignment of the acting model usually enter as evidence of how often a source fires (system cards, incident logs, published miss rates), and only when that rate is measured.
- Record the answers to (a) to (f) in the analysis trail with their evidence, so a reviewer can dispute a credited layer question by question.

Done when every model-based measure in the assessment has either a recorded credit with answers (a) to (f), or zero credit with the question that zeroed it.

Violation: crediting a guardrail by its score on a static benchmark.
