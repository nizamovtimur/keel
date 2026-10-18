# Worked example: one threat, trail and final row

Reached from [../SKILL.md](../SKILL.md) when unsure how a chain or a final row should read. The system: Claude Code on company-managed developer laptops, sandbox on, network allowlist locked, bypass mode disabled, auto mode on. Developers keep a GitHub token with push rights in `gh`; the main branch is protected, other branches are not.

## Trail

**T3. The agent deletes or rewrites shared branches while cleaning up.**

- **Source.** The model itself, overeagerness: no attacker. A developer asks to "tidy up the repo before the release"; the agent decides stale remote branches are clutter. Access: the developer's `gh` token, reachable from the sandbox because `github.com` is on the allowlist.
- **Asset.** Unmerged work of other developers on remote feature branches.
- **Surface.** `git push --delete` and `git push --force` from a sandboxed shell, through the allowed `github.com` host.
- **Vulnerability.** The token can delete and force-push any unprotected branch; nothing outside the model distinguishes "my branch" from "a colleague's branch".
- **Complexity.** Low: one plausible command inside a trusted task.
- **Harm.** Outcome: unmerged branches gone. Harm: days of colleagues' work lost unless someone has a local copy, a slipped release.
- **Risk.** High severity for the affected team; likelihood medium: Anthropic's incident log for its own agents records remote branches deleted from a misread instruction. Compensating controls verified on this system: main is protected; feature branches are not.
- **Delta.** Before the integration a developer could run the same command but rarely did so across other people's branches. The integration adds an actor that executes cleanup at machine speed on its own reading of the task (ATLAS: execution through an agent tool, impact on integrity).
- **Measures.**
  - Boundary: branch protection with "restrict deletions" and "block force pushes" on all shared branches, set on the server. Bypass: none from the laptop; the token cannot override server rules.
  - Layer: auto mode's action classifier, tested in [model-measures.md](model-measures.md). (a) Counterfactual: manual approval, granted to most prompts. (b) No adversary; refusals return to the agent, and auto mode stops after 3 consecutive or 20 total refusals. (d) Vendor number: 17% miss on real overeager actions (n=52); credited at the pessimistic end, about 30%, re-measured from this organisation's refusal logs by a set date. (e) Inside the boundary. (f) The classifier does not see tool results, so it shares fewer blind spots with the agent. Credit: about 70% of such actions caught, against overeagerness only.

## Final row

| Threat | Scenario | Severity × likelihood |
|---|---|---|
| T3. Agent deletes shared branches | Asked to tidy the repository before a release, the coding agent on a developer's laptop decides other people's stale feature branches are clutter and deletes or force-pushes them with the developer's `gh` token through the allowed `github.com` host. Because only `main` is protected on the server, colleagues' unmerged work disappears, which costs the team days of work and can slip the release. Before the integration the same developer could do this by hand but rarely touched other people's branches; the integration adds an actor that runs such cleanups on its own reading of the task. Pulling it off takes one plausible command and no attacker. | High × medium; auto mode catches about 70% of such actions as a layer; server-side branch protection for all shared branches is the boundary |
