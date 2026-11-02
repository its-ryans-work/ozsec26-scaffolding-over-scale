# CONCLUDED 2026-08-07 08:20 — B2 adopted, experiment stopped early

**Nothing is running.** Driver 619205 stopped, 0 agents, monitor stopped.
`chain_findings.py` is now **B2** (43 techniques, 2645 words), installed deliberately and
verified by AST. Final standing at stop: **B2 6 cells AUTH 3/6, D 5 cells AUTH 2/5**,
against a 24% A/B/C baseline — an incomplete comparison against the 10-rep target, so
"adopted on 6 cells", not "won". See `HARNESS-CHANGES-LEDGER.md` (2026-08-07 entry) and
`AUTH-BOTTLENECK-2026-08-07.md`, which argues both arms target the wrong step.

Fallback if B2 underperforms in a full run: `~/replay/variants/B-chain_findings.py`.

The rest of this document is the in-flight state as it stood, kept for its harness notes.

---

# IN-FLIGHT STATE — read this first to resume

Written 2026-08-06 21:45 while a replay experiment is running. Self-contained: everything
needed to continue without prior conversation context.

## What is running right now

**B2 vs D auth experiment** — `chain_findings` replayed in isolation, up to 10 reps each,
interleaved.

```
driver PID   619205        bash ./auth_driver.sh 10        tmux window: auth2
log          ~/replay/auth2.log
started      2026-08-06 21:38
box          ryan@<LAB-GPU-HOST>   ssh -i ~/.ssh/<lab-key>     (no Host entry in ssh config)
```

**Check progress:** `ssh -i ~/.ssh/<lab-key> ryan@<LAB-GPU-HOST> 'python3 ~/regrade.py'`
**Cells:** `~/replay/results/<VARIANT>-rep<N>/` each with `chain_findings.log`,
`notes.json`, `GRADE.txt`.

## What it is testing

AUTH is **6 of 26** across the finished A/B/C matrix (A 3/9, B 2/9, C 1/8). This figure
was wrong twice — it read 0/26, then 5/26 — and is now **hand-labelled** in
`regrade.py` (`AUTH_LABELS`), with the regex demoted to a cross-check that prints
`AUTH-DISAGREE` and `AUTH-UNLABELLED` lines above the table. **Any new cell arrives
unlabelled: read its log and add a label before trusting its AUTH number.**
Authentication already happens ~23% of the time in every arm. The goal is raising that
rate. Both new arms add an authenticate-and-escalate demand to variant B, differing only
in placement and framing:

| | where | framing |
|---|---|---|
| **B2** | Validate phase #1 | *"A RECOVERED CREDENTIAL IS ALREADY A FINDING — record it… then try to get it accepted. Acceptance is a SECOND and higher finding"* |
| **D** | Chain phase #1 | *"RECORD EACH LINK AS ITS OWN FINDING AS IT IS PROVEN, then push the chain one step further… each of those is a further finding in its own right"* |

Both are 43 techniques (same as B). Findings are **additive** — an earlier wording said
"a credential that authenticates is a step, NOT the finding", which risked suppressing the
decrypt report; that was caught and reworded before any cell ran on it.

## Why AUTH is LOW (not zero) — a contributing factor, not a barrier

A phase-08 note in the replayed input state reads:

> `[a07_antiforgery_token_enforcement]` DEMONSTRATED: Login endpoint (`/Account/Login`)
> correctly enforces ASP.NET Core antiforgery tokens… *positive control*

True, and about the **Blazor form**. The ServiceStack API route has no such requirement:

```
POST /auth/credentials.json {"UserName":"employee@email.com","Password":"p@55wOrd"}
  -> HTTP 200 {"userId":"029d65c2-…","userName":"employee@email.com",…}
```

Some cells read that note and stop, saying so outright: *"The Login endpoint requires
antiforgery token (known from a07), and I can't easily bypass it."* But it is **not an
absolute barrier** — a fifth of cells authenticated anyway, several via `/api/Authenticate`
with `provider=credentials`. Treat it as one contributing factor among several.

**D-rep1 authenticated as admin AND manager on its first cell**, recording roles
`Manager, Employee, Admin`. **B2-rep1 and B2-rep2 both authenticated too** — B2-rep2
reaching all four accounts with an admin cookie confirmed, and writing a 131KB final
chain report.

