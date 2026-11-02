# Config snapshot — as run26 executed (2026-08-04)

Everything needed to return to this exact configuration. Captured after run26 finished
and before the run27 changes.

## Hosts

| | where | notes |
|---|---|---|
| Target app | this Mac, `dotnet run --urls http://0.0.0.0:5000` | reached from Kali via `ssh -R 5000:127.0.0.1:5000`; the tunnel does not survive a sleep |
| PentestAgent | `ryan@<LAB-GPU-HOST>` (Kali arm64), `~/pentestagent` | tmux session `pentestagent` |
| MCP kali server | same Kali box, `~/mcp-kali-server`, API on `127.0.0.1:5111` | Flask API; `client.py` is the stdio MCP bridge |
| Model host | `<user>@<LAB-MODEL-HOST>` = `<LAB-MODEL-HOST>`, key `~/.ssh/<lab-key-mac>` | tmux `pentest-llm` |

**`~/mcp-kali-server` is a deployed artifact.** Source of truth is
`<dev-root>/Kali-MCP` on the Mac, pushed with
`./deploy.local.sh sync`. Editing the Kali copy directly gets overwritten on the next
deploy — that happened once and silently reverted a day's changes.

## Model serving

```
8081  RTX 4090 / CUDA      -ngl 99 -c 73728 -np 1
                           -fa on -ctk q8_0 -ctv q8_0
                           --spec-type draft-mtp --predict 8192
                           --reasoning on --reasoning-budget 2048
                           temp 1.0  top-p 0.95  top-k 20  min-p 0.0

8082  Strix Halo / Vulkan  -ngl 99 -c 393216 -np 2   (196,608 per slot)
                           same sampler and reasoning settings
                           api key from EnvironmentFile at [Service] scope
```

Model: `Qwen3.6-27B-Fable-Fus-711-UnHeretic-NM-DAU-NEO-MAX-NEO-MTP-IQ4_XS.gguf`
(`qwen35` arch, `context_length = 262144`, 65 layers, 4 KV heads, key/value length 256 →
**138 KiB/token** of KV at q8_0).

Hard-won settings, do not change casually:

- **`-ctv q4_0` destroys CUDA prefill.** Measured on an idle box: 140 tok/s at 3.6k
  tokens falling to 52 tok/s at 14.4k, against 786 → 2,835 tok/s at q8_0. Roughly 50x.
  Generation speed is unaffected either way, so a short smoke test will not catch it.
- **`--reasoning-budget` must be set**, or the model spends its whole completion budget
  thinking and returns empty content, which the harness once scored as success.
- **8082 is ~25x slower than 8081** for the same work (919 s vs ~35 s on the same
  retrieval probe). Its larger window is only worth using for occasional oversized calls.
- Servers are systemd **quadlets**; edit the `.container` file then
  `systemctl --user daemon-reload && systemctl --user restart <svc>`. A bare `podman rm`
  is undone by systemd.

## PentestAgent runtime

```
.env
  PENTESTAGENT_MODEL=openai/qwen3.6-27b-fable
  OPENAI_API_BASE=http://<LAB-MODEL-HOST>:8081/v1
  PENTESTAGENT_EMBEDDINGS=local
  PENTESTAGENT_MAX_CONCURRENT_TOOL_CALLS=8
  PENTESTAGENT_AGENT_MAX_ITERATIONS=60      # overridden per phase by the runner
```

Context and output limits:

```
CONTEXT_BUDGET_TOKENS      73728    override with PENTESTAGENT_CONTEXT_BUDGET
CONTEXT_RESPONSE_RESERVE    9000    must exceed the server's --predict
CONTEXT_CHARS_PER_TOKEN       3.6   deliberately pessimistic
CONTEXT_MIN_TOOL_CHARS       200
VERBATIM_TOOL_RESULTS          4    most recent results sent uncompacted
COMPACT_TOOL_CHARS           700    older ones squeezed to this
MAX_MCP_OUTPUT_CHARS       12000    per MCP result
_MAX_WORKER_RESULT_CHARS    6000    per crew worker result
MAX_OUTPUT_CHARS           50000    terminal tool self-cap
CHECKPOINT_EVERY              12    tool calls between checkpoints
CHECKPOINT_WINDOW             10    commands quoted in one
MAX_EMPTY_RESPONSE_RETRIES     3
```

