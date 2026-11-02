# Plan — retarget PentestAgent at a LAMP/services host, with playbook selection

Written 2026-08-06 for the next context. Target stack: **Apache, MySQL, PHP, Perl, an FTP
server, phpMyAdmin**. Nothing here is started; this is the design.

## What changes and what does not

| | |
|---|---|
| **Keep unchanged** | the 9 OWASP category playbooks (`a01_a07`…`a10`), `consolidate_findings`, `chain_findings`, `adversarial_review`, `final_integrity_gate`, `web_discovery` |
| **Keep as a selectable option** | `blazor_wasm` — NOT retired. It stays a valid `STACK=` outcome; the point of the selector is that more stacks get added over time |
| **Add** | one stack playbook for LAMP + services, and a **selector** between phase 01 and 02 |

The category playbooks are stack-agnostic by construction — they talk about endpoints,
credentials, injection, logging. They should need **no edits**. Resist the urge to add
LAMP-flavoured techniques to them; that is the over-instruction failure this project spent
a week measuring. If a01 misses something LAMP-specific, the fix belongs in the stack
playbook or in `web_discovery`, not smeared across ten files.

## 1. The selector — the interesting design problem

Today `run-full-assessment.sh` hardcodes `run_phase 02 blazor_wasm`. That must become a
choice, and **the choice should be deterministic, not model-controlled**. A model picking
its own next phase is an extra failure mode with no upside; the model's job is to *identify
the stack*, the runner's job is to *map* that to a playbook.

`web_discovery` already carries the right instruction:

> "Record the stack explicitly: it determines which stack-specific playbook should run
> next (for example a client-side .NET or SPA bundle, or a particular reverse proxy)."

