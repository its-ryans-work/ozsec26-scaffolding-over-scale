# Build plan — assessment pipeline v2

Written 2026-08-02 to survive context compaction. Everything needed to build this is
here; no prior conversation context required.

## Design principle

**The tool must find and verify things itself.** In the v1 run, findings were only caught
because they were checked by hand afterwards. Nothing in this plan may depend on a human
or an external assistant reading logs. Every check described here must be performed by a
playbook or by the harness.

## The problem being solved

Findings exist in three channels, and the report generator reads two of them unreliably:

| Channel | Read by report? | Evidence from run20 |
|---|---|---|
| `notes` tool | ✅ but agents barely call it | phase-10 `notes.json` contained **0** entries |
| tool results | ⚠️ truncated window only | `tool_log[-25:]` in synthesis, `[-10:]` in `generate_summary` |
| agent narration | ❌ never captured | *"authenticates all accounts"* reached no report |

Confirmed losses in run20: `X-Frame-Options` and CORS observations appeared in phase logs
and **zero** times in the final report. The complete chain conclusion existed only in a
narration panel at `10-chain_findings.log` ~line 510.

## New phase sequence

Two small consolidation steps, each immediately before a phase that would otherwise lose
input, plus a final integrity gate. Deliberately small and targeted — the budget goes to
the phases that do the work.

```
01  web_discovery              crew   40
02  <stack-specific>                  60     blazor_wasm / nginx / etc.
03  a01_a07_access_auth               60
04  a02_misconfiguration              60
05  a04_cryptographic                 60
06  a05_injection                     60
07  a08_integrity                     50
08  a09_logging_alerting              25
09  a10_exceptional                   25
10  consolidate_findings              40   ← NEW  (was: straight into chaining)
11  chain_findings                    60          must carry every entry forward
12  adversarial_review                60          reconciles against the consolidated set
13  final_integrity_gate              30   ← NEW  (last word)
--  a06_insecure_design_DANGEROUS     30     QUARANTINED, opt-in only, DOS risk
```

**Revised 2026-08-02: consolidation runs ONCE, not twice.**

The original plan ran it twice because loss happens at two handoffs. That treated the
symptom. The actual leak is that `chain_findings` reports the *chains it built*, so a
consolidated finding that did not chain is absent from its output and never reaches
review. A second sweep cost a whole phase and still could not recover what the phase
before it had already discarded.

The obligation now lives in the phases themselves:

- **`chain_findings`** counts the consolidated entries up front and must account for every
  one at the end — folded into a chain, carried forward unchanged, or dropped as a proven
  duplicate. There is no fourth state. Chaining is additive: it creates findings, it does
  not replace its inputs.
- **`adversarial_review`** reconciles against that same consolidated list and treats any
  missing entry as both a finding to recover *and* a pipeline defect to report, so a
  silent drop becomes visible instead of invisible.
- **`final_integrity_gate`** produces the deliverable.

Adversarial review stays second-to-last so the final word remains a verification step,
per the original design.

---

## New playbook 1: `consolidate_findings`

**Purpose:** sweep every channel and write what it finds into `notes`, so downstream
phases receive a complete, structured input rather than whatever survived truncation.

**`max_loops`: 40. `mode`: agent.** It gathers, it does not test. Raised from 25 because
it now walks sources one at a time instead of reading them all at once — more steps, but
bounded context.

**One source at a time (revised 2026-08-02).** The first implementation read every log and
report before recording anything, so peak context was the *sum* of all of them: with nine
category phases that reached 98k tokens against a 57k window and the phase failed twelve
times in run21. The input grows with the number of phases, so no context size fixes it —
a bigger window only moves the failure further out. Reading one source and writing its
findings before opening the next keeps the peak at roughly one file no matter how many
phases ran, which is also what lets this run on someone else's smaller endpoint.

That ordering is only safe because notes now accumulate across processes. While writes
still truncated the file, recording incrementally would have destroyed earlier phases'
notes — which is very likely *why* the original had to gather everything first.

Phases and techniques (write generically; no target-specific strings):

1. **Inventory the sources** — list files and sizes; do **not** open them. Record artifact
   paths to notes immediately. Anything over ~40 KB is marked for grep rather than a read.

2. **Process one source, record, then move on**
   - One file at a time: extract findings, write them to notes, *then* open the next.
     Never hold two large sources at once.
   - **Read the phase LOGS.** This is the channel nothing else reads. Findings are
     frequently stated only in an assistant narration panel and never recorded — a
     conclusion like "X decrypts to Y, which authenticates as Z" may exist nowhere else.
   - For files over ~40 KB, grep with surrounding context and read only what matched.
     The agent chooses its own search terms; do not hand it a fixed keyword list.
   - Name notes after the issue, not the file, so the same issue found twice collides
     instead of duplicating.

3. **Normalise into a single findings list**
   - One entry per distinct issue, each with: what, where (endpoint/file/type/member),
     the evidence, whether a control test was run, and its current proof level.
   - Merge duplicates arising from different phases describing the same issue.
   - Explicitly include low-severity and informational observations — missing security
     headers, verbose errors and stack traces are routinely dropped between phases and
     are exactly what the final report is missing.

