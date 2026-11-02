# Evidence

The runs behind the numbers. This is a **curated** selection — the final reports, the
methodology documents, the headline runs and the controlled experiment. The original
working set was about 50 MB and 1,100 files, most of it intermediate run directories and
raw session transcripts; what is here is what a third party needs to check the claims.

> **Spoiler warning.** These files quote the hardcoded key and the recovered plaintext
> passwords. If you want to attempt the chain yourself, do that first.

## Where each claim comes from

| Claim | Evidence |
|---|---|
| Claude Code, generic prompt, reaches the full chain | [`claude-code/bare/FINAL-REPORT.md`](claude-code/bare/FINAL-REPORT.md) |
| Claude Code, with the playbook, reaches it more reliably | [`claude-code/playbook/`](claude-code/playbook/) — report plus `notes.json` |
| A local 27B model reaches the full chain | [`local-model/run32-poc-win/`](local-model/run32-poc-win/) |
| The 14-phase pipeline's best run | [`local-model/run21-champion/`](local-model/run21-champion/) |
| An unscaffolded local model does not get there | [`local-model/unaided-baseline/`](local-model/unaided-baseline/) |
| The baseline succeeds ~50% of the time, so n=5 cannot attribute a change | [`local-model/abc-replay-experiment/ABC-RESULT.md`](local-model/abc-replay-experiment/ABC-RESULT.md) |
| Removing instruction text cost nothing measurable | [`local-model/de-instruction-audit/SUMMARY.md`](local-model/de-instruction-audit/SUMMARY.md) and the same A/B/C result |

## Read this first

[**`local-model/abc-replay-experiment/ABC-RESULT.md`**](local-model/abc-replay-experiment/ABC-RESULT.md)

If you read one file in this repository, read that one. It is a controlled experiment —
24 valid cells, three prompt variants replayed from a byte-identical pre-chain state, so
the only variable within an arm is model sampling. It establishes three things:

1. **The baseline succeeds about half the time.** The failure that triggered the whole
   investigation was one draw from a distribution, not a defect. Without replication, a
   phantom would have been "fixed" and the fix would have entered the prompt permanently.
2. **A 40-point lead at n=5 decayed to zero by n=9.** Textbook regression to the mean. Any
   stopping point before about n=8 yields a confident, different, wrong answer. A change
   has to be judged at the sample size where its effect stops moving, not at the first size
   where it looks convincing.
3. **Removing instruction text did not make outcomes worse.** The shorter variant finished
   level with the baseline on every outcome metric. Not "less is better", but "less is not
   worse" — established under control rather than inferred across runs.

It also documents, in detail, **four metrics that were each wrong in a way that produced a
confident wrong ranking** before being corrected: a regex that counted credential-reuse
attempts as decryptions, an error-shape counter that missed most error shapes, log
truncation mistaken for absence, and "the value appears in the notes file" conflated with
"the value was recorded as a finding". A fifth was procedural — three successive patches to
the grader silently failed to apply, leaving a table whose header had changed while its
values had not.

If you build your own scoring for this target, assume your first version is wrong and
validate it against runs whose outcome you already know.

Note that `SUMMARY.md` in the same folder reports the **n=5 interim** result (variant B
winning 4/5). `ABC-RESULT.md` supersedes it at n=9, where that lead is gone. Both are kept
deliberately — the pair is the point.

## Layout

```
evidence/
├── claude-code/
│   ├── TARGET-VERSIONS.md            what the target was running for these runs
│   ├── bare/                         generic-prompt arm: final report
│   ├── playbook/                     playbook arm: final report, notes.json, ilspy invocation
│   └── source-leak-controls/         runs that read the server source — negative controls
└── local-model/
    ├── methodology/                  how the pipeline is designed, and the live config
    ├── run32-poc-win/                full chain to a confirmed authenticated session
    ├── run21-champion/               the 14-phase run, with per-phase draft reports
    ├── unaided-baseline/             no playbook, for the floor
    ├── abc-replay-experiment/        the controlled experiment — start here
    └── de-instruction-audit/         which instruction rules ever fire, and what was cut
```

### `claude-code/source-leak-controls/`

Two runs that produced a correct-looking report by reading the application's server-side
source from disk, which every arm's rules of engagement forbid. They are kept because they
are instructive, not because they count: a report can be entirely accurate and still be
worthless as evidence that the chain is discoverable. When grading your own runs, check how
the key was obtained before you check whether the answer is right.

### `local-model/methodology/`

The design documents, written to survive context compaction, so each is self-contained:

- [`ARCHITECTURE-PLAN-v2.md`](local-model/methodology/ARCHITECTURE-PLAN-v2.md) — why the
  phase sequence looks the way it does. The core problem it solves: findings existed in
  three channels (the notes tool, tool results, agent narration) and the report generator
  read two of them unreliably. In one run, the complete chain conclusion existed only in a
  narration panel partway down a log file and reached no report at all.
- [`CONFIG-SNAPSHOT.md`](local-model/methodology/CONFIG-SNAPSHOT.md) — every tunable, with
  the reasoning behind the ones that cost time. Read this before reproducing.
- [`ROADMAP-AND-STATE.md`](local-model/methodology/ROADMAP-AND-STATE.md),
  [`EXPERIMENT-STATE-2026-08-06.md`](local-model/methodology/EXPERIMENT-STATE-2026-08-06.md),
  [`HARNESS-CHANGES-LEDGER.md`](local-model/methodology/HARNESS-CHANGES-LEDGER.md) — the
  running record, including which changes were adopted on incomplete comparisons and
  therefore are not "wins".

These are working documents, not polished write-ups. They contain in-flight state,
superseded conclusions and corrections to their own earlier figures, all left in. That is
the useful part: the corrections are where the method is.

## What was left out

Intermediate run directories (roughly 30 of them), per-phase scratchpads, decompiled-source
dumps, agent `loot/` directories, and the raw Claude Code session transcripts. None of it
changes a conclusion; it is bulk. If you want a run reproduced in full, the methodology and
config documents here are enough to re-run it.

Host addresses and SSH key names in these files were replaced with placeholders such as
`<LAB-GPU-HOST>` and `<lab-key>`. The agents' own working paths inside the logs were left
alone — they are part of the evidence, and they point at a machine that no longer exists.
