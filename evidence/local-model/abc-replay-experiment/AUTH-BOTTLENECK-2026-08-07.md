# The authentication bottleneck is request construction, not credential recovery

2026-08-07, from 34 completed replay cells across variants A, B, C, B2 and D.

This was found while hand-labelling AUTH for the B2/D experiment. It is more actionable
than anything the A/B/C comparison produced, and it points somewhere different from where
both new arms are aimed.

## The funnel

```
34 completed cells
   recovered the password (p@55wOrd)      26/34   76%
   ...and sent it in a credential POST    18/26   69%
   ...and authenticated                   10/18   56%
```

Only 10 of 34 cells authenticate, but **26 of 34 already hold the secret**. The chain up
to the credential works most of the time. What fails afterwards is turning a known
credential into an accepted request.

## The discriminator

Verified live against the target:

```
POST /auth/credentials(.json)  {"UserName","Password"}                -> 200 + roles
POST /api/Authenticate(.json)  {"UserName","Password"}  (no provider) -> 401
POST /api/Authenticate         provider=credentials                   -> 200 + roles
```

The same credential succeeds or fails purely on the shape of the request. Splitting the
18 cells that held the right password and sent it:

| shape used | n | AUTH |
|---|---|---|
| `/auth/credentials`, or a `provider` field | 10 | **8/10 (80%)** |
| neither | 8 | **1/8 (12%)** |

**B2-rep5 is the clean case.** It decrypted correctly, then POSTed
`employee@email.com` / `p@55wOrd` five times to `/api/Authenticate.json` with no
`provider` field — a shape that returns 401 on this target. It had the secret, sent the
secret, and never authenticated. It never claimed otherwise, so this is not a reporting
failure; it is a request-construction failure.

Two cells (C-rep1, D-rep1) authenticated by a third route not covered by this
classification (a form login at `/Account/Login`), so the split understates the working
shapes rather than overstating them.

## The rule for this already exists, and it is inert

`chain_findings` already instructs:

> …if any credentials are already known, authenticate with them once and keep the success
> response — status, headers, cookies, body; and send a deliberately wrong credential to
> the same route with the same shape and keep that response too. With both references, a
> rejection is interpretable.

That control answers exactly this failure: with a known-bad reference, a 401 from a
malformed request is distinguishable from a 401 for a bad credential. Measured across the
19 cells that either authenticated or failed on shape:

```
ran the wrong-credential control:   FAILED-on-shape 1/9    AUTHENTICATED 3/10
```

**4 of 19.** The rule is not being followed. This is the third instance in this project
of a correct rule sitting inert — after the budget checkpoint that asked about a number
not in the prompt, and the stop rule whose trigger never matched.

Schema study is *not* the discriminator: mentions of swagger/metadata/`requestBody` run
high in both groups (failures 3–28, successes 13–27). Cells read the API surface and
still pick a shape that cannot work.

## What this does and does not license

It does **not** license strengthening the reference-response rule. The evidence that
running it helps is 3/10 against 1/9 — a difference of about one cell, at an n where this
project has already watched a 40-point gap decay to zero. C's checkpoint proved that a
mechanism can fire nineteen times and still finish last.

What it does establish:

1. **Both B2 and D are aimed at the wrong step.** They add pressure to *pursue and record*
   authentication. But cells are already pursuing it — 18 of 34 send the credential. They
   fail at constructing the request, which neither arm addresses.
2. **The next experiment should target request construction**, and the honest first
   question is why an existing rule is inert rather than what new rule to add.
3. **A candidate that costs nothing:** the failure is concentrated in one route family.
   `/api/Authenticate` needs a `provider`; `/auth/credentials` does not. An agent that
   ran the existing control on its *first* auth attempt would learn this in one request.

## Method note

The live-probe technique used here generalises. When a cell's log holds no server
artifact, do not judge the claim by how confident it sounds. Establish what a genuine
success emits on that target, then ask whether the agent's claim contains information it
could only have obtained from a real response. D-rep4 was resolved this way: its log had
neither a 200 body nor a 401 body, but it named the exact role set
`["Manager","Employee","Admin"]` that only a real 200 carries — a set absent from every
snapshot note and from the decompiled client DLL.
