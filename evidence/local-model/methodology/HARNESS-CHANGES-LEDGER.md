# Harness changes ledger

Every modification made to PentestAgent during this work, why it exists, and how it was
verified. Written 2026-08-04 so the reasoning survives a context reset — several of these
look arbitrary without the failure that produced them.

All patches are idempotent and each modified file has a `.orig*` backup beside it on the
Kali box. Each phase runs as a fresh process, so an edit takes effect at the next **phase
boundary**, never mid-phase.

---

## Correctness fixes

### `notes/__init__.py` — writes truncated the notes file
`create`/`update`/`delete` mutated a module-level dict initialised `{}` at import and
wrote it in full, with no load in the write path. Every phase is a separate process, so
**the first note any phase wrote replaced the entire file**. Read helpers already loaded
lazily; only writes were unguarded.

Fixed with an explicit `_notes_loaded` flag and `_ensure_loaded_unlocked()` called before
any mutation. A flag rather than `if not _notes` because a falsy check cannot distinguish
"never loaded" from "loaded and genuinely empty", and would re-read disk after any
delete-to-empty.

Verified: three separate processes each writing one note; all three present.

### `cli.py` — `pentestagent run` ignored MCP entirely
The run path hard-set `mcp_manager = None`. `mcp test` reported 24 tools while the agent
received none. Now constructs a manager and merges its tools **only when
`mcp_servers.json` exists**, preserving the original "no automatic installs" intent, and
fails soft so an unreachable side tool degrades the run rather than ending it.

### `mcp/tools.py` — `_cap_mcp_output`, 12,000 chars
Built-in tools self-cap (the terminal tool at 50,000). MCP tools had no cap, so a single
scanner dump entered the prompt whole → requests of 109k–124k tokens against a 73,728
window. 50,000 was tried first and was still too generous: with four results held
verbatim that is most of the budget before prompt and history.

### `crew/tools.py` + `worker_pool.py` — worker results capped, full text to disk
`wait_for_agents` concatenated every worker's **full** response into one tool result
(status summaries beside it already used `[:200]`). Capped at 6,000 chars each; the full
text goes to `scratchpads/<phase>/<agent>.md` so nothing is destroyed. Write failures
return `""` — a scratchpad must never take down the run that produced the finding.

### `base_agent.py` — `_enforce_context_budget`
Per-item caps bound each contributor but not their sum, so totals drifted over the window
as history grew. Measures the assembled prompt and compacts tool contents oldest-first
until it fits. Configurable via `PENTESTAGENT_CONTEXT_BUDGET`.

**Shrinks, never drops.** OpenAI-compatible APIs require a `tool` message for every
`tool_call_id`; removing one turns a context overflow into a hard 400. Verified: 801k →
222k chars with all 40 tool messages and their pairings intact, system and assistant
turns untouched, newest tool result protected, and a 32k budget trimming harder.

---

## Visibility and instrumentation

### `base_agent.py` — `_todo_block`
Per-phase checklist seeded from the playbook's own phases, rendered into the session
ledger. The ledger is rebuilt from disk every turn, so the list survives summarisation
and the agent need not remember to re-read it — the failure mode of any checklist written
once and never reopened.

**KNOWN BUG:** emits a relative path; see ROADMAP-AND-STATE.md.

### `cli.py` — `_append_tool_scratchpad`
Every tool result appended to `scratchpads/<phase>/tool-log.md`. Older tool output is
compacted out of context (700 chars, and more once the budget enforcer runs), so a
command run at iteration 5 is largely gone by iteration 40. Deliberately separate from
notes: notes are curated findings, this is the raw record.

### `base_agent.py` — `_budget_line`
The iteration counter existed only in console output and a local of the run loop, so a
checkpoint asking "given the budget left…" was asking about a number the model could not
see. Now published onto the agent by the run loop and rendered in the checklist header
and checkpoint. Degrades to silence rather than a fabricated figure when unset.

### `cli.py` — command display
Was truncated at 80 chars **and** wrapped at 80 columns, because Rich falls back to 80
when stdout is not a TTY. Now 400 chars, multi-line rendering for heredocs, and
`escape()` so bracket patterns are not eaten as markup. Forcing a global console width
was tried and reverted — it widened every Panel border, which then wrapped. `soft_wrap`
on the specific lines is the correct fix and behaves identically at any width.

### `cli.py` — `_audit_report_against_notes`
Final deliverable compared against notes; any finding note whose **recovered values** are
absent gets appended to the report with the missing values named. Appending rather than
warning, because a console warning in a 6-hour run is read by nobody.

Matching on *recovered values*, not any shared token — the first version declared the
credential chain covered because the report named the AES key while omitting what the
chain proved. A chain note necessarily shares vocabulary with notes about its components.
Asset filenames are excluded (observed, not recovered). Entries ranked credential →
vulnerability → finding, capped at 10 with the remainder counted.

