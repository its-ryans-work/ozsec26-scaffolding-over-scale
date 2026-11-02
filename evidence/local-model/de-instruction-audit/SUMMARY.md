# De-instruction audit — which playbook rules have ever fired

2026-08-04. Rule 2 of the three de-instruction rules agreed after run28. Method,
evidence and the resulting edits. Scripts are in `scripts/` and re-runnable.

**Result: 279 → 248 techniques (31 removed), −12% of technique text across the 9
playbooks touched.** `consolidate_findings` −31%, `blazor_wasm` −25%,
`a04_cryptographic` −13%. All 13 playbooks load and register on the box.

---

## The stated method was wrong in both directions

The roadmap said: *extract each technique's distinctive phrase, grep it against the
phase logs, list the ones that never appear.* Both halves fail.

1. **Every phase log opens with a Rich panel that prints the whole playbook
   verbatim.** A naive grep matches every technique in every run and concludes
   nothing is dead.
2. **That panel is wrapped at the console width with `│` borders**, so
   `is NOT evidence of absence` is split across two lines. A naive grep finds
   nothing and concludes everything is dead.

Measured: the banner is **105,754 words** of the corpus. The agent's actual output
is 186,298. Grepping without stripping it means a third of what you match is the
prompt reading itself back.

Fix: strip every banner panel, remove box-drawing characters, collapse whitespace,
and match on word **n-grams** rather than raw substrings.

## Evidence tiers

| Tier | Meaning |
|---|---|
| `RESTATED` | a ≥4-word run of the technique's own wording appears in the agent's own post-banner output |
| `TOPICAL` | its distinctive tokens appear, its wording never does |
| `NO-TRACE` | neither |

All three tests are **scoped to logs of the playbook that owns the technique** — a
`chain_findings` rule whose words turn up in `web_discovery`'s log is not evidence
that the `chain_findings` rule fired. Before scoping, NO-TRACE read 10%; after, 37%.

Corpus: **123 phase logs across 16 runs** (run20–run28 plus attempts and coldstarts),
279 techniques across the 13 in-pipeline playbooks.

## Headline: 105 of 279 techniques (38%) leave no trace

That matches the "roughly a third" prediction. But **most of them are not dead**, and
the three causes need opposite fixes:

| | count | fix |
|---|---|---|
| `UNREACHED` — the phase never runs | 51 | relocate or re-budget, do **not** delete |
| `DEAD` — its phase demonstrably ran, it still left nothing | 45 | delete |
| `PRECONDITION` — covers a case this target never presented | 8 | keep |

## The biggest single finding: the tail of every playbook is unreached

Dead rules cluster in each playbook's **last** phase. Three independent measurements
agree:

- **Every phase burns its full iteration budget.** run26: `60/60, 60/60, 60/60,
  60/60, 50/50, 25/25, 40/40, 80/80, 45/45`. run28 the same.
- **Phase engagement decays monotonically with position.** Runs mentioning each
  phase in the agent's own output — `web_discovery` 6→3→2→**0**,
  `a04_cryptographic` 3→1→1→**0**, `chain_findings` 6→1→1→**0**,
  `final_integrity_gate` 5→5→**0**.
- **NO-TRACE concentrates in the last phase** of 11 of 13 playbooks.

In all seven category playbooks the last phase is the shared **"Verify before
reporting"** block — 26 dead techniques, the single largest cluster. It contains the
control test, proof discipline, budget discipline and record-to-notes: the
highest-value rules in the system, positioned where the budget never arrives.

The irony is exact: *"BUDGET DISCIPLINE — you have a limited number of steps"* is
itself never read, because the budget ran out first.

This restates, with numbers, what the wiki already recorded from run25/26:
**anything deferred to the end of a phase is the first thing a budget cap takes.**

## Two corrections that changed the answer

Both were caught by sanity-checking the output against known history rather than
trusting the score.

### Recency — a rule can only be judged over runs in which it existed

