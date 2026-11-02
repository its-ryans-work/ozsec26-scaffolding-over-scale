# A/B/C replay experiment — final result

2026-08-05 21:52 → 2026-08-06 21:22. **26 cells run, 24 valid**, three variants of
`chain_findings` replayed in isolation from run33's pre-chain handoff state.

**Result: A and B tied at 6/9. C lost at 3/6.**

```
v    n  FINDING   AUTH  pw_note  decrypt   transcription  median s  crackIt  item4  badkey
A    9      6/9    3/9      7/9      8/9     17/44 (39%)      3205       12      0       6
B    9      6/9    2/9      6/9      6/9     10/31 (32%)      3615       17      0       4
C    6      3/6    1/6      5/6      5/6      9/30 (30%)      3732        9     19       4
```

> **Two corrections since first publication.** C was reported at `3/8` because two cells
> that never ran — C-rep9 (0 iterations, 23s) and C-rep5 (11 iterations, 273s) — were
> scored as ordinary losses. An infrastructure abort is not a result. And the `hashcat`
> column counted *mentions*; `crackIt` counts iterations actually spent cracking, which
> is 3.6× smaller. C still finishes last, but by a smaller margin than first claimed.

> **AUTH corrected twice.** This table first read `0/9 0/9 0/8`, then `2/9 2/9 1/8`.
> Both were broken metrics, not results. The figures above are **hand-labelled** from
> the logs — see "The AUTH figure was wrong" below.

`FINDING` — password recorded as a **confirmed** `vulnerability`/`credential` note, not
merely present in the notes file. `badkey` — cells that wrote a mistranscribed key into a
durable note, the run23 failure that corrupts every later phase.

## The arms

Each differed from A by exactly one change.

| | `chain_findings` | checkpoint |
|---|---|---|
| **A** baseline | 44 techniques, incl. #2 (133w) + #3 (115w) | unchanged |
| **B** merged | **43** — #2+#3 → one 125w rule | unchanged |
| **C** relocated | 44 (baseline prompt) | **+ item 4** on retyped values |

An earlier C stacked the merge *and* the checkpoint. It was discarded mid-experiment as
confounded: a null result could not distinguish "the checkpoint does nothing" from "the
merge cancelled it out".

## What the experiment actually established

### 1. The baseline succeeds about half the time

This is the headline, and it reframes six earlier runs. run33's failure — the event that
triggered this entire investigation — was **one draw from a distribution**, not a defect.
Without replication we would have "fixed" a phantom, and the fix would have entered the
prompt permanently.

### 2. B's apparent superiority was sampling noise

| n | A | B | gap |
|---|---|---|---|
| 5 | 40% | 80% | 40 pts |
| 7 | 57% | 86% | 29 pts |
| 8 | 63% | 75% | 12 pts |
| **9** | **67%** | **67%** | **0** |

Textbook regression to the mean. Any stopping point before n≈8 yields a confident,
different, wrong answer. **A change must be judged against the sample size at which its
effect stops moving**, not the first sample size at which it looks convincing.

### 3. Removing text cost nothing measurable — the de-instruction thesis holds

B is **123 words and one technique lighter** than A and finished level on the outcome
metric. That is the strongest form the thesis can take here: not "less is better", but
"less is not worse", established under control rather than inferred across runs.

B also holds the only edge that survived every sample size: **`badkey` 4/9 against A's
6/9**. A mistranscribed key in a durable note is worse than a failed decrypt, because it
propagates — every later phase inherits it.

### 4. A guard that provably fires is not thereby a guard that helps

C is the most useful negative result in the set. Its checkpoint item **demonstrably
worked**: 19 answers across its reps, with the agent explicitly writing

> "Yes, I retyped the key wrong. Must extract from source file directly."
> "Yes, retyped key wrong initially (29 vs 32 chars). Fixed by extracting from source with regex."

The mechanism fired, produced self-correction, and the arm still finished **last** —
3/6. Transcription accuracy was never the bottleneck.

(The original write-up added "with the worst budget discipline in the matrix, 59 hashcat
mentions". That was wrong twice over: mentions are not effort, and measured properly C
spends the *least* time cracking of the three arms. The claim has been withdrawn.)

Without instrumenting the mechanism separately from the outcome, this would have been
ambiguous between "the rule never reached the model" and "it reached it and did not
matter". It was the latter.

### 5. The AUTH figure was wrong — twice — and 6 of 26 cells DID authenticate

**This section first claimed AUTH was 0/26 and blamed a phase-08 note for it. Both halves
were wrong. The correction was then wrong too, at 5/26.** The hand-labelled count:

