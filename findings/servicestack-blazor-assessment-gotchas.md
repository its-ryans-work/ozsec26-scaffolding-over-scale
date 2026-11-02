# Assessment gotchas: ServiceStack v10 + Blazor SSR + Identity + OrmLite/SQLite

*Nine behaviours that waste time or pay off when testing a ServiceStack v10 + Blazor SSR + Identity app: content negotiation, antiforgery cookie jars, dev-mode confirmation links, 401-vs-403, and the metadata endpoint as free enumeration.*

## Things that waste time

**1 — Endpoints return HTML unless you ask for JSON.** ServiceStack's default content negotiation
serves the ServiceStack UI "Snapshot" HTML page when `Accept` is missing or `text/html`, so `curl`
returns a full page and `json.loads()` fails.

```bash
curl -H "Accept: application/json" http://target/api/SomeEndpoint
```

**2 — Blazor SSR antiforgery: GET and POST must share one cookie jar.** SSR forms use
`__RequestVerificationToken`; the token in the body must match the cookie issued on the GET.
Separate sessions → `400 A valid antiforgery token was not provided`.

```bash
curl -c jar.txt -b jar.txt http://target/Account/Login > page.html   # GET sets the cookie
# extract the token from page.html, then POST with the SAME jar
curl -c jar.txt -b jar.txt -X POST ... --data-raw "...$TOKEN"
```

**3 — 401 vs 403 mean different things, and 401 can lie.** `401` = no Identity cookie, or a cookie
ServiceStack does not recognise; `403` = valid cookie, role check failed. In a Blazor+ServiceStack
hybrid the ServiceStack layer reads `.AspNetCore.Identity.Application` — so **a present, valid
cookie whose session is not synced to ServiceStack** (user not fully registered/confirmed) still
yields 401. Don't read 401 as "my auth is wrong" without checking sync state.

**4 — `AdminDatabase` is a GET.** POST returns `405`, despite the operation being data-mutating in
some uses. Requires Admin role (403 otherwise).

```bash
curl -G http://target/api/AdminDatabase --data-urlencode "db=main" --data-urlencode "table=T"
```

## Things that pay off

**5 — The metadata endpoint is free enumeration.** `curl http://target/types/metadata.json` returns
**all** operations with routes, verbs and auth attributes. `[ExcludeMetadata]` suppresses an
operation from this list — which makes the *absence* of an endpoint you know exists a signal in
itself. Pairs directly with the per-DTO auth finding in
[servicestack blazor attack surface](servicestack-blazor-attack-surface.md): the metadata dump is the DTO list you need to enumerate.

**6 — Dev-mode `RegisterConfirmation` renders the confirmation link inline.** With
`ASPNETCORE_ENVIRONMENT=Development`, the page emits
`<a href=".../Account/ConfirmEmail?userId=…&code=…">`. This is intentional Identity dev scaffolding.
**`ForgotPasswordConfirmation` does *not*** — it shows only "Please check your email". **The
asymmetry is deliberate**, so finding one does not imply the other.

## Things that are genuinely solid (record the negatives)

**7 — AutoQuery is parameterised; no SQLi.** `QueryDb<T>` goes through OrmLite, which parameterises
even dynamic `orderBy`/`take`/`skip`.

**8 — SSR component state is DataProtection-encrypted.** The
`<!--Blazor-Server-Component-State:…-->` HTML comment is a DataProtection token, **not** AES under a
recoverable key, so it cannot be forged without server keys — unlike the batch channel
(the AES-CBC padding oracle).

> **Note on the padding oracle.** This describes an earlier revision of the target.
> The batch endpoint in the shipped code collapses every payload failure to one
> response and is no longer an oracle — see `target/README.md`. The finding is kept
> because the flaw class is real and the fix is the interesting part.

> Recording what is *not* vulnerable is part of the assessment: it stops the next pass re-testing
> ground already cleared, and it isolates the real finding.

## Related

- [servicestack blazor attack surface](servicestack-blazor-attack-surface.md) · ASP.NET Identity v3 hash cracking · [vulnblazor](overview.md)
