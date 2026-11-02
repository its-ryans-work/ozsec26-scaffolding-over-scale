# Roadmap and current state

Written 2026-08-02, updated 2026-08-04. Self-contained: everything needed to continue
without prior conversation context. Companions: `ARCHITECTURE-PLAN-v2.md` (pipeline
design) and `run26-record-and-auth-2026-08-04/CONFIG-SNAPSHOT.md` (every tunable, both
llama.cpp quadlets, and the reasoning behind settings that cost time to learn).

---

> **2026-08-06 — READ `EXPERIMENT-STATE-2026-08-06.md` FIRST.** A replay experiment is
> in flight (B2 vs D, driver PID 619205 on the Kali box). That file is self-contained and
> supersedes the "run30 is in flight" text below.
>
> Since then: run32 was a **PoC-Win** (full chain to a confirmed authenticated session,
> employee account only); run33 achieved 4-account enumeration but lost the chain to a
> two-character key transcription error; the **A/B/C replay experiment** (26 cells) found
> the baseline succeeds ~50% of the time, so no single run can attribute a prompt change.
> Details in `chain-findings-replay-experiment-2026-08-06/ABC-RESULT.md` and
> `PENDING-DOC-UPDATES-2026-08-05.md`.

## STATE AS OF 2026-08-04 — read this first

**run29 is in flight**, launched 2026-08-04 20:48, assessment id
`20260804_204847_http_127.0.0.1_5000`. tmux session `pentestagent`, window `run29`;
runner log `~/run29-deinstruct.log`, phase logs
`~/pentestagent/assessment-20260804_204847/`. Roughly 6 hours.

**What run29 tests: the de-instruction pass, and nothing else.** 279 → 248 techniques
(−12% of technique text) plus the still-untested 31 → 15 `chain_findings`
consolidation. The relocation was deliberately held back to run30 so this result is
attributable — see the audit section below.

Pre-flight done and recorded, because a missed cold start invalidated run18:
`/tmp/blazor-source/` still held run28's **decompiled source containing the key**,
along with `workspaces/vulnblazor/loot/notes.json` (14 entries) and run28's draft
reports and deliverable. All archived to `~/prior-runs-archive/run28-final/` (13 MB,
file-count parity asserted before anything was removed), then cleared. Final check
`grep -rl "p@55wOrd\|Vu1nB1az0r" /tmp loot workspaces` → **clean**. Target HTTP 200,
model HTTP 200, 248 techniques staged.

**run28 had never been captured** — it is now in `~/prior-runs-archive/run28-final/`
with phase logs, reports, notes.json, the runner log, 58 screenshots and
`playbooks-as-run/` (the pre-de-instruction backups).

### RESOLVED — the `/root` path bug (fixed 2026-08-04)

The session ledger advertised relative paths and the agent resolved them against a
guessed home directory, prefixing `/root/` and escalating to `sudo cat` — 44 failed
reads and zero successful ones in run27 phase 11. Fixed with `.resolve()` in
`base_agent._todo_block()` (checklist path and TOOL LOG hint) and
`worker_pool._write_worker_scratchpad()`.

### NEXT TASK ON RESUME — de-instruct the playbooks (3 rules, agreed 2026-08-04)

The working hypothesis, now evidenced: **the playbooks are over-instructed, and the
growth caused regressions.** `chain_findings` went 3,600 → 6,950 tokens between run26
and run28; run26 is still the high-water mark and both later runs regressed. ~20
techniques were added in that window and none removed.

Apply in order:

1. **Every new rule replaces one, or it does not go in.** DONE, and now measured:
   **zero within-playbook near-duplicate pairs remain** (Jaccard ≥ 0.20). The 31 → 15
   `chain_findings` consolidation already removed them. All 161 duplicate pairs that
   exist are *cross-playbook* clones of the shared "Verify before reporting" block
   (Jaccard 1.00 across 7 playbooks) — and since only one playbook loads per phase,
   those cost **no prompt tokens at runtime**. Not worth a change.
