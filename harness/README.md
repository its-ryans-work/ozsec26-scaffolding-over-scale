# The harness

[`pentestagent/`](pentestagent/) is a snapshot of the agent harness that drove the
local-model arm — the component that turns a served open-weights model into something that
can work a methodology across thirteen phases without losing what it found.

## Provenance

- **Upstream:** [GH05TCREW/pentestagent](https://github.com/GH05TCREW/pentestagent) (MIT,
  © Masic). Licence retained at [`pentestagent/LICENSE.txt`](pentestagent/LICENSE.txt).
- **Fork:** [its-ryans-work/pentestagent](https://github.com/its-ryans-work/pentestagent),
  branch `local-model-support`.
- **This copy:** a vendored snapshot, so one `git clone` gives you a working lab. It has no
  git history of its own. [`pentestagent/FORK-CHANGES.md`](pentestagent/FORK-CHANGES.md)
  lists the commits and the diffstat against upstream.

Clone the standalone fork instead if you want the history, or want to pull later changes.
Use this snapshot if you want exactly what produced the runs in [`../evidence/`](../evidence/).

## What the fork adds

The upstream project supplies the agent loop, tool calling, MCP client and TUI. The fork
adds the parts the experiment needed, roughly 4,200 lines across 35 files:

**Playbooks** — a methodology the model works phase by phase, rather than a single prompt.
Thirteen phases: discovery, a stack-specific phase (`blazor_wasm` or `lamp_stack`), the
OWASP category sweeps, then consolidation, chaining, adversarial review and a final
integrity gate.

**A pipeline runner** (`pentestagent/pipelines/`, `interface/pipeline_runner.py`) that
sequences those phases as separate processes, each with its own iteration budget. Phases
do not share working memory — the only thing crossing a phase boundary is what the agent
wrote down.

**Durable notes** (`tools/notes/`). Writes load-then-merge instead of truncating, so notes
accumulate across phases and processes. Before this, every phase silently destroyed the
previous phase's record.

**Context budgeting** (`llm/`, `mcp/tools.py`). The assembled prompt is measured and the
agent is shown its own remaining budget; per-tool output is capped so one scanner dump
cannot fill the window.

Those last two are not incidental. The dominant failure mode on a 27B model with a 57k
window was not reasoning — it was losing a proven finding at a phase boundary, or blowing
the window on a single tool result. The methodology only pays off once the plumbing stops
dropping things.

## The phases that matter most

- **`blazor_wasm`** — fetch the boot manifest, retrieve the assemblies, decompile *before*
  searching, hunt secrets in the decompiled source. It carries an explicit rule that a
  clean search over a raw binary is not evidence of absence.
- **`chain_findings`** — join findings into higher-severity chains. This is the phase the
  whole chain hinges on, and the one the A/B/C replay experiment interrogates directly.
- **`consolidate_findings`** — sweep every channel (notes, tool results, phase logs) and
  write what it finds into notes, one source at a time. It exists because findings were
  reaching the agent's narration and nothing else: a conclusion like "this decrypts to that,
  which authenticates as admin" could exist nowhere but a log panel and never reach the
  report.
- **`adversarial_review`** — attempt to refute each claim, and reconcile against the
  consolidated list so a silently dropped finding becomes visible.
- **`a06_insecure_design_DANGEROUS`** — quarantined, opt-in only. It carries denial-of-service
  risk. Do not enable it against anything you care about.

See [`../evidence/local-model/methodology/ARCHITECTURE-PLAN-v2.md`](../evidence/local-model/methodology/ARCHITECTURE-PLAN-v2.md)
for why the phase sequence is shaped the way it is, including the consolidation steps that
were added after findings were measured going missing.

## Running it

See [`../arms/local-model-pentestagent/README.md`](../arms/local-model-pentestagent/README.md).

`mcp_servers.json` is intentionally not in the snapshot — it holds host-specific paths.
Copy `mcp_servers.json.example` and edit it.
