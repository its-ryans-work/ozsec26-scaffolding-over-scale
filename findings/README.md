# Findings

The transferable part. These are written to apply to **real** ServiceStack and Blazor
applications — the target is disposable, the detection techniques are not.

The vulnerabilities in [`../target/`](../target/) are intentional and are training
material, not disclosures. What makes them worth writing up is that each is a real-world
class: the app was built to embody patterns that ship in production .NET applications, so
the technique transfers even though this target does not.

| Document | What it covers |
|---|---|
| [`servicestack-blazor-attack-surface.md`](servicestack-blazor-attack-surface.md) | Where the surface actually is: per-DTO attribute authorization, what Blazor render modes ship to the browser, and the encrypted batch envelope. |
| [`servicestack-blazor-assessment-gotchas.md`](servicestack-blazor-assessment-gotchas.md) | Nine behaviours that waste time or pay off when testing ServiceStack v10 + Blazor SSR + Identity. Includes the negatives worth recording. |

## The three that matter most

**Attribute authorization in ServiceStack is per request DTO — not per file, not per
service class.** In the target, `QueryUsers` is correctly gated with `[ValidateIsAdmin]`
while `GetUserId` and `GetUserInfo`, in the same file, carry no auth attributes at all.
This is the realistic mistake: the one obvious "list users" operation gets locked down and
the sibling lookups are left open. **When reviewing any attribute-routed API, enumerate
every request DTO individually.** Never infer that a service class is covered because a
representative endpoint is gated — and `/types/metadata.json` gives you that DTO list for
free, with routes, verbs and auth attributes.

**Treat every assembly under `/_framework` as public.** A Blazor app using `InteractiveAuto`
bundles the shared DTO assembly into the WASM payload, so anything reachable from the shared
or server project is fully readable in the browser: embedded constants, DTO shapes,
internal-only operations, and `[ValidateHasRole(...)]` attributes that hand over the exact
authorization model. Never place a secret as a constant in an assembly that anything
client-reachable references. Keep it server-only, injected from configuration, in an
assembly with no reference path to the client.

**A clean search over a binary is not evidence of absence.** Compiled and minified client
code has to be decompiled or unpacked before it can be searched. This is the single rule
that most changes outcomes for an automated assessment, which is why it appears explicitly
in the playbook's `blazor_wasm` phase.

## A correction worth keeping

These notes were written against an earlier revision of the target and describe the batch
endpoint as a usable AES-CBC padding oracle. **It no longer is.** The shipped code collapses
every failure in the payload path to one indistinguishable response, logging detail
server-side only — see the hardening section of [`../target/README.md`](../target/README.md).

The finding is left in because the flaw class is real and common, and because the fix is the
instructive part: hiding the `CryptographicException` is not enough. A distinct "invalid
timestamp", "invalid envelope", or even "unknown action" each confirm that padding was
valid, which is the same leaked bit under another name. They all have to collapse to one
answer.

The endpoint is now a useful negative control: an agent that reports a padding oracle there
is reporting a false positive.
