# Replay experiment — which prompt change actually fixes the decrypt?

2026-08-05 21:52 → 2026-08-06 11:00. **15 cells, 3 variants × 5 reps**, replaying
`chain_findings` alone from run33's pre-chain state. ~13 hours of machine time to answer a
question that would have cost 75 hours as full runs.

**Winner: B — the merged, shorter rule. 4/5 against 2/5 for both alternatives.**

## Why replay rather than full runs

`chain_findings` is a separate process whose whole input is on disk. run33 snapshots notes
at the end of every phase, so `consolidate_findings_notes.json` **is** the exact
pre-`chain_findings` handoff — 22 notes, 20 draft reports, plus the decompiled source in
`/tmp`. Every cell restores byte-identical inputs, so the only variable within an arm is
model sampling.

That mattered more than expected: **the baseline succeeds about half the time.** run33's
failure, which started this whole investigation, was one draw from a distribution — not a
deterministic defect. Without reps we would have "fixed" a phantom.

## The three arms

Each differs from A by exactly one thing.

| | `chain_findings` | checkpoint |
|---|---|---|
| **A** baseline | 44 techniques, incl. #2 (133w) + #3 (115w) | unchanged |
| **B** merged | **43** — #2+#3 → one 125w rule | unchanged |
| **C** relocated | 44 (baseline prompt) | **+ item 4** on retyped values |

An earlier C stacked the merge *and* the checkpoint; it was discarded mid-experiment as
confounded, because a null result could not distinguish "checkpoint does nothing" from
"merge cancelled it out".

## Results

```
v    n  FINDING  pw_note  decrypt   transcription  median s  hashcat  item4  badkey
A    5      2/5      3/5      4/5     10/28 (36%)      3831       21      0       3
B    5      4/5      4/5      4/5      5/19 (26%)      3615       17      0       1
C    5      2/5      3/5      3/5      6/17 (35%)      2347       52     10       3
```

`FINDING` = the password recorded as a **confirmed vulnerability/credential note**, not
merely present somewhere in the notes file. `badkey` = a mistranscribed key written into a
durable note, which is the run23 failure that corrupted every downstream phase.

**B leads on every outcome metric and has the fewest poisoned notes.** Its single failure
(rep1) was upstream — it never obtained a token at all, so its rule never got to apply.

## The result is on-thesis

B is the only arm that **removed** text: 44 → 43 techniques, 248 → 125 words. It won.
That is the de-instruction thesis holding up under a controlled test rather than
inference from run-to-run comparison.

## The negative result on C is worth as much

C's checkpoint **demonstrably fired** — 10 item-4 answers across 5 reps, 12 self-
corrections, with the agent explicitly saying *"Yes, I retyped the key wrong. Must extract
from source file directly"* and then re-extracting with regex. The mechanism worked
exactly as designed.

**And it did not improve outcomes.** C finished level with baseline at 2/5, with the worst
budget discipline in the matrix (52 hashcat mentions, driven by one rep that spent its
whole phase cracking PBKDF2). So:

> A guard that provably fires is not thereby a guard that helps.

Transcription accuracy was never the bottleneck. C fixed the thing it aimed at and the
runs still failed, because failures came from elsewhere — never obtaining a token,
declaring completion early (C-rep5 stopped at iteration 13/80 with 6 tool calls), or
falling into the hash-cracking dead end.

## Honest limits

- **4/5 vs 2/5 at n=5 is a lead, not proof.** Under a null of equal ~53% success,
  P(B ≥ 4/5) is roughly 0.25. B beats both alternatives by the same margin and wins on
  `badkey` too, which is why it is the pick — but one or two cells would move it.
- Cells are unpaired. Matched seeds would have given far more power per run; no seed is
  plumbed through litellm today, and `top_k` is 40 against Qwen's recommended 20. Both are
  worth fixing before the next experiment.
- Runtime is an outcome, not a cost: slow cells are the ones that failed the decrypt and
  fell back to hashcat.

## Measurement errors found and fixed mid-experiment

Four, each of which had flattered the wrong arm:

1. `accounts_decrypted` matched account names near the password, so **credential-reuse
   attempts counted as decryptions**. C looked like it had cracked admin when it had
   decrypted one token and tried that password against admin.
2. `key_6at` counted only one error shape. The model produces many — 1, 4, 5, 6, 9, 10 `@`
   all observed — so most errors went uncounted.
3. **Log truncation hid evidence.** C-rep1 has 30 `[+N chars]` markers and no ciphertext
   in its log, yet decrypted. Log presence is a lower bound; `notes.json` is untruncated.
4. **"Password in notes" is not "recorded as a finding."** C-rep2 logged it only inside an
   `info`/`closed` inventory note. Correcting this dropped C from 3/3 to 2/3 at the time
   and changed the ranking.

A fifth was procedural: three successive string-patches to the grader silently failed to
apply, leaving a table whose header had changed while its values had not. The reporting
was rewritten from scratch. **A checker whose patch silently no-ops reports confidently
and wrongly** — the same lesson this project keeps producing about the agent, applied to
its own instrumentation.

## Applied

Variant B is now the live configuration: `chain_findings` at 43 techniques, `base_agent`
checkpoint unchanged (C's item 4 dropped). Full pipeline back to 247 techniques.

Artifacts: `~/replay/` on the Kali box — `snapshot/` (the replayable input state),
`variants/`, `results/<cell>/` with log, notes and grade, `regrade.json`, `matrix2.log`.
Harness scripts in `scripts/`.