2. **Delete rules that have never fired.** DONE 2026-08-04 — full write-up in
   `de-instruction-audit-2026-08-04/SUMMARY.md`, scripts and outputs beside it.
   **279 → 248 techniques, −12% of technique text.** See the section below; the
   method in the original plan would have been wrong in both directions.
3. **Prefer restoring capability over adding constraint.** The three worst changes were
   removals dressed as improvements: forbidding the gate's fallback, per-phase model
   routing, and narrowing the gate's inputs. The additions that worked (checkpoint
   recording, absolute paths) gave the agent something it lacked.
   **The audit's main finding is an instance of this** — see "the tail is unreached".

### THE AUDIT RESULT — 2026-08-04

**Do not grep the phase logs naively.** Every log opens with a Rich panel printing
the whole playbook verbatim (105,754 words of the 292k corpus), and that panel is
wrapped with `│` borders so phrases break mid-sentence. Grepping without stripping it
matches everything; grepping the wrapped text matches nothing. Strip the banner,
remove box characters, collapse whitespace, match on word n-grams, and **scope every
test to logs of the playbook that owns the technique** (unscoped, NO-TRACE reads 10%;
scoped, 37%).

105 of 279 techniques (38%) leave no trace. **Most are not dead:**

| | count | fix |
|---|---|---|
| UNREACHED — phase never runs | 51 | relocate / re-budget, do NOT delete |
| DEAD — phase ran, still nothing | 45 | delete |
| PRECONDITION — case never arose | 8 | keep (the decompiler-install ladder) |

**The tail of every playbook is unreached.** Three independent measurements agree:
every phase burns its full iteration budget (run26: 60/60, 60/60, 80/80, 45/45…);
phase engagement decays monotonically with position (`chain_findings` 6→1→1→**0** runs
mentioning each phase); and NO-TRACE concentrates in the last phase of 11 of 13
playbooks. In all seven category playbooks that last phase is the shared **"Verify
before reporting"** block — 26 dead techniques holding the control test, proof
discipline, budget discipline and record-to-notes. *"BUDGET DISCIPLINE — you have a
limited number of steps"* is itself never read, because the budget ran out first.

**Two corrections changed the answer, both caught by checking output against known
history rather than trusting the score:**

- **Recency.** A rule can only be judged over runs in which it existed. The first list
  condemned `CHECK THE VERDICT RECORD IS ACTUALLY POPULATED` (added *after* run28
  broke on exactly that) and `QUOTE THE EVIDENCE, NEVER CITE IT` (the run26 change
  that first got the decrypt into a deliverable). Dated every technique against the
  `.orig-*` snapshots + run21's `playbooks-as-run`. **22 techniques have never been
  exercised at all.** Nothing under 3 runs of exposure is judged.
- **Channel.** Rules governing the *written report* leave their trace in the report,
  not the log — the gate's deliverables show 17/15/21 `DEMONSTRATED` labels and the
  key literal quoted 15–17×. Six techniques excluded on that ground.

Deletion used AST source offsets with a checksum guard against stale snapshots; each
file re-parsed, count asserted, every survivor asserted byte-identical. Backups at
`<playbook>.py.orig-preDeInstruct`. All 13 playbooks load on the box.

**DEFERRED TO run30 — the relocation.** The 51 UNREACHED techniques were not deleted.
The fix the evidence points to is the one that already worked once: run26 solved the
recording failure by moving the demand out of a playbook phase into the **checkpoint**
(fires every 12 tool calls, wherever the agent is). The same move applies to the
"Verify before reporting" block.

**Decision 2026-08-04: not before run29.** run29 tests exactly one variable — the 31
deletions plus the still-untested 31 → 15 consolidation — so its result is
attributable. Bundling the relocation would confound it, and run21 already showed what
a mixed-state run costs in interpretability. Relocation is run30.

