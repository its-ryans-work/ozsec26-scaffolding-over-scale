# ServiceStack + Blazor: where the surface actually is

*Attribute auth in ServiceStack is per-DTO, so a locked-down Query endpoint tells you nothing about its siblings. Blazor Auto render mode ships the shared server DTO assembly — including a live AES key — to the browser.*

## Attribute authorization is per-DTO, so siblings prove nothing

`GetUserId` (`/users/id/{int}`) and `GetUserInfo` (`/users/info/{guid}`) carried **no**
`[Authenticate]` / `[ValidateRequest]` attributes — unlike the sibling `QueryUsers` operation **in
the same file**, which correctly carried `[ValidateRequest("IsAdmin")]` and returned 401/403 in
testing.

**Root cause:** attribute-based authorization in ServiceStack is applied **per request-DTO**, not
per file or per service class. It is easy for the one "obvious" endpoint (a Query/List operation) to
be locked down while sibling lookup endpoints (get-by-id, get-info) are left open.

Chaining sequential-int enumeration through the unauthenticated `GetUserId` into `GetUserInfo`
yielded **every user's email, PBKDF2 password hash, and a `LastSeenToken`** — fully unauthenticated.

**Pattern:** when reviewing any attribute-routed API, **enumerate every request DTO individually**
and check its auth attributes. Never infer that a service class is "covered" because a
representative endpoint is gated. Confirmed by live `curl` with no auth cookie.

## Blazor "Auto" render mode ships the server DTO assembly to the browser

`blazor.boot.json` for this Auto (server + WASM) app listed **two** app assemblies: the expected
`*.Client.dll` **and** the shared/server project containing the **full ServiceModel** — every
request/response DTO (including ones marked `[ExcludeMetadata][Restrict(InternalOnly=true)]`) plus a
static class holding a **hardcoded AES-256 key used to sign password-reset tokens**.

**Why:** Auto render mode bundles the shared DTO assembly into the WASM payload so client-side
interactivity and fallback work — not just the `.Client` project. Decompiling both fully exposed
server-side business logic, internal-only DTOs, and a **real, live cryptographic secret**.

**Generalises to any Blazor app using InteractiveAuto or InteractiveServer-with-WASM-fallback:**
assume **any** assembly reachable from the shared/server project that lands under `_framework/*.dll`
is fully readable — embedded constants, DTO shapes, and validation attributes alike.
`[ValidateHasRole(...)]` attributes reveal the **exact authorization model** for free.

**Rule:** never place secrets as constants in an assembly referenced by anything that can reach a
Blazor WASM/Auto boot manifest. Keep them server-only, injected via config, in an assembly with **no
client-reachable reference path**.

## The encrypted batch channel: `action` is outside the ciphertext

`/api/batch` expects an outer HTTP body of `{"action": "<ActionName>", "payload": "<base64>"}`.

- `action` sits **outside** the encrypted payload, at the HTTP request level.
- `payload` is AES-CBC encrypted and contains the envelope
  `{"Ts": "<ISO8601_UTC>", "Data": "<JSON string of the inner request>"}`.

**Gotcha:** sending `{"payload": …}` without `action` returns `Unknown action: ` (empty) — the server
reads `action` from the **unencrypted** body. That split is what makes the endpoint a usable oracle
target: the attacker controls a cleartext selector alongside the ciphertext
(the AES-CBC padding oracle).

## Related

- [vulnblazor](overview.md) · the reversible-credential-storage chain · ASP.NET Identity v3 hash cracking
- Blazor WASM client secret extraction · the OWASP Top 10