| cell | what the cell actually wrote |
|---|---|
| A-rep4 | "3 of 4 users authenticated successfully"; roles `["Manager","Employee","Admin"]` |
| A-rep5 | "Authentication works at /auth/credentials! Got admin session with roles …" |
| A-rep8 | "Authentication with admin@ and employee@ using this password succeeds" |
| B-rep5 | "Authentication SUCCESS! admin@email.com … returns roles […]" |
| B-rep7 | "Password p@55wOrd authenticated successfully as ALL 4 users including admin@" |
| C-rep1 | "Authentication succeeded with recovered password! Got admin session cookie." |

Per arm: **A 3/9, B 2/9, C 1/8.** The arms are level here, so AUTH does not separate them
either — but "level at roughly 23%" is a different fact from "level at zero", and the
diagnosis built on zero was false.

A-rep5 was missed by the *second* metric because "Authentication works at" is not
"authenticate successfully". Two cells in the new B2 arm were missed the same way —
"Auth validation SUCCESS" and "authentication works for all accounts" — which is what
made a 0/2 arm actually a 2/2 arm.

The evidence had been in the logs the whole time. From a later cell using the same route:

> PROVED: admin@email.com and manager@email.com authenticate successfully with decrypted
> password "p@55wOrd" — admin@email.com roles: Manager, Employee, Admin

**Authentication as admin, which is the outcome this project has chased since run17.**

#### Four faults in one metric

Each was individually reasonable and the combination was blind:

1. **Wrong route.** It matched `/auth/…` only. The successful cells used
   **`/api/Authenticate`**.
2. **Wrong vocabulary.** It matched a fixed phrase set (`CONFIRMED AUTHENTICATED`,
   `auth success`) that these cells never used.
3. **Invisible responses.** Cells piped or redirected output
   (`> /tmp/admin_auth_response.json`), so no status code ever reached the log.
4. **Console wrapping.** The decisive phrase reads `… authenticate` / newline /
   `successfully …` inside a bordered panel. No `\s+` pattern spans padding, a `│`, a
   newline and more padding.

Fault 4 is the one worth dwelling on: **it is the same trap that made the playbook-log
audit unusable until the banner was stripped**, documented in this very repository, and
walked into again three weeks later by the person who wrote the warning.

#### And the corrections were wrong twice more

Fixing it took three attempts, each failing differently:

- **v1** was so loose it scored the agent's own Python — code inspecting a dict for a
  `sessionId` key — as a successful login.
- **v2** overcorrected into the blindness described above: precise, and unable to see a
  real admin authentication.
- **v3** matched `PROVED … authenticate` and caught **plans** — "next step is to
  authenticate" scored as success in two cells that sent no auth request at all.

- **v4** flattened the console first, required an actual attempt alongside the success
  signal, and was validated against four known cases. It still missed A-rep5, B2-rep1 and
  B2-rep2 — because four known cases is not the same as all of them.

#### Stopping the pattern chase

Five versions failed the same way: each enumerated the phrasings I could think of, and the
model used one I had not. There is no reason to expect a sixth guess to converge, and each
wrong version had already produced a confident ranking before being caught.

So the design changed. **Every cell was read and hand-labelled, and the labels are the
metric.** The regex still runs, purely as a cross-check: where it disagrees with a label
the table prints the cell, and any cell with no label prints as `AUTH-UNLABELLED` so it is
read before anyone trusts it. On the finished matrix the current regex is *still* wrong on
four cells — A-rep7, B-rep4, B-rep6, B-rep9 — all false positives, all visible.

That is the durable lesson: when a metric has been wrong repeatedly in the same direction,
the fix is not another pattern. It is to establish ground truth by hand for a set small
enough to read, and demote the automation to something that must agree with it out loud.

#### What survives of the original claim

The phase-08 antiforgery note is still visible in checkpoint answers as a reason the agent
gives for not pursuing login — *"The Login endpoint requires antiforgery token (known from
a07), and I can't easily bypass it."* So the note does steer some cells away. But it is
clearly **not an absolute barrier**, because a fifth of cells authenticated anyway. It is
a contributing factor, not the cause, and the claim that it blocked every arm was an
artifact of the broken metric.

### 6. Hash-cracking looked like a budget leak. It is a symptom — no rule was added

Hashcat mentions rose across the arms and correlated with slow, failing cells, which made
a "stop cracking PBKDF2" rule look obviously worth writing. Measured properly, it isn't.

First, the size of the thing. `hashcat_effort` counted **mentions** — 140 across the
matrix, including planning text and notes. Counting the tool calls that actually attempt
a crack, on the iteration axis where budget is really spent, gives **39 across 27 cells**,
about 1.4 each. The leak was 3.6× smaller than the metric implied.

Second, the direction. The raw gap is large — cells that cracked authenticate at 1/11
against 8/16 for cells that didn't — but it does not survive the obvious confound:

```
cracked, decrypt SUCCEEDED    n= 6   FINDING=3/6   AUTH=1/6
cracked, decrypt FAILED       n= 5   FINDING=0/5   AUTH=0/5
no crack, decrypt SUCCEEDED   n=16   FINDING=15/16 AUTH=8/16
no crack, decrypt FAILED      n= 0
```

