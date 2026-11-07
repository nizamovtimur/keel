# Getting started: from clone to your first report

This page takes you from an empty folder to a signed-off assessment of one AI system. It uses the demo system "Halo" so you can follow it without a system of your own, then tells you what to prepare for yours.

## What you need

- **Python 3.11 or newer** and [uv](https://docs.astral.sh/uv/) (or plain `pip`).
- **Git**, with `user.name` and `user.email` set. The report records them as the assessor.
- **One coding agent that speaks MCP** (Model Context Protocol, the way an agent calls outside tools). Any agent in the table in step 2 works.
- **A description of the system** you want to assess. For the first run, the demo description is enough.

## 1. Get Keel and check it loads

```bash
git clone https://github.com/roselis-lab/keel.git
cd keel
uv sync
uv run keel validate
```

If your company mirrors Keel internally, clone the internal copy instead; [Adopt Keel in your company](adopt.md) explains how to set that up.

`keel validate` prints a list of warnings and ends with `Catalog is valid.` The warnings are unfinished catalog cards, such as a control with no acceptance criteria yet. They never fail the check. Errors do: a broken link between records or a value outside the fixed vocabularies ends with `Catalog invalid` and a non-zero exit code.

## 2. Open the folder in your agent

The repository carries the configuration each agent reads. Keel's MCP server runs over stdio as `python -m keel.mcp.server`, so the agent starts it itself and there is no server for you to run.

| Agent | MCP server config | Skills folder |
| --- | --- | --- |
| Claude Code | `.mcp.json` | `.claude/skills/` |
| Codex | `.codex/config.toml` (trusted projects only) | `.agents/skills/` |
| Cursor | `.cursor/mcp.json` | `.agents/skills/` |
| GitHub Copilot / VS Code | `.mcp.json` | `.agents/skills/` |
| OpenCode | `opencode.json` | `.agents/skills/` |
| Kilo Code | `.kilo/kilo.jsonc` | `.agents/skills/` |
| Gemini CLI | `.gemini/settings.json` | `.agents/skills/` |

Any other agent: point it at the same command, run from the repository root, and at `.agents/skills/`.

One thing to get right: the `python` the agent finds on its path has to be the one Keel is installed into. Activate the environment `uv sync` made (`.venv`) before you start the agent, or install with `pip install -e .` into the Python the agent uses. If the agent cannot see Keel's tools, this is almost always why.

## 3. Ask for the assessment

Open [`docs/demo/system-under-assessment.md`](demo/system-under-assessment.md), copy the Halo section and give it to the agent with:

> Assess the GenAI security of this system.

Here is what happens, in order.

**The agent looks for an earlier assessment.** Reports are kept per system. If one describes the same system, the agent proposes the match and waits for you to confirm. Then it works from that report: it assesses what changed in the architecture since that date and re-checks each earlier finding rather than copying it.

**It picks candidate threats and tests each one.** Every threat in the catalog carries a sentence saying when it does *not* apply. Take `T-TOOL-ABUSE`, a tool the agent holds changes or destroys state on the model's say-so. It does not apply when the tools only read, or when the model chooses neither the tool nor its arguments. Halo's `update_shipping_address` writes to the production database and the model fills in the arguments, so the threat stays live.

**It asks when a fact is missing.** If the description does not say whether the chat panel renders images from model output, the agent stops that line of analysis and asks you. It does not assume "no" to drop a threat, and it does not assume "yes" to keep one. This rule is the main thing that makes the report defensible, and it is also what decides how long the run takes.

**It checks controls against your deployment, not only the catalog.** For a live threat it reads the linked controls, and for each one asks whether it is in place in this system. A control your organisation has recorded an implementation for counts as in place; one without is a recommendation.

**It saves a draft report and gives you a link**, such as `http://127.0.0.1:8420/reports/halo/2026-11-07`. The file is `reports/halo/2026-11-07.yaml`. The agent writes it through Keel's tools, which reject a grade outside the scale or a control id that does not exist.

## 4. Review and sign off

```bash
uv run keel up      # starts the local UI in the background and prints its address
```

Open the link the agent gave you. Read each finding, correct the grades and wording where you disagree, and press **Finalize**. A final report is the dated record of that assessment. Editing it again drops it back to draft; assessing the system again starts a new report with a new date.

`uv run keel down` stops the UI.

## 5. Keep it and share it

The report is a file, so keeping it means committing it. Upstream Keel ignores `reports/` on purpose, so that findings never end up in a public pull request; in your company you decide where reports live. See [Where reports live](adopt.md#where-reports-live).

To show it to someone who does not run Keel, build the read-only site:

```bash
uv run keel site --out public --reports reports
```

Open `public/index.html` in a browser, or publish the folder with GitHub Pages or GitLab Pages: [Publish the read-only site](adopt.md#publish-the-read-only-site).

## Before you assess your own system

The run is as fast as the description is complete, because every gap is a question back to you. Write down four things first, the same four the demo description covers:

1. **The pieces.** The model and how it is called, every tool and what it can change, what it retrieves from, what it remembers between conversations, where the output goes and how it is rendered.
2. **Who can put text in.** Users, uploaded files, retrieved documents, other systems, other agents. Anything the model reads is a way in.
3. **What is worth protecting.** Data, money, actions with real consequences, people's time, reputation.
4. **What is already in place.** Sign-in, filters, caps, approvals, logging, and anything you know is missing.

Bring the person who knows the architecture. The accountable assessor can be the same person.

## Check yourself

The demo file has a second architecture: Halo on the plan for small customers. It answers questions only, the four tools are gone, it reads only the public help centre, keeps no note between conversations and runs one company per instance.

Is `T-TOOL-ABUSE` live for this version?

<details>
<summary>Answer</summary>

No. Its "does not apply when" sentence starts: the reachable tools have no operations with real consequences. With no tools at all, nothing the model says can change state, so the threat is ruled out. The report lists it under "ruled out" with that reason, so the next reviewer can see it was considered rather than missed.

If you said "it depends on the help centre", look again at what the threat is about: a *tool* acting on the model's say-so. What the model reads matters for other threats, such as poisoned retrieved content, but not for this one.
</details>

Next: [Reading a report](reading-a-report.md).