Also worth checking: `web_discovery` is the smallest playbook (431 tokens, 13 techniques)
and the only phase that never caps — and it MISSED the user-data exposure that
`a01_a07_access_auth` caught. It may be *under*-instructed, which would be the opposite
problem in the same system.

### run28 RESULT — regressed; the final gate is the failure point

Never decrypted, no `provider`, no accounts enumerated. But the important finding is the
user-data exposure trace, which shows the pipeline working right up to the last step:

```
saw PasswordHash / users/info:  a01_a07(4) a05_injection(2) a08_integrity(1)
                                consolidate(3) chain_findings(1)
in notes:                       3 notes
in draft reports:               7
in final deliverable:           0
```

**Cause, and it was my instruction.** `adversarial_review` ran out of budget having
written only a 214-byte header to `adversarial_verdicts.md`. The gate had been told that
file was its primary input and told NOT to re-read the per-phase reports, so it read a
stub 16 times, had no structured input and no permitted fallback, and emitted 2,716 lines
/ 79 numbered findings / 4 duplicate summary sections — still omitting the finding.

FIXED: the gate now verifies the record is populated and falls back to the per-phase
reports if it is not, reporting that the pipeline lost a step. The notes-vs-report audit
did not catch this because it matches on *recovered values*; `PasswordHash` is a field
name, not a value.

### MEASUREMENT BUG — the TODO counter undercounts (FIXED 2026-08-04)

Was `body.count("- [x]")`. Agents rewrite the seeded format — run28's `chain_findings`
used bare `[x] 2.1` — so a checklist with 8 done and 12 open reported **0 done, 0
remaining**, and that figure is rendered INTO the prompt, so agents were told their own
progress was zero. Now matches any checkbox form via
`^[ \t]*(?:[-*+]|\d+[.)])?[ \t]*\[(.)\]` — done is any non-space marker (x, X, +, check
marks), open is an empty box. Verified against the real run28 files: `chain_findings`
9/12, `consolidate_findings` 4/0, `a10_exceptional` 5/9.

Two earlier conclusions came from the broken counter and were WRONG: "chain_findings
closed 0 of 4 items across two runs" and "it does not treat the checklist as a plan".

### (superseded) original counter-bug note

Progress is counted with `grep -c "^- \[x\]"` / `"^- \[ \]"`, but agents rewrite the
seeded checklist in their own format — run28's `chain_findings` used `[x] 2.1` with no
leading `- `, so the counter reported **done=0 open=0** for a file that was being
actively worked. Two earlier conclusions were drawn from this and were wrong:
"chain_findings closed 0 of 4 items across two runs" and "it does not treat the checklist
as a plan". It does; the counter could not see it.

Fix: count with a pattern tolerating both forms, e.g. `^\s*-?\s*\[[xX ]\]`, wherever
checklist completion is reported (the run summaries and any analysis script). The seeded
format should also be stated in the ledger so rewrites stay parseable, or the counter
should simply accept anything checkbox-shaped.

### Changes queued after run27 lands

1. Absolute paths in the ledger (above).
2. Whatever run27's result indicates for the five run27 fixes — incremental verdict
   record, search-before-probing, observe-the-app, scope-after-proving, checklist
   usability.
3. Still unresolved across runs: `chain_findings` has closed 0 of 4 checklist items in
   two consecutive 80-iteration runs. Budget is not the constraint.

### Where the recurring failure stands

The credential chain reaching the final deliverable was the project's core problem for
six runs. **run26 solved the reporting half** — the decrypt reached the deliverable as a
DEMONSTRATED finding with evidence quoted inline. What remains is the exploitation half:
the agent sends a correct password to a correct endpoint while omitting one required
field, reads the rejection as a bad credential, and stops. No authenticated session has
ever been demonstrated by the tool.

---

## Infrastructure