---

## Playbook changes (the behavioural ones)

| change | failure it addresses |
|---|---|
| record-when-proven, then **moved into the checkpoint** | a phase-scoped instruction only speaks inside that phase; the agent proved the decrypt mid-work and never recorded it, four runs running |
| "record successes with at least the care you give failures" | it wrote a note for a credential test that failed and none for the decrypt that succeeded |
| computed-not-stated key length | "assert the length is one the algorithm accepts" passed on a 24-byte value for a 32-byte key, because 24 is a legal AES size; the wrong number then propagated through notes |
| countable stop rule | "8-10 steps with no new evidence" never fired because each near-identical grep looked like a new step; now "count repetition by what the command does, not how it is spelled" |
| auth: establish what success looks like first | a rejection does not distinguish wrong credential from wrong request shape; without a known-good reference the only reading is "credential is bad", which discarded correct material twice |
| search before probing | the answer to "what does this request need" is usually already in notes, a published API description, or recovered source |
| observe the app performing the operation | 29 browser calls, none used to watch the application authenticate itself |
| scope after proving | proved on one account and stopped; "one account" and "every account including a privileged one" are different findings |
| quote the evidence, never cite it | the deliverable cited filenames instead of quoting the artefact, and the claim inflated in the gap |
| compounding / mitigating factors per finding | a chain had one home, so losing one phase lost it; and there was nowhere to write "authentication not demonstrated", so the untested step became part of the impact claim |
| verdict record written incrementally | adversarial_review reached 74/75 having named the file four times without writing it |
| start from the verdict record | the final gate spent 14 of 26 calls re-reading drafts review had already read |

---

## 2026-08-04 — de-instruction pass (31 techniques removed)

Full write-up: `de-instruction-audit-2026-08-04/SUMMARY.md`.

| Change | Why |
|---|---|
| removed 31 techniques across 9 playbooks (279 → 248, −12% of technique text) | each had ≥3 runs of exposure, sat in a phase that demonstrably ran, and left no trace in the agent's own output across 123 phase logs |
| kept the 51 "unreached" techniques | their phase never runs — every phase burns its full iteration budget, and engagement decays monotonically with phase position. Deleting them would remove rules never given a chance |
| kept the decompiler-install ladder (8 techniques) | dead only because `ilspycmd` is present on the box; the absent-decompiler test proved these work when the case arises |
| excluded `Emit the final deliverable` (6 techniques) from deletion | report-shaping rules leave their trace in the report, not the log — the deliverables show 17/15/21 `DEMONSTRATED` labels and the key quoted 15–17× |
| excluded everything with <3 runs of exposure (28 techniques) | a rule can only be judged over runs in which it existed; without this the list condemned the run26 and post-run28 fixes |

**Verification.** Deletion by AST source offsets, not text matching, with a checksum
guard refusing to patch a snapshot that differs from the box. Per file: re-parsed,
technique count asserted, every surviving technique asserted byte-identical. Then all
13 playbooks imported and registered on the box. Backups: `*.py.orig-preDeInstruct`.

**Two bugs in my own tooling, caught before they did damage.** The first cutter took
only the element's source span and then ate the following whitespace, which stole the
*next* element's indentation — valid Python, unreadable diffs. The first pass also
deleted `RUN THE CONTROL TEST` from `a05_injection` while six other playbooks kept it;
reverted, because a rule that fixed a known false positive should not be removed from
one playbook only.

---

## Recurring lessons

- **Anything deferred to the end of a phase is the first casualty of a budget cap.**
  Three separate losses had this shape. Durable output must be written as it becomes true.
- **A guard can read correctly and be inert.** Three were: a checkpoint asking about a
  budget not in the prompt, a report audit whose gap was upstream of it, and a stop rule
  whose trigger never matched. Assume a new guard does not work until something shows it
  firing.
- **Test the property that matters, not a plausible proxy.** "Is this a legal key size"
  passes on a wrong key.
- **Verify through the path you actually use.** `mcp test` passed while the run path had
  MCP disabled.
- **Cold starts must be verified, not assumed.** Contamination has invalidated a run
  before, and a verification run of mine contaminated the box afterwards.
- **The phase log contains the prompt, not just the agent.** Every log opens with a
  Rich panel printing the whole playbook verbatim — 105,754 words of a 292k corpus —
  and it is border-wrapped, so phrases break mid-sentence. Any analysis that greps the
  logs for instruction text matches everything before stripping the banner and nothing
  after wrapping. Scope the search to the owning playbook's own logs too; unscoped, the
  dead-rule rate reads 10%, scoped it reads 37%.
- **"Never fired" is not one thing.** It splits into *unreached* (the phase never
  runs), *precondition absent* (the case never arose), and *actually dead*. They need
  opposite fixes, and only the third is a deletion.
