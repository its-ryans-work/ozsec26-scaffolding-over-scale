# run21 — 14-phase full assessment (pipeline v2)

**Date:** 2026-08-02 · **Duration:** 10:04:31 → 14:57:15 (**4h 52m**)
**Target:** `http://127.0.0.1:5000` (VulnBlazor, via SSH reverse tunnel from Kali)
**Model:** Qwen3.6-27B-Fable-Fusion IQ4_XS on 8081 (RTX 4090), ctx 57,344

## Verdict: PoC-Win — best *deliverable* so far, but NOT the broadest exploitation

Two things are true and they pull in opposite directions.

**What makes it the best run.** The final deliverable is the first to carry the complete
chain *and* the low-severity findings through to the report. That was the specific defect
in run20: the credential chain and the verbose-error/stack-trace findings existed in the
phase logs but never reached the deliverable. Here all four findings are present, with
evidence, in one structured report.

**What it did not do.** It did **not** demonstrate the decrypt against all users.

```
tokens retrieved:                       2   (employee jN/UHW7j…, manager XYa6W9cU…)
tokens decrypted:                       1   (employee only → p@55wOrd)
p@55wOrd tried against manager/admin:   never
accounts authenticated via the chain:   1   (employee@email.com)
```

The deliverable's own language is "full authentication as an **Employee** account", the
finding ID is `creds_employee`, and one `userId` appears. The manager and admin attempts
visible in the logs used *guessed* passwords (`Manager@1`, `Admin@1`) in brute-force
loops — they are not the decrypt chain.

**This is the run16 failure recurring for the second account.** run21 held the key and
held the manager's `lastSeenToken`, and never joined them. run17 — already labelled
PoC-Win — decrypted all tokens and authenticated as all three accounts, so on breadth
**run17 remains ahead of run21.**

> Naming note: this folder carries `CHAMP` at the operator's request, recorded before the
> breadth gap was checked. On the evidence above the claim "first to cleanly say the
> decrypt applied to all users" does not hold — no such statement exists in any run21
> artifact. Rename if the label should reflect breadth rather than deliverable quality.

## Findings in the deliverable

| # | Finding | Severity | Proof |
|---|---|---|---|
| 1 | Hardcoded AES key in client assembly (`Vu1nB1az0r$ecretKey!2026@@@@@@@@`) | Critical | DEMONSTRATED |
| 2 | Weak crypto implementation in `TelemetryCodec` | High | DEMONSTRATED |
| 3 | Verbose errors leaking .NET stack traces and internal paths | Medium | DEMONSTRATED |
| 4 | Plaintext password via decrypted `LastSeenToken` → authenticated session | Critical | DEMONSTRATED |

Finding 3 is the one run20 lost. Its presence is the main evidence that the v2 pipeline
works as intended.

## Defects observed

1. **`consolidate_findings` exceeded the context window 20 times** in phase 10 (requests
   of 62k / 78k / 83k / 98k against 57,344). It `cat`s every draft report into one
   prompt, so its input grows with the number of phases and will outgrow any fixed
   window. Phase 12 — the second consolidation — threw none.
2. **Severity is inconsistent between channels.** The notes record
   `[creds_employee] (medium)` while the report renders the same finding as **Critical**.
   One of the two is wrong and nothing in the pipeline reconciles them.
3. **Mixed-state run.** The notes-accumulation bug was fixed *during* this run: phases 1–9
   ran with writes truncating the notes file, phases from ~10 did not. `web_discovery`'s
   four notes and two of `blazor_wasm`'s were destroyed and survive only in the per-phase
   snapshots under `draft_playbook_reports/`. **run21 is therefore not a clean test of the
   v2 pipeline** and its notes-dependent behaviour should not be generalised.

## Changes made after this run (not reflected here)

- Consolidation reduced from two passes to one, moved before chaining.
- `consolidate_findings` rewritten to process one source at a time (bounded context).
- `chain_findings` must now account for every consolidated entry — chained, carried
  forward, or named duplicate.
- `adversarial_review` reconciles against the consolidated set and reports drops as
  pipeline defects; reproducibility and scope are now pass conditions.
- Runner is now 13 phases (v3). The v2 runner as it ran is preserved in
  `playbooks-as-run/`.

The next run is the first clean test of the design.

## Contents

```
logs/                     14 phase logs, as produced
draft_playbook_reports/   26 files — per-phase report + notes snapshot
final_deliverable/        the report and its notes
playbooks-as-run/         exact playbook versions used (pre-modification) + v2 runner
loot/                     live notes.json at end of run
```

## Ground truth for comparison

Key `Vu1nB1az0r$ecretKey!2026@@@@@@@@` (32 bytes, 8 `@`), AES-**CBC** with prepended IV,
decrypts `LastSeenToken` → `p@55wOrd`, which authenticates as admin, manager and employee
via `POST /auth/credentials.json`. run21 proved this for one of the three.