| Thing | Where | Notes |
|---|---|---|
| Target app | Mac `<LAB-TARGET-HOST>`, `dotnet run` on `0.0.0.0:5000` | Reached from Kali via SSH reverse tunnel to `127.0.0.1:5000` (Mac firewall blocks inbound) |
| PentestAgent | `ryan@<LAB-GPU-HOST>` (Kali arm64), `~/pentestagent` | tmux session `pentestagent`, window `run`. **SSH key is `~/.ssh/<lab-key>`** — there is no `Host` entry for this box, so the default `id_ed25519` is offered and rejected. Use `ssh -i ~/.ssh/<lab-key> ryan@<LAB-GPU-HOST>` |
| Model host | `<user>@<LAB-MODEL-HOST>` = `<LAB-MODEL-HOST>`, key `~/.ssh/<lab-key-mac>` | tmux session `pentest-llm` |
| 4090 / CUDA | `:8081` | **RETUNED 2026-08-02** — `-np 1 -c 73728` (was 57,344, **+29%**), `-ctk q8_0 -ctv q8_0`, mmproj dropped, `--reasoning-budget 2048`. VRAM 20,226/23,028, 2,331 free. **Prefill 2,835 tok/s @72k**, gen ~85 tok/s. Needle 6/6 @68,300 tok in ~35s. **Do not use `-ctv q4_0`** — see below |
| Strix Halo iGPU / Vulkan | `:8082` | **FIXED 2026-08-02** — `-np 2 -c 393216` → **196,608/slot**, q8_0 KV, mmproj dropped, auth enforced, reasoning budget added. **But only ~190 tok/s prefill and 18.5 tok/s gen — 4.5x slower than 8081** |
| Do not touch | `:8080` `zdm-llama-nvidia`, `:8090` `llama-qwythos` | unrelated workloads |
| Backups | `~/pentest-demo-backup/`, `~/pentest-prior-state/` | quadlets + prior run state |

Model servers are systemd **quadlets** (`~/.config/containers/systemd/*.container`) —
edit the quadlet then `systemctl --user daemon-reload && systemctl --user restart <svc>`.
A `podman rm` alone will be undone by systemd.

---

## RESOLVED: notes were replaced, not accumulated

**Fixed 2026-08-02, mid-run21.**

**Root cause.** In `pentestagent/tools/notes/__init__.py`, the `create`/`update`/`delete`
actions mutated the module-level `_notes` dict and called `_save_notes_unlocked()`, which
writes the **whole** dict. Nothing in the write path loaded the file first, and `_notes`
is initialised `{}` at import. Every phase is a separate process, so **the first note any
phase wrote replaced the entire file.** The read helpers (`get_all_notes`,
`get_all_notes_sync`) already loaded lazily — only writes were unguarded. Workspace
resolution was never the problem; all phases used the same path.

**Fix.** Load once per process before the first mutation, tracked with an explicit
`_notes_loaded` flag and `_ensure_loaded_unlocked()`, called at the top of the
`async with _notes_lock:` block. A flag rather than a falsy `if not _notes` check: an
empty file and an unloaded state are otherwise indistinguishable, and a falsy check would
re-read disk after every delete-to-empty. Backup at `notes/__init__.py.orig`.

**Verification.** Two independent checks.

1. *Synthetic* — three separate processes each writing one note; all three present.
2. *Production*, from run21's per-phase `*_notes.json` snapshots. Only phases that
   actually wrote a note are evidence; the rest wrote nothing and prove neither way.

| Phase | Wrote | Destroyed | |
|---|---|---|---|
| `web_discovery` 10:47 | 4 | — | baseline |
| `blazor_wasm` 11:47 | 3 | **4** | bug |
| `a04_cryptographic` 12:17 | 1 | **2** | bug |
| `a10_exceptional` 13:12 | 1 | **0** | **fixed** — accumulated to 3 |

Caveat: one post-fix production write so far. Confidence comes from that plus the
synthetic test and the identified mechanism, not from volume of samples.