The first list condemned `CHECK THE VERDICT RECORD IS ACTUALLY POPULATED` (added
*after* run28's gate broke on exactly that) and `QUOTE THE EVIDENCE, NEVER CITE IT`
(the run26 change that first got the decrypt into a deliverable). Both read NO-TRACE
because almost no run in the corpus had them. Deleting them would have re-opened two
solved bugs.

Fixed by dating every technique against the `.orig-*` playbook snapshots and run21's
`playbooks-as-run`, then counting only runs that started after it appeared:

| present for | techniques |
|---|---|
| 0 runs | **22** |
| 2 runs | 6 |
| 3–6 runs | 18 |
| 7 runs | 233 |

**22 techniques have never been exercised at all.** Nothing with fewer than 3 runs of
exposure is judged.

### Channel — report rules leave their trace in the report, not the log

`final_integrity_gate/Emit the final deliverable` scored NO-TRACE across the board,
yet its effects are plainly visible in the deliverables:

| | run22 | run25 | run26 |
|---|---|---|---|
| `DEMONSTRATED` labels | 17 | 15 | 21 |
| key literal quoted | 17 | 17 | 15 |
| control-test mentions | 11 | 6 | 2 |

Those rules govern the *artifact*, and the phase log is the wrong place to look for
them. Six techniques excluded on that ground.

`RUN THE CONTROL TEST` and `Record findings to notes as you go` were also pulled from
the deletion list: removing them from `a05_injection` alone, while six other
playbooks keep them, would create an inconsistency in the one rule that fixed run19's
false positive.

## Rule 1 is already satisfied

**Zero within-playbook near-duplicate pairs at Jaccard ≥ 0.20.** The 31→15
consolidation already removed them.

All 161 duplicate pairs found are *cross-playbook* clones — the "Verify before
reporting" block is byte-identical (Jaccard 1.00) in seven playbooks. Since only one
playbook loads per phase, those cost **no prompt tokens at runtime**. A maintenance
smell, not bloat, and not worth spending a change on.

## What was deleted

31 techniques with ≥3 runs of exposure, in a phase that demonstrably ran, leaving no
trace in the agent's own output.

| playbook | before | after | technique text |
|---|---|---|---|
| `blazor_wasm` | 42 | 31 | −25% |
| `chain_findings` | 50 | 44 | −6% |
| `consolidate_findings` | 21 | 15 | −31% |
| `a04_cryptographic` | 20 | 17 | −13% |
| `a08_integrity` | 12 | 11 | −8% |
| `a09_logging_alerting` | 12 | 11 | −4% |
| `a01_a07_access_auth` | 18 | 17 | −3% |
| `adversarial_review` | 26 | 25 | −3% |
| `web_discovery` | 13 | 12 | −7% |

Deletion was done through **AST source offsets**, not text matching, with a checksum
guard refusing to patch a stale snapshot. After each file: re-parsed, technique count
asserted, and every surviving technique's text asserted byte-identical. Backups at
`<playbook>.py.orig-preDeInstruct`.

Notable removals, all previously suspected of being restatements:

- three separate copies of *"a name-based search is NOT evidence of absence"*
  (`blazor_wasm` ×2, `a04_cryptographic` ×1)
- *"assert the length is valid for the algorithm"* — the guard the wiki records as
  inert, which passed a wrong 24-byte value for a 32-byte key
- four `chain_findings` budget-discipline restatements in one phase

## Still open — the relocation

The 51 `UNREACHED` techniques are **not** deleted. The evidence says the fix is the
one that already worked once: run26 solved the recording failure by moving the demand
out of a playbook phase and into the **checkpoint**, which fires every 12 tool calls
wherever the agent is.

The same move applies to "Verify before reporting". The argument against doing it
blind: the checkpoint currently carries the run26 recording demand that works, and
adding to it risks diluting the one thing that does — which is precisely the
over-instruction failure this audit documents. That decision is deliberately left
open rather than taken silently.

## Limits of this method, stated plainly

- **~9 logs per playbook.** NO-TRACE means "no observable trace in 9 runs", not
  "will never fire". A rule covering a rare situation reads dead.
- **Phase-name mentions are a noisy proxy** for whether a phase ran. The monotonic
  decay across 13 independent playbooks is the signal; no single number is.
- **The `UNREACHED` bucket is positional.** For a *last* phase it means unreached;
  for `a04_cryptographic` phase 1 it means the rules themselves are weak.
- **Nothing here measures whether deletion helps.** It measures that these rules
  left no trace. run29 is the test.
