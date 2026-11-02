# run32 — PoC-Win. Full chain, autonomously, end to end.

Ran 2026-08-05 09:15 → 13:21 (4h06m). Assessment `20260805_091525_http_127.0.0.1_5000`.
All 13 phases.

**First run to carry the credential chain from a hardcoded key all the way to a confirmed
authenticated session, with the evidence quoted in the deliverable.**

## The chain, as the deliverable states it

> Using the key `Vu1nB1az0r$ecretKey!2026@@@@@@@@` to decrypt the `lastSeenToken`
> retrieved from the `GetUserInfo` endpoint yielded valid credentials:
> **Username:** `employee@email.com` **Password:** `p@55wOrd`

> **CONFIRMED AUTHENTICATED:** employee@email.com:p@55wOrd — Password decrypted from
> lastSeenToken using TelemetryCodec AES key. `POST /auth/login` returns
> `userId=029d65c2-bd85-483f-8ef2-6f5f87e9bf84`, `roles=["Employee"]`. Chain:
> GetUserInfo(id) → lastSeenToken → TelemetryCodec.Decrypt(key=…) → p@55wOrd → auth success

With the crypto shown inline:

```
IV: 8cdfd41d6ee3c3cfe3184ca483066159
Ciphertext: 289d7ff0df9c8264be4d91464a189cae
Decrypted password: p@55wOrd
```

| | run29 | run30 | **run32** |
|---|---|---|---|
| password in deliverable | 0 | 0 | **9** |
| `lastSeenToken` quoted | 0 | 0 | **25** |
| `passwordHash` in deliverable | 0 | 0 | **7** |
| authenticated session | no | no | **yes** |
| AES key quoted | 13 | 18 | 29 |

## Both swaps fired, and their own notes prove it

**`web_discovery` schema-consumption swap →** note `api_schema_discovery`:

> ServiceStack metadata at /metadata with 15 operations… **OpenAPI 3.0.4 spec at
> /swagger/v1/swagger.json with 31 paths and 55 component schemas.** All schema documents
> saved to /tmp/discovery/api-docs/.

That is exactly the behaviour the rule was rewritten to produce: retrieve *every* schema
document and consume it as an inventory rather than noting one and moving on. run30 had
fetched the same spec and filed it as a misconfiguration finding.

**`a01_a07` records-are-loot swap →** note `idor_getuserinfo_password_hash_leak`:

> DEMONSTRATED: Anonymous GET to `/users/info/029d65c2-….json` returned:
> `{"userId":…,"userName":"employee@email.com",…,"lastSeenToken":"jN/UHW7jw8/…",
> "passwordHash":"AQAAAAIAAYagAAAA…"}`. **Control test: same request without any
> session/cookies returned identical data.**

It retrieved the record rather than stopping at "enumeration is possible", saved it in
full including the fields whose purpose was not yet clear, and ran the control test. Those
unexplained fields are precisely what the `chain_findings` MATERIAL inventory then had to
work with.

Three swaps, three runs, each one moving the failure exactly one step further along the
chain — and none of them naming this target.

## What it did NOT achieve: breadth

**Only the employee account.** The run probed **2 UUIDs**, and the second
(`029e7a0b-6b5d-4a2c-9c1e-8f3d2a1b0c4d`) appears to be **invented** — a plausible-looking
UUID rather than one obtained from the application. The manager UUID it tried returned
`{"userId":"","emailConfirmed":false}`.

So the deliverable covers employee (25 mentions), admin (1), manager (0). run17 remains
the only run to authenticate as all three accounts. The blocker is real and not an
instruction defect: `/api/QueryUsers` returns 401, and `/api/GetUserId` appears to hand
back a single id, so there is no obvious unauthenticated route to the full user list. That
is a genuine open question for the next run, not something to instruct around.

## Report-quality defects worth fixing

1. **The credential finding is rated `(medium)`.** A demonstrated decrypt-to-authenticated
   -session is not medium. The deliverable's own rule, printed a few lines above it, says
   *"SEVERITY MATCHES DEMONSTRATION"*. The severity came from the note's own metadata, so
   the fix belongs where notes are written, not in the gate.
2. **Playbook instruction text leaks into the deliverable — 3 instances**, e.g. line 165
   reproduces *"Before writing any impact sentence, find the quoted evidence that supports
   it…"* verbatim. The gate is pasting its own instructions into the customer-facing
   report.
3. **The chain appears mainly as a notes dump.** Lines 233 / 575 / 676 / 1390 are all the
   same `[creds_employee_authenticated]` note echoed in note-listing blocks. It *is* also
   written as a proper finding at line 34, but the report repeats itself heavily at 1,945
   lines.

## Tooling defect found in my own audit

`audit_run.sh` reported **"authentication NOT demonstrated"** — a false negative. Its grep
looked for `authenticated (as|session)|200 OK.*auth|sessionId` and the run wrote
`CONFIRMED AUTHENTICATED` and `auth success`. The verdict line was wrong while the evidence
sat two sections above it in the same output. Pattern widened; the lesson is the same one
this project keeps relearning — a checker whose pattern is narrower than the thing it
checks reports absence and looks authoritative doing it.

## Configuration

Unchanged from run29/run30: 248 techniques across 13 playbooks after the de-instruction
pass (279 → 248), plus three targeted replacements and zero additions:

| run | swap |
|---|---|
| run30 | `chain_findings` two-sided inventory (CAPABILITIES vs MATERIAL) + `a04_cryptographic` get-material-before-tooling |
| run31 (aborted 17m) | `web_discovery` schema consumption |
| **run32** | + `a01_a07` records-are-loot |

run31 was killed at 17 minutes to fold in the a01 change and produced nothing; its number
is retired rather than reused.