**Collateral damage to run21.** The pre-fix wipes are permanent in the live notes file:
`web_discovery`'s four notes and `blazor_wasm`'s `api_endpoints_from_decompile` /
`batch_endpoint_dispatch` survive **only** in the per-phase snapshots under
`draft_playbook_reports/`. `consolidate_findings` reads the draft *reports*, not just
notes, so it can still recover them — but run21 is a mixed-state run and is not a clean
test of the v2 pipeline.

---

## Planned work, in order

### 1. ~~Fix notes accumulation~~ — DONE
See the resolved section above. The regression check (two processes, both notes present)
is worth promoting into the test suite rather than living as an ad-hoc script.

### 2. ~~Inter-phase context carry-forward~~ — DONE, differently
Resolved 2026-08-02 without adding a between-phase query. Two changes made the extra
query unnecessary:

- Notes now accumulate across processes, so the existing channel actually works.
- The carry-forward obligation moved **into the phases that were dropping findings**:
  `chain_findings` must account for every consolidated entry (chained / carried forward /
  named duplicate, no fourth state), and `adversarial_review` reconciles against the same
  list and reports any drop as a pipeline defect.

This also let consolidation collapse from two passes to one. A separate query would have
been a third place for findings to be summarised and lost; putting the obligation on the
phase that loses them is cheaper and self-checking.

### 3. ~~ilspycmd install test~~ — DONE, passed on the second attempt
2026-08-02. Full write-up in `report/ilspycmd-absent-test-2026-08-02/`.

Attempt 1 failed: 80 iterations, no decompiler, key never found. The agent reasoned
correctly (check first, then pin an older release) but **guessed three-part version
strings against a package that publishes four-part versions**, so every pin 404'd
identically. It then did both things the playbook already forbade — six `pip3 install`
attempts and a 17 MB ILSpy source clone — proving those prohibitions were too abstract
to bind.

Three fixes to `blazor_wasm`'s toolchain phase: query the package feed instead of
guessing a version; name pip/source-builds explicitly and cap install attempts at six;
and make UTF-16LE literal extraction (`strings -e l`, because .NET stores literals in the
`#US` heap) a **required** fallback rather than a forbidden one — the old rule "never fall
back to searching binaries" was actively steering it away from the one thing that works
without a decompiler.

Attempt 2: 3 install attempts, 0 pip, 0 clones, 37 iterations, `ilspycmd 9.0.0.7889`
installed and the key recovered. Note the box now has 9.0.0.7889 rather than the
9.1.0.7988 it started with; the original is in `~/tool-backup-2026-08-02/`.

<details><summary>original plan (kept for reference)</summary>
Verify the toolchain phase actually installs a decompiler when one is absent.
- Uninstall first: `~/.dotnet/tools/ilspycmd` (and confirm `command -v ilspycmd` fails).
  Preserve a copy so it can be restored.
- Run **only** `blazor_wasm` to keep it short.
- Success = it installs or obtains a working decompiler, or correctly reports it cannot
  and falls back, rather than silently producing a false negative.
- The playbook's install ladder: existing SDK → `dot.net/v1/dotnet-install.sh` (rootless,
  arm64) → distro package → container. It also forbids pip-hunting and building ILSpy
  from source (both wasted a full run previously).
- Note: `ilspycmd` needs `DOTNET_ROOT` exported; `.zshrc` sets it for interactive shells
  only, so it works in a terminal and fails over plain ssh.
</details>

### 4. Raise usable context — **8082 DONE 2026-08-02; 8081 retuned**

Ground truth from the GGUF (`qwen35` arch): **`context_length = 262144`** — the model is
natively trained to 256k, so no rope scaling is needed anywhere below that. 65 layers,
4 KV heads, key/value length 256 → **138 KiB/token** of KV at q8_0.

**8082 / Strix Halo — fixed, now the long-context backend.**
Was `-c 65536 -np 4`, i.e. `n_ctx_slot = 16384` — *less than a third of 8081* despite
sitting on 123 GiB of shared RAM. Now:

```
-ngl 99 -c 262144 -np 2          # 131,072 tokens per slot, 2 slots for crew parallelism
--reasoning on --reasoning-budget 2048
```

Verified at startup: `n_slots = 2, n_ctx_slot = 131072`. Memory after: 57/123 GiB used,
65 GiB still available.

*Auth was two separate faults.* `--api-key ${LLAMA_API_KEY}` expanded to **empty**: the
`EnvironmentFile=` under `[Container]` populates the **container's** env, while `${...}`
in `Exec=` is expanded by systemd against the **unit's** env. Fixed by adding the same
`EnvironmentFile=` under `[Service]`. With an empty key llama.cpp allowed unauthenticated
calls but rejected any *supplied* key — which is why it looked like a 401 to PentestAgent
and like an open server to `curl`. Now: no-auth → 401, wrong key → 401, correct key → 200
on `/v1/chat/completions`. (`/v1/models` is unauthenticated by design in llama.cpp.)
The key is the **same** as 8081's, so one `OPENAI_API_KEY` works against both.

*It was also missing `--reasoning-budget`*, which is the exact cause of the old
"empty response = COMPLETE" bug — a smoke test returned 24 completion tokens and empty
content. With the budget added it returns `'Paris'` plus separate `reasoning_content`.

**Long-context recall was measured, not assumed.** A needle-in-a-haystack probe (unique
value buried at depths 0.1/0.5/0.95, asked back) on 8082 at q8_0 scored **6/6** across
53,360 and 101,366-token prompts. So the model recalls reliably at depth and the probe
itself is sound — any failure on another config is attributable to that config.

Two traps that probe exposed, both worth remembering:

- **A small `max_tokens` produces empty content, which looks exactly like a recall
  failure.** Reasoning is drawn from the same completion budget, so `max_tokens: 128`
  returns nothing at all. Measured: 64 → empty, 128 → empty, 512 → answers. Any probe
  must request well above `--reasoning-budget`. (PentestAgent sets no `max_tokens`, so it
  inherits `--predict 8192` and is not affected.)
- **Never benchmark two backends on this host concurrently.** The Vulkan iGPU test drives
  load average to 15 and appears to starve the CUDA server's host-side work.

**DO NOT quantise the V cache below q8_0 on CUDA.** Tried `-ctk q8_0 -ctv q4_0` to buy
context (the memory math is right: 138 → 106 KiB/token, enough for 90,112). It leaves
llama.cpp's optimised CUDA flash-attention path and prefill collapses — measured on an
idle box:

| prompt tokens | `-ctv q4_0` | `-ctv q8_0` |
|---|---|---|
| 3,618 | 140 tok/s | **786 tok/s** |
| 14,418 | 52 tok/s | **1,811 tok/s** |
| 36,018 | — | **2,527 tok/s** |
| 72,018 | — | **2,835 tok/s** |

About **50x**, and q4_0 got *worse* with length while q8_0 got better (larger batches
amortise overhead). A 72k prompt: 25 seconds at q8_0, extrapolated ~50 minutes at q4_0 —
slower at prefill than the Vulkan iGPU. Generation speed was unaffected (~85 tok/s
either way), so a short smoke test will not catch this; it only shows up under length.

Final: buy context by dropping the unused mmproj and accept 73,728, rather than by
degrading the cache. 2,331 MiB VRAM remains free, so ~82k is probably reachable, but
stability was preferred over another 11% now that consolidation no longer needs a huge
window.

**Per-phase routing was considered and rejected.** The original plan was to send the
context-hungry phases to 8082 and leave breadth sweeps on 8081. Two reasons not to:

1. **It overfits to this hardware.** The pipeline should work for anyone who can run the
   model, and a runner that hardcodes a two-endpoint topology does not.
2. **8082 is ~25x slower.** Same needle test, same model, both at q8_0: 8081 answers a
   68,300-token retrieval in **~35 s**; 8082 takes **919 s** for 101,366. Its 196k window
   is real but costs ~14 minutes per large call, so a phase making 40-60 calls would run
   for days. Routing consolidation there would have traded a hard failure for a run that
   never finishes.