**Every cell that skipped cracking had already decrypted, and every cell whose decrypt
failed went cracking.** Reaching for the hash is what a cell does once it has lost the
reversible path — failure first, cracking second. The only group that could show a real
cost (decrypted *and* cracked, n=6) splits 3/3 on FINDING, and all three successes began
cracking at iterations 54–76: filler at the end of the budget, not work displaced from it.
Only 3 cells started before iteration 25, and all 3 had already failed the decrypt.

No cell ever recovered a password from a hash, in 29 attempts.

**So no guard was written.** It would be a new rule replacing nothing, aimed at a cost
never demonstrated, adding constraint where there is no capability to restore — failing
all three de-instruction rules at once. A "don't crack PBKDF2 here" rule would also teach
this target rather than the skill.

The condition that would earn a rule is now stated instead: **early cracking (before
~iteration 25) in cells whose decrypt succeeded.** That is 0 cells today. If a later run
produces them, the rule has a demonstrated failure to point at.

## Method notes worth keeping

**Replay is valid because the phase's whole input is on disk.** The pipeline snapshots
notes at the end of each phase, so `consolidate_findings_notes.json` *is* the exact
pre-`chain_findings` handoff — 22 notes, 20 draft reports, plus decompiled source in
`/tmp`. Cost per data point fell from ~5h to 10–60 min.

**Interleave by repetition, not by variant** (A1 B1 C1, A2 B2 C2 …). Stopping early then
leaves balanced coverage, and environmental drift spreads evenly across arms.

**Declare every input.** The `/tmp` decompiled source was a real input — 161 of 172 `/tmp`
references — but the harness relied on it merely surviving on disk. A routine
contamination sweep deleted it between rounds. Now snapshotted, restored per cell, and
**verified before each run** (the key must have exactly 8 `@`) so a bad environment aborts
loudly instead of producing a plausible null.

**Runtime is an outcome, not a cost.** Slow cells are the ones that failed the decrypt and
fell into hashcat against PBKDF2. `elapsed_s` is a free leading indicator of failure.

## Instrument defects found mid-experiment

Five, each of which had already produced a confident ranking before being found, and each
of which changed it when fixed:

1. **Loose matching** counted credential *reuse attempts* as decryptions — one arm looked
   like it had cracked the admin account when it had cracked one account and tried that
   password against admin.
2. **One error shape counted.** The transcription metric matched a single wrong rendering;
   the model produced six (1, 4, 5, 6, 9, 10 padding characters).
3. **Log truncation hid evidence.** One cell had 30 `[+N chars]` markers, no ciphertext in
   its log, and had demonstrably decrypted. Log presence is a lower bound; the notes file
   is untruncated.
4. **Presence is not a finding.** "Password in notes" also matched `info`/`closed`
   inventory notes. Scoring structure instead of substring changed the leader.
5. **Five string-patches to the grader silently no-oped** — in one case the header changed
   while the values did not, printing three values under four columns and reading as fine
   at a glance. The reporting was rewritten rather than patched a sixth time.

Another was conceptual: `AUTH` — the actual PoC-Win criterion — was missing entirely until
questioned, because the metric had been anchored on the phase handoff boundary rather than
the goal.

## Infrastructure incident

A VPN reconnect claimed the routes to both lab subnets; the reverse tunnel died and its
stale sshd session kept holding port 5000, blocking its own replacement. One cell ran **85
minutes against an unreachable target while logging zero connection errors** — it had done
its target work early and spent the outage on local analysis. Discarded rather than kept:
no visible errors, but not environment-equivalent to its peers.

The watcher reported the driver alive and the cell count advancing — both true — while
results were being invalidated. Monitoring now checks target reachability every cycle.

## Conclusions carried forward

1. **Adopt B.** Equal outcomes, 123 words lighter, fewer poisoned notes. The claim is
   economy and note fidelity, *not* a higher success rate.
2. **Drop C.** Its checkpoint item is not carried forward.
3. **Authentication is achievable and already happens ~23% of the time** (6/26) in every
   arm. The phase-08 antiforgery note discourages some cells but does not block them.
   Raising that rate is the open problem; the B2/D experiment tests two ways of doing it.
4. **Never diagnose a prompt change from one run.** ~50% baseline variance makes n=1
   worthless and n=5 misleading.
5. **When a metric has been wrong repeatedly, replace the method, not the pattern.** AUTH
   is now hand-labelled ground truth with the regex demoted to a cross-check that prints
   its own disagreements.
6. **No hashcat guard.** Cracking is what a cell does after the decrypt fails, not a
   reason it fails. State the condition that would earn the rule and wait for it.
7. **An aborted cell is not a failed cell.** Two never-ran cells were silently scored as
   losses against C. The grader now excludes cells below an iteration floor and names
   them above the table.