The three tool-output caps exist because the verbatim window holds four results at once;
4 × 50,000 chars alone is most of a 73,728-token budget.

## Phase budgets (13-phase v3 runner)

```
01 web_discovery          40      08 a09_logging_alerting  25
02 blazor_wasm            60      09 a10_exceptional       25
03 a01_a07_access_auth    60      10 consolidate_findings  40
04 a02_misconfiguration   60      11 chain_findings        80
05 a04_cryptographic      60      12 adversarial_review    75
06 a05_injection          60      13 final_integrity_gate  45
07 a08_integrity          50
```

`a06_insecure_design_DANGEROUS` is excluded from the runner: it tests for the absence of
rate limiting and lockout, which means provoking the conditions those controls prevent.

## MCP

`~/pentestagent/mcp_servers.json` points at
`/home/ryan/mcp-kali-server/venv/bin/python client.py --server http://127.0.0.1:5111/`
(stdio). 24 tools, under the 128 `_TOOL_LIMIT`, so all are exposed directly.

Two things that were not obvious:

- **`pentestagent run` ignored MCP entirely** until patched — `cli.py` hard-set
  `mcp_manager = None`. Config alone did nothing. `mcp test` reported 24 tools while the
  agent received none.
- **`mcp` must be pinned `<2`.** Version 2.0.0 moved `FastMCP` from
  `mcp.server.fastmcp` to `mcp.server.mcpserver`, so the unbounded `mcp>=1.0.0` in
  requirements resolves to something `client.py` cannot import.
- The bridge venv is `venv/`, and the deploy rsync originally excluded only `.venv` — so
  `--delete` wiped it on every deploy until both excludes were added.

## Harness modifications (all in-tree, `.orig*` backups beside each file)

```
base_agent.py   _enforce_context_budget   trim-to-fit before sending; shrinks tool
                                          contents only, never drops a tool message
                                          (pairing with tool_call_id would break)
                _todo_block               per-phase checklist seeded from playbook phases
                _checkpoint_block         every 12 calls: what did this establish, do you
                                          continue, and what have you proven but not
                                          recorded
                _budget_line              publishes iteration/budget into the prompt
cli.py          _append_tool_scratchpad   every tool result appended to tool-log.md
                _audit_report_against_notes  final deliverable compared to notes; missing
                                          recovered values appended
                command display           400-char limit, multi-line, escape()
crew/tools.py   worker result cap + scratchpad path
worker_pool.py  _write_worker_scratchpad  full worker output to disk
mcp/tools.py    _cap_mcp_output
notes/__init__.py  _ensure_loaded_unlocked  load before mutate (writes used to truncate
                                          the file to whatever one process held)
```

## Restoring this state

Every patch is idempotent and has a `.orig*` backup alongside the file it modified. To
revert one, copy its backup back and restart nothing — each phase is a fresh process, so
changes take effect at the next phase boundary, never mid-phase.

## Known-good ground truth for the target

Key `Vu1nB1az0r$ecretKey!2026@@@@@@@@` (32 bytes, 8 `@`), AES-CBC with the IV prepended,
decrypts `LastSeenToken` → `p@55wOrd`. Authentication:

```
POST /auth/credentials.json  {"userName":…,"password":…}                    -> 200 + roles
POST /api/Authenticate       {"userName":…,"password":…}                    -> 401
POST /api/Authenticate       {"provider":"credentials","userName":…,…}      -> 200 + roles
```

The `provider` field is what run24 and run26 both omitted.