**8082 is a specialist, not a general backend** — worth using only for a handful of
genuinely oversized one-shot calls. The general fix is the bounded-context consolidation
rewrite, which works on any endpoint size.

If two backends are ever used, route **per phase, not per request** — llama.cpp caches
the prompt prefix per slot, so bouncing one conversation between backends reprocesses the
whole context each turn. Session affinity matters more than balancing.

The only 8081 change worth making, and only incidentally: drop `--mmproj` since
PentestAgent never sends images. Do it at the next restart, not for its own sake.
- No proxy needed for per-phase routing: set `OPENAI_API_BASE` per `run_phase` in the
  runner. A proxy (LiteLLM preferred, since PentestAgent already uses litellm) is only
  needed to distribute **crew workers within** a phase.
- Suggested split: breadth phases (category sweeps) on iGPU concurrently; depth phases
  (`chain_findings`, `adversarial_review`, `final_integrity_gate`) on the 4090.

### 5. MCP server run
PentestAgent supports MCP: `pentestagent mcp add <name> <command> [args]` writes
`mcp.json`; `mcp list/test/connect` manage it. **You do not point the model at the
server** — the agent merges the server's tools into the tool list the model already sees.
There is a `_TOOL_LIMIT` in `base_agent.py` worth checking before adding many tools.

Candidates: the CVE→PoC tool (would also supply the advisory grounding that made an
earlier run fabricate `CVE-2025-9287`), plus anything covering the gaps below.

Sandboxing: `--docker` exists (image `ghcr.io/gh05tcrew/pentestagent:kali`) but **neither
docker nor podman is installed on the Kali box**. Installing podman + pulling that image
would also fix Playwright and ilspycmd at once, since the image ships them.

---

## Known gaps

- **`consolidate_findings` exceeds the context window.** Observed repeatedly in run21
  phase 10: 12 `ContextWindowExceededError`s, requests of 62,792 / 78,457 / 83,088 /
  98,121 tokens against 57,344 available. The agent `cat`s every draft playbook report
  (9 reports, 15–43 KB each) into one prompt, so the input grows linearly with the number
  of phases — it will outgrow **any** fixed context as categories are added.
  Raising context (item 4) relieves it but does not fix it. The structural fix is
  **map-reduce**: have the playbook summarise each report individually, then merge the
  summaries, instead of loading everything at once. Do both.
- **Playwright is broken on Kali** — `BrowserType.launch: Executable doesn't exist`. Every
  run has fallen back. `a09_logging_alerting`'s session-collision test needs it (or uses a
  cookie-jar approximation and says so). Fix: `playwright install chromium`.
- **Supply chain (A03:2025) is deliberately not covered** — without a live advisory feed a
  model asserts CVEs from version strings alone. The MCP CVE tool would close this.
- **`a06_insecure_design_DANGEROUS` is quarantined** — tests for absent rate limiting and
  lockout, i.e. provokes DOS. Excluded from the runner; opt-in, disposable targets only.

---

## Report naming convention (keep)

`report/run<N>-<descriptor>-<YYYY-MM-DD>/` with a written `SUMMARY.md` giving the verdict,
what worked, what failed and why. Add **`PoC-Win`** to the folder name only when the run
reproduces the full chain through to an authenticated session. Contaminated or invalid
runs keep their number and are labelled (e.g. `run18-...-CONTAMINATED-...`) rather than
deleted.

Capture with `report/capture-run.sh <label> <remote-log-basename> [playbook]`. It now
prefers the per-assessment `loot/assessments/<id>/` layout and falls back to the legacy
flat `loot/reports/`.

**Always verify a cold start before claiming one:**
```bash
grep -rl "p@55wOrd\|Vu1nB1az0r" /tmp loot workspaces
```
`zsh` aborts an entire `rm` line on an unmatched glob, so cleanup silently does nothing —
use `find ... -delete`. This invalidated run18.