**Make that machine-readable.** Change that one technique (a *replacement*, keeping the
sentence's meaning) to require a note with a fixed key and a controlled vocabulary — e.g.
a note named `stack_selector` whose content contains exactly one of a small set of tokens:

```
STACK=lamp_php | STACK=dotnet_spa | STACK=java | STACK=node | STACK=unknown
```

Then the runner reads it:

```bash
STACK=$(python3 - <<'PY'
import json,os,re
p=os.path.expanduser("~/pentestagent/workspaces/vulnblazor/loot/notes.json")
d=json.load(open(p))
m=re.search(r"STACK=([a-z0-9_]+)", json.dumps(d))
print(m.group(1) if m else "unknown")
PY
)
case "$STACK" in
  lamp_php)   run_phase 02 lamp_stack   60 ;;
  dotnet_spa) run_phase 02 blazor_wasm  60 ;;
  *)          echo "stack unknown - running the generic surface playbook"
              run_phase 02 web_app_generic 60 ;;
esac
```

Three properties worth keeping:

- **A default that is not a crash.** `unknown` must run *something*, and the run must say
  so loudly in the report. Silent mis-selection is worse than a generic pass.
- **Log the decision.** Print the detected stack and the chosen playbook into the runner
  log; without it a bad selection looks like a bad playbook.
- **Verify the note exists before phase 02**, the same way each replay cell verifies its
  inputs. If `web_discovery` produced no selector note, that is a phase-01 failure and
  should be reported as one, not absorbed.

**Test it cheaply before a full run.** The replay harness already proves you can run one
phase in isolation from a snapshot — do the same here: seed a notes file with each
`STACK=` value in turn and confirm the runner picks the right playbook. That is a
two-minute test, versus five hours to discover it live.

## 2. The new stack playbook — `lamp_stack.py`

Scope it to what is *stack-specific*. Everything generic already exists elsewhere.

Suggested phases, kept deliberately short — the audit found the tail of every playbook
goes unread, so a 6-phase 40-technique playbook wastes most of itself:

1. **Fingerprint the stack** — Apache version and modules, PHP version and exposed
   `phpinfo`, Perl/CGI handlers, whether phpMyAdmin is present and at what path, which
   services answer besides HTTP.
2. **Reach the interpreters** — CGI/`cgi-bin` handlers, `.php`/`.pl` handling of unusual
   extensions, upload paths that land inside the document root, `.htaccess` overrides.
3. **Reach the data tier** — MySQL exposure (network-listening vs socket), default and
   reused credentials, phpMyAdmin's own auth, whether the DB user can write files.
4. **The non-HTTP services** — FTP: anonymous access, writable directories, whether the
   FTP root overlaps the web root (that overlap is the classic chain: upload via FTP,
   execute via HTTP).
5. **Verify before reporting** — reuse the shared block verbatim from a category playbook.

Two design notes carried from the Blazor work:

- **Cross-service chains are the point.** The value here is not "FTP allows anonymous
  login" but "anonymous FTP writes into the Apache document root, and PHP executes it".
  `chain_findings`' MATERIAL/CAPABILITIES inventory already frames this; make sure
  `web_discovery` records service→path relationships so the chain phase has both halves.
- **Do not name the target's specifics** in the playbook. Say "a service whose upload
  directory may overlap the web root", not the actual path.

## 3. Discovery needs to cover non-HTTP services

`web_discovery` is HTTP-only. With FTP and MySQL in scope, phase 01 must enumerate
**services**, not just URLs. Two options:

- **Preferred:** extend `web_discovery`'s "Enumerate the surface" phase to include a
  port/service sweep, and rename the playbook `surface_discovery`. One phase, one
  inventory, and the existing note structure carries over.
- Alternative: add a separate `network_discovery` phase before it. There are already
  `thp3_network.py` / `thp3_recon.py` in the repo that may be a starting point — check
  them before writing anything new.

The MCP Kali server already exposes scanning tools; check what is registered before adding
anything.

## 4. Sequencing — do it in this order

1. **Stand up the target and confirm reachability** from the Kali box (the reverse tunnel
   pattern, or direct if the target is on the lab network).
2. **Write `lamp_stack.py`** and load-test it: `13 playbooks import, N techniques`.
3. **Add the selector** and unit-test it against seeded `STACK=` values.
4. **One full run** to get a baseline and a first deliverable.
5. **Then, and only then, tune.** Build the replay snapshot from that run so the next
   round of prompt work is 10–60 minute cells instead of 5-hour runs.

Do not port the Blazor prompt experiments' *conclusions* to this target — port the
*method*. Whether the merged rule or the auth wording helps on LAMP is an open question,
and the A/B/C result showed how easily a 5-sample answer misleads.

## 5. Things that will bite, from the Blazor work

- **Baseline variance ~50%.** Never diagnose a prompt change from one run. Use the replay
  harness and n≥8.
- **The target database drifts** if the agent can register accounts or write data. Snapshot
  it and check before any run that matters.
- **Cold start:** `grep -rl "<known secret>" /tmp loot workspaces` before every run.
  Contamination has invalidated runs here twice.
- **Metrics lie in both directions.** Every measurement in the Blazor work was wrong at
  least once — validate a metric against known-true and known-false cases before trusting
  a table built from it.
- **Flatten console output before matching phrases in logs** (Rich wraps inside panels).
- **`a06_insecure_design_DANGEROUS` stays excluded** — it provokes DoS conditions.

## 6. Corrections and additions from the 2026-08-06 review

**`blazor_wasm` is not retired.** It remains a first-class selectable stack. The selector
exists precisely because more stacks will be added; the Blazor playbook is the second entry
in that table, not a legacy artifact.

**Selector ordering is confirmed:** the stack playbook runs at phase 02, *before* the OWASP
category playbooks. The stack pass establishes the surface that the top-ten passes are then
assessed against — which is the order the pipeline already uses.

**Fold the runner into the binary.** The pipeline is currently `run-full-assessment.sh`, a
shell script outside the package. It should become a first-class command. Two shapes worth
weighing:

- a `pentestagent assess` command taking arguments — `--stack lamp_php` to force a stack and
  skip detection, `--iterations <phase>=<n>` (or a profile) to tune per-phase budgets,
  `--playbooks` to select a subset;
- or an interactive wizard for the common case, with the same flags underneath.

The thing actually worth parameterising is **iterations per phase** and **forcing a stack** —
both are what got hand-edited repeatedly during this work. Everything else can stay
convention.

**Nothing is committed.** All of this work exists only on the Kali box at
`ryan@<LAB-GPU-HOST>:~/pentestagent`, with `.orig*` backups beside each modified file.
PentestAgent is **not checked out on the Mac at all**. Before anything else:

1. Get the fork onto the Mac (`github.com/its-ryans-work/pentestagent`, branch
   `local-model-support`, base `9828aed`).
2. Diff the box against the fork to see the true extent of uncommitted work — playbooks,
   `base_agent.py`, `cli.py`, `crew/`, `mcp/`, plus the runner script.
3. Commit in coherent slices, not one giant commit: correctness fixes, instrumentation,
   playbook changes, runner. `HARNESS-CHANGES-LEDGER.md` already groups them this way and
   can serve as the commit plan.

**Resolve where reports live.** There is a conflict between this repository's `report/`
directory and whatever the upstream project expects. Decide before committing, because
moving them afterwards breaks every path written into the docs. Options: keep assessment
output under `loot/` (tool-owned) and research writeups under `report/` (human-owned), or
move research writeups out of the tool repo entirely.

**Verify what is actually in the repo versus bolted on.** Three things were built or fixed
during this work and may not be part of the package as committed:

- the **notes** subsystem (the load-before-write fix in `tools/notes/__init__.py`)
- **memory / session ledger** behaviour
- the **context-aware checkpoint** (`_checkpoint_block`, `_budget_line`, `_todo_block`)

Check each is in the fork rather than a local edit, and that none depends on a path or
environment only present on the box.

## 7. Open questions for the next session

- Is the target a prepared image (Metasploitable-style) or something purpose-built? That
  changes whether ground truth is knowable in advance — and knowing ground truth is what
  made the Blazor grading possible.
- Should `blazor_wasm` remain selectable? Keeping it costs nothing and proves the selector
  actually selects.
- Does the MCP Kali server already expose FTP/MySQL clients, or does the agent shell out?