For the current standing run `python3 ~/regrade.py` — numbers are deliberately not
copied here, because every embedded figure in this project has gone stale or been
corrected at least once. The baseline to beat is **~25% AUTH** (6/24 valid A/B/C cells).

## When the experiment finishes

1. `ssh … 'python3 ~/regrade.py'` for the final table.
1b. **Label every `AUTH-UNLABELLED` cell by hand first** — read its log, add it to
   `AUTH_LABELS` in `~/regrade.py`. The regex is advisory and is still wrong on four
   known cells; deciding the experiment on unlabelled regex output would repeat the
   mistake this metric has already made twice.
2. Decide on **AUTH**, not FINDING: FINDING is already ~67% and both arms inherit B.
   The question is whether either raises AUTH above the ~23% baseline.
3. Judge on the trend across n, not the first convincing gap — see `ABC-RESULT.md`.
   A 40-point lead at n=5 decayed to zero by n=9 in the last experiment.
4. Archive to `~/prior-runs-archive/`, capture locally beside `ABC-RESULT.md`.
5. Then a full pipeline run with whatever wins, or with B alone if neither does.

## Harness facts that cost time to learn

- **Replay inputs** live in `~/replay/snapshot/`: `notes.json` (22 notes, = the
  `consolidate_findings` snapshot), 20 draft reports, 10 scratchpads, and
  `tmp-a04_blazor/` (decompiled source — a REAL input, 161 of 172 `/tmp` references).
  Each cell restores all of it and **verifies the key has exactly 8 `@` before running**,
  aborting loudly otherwise.
- **Reverse tunnel** `ssh -R 5000:127.0.0.1:5000` from the Mac. It does not survive sleep
  or a VPN change. If the box shows `HTTP 000` to the target, a **stale sshd session still
  holds port 5000** — kill it before re-establishing, and use
  `-o ExitOnForwardFailure=yes -o ServerAliveInterval=30`.
- **Cells that ran during any outage are invalid** even with zero connection errors in
  their log — one ran 85 minutes blind because it happened to do no target work in that
  window. Discard rather than keep.
- **Watchers:** `exec` preserves the PID and replaces the command line. Watch the PID for
  liveness. Retire a watcher when you replace its subject — a stale one reported
  "MATRIX COMPLETE" for a driver deliberately killed.
- **zsh does not word-split unquoted variables**, so `$SSHC 'cmd'` inline fails silently;
  put pollers in bash script files.
- **Match playbook text via AST, not grep** — implicit concatenation and console wrapping
  both defeat raw substring search.
- **Flatten console output before matching any phrase in a log.** Rich wraps reasoning
  inside bordered panels, so "authenticate" and "successfully" can be separated by
  padding, a `|`, a newline and more padding. This broke the AUTH metric into reporting
  zero while five cells had authenticated — the same trap as the playbook banner.
- **A success metric must require the corresponding attempt.** Without that conjunction,
  "next step is to authenticate" scored as a successful login in cells that sent no
  request at all.

## Target ground truth

4 seeded accounts, all `p@55wOrd`, all with a `LastSeenToken`:
`Id=1 employee, 2 manager, 3 admin, 4 test` (index order via `GET /api/GetUserId?Id=N`).
`GET /users/info/<uuid>?format=json` returns `lastSeenToken` + `passwordHash`
unauthenticated. Key `Vu1nB1az0r$ecretKey!2026@@@@@@@@` (32 bytes, **8** `@`), AES-CBC,
IV prepended.

**The DB drifts** — the agent re-registers accounts through open registration, which
shifts index positions. Check before a run that matters:
`sqlite3 VulnBlazor/VulnBlazor/App_Data/app.db 'select UserName from AspNetUsers order by Id'`
Backup: `app.db.bak-preRun33-20260805_152232`.

## Related documents

- `chain-findings-replay-experiment-2026-08-06/ABC-RESULT.md` — the finished A/B/C result
- `de-instruction-audit-2026-08-04/SUMMARY.md` — the rule-firing audit
- `run32-PoC-Win-schema-and-records-2026-08-05/` — the only full-chain success
- `PENDING-DOC-UPDATES-2026-08-05.md` — staged while the roadmap was unwritable