---

## Run history

| Run | Result |
|---|---|
| unaided baseline | never requested `/_framework/` |
| 11 | first full chain to plaintext credentials |
| 16 | held key + tokens for all accounts, never joined them |
| **17** | **PoC-Win** — join rule added; decrypted all tokens, authenticated as all 3 accounts |
| 18 | CONTAMINATED — prior state not cleared |
| 19 | cold Top-10 sweep found the key; produced a false-positive Critical (no control test) |
| **20** | **PoC-Win** — 11-phase pipeline, 2h09m; report had ECB/CBC and key-length errors |
| **21** | **PoC-Win** — 14-phase v2, 4h52m. Best *deliverable* so far: first to carry the full chain **and** the low-severity items (verbose errors/stack traces) that run20 lost. But **employee account only** — held the manager's token and never decrypted it, i.e. the run16 join failure recurring, so run17 still leads on breadth. Phase 10 threw 20 context errors. **Mixed state** (notes fix landed mid-run), so not a clean v2 test. Captured as `run21-CHAMP-PoC-Win-full-assessment-14-phase-2026-08-02` |
| 22 | **not a PoC-Win, but the closest miss yet** — v3 + MCP, 13/13 phases, 5h33m. Decrypted `LastSeenToken` → `p@55wOrd` at iter ~19, then failed auth by omitting ServiceStack's `"provider":"credentials"` field (verified: `/api/Authenticate` returns 401 without it, 200 with it). **Infrastructure all passed**: 0 context errors (run21 had 20), 17 notes accumulated (run21: 3), 8 MCP tools used, gobuster digest held. **Defect**: `chain_findings` hit 60/60 and stopped before its final phase, where the carry-forward-to-notes rule lives — so the proven decrypt never became a finding and the deliverable calls decryption "potential". Captured as `run22-v3-mcp-13-phase-2026-08-03` |
| 23 | regression — never decrypted. Phase 05 recorded the key as "24 bytes" (it is 32) and `chain_findings` inherited the wrong spec, then ground on one grep to 59/60. Fixes: computed-not-stated key length, countable stop rule |
| 24 | decrypted, then 401'd on `/api/Authenticate` for a missing `provider` field and concluded the password was wrong. Note existed; deliverable cited filenames instead of quoting evidence, and inflated it to "authenticates as privileged users" |
| 25 | worst carry so far — decrypted but wrote **no note**, so nothing downstream could recover it. Verdict record + tool-log scratchpads + checklists all worked; the notes-vs-report audit fired and could not help, because the gap was upstream of it |
| **26** | **decrypt reaches the deliverable as a real finding for the first time** — section 2.1, evidence quoted inline (key + source line, token, `p@55wOrd`). Fixed by moving the recording demand into the **checkpoint**, which fires wherever the agent is rather than only inside one playbook phase. Still not a PoC-Win: sent the right password to the right endpoint but omitted `"provider":"credentials"` → 401. Captured as `run26-record-and-auth-2026-08-04` |
| 27 | next — make the auth baseline actually run (observe the app's own login); make `chain_findings` work its checklist; find why `adversarial_verdicts.md` was skipped |

Verified ground truth for the target: key `Vu1nB1az0r$ecretKey!2026@@@@@@@@` (32 bytes,
8 `@`), AES-**CBC** with prepended IV, decrypts `LastSeenToken` → `p@55wOrd`, which
authenticates as admin/manager/employee via `POST /auth/credentials.json`.

## Fork

`github.com/its-ryans-work/pentestagent`, branch `local-model-support`, base `9828aed`.
Four commits pushed. **Not yet pushed:** the join rule, `credential_exposure` updates,
`owasp_top10`, the 10 per-category playbooks, `consolidate_findings`,
`final_integrity_gate`, the evidence-selection and per-assessment-layout patches, and the
v2 runner.