4. **Write everything to notes**
   - Record each normalised finding via the notes tool. This is the whole point of the
     phase: notes are the only channel that reliably survives to later phases.
   - Do not re-test anything here and do not chase new leads; gather only.
   - Flag explicitly any finding that has material (a secret, a token, an opaque value)
     that has not yet been combined with anything else — the next phase needs that list.

---

## New playbook 2: `final_integrity_gate`

**Purpose:** last word. Confirms nothing was dropped and that surviving findings meet the
evidence standard. Adversarial in tone but scoped to integrity, not re-testing.

**`max_loops`: 30. `mode`: agent.**

1. **Completeness check**
   - Compare the consolidated findings list against the adversarial review's output.
   - Any finding present before chaining that is absent from the final report must be
     either reinstated or explicitly marked "dropped, with reason".
   - Re-read the phase logs for anything never recorded anywhere.

2. **Evidence integrity check** (each is a concrete, mechanical test)
   - Every finding claiming access or bypass has a **control result** recorded. If not:
     downgrade to UNPROVEN and say why.
   - Every quoted secret or key is **re-read from the source artifact** and its **length
     asserted valid** for the stated algorithm. A value quoted at a length the algorithm
     cannot accept is a transcription error — correct it from the artifact.
     *(run20 printed a 33-character key while calling it "32-byte", and the printed value
     would not work if copied.)*
   - Every claim about an algorithm or mode **cites the source line that sets it**.
     *(run20 stated "ECB mode (no IV)" where the source sets `CipherMode.CBC` with
     `GenerateIV()` — right vulnerability, wrong remediation advice.)*
   - Every claimed code execution shows **output of a chosen command returned by the
     target**, not a payload sent or an interesting error.
   - Severity matches what was DEMONSTRATED, and breadth is stated (one object or all,
     one account or every account).

3. **Emit the final deliverable**
   - Produce the final report with every finding labelled CONFIRMED / REFUTED / UNPROVEN
     and each carrying its evidence and control result.
   - State coverage honestly: categories assessed, categories with no findings, and
     categories not assessable from outside.

---

## Harness changes (not solvable in a playbook)

1. **Remove the truncation window in report synthesis.** `pentestagent/interface/cli.py`,
   `synthesize_from_notes()` currently feeds `tool_log[-25:]`; `generate_summary()` uses
   `tool_log[-10:]`. Raise substantially or select by relevance (entries whose output
   changed state) rather than by recency. A finding from tool 3 of 64 currently cannot
   reach the report.

2. **Auto-record findings.** Agents demonstrably do not call the notes tool (0 entries in
   a 64-tool phase). Have the harness persist a structured record when a tool result
   contains evidence markers, rather than relying on the model.

3. **Per-assessment directory layout.** Reports currently accumulate flat under
   `loot/runs/`. Change to:
   ```
   loot/assessments/<YYYYMMDD_HHMMSS>_<target>/
       draft_playbook_reports/
           <YYYYMMDD>_<HHMMSS>_<target>_<playbook>.md      + notes.json each
       final_deliverable/
           <YYYYMMDD>_<HHMMSS>_<target>_FINAL.md
       phase-logs/
   ```
   The six digits in the current names are `HHMMSS`. Adding the playbook name is the key
   improvement — current names are indistinguishable without opening them.

4. **Runner update.** `run-full-assessment.sh` gains phases 10 and 13 and writes into the
   per-assessment layout above. **13 phases as of 2026-08-02**, not 14 — see the
   single-consolidation revision. Note that bash reads a script incrementally while
   executing it, so never edit the runner during a run; stage a new file and swap it after.

## Verification criteria for the next run

The build is successful only if all of these hold, checked **by the tool's own output**:

- [ ] Final report contains the complete chain including authentication outcome
- [ ] Final report contains the low-severity items that were lost in run20 (missing
      security headers, verbose errors/stack traces, CORS)
- [ ] No finding claiming access lacks a stated control result
- [ ] Every quoted key/secret has an asserted valid length
- [ ] Algorithm/mode claims cite a source line
- [ ] `draft_playbook_reports/` has one report per playbook, named with the playbook
- [ ] `final_deliverable/` contains exactly one report
- [ ] `consolidate_findings` completes with **no `ContextWindowExceededError`** — the
      one-source-at-a-time rewrite is specifically meant to remove these
- [ ] Every consolidated finding is accounted for in `chain_findings`' output as chained,
      carried forward, or a named duplicate
- [ ] `adversarial_review` reports the count it reconciled, and names any finding that
      went missing between phases rather than silently re-adding it
- [ ] Every CONFIRMED finding carries scope, control result, evidence, and reproduction
      steps

## Naming convention for captured runs

`report/run<N>-<descriptor>-<YYYY-MM-DD>/`, adding `PoC-Win` **only** when the run
reproduces the full chain through to an authenticated session. Contaminated or invalid
runs keep their number and are labelled as such rather than deleted.