- **Judge a rule only over the runs in which it existed.** Recency makes the newest
  rules look deadest, so an uncorrected audit deletes precisely the fixes that were
  added for known failures.
- **Ask which channel a rule acts on.** A rule shaping the written report leaves its
  evidence in the report; looking for it in the log finds nothing and proves nothing.

---

## 2026-08-06 — replay experiment (see `chain-findings-replay-experiment-2026-08-06/`)

Full detail in `ABC-RESULT.md`; staged change log in `PENDING-DOC-UPDATES-2026-08-05.md`.

| Change | Why |
|---|---|
| adopt variant **B** — `chain_findings` #2+#3 merged into one 125w rule (44 -> 43 techniques) | tied the baseline at 6/9 over 9 reps each while being 123 words lighter, and wrote fewer mistranscribed keys into notes (badkey 4/9 vs 6/9) |
| **do not** adopt the checkpoint item on retyped values | it provably fired (19 answers over its reps, with the agent self-correcting in its own words) and still finished last at 3/6. A guard that fires is not a guard that helps |
| **do not** add a hash-cracking guard | cracking is a symptom of a failed decrypt, not a cause of failure: every cell that skipped it had already decrypted, and every cell whose decrypt failed went cracking. Measured effort is 39 iterations over 27 cells, 3.6× smaller than the mention count suggested, and no cell ever recovered a password from a hash in 29 attempts. The condition that *would* earn the rule is recorded instead: early cracking (< iter 25) in cells whose decrypt succeeded — 0 cells today |

## 2026-08-07 — B2 adopted, B2/D experiment stopped early

`chain_findings.py` is now **B2**: variant B plus one rule at technique #9 —
*"A RECOVERED CREDENTIAL IS ALREADY A FINDING — record it… then try to get it accepted.
Acceptance is a SECOND and higher finding."* 43 techniques, 2645 words. Verified by AST
and byte-identical to `~/replay/variants/B2-chain_findings.py`; all 20 playbooks import.
Backup: `chain_findings.py.bak-preB2adopt`.

**This was a call made on an incomplete comparison, and the record should say so.** The
B2/D experiment was stopped at 6 B2 cells and 5 D cells against a 10-rep target:

```
B2   6   FINDING 4/6   AUTH 3/6      A/B/C baseline AUTH: 6/25 (24%)
D    5   FINDING 2/5   AUTH 2/5
```

B2 leads, but n=6 is inside the range where this project has already watched a 40-point
gap decay to zero by n=9. The honest summary is *"B2 was adopted on 6 cells"*, not
*"B2 won"*. B remains the only variant with a completed, adequately-powered comparison
(9 reps per arm), and `~/replay/variants/B-chain_findings.py` is the fallback if B2
underperforms in a full pipeline run.

Also unresolved: `AUTH-BOTTLENECK-2026-08-07.md` found that both B2 and D target a step
that is not the bottleneck. 26 of 34 cells already recover the credential; they fail at
constructing the request. Whatever B2 buys, it is not aimed there.

### Grader changes 2026-08-07 (measurement only — no playbook text touched)

| Change | Why |
|---|---|
| `AUTH_LABELS` — hand-labelled ground truth, regex demoted to a cross-check printing `AUTH-DISAGREE` / `AUTH-UNLABELLED` | the AUTH pattern was wrong five times (0/26, then 5/26, actual 6/26). Enumerating vocabulary does not converge against a model that invents phrasing; the regex is *still* wrong on four cells and now says so instead of deciding the experiment |
| aborted cells excluded from variant aggregates below a 15-iteration floor, named above the table | C-rep9 ran 0 iterations in 23s and C-rep5 ran 11 in 273s; both were scored as ordinary losses, which reported C at 3/8 instead of 3/6. An infrastructure abort is not a result |
| `hashcat` column (mentions) replaced by `crackIt` (iterations spent cracking) | mentions counted planning text and notes — 140 across the matrix against 39 real cracking iterations, and it ranked C *worst* on a dimension where C is in fact best |

### New recurring lessons

- **Never diagnose a prompt change from one run.** The baseline succeeds ~50% of the
  time; a 40-point gap at n=5 decayed to zero by n=9. Judge a change at the sample size
  where its effect stops moving.
- **Interleave experiment cells by repetition, not by variant**, so stopping early leaves
  balanced coverage and environmental drift spreads evenly.
- **Declare every input a replay depends on.** A routine contamination sweep deleted the
  decompiled source the phase re-reads; cells 1-5 had only survived by luck.
- **Watch the PID for liveness and the command line for identity** — `exec` preserves one
  and replaces the other, and both directions produced false signals here. Retire a
  watcher when you replace its subject.
- **A metric must match the channel a behaviour writes to** — notes, log, or final
  artifact. Report-shaping rules leave no trace in the log and look inert.
- **"Present in notes" is not "recorded as a finding".** Scoring structure rather than
  substring changed the leader.
