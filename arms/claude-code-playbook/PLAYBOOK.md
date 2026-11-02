# Assessment methodology — full playbook

13 phases, 247 techniques total.

Each phase is scoped to its own objective and iteration budget. Phases do not share
working memory: the only thing carried from one phase to the next is what you wrote
down. Anything proven but unrecorded is lost at the phase boundary.

---

## PHASE 01 — `web_discovery`  (40 iterations)

### Fingerprint the stack

**Objective.** Identify what is running so later playbooks can be selected sensibly.

**Techniques (4):**

1. Identify server, framework and client technology from headers, cookies, error pages, asset names and response shapes.

2. Note the authentication mechanism and session representation (cookie names, token formats, headers).

3. Record the stack explicitly: it determines which stack- specific playbook should run next (for example a client-side .NET or SPA bundle, or a particular reverse proxy).

4. Identify the API style and RETRIEVE every schema or documentation document published, not just the first one you find - a framework's human-readable API index and its machine-readable specification routinely disagree, and the spec is usually far larger. A schema document is not a finding to note and move on from; it is an inventory to consume. Resolve every operation it declares to the concrete request path and method a client would actually send, because frameworks commonly name operations separately from their routes, and record those paths - including the ones no page links to.

### Enumerate the surface

**Objective.** Map endpoints, parameters and inputs.

**Techniques (3):**

1. Enumerate routes and endpoints from metadata documents, client code, sitemaps and directory discovery.

2. Record every parameter and input point, including headers and cookies, and which are reflected in responses.

3. For each endpoint note whether it responds without authentication, and what differs when authenticated. This baseline is what later control tests compare against - capture it carefully.

### Collect the client payload

**Objective.** Everything the browser receives is public and must be retrieved.

**Techniques (3):**

1. Download what the client downloads: scripts, bundles, source maps, compiled binaries, WebAssembly, configuration blobs.

2. Compiled or minified client code must be unpacked or decompiled before it can be searched. A clean search over a binary or a minified bundle is NOT evidence of absence.

3. Record where artifacts were written so later playbooks reuse them rather than downloading again.

### Write the inventory

**Objective.** Leave a durable, structured record.

**Techniques (2):**

1. Save to notes: technology stack, endpoints with auth status, parameters, client artifacts and their paths, and any credential-bearing material observed.

2. Do not attempt exploitation here. Flag candidates for the category playbooks instead, with the evidence that makes them candidates.

---

## PHASE 02 — `blazor_wasm`  (60 iterations)

### Fingerprint the client-side .NET delivery

**Objective.** Decide whether .NET assemblies are shipped to the client, and find the manifest or loader that lists them. Filenames and layout vary by .NET version and by product — investigate what is actually served rather than assuming a fixed path.

**Techniques (4):**

1. Read the site root and app host pages and look at how the app boots. A loader referencing WebAssembly means assemblies ship; a server-side render mode means they do not and this playbook does not apply. Newer unified loaders can mean either - determine which rather than guessing.

2. Asset names are frequently fingerprinted with a content hash, so match on stems and patterns, not exact filenames.

3. Respect any <base href> - the framework directory is relative to it, so probe both the site root and the base path.

4. Find the assembly inventory by whatever route exists: a boot manifest file, a boot config embedded in or fetched by the runtime JavaScript, or the loader script itself. If one route does not exist on this target, try the next; the loader must reference the assets somehow.

### Prepare the decompilation toolchain

**Objective.** Get a working IL decompiler BEFORE analysing anything, then stop thinking about tooling. Skipping this produces false negatives; over-investing in it wastes the entire step budget.

**Techniques (12):**

1. Check what is already available in ONE compound command rather than a sequence of separate probes: look for common decompilers on PATH, in per-user tool directories, and for a .NET runtime. Batch independent checks - you may also issue several tool calls in a single turn.

2. If a decompiler is present, immediately prove it actually runs (invoke its help or version). If it works, the toolchain is DONE: stop, record it, and move to the next phase. Do not install anything and do not evaluate alternatives. Toolchain hunting is the single largest time sink in this assessment.

3. Record the exact working invocation - including any environment prefix - both as a note and to a file on disk. THIS PHASE IS ONCE-ONLY: before any later tooling check or install, read that back and reuse it verbatim. A decompiler proven earlier in the session stays valid even if you no longer recall proving it.

4. A .NET decompiler distributed as a managed tool needs a matching runtime. If it is found but refuses to launch complaining the runtime is missing, the runtime is usually present but undiscovered - set the appropriate environment variable to point at it and retry once before concluding it is unavailable.

5. Only if nothing usable exists, install by the least invasive route available: an existing SDK's tool installer, the vendor's rootless install script, a distro package if the repo carries one, or a container image that already has the SDK. Stop at the first success.

6. NEVER GUESS A VERSION NUMBER. If an install fails, the usual cause is that the newest published release targets a newer runtime than the SDK installed here - so pinning an older release is right, but you must look up which releases exist instead of inventing one. Query the package feed for the actual version list, then choose from it. Version schemes vary and are not always three-part: a package may publish four-part versions, so a plausible-looking guess will simply not exist and every attempt will fail identically no matter how many you try.

7. Check what runtime you actually have before choosing that version, and pick a release built for it rather than the newest one. Two failed installs of the same package mean your version string is wrong, not that the package is unavailable.

8. HARD LIMIT: at most SIX install attempts across ALL routes for the entire assessment. Count them. On the sixth failure stop trying to install anything and go to the fallback below. A seventh attempt has never once succeeded and the budget spent here is taken directly from finding vulnerabilities.

9. Two routes are forbidden because they cannot work and have wasted entire runs: (1) Python and JavaScript package managers do not carry a .NET decompiler - `pip install` of anything decompiler-shaped is always wrong, whatever the name looks like; (2) do not clone or build a decompiler from source. If you have typed either, stop and go to the fallback.

10. REQUIRED FALLBACK, and it usually works: if no decompiler can be obtained, extract string literals directly from the assemblies as UTF-16. .NET stores literals in the #US metadata heap encoded UTF-16LE, so a default ASCII strings pass shows almost nothing and looks like the file holds no secrets - which is exactly the false negative that makes this step feel pointless. Use the little-endian 16-bit encoding option of your strings utility (on GNU binutils, the `-e l` flag). This is a last resort, not a substitute for decompiling: it recovers literal values but not the code that uses them, so say in your findings that you could not decompile and note what that leaves unproven.

11. An IL disassembler is also an acceptable fallback if a C# decompiler cannot be obtained; say so in your findings if you had to fall back.

12. Time-box this. Working decompiler: move on. Six failed install attempts: use the fallback, note the limitation, and CONTINUE THE ASSESSMENT - failing to obtain a tool is never a reason to end the run without analysing the assemblies you already hold.

### Retrieve the shipped assemblies

**Objective.** Download what the browser actually receives.

**Techniques (3):**

1. Read manifests with a real GET. A HEAD request returns headers only and tells you nothing about contents.

2. Prioritise application assemblies over framework/runtime ones. Shared libraries referenced by both client and server are the highest-value targets, because developers often forget that half of a shared project ships to the browser.

3. Verify each download is a real assembly and not an error page or empty file - check size and leading bytes. Keep everything in ONE working directory and do not re-download assemblies you already have; repeated downloads into new directories waste the budget.

### Decompile to source before searching

**Objective.** Convert retrieved assemblies to readable source. Do this first - analysis of raw binaries is unreliable.

**Techniques (3):**

1. Decompile each assembly as the NEXT action after retrieving it. Do not search, grep or triage the binaries first.

2. Know whether your invocation produced a directory of sources or a single file, and remember which - later searching a path as if it were the other form silently returns nothing and looks like the decompile failed.

3. Decompile EVERY application assembly retrieved, not just the first or the most obviously named. The entry-point client assembly often holds only UI code while the interesting material sits in a referenced shared library.

### Hunt secrets in the decompiled source

**Objective.** Find embedded credentials and sensitive material. Search along several INDEPENDENT axes and iterate — no single pattern is sufficient, and you are expected to devise your own.

**Techniques (5):**

1. Search the decompiled SOURCE, never the binaries, and always with line numbers so you can navigate to hits.

2. Cover these independent axes, designing patterns yourself and refining them as you learn what this codebase looks like:
  - BY NAME: identifiers and comments suggesting credentials.
  - BY DECLARATION: compile-time constants and static readonly fields, which is where embedded values structurally live.
  - BY SHAPE: string literals that look like key material - long, unbroken, high-entropy, base64/hex-like, or padded/repeating.
  - BY USE: cryptographic and auth APIs, and what gets passed to them.
  - BY CONFIG: endpoints, hostnames and connection strings.

3. TRACE INDIRECTION. A crypto call usually references an identifier rather than a literal. That is a lead, not an answer: search for that identifier's definition and repeat until you reach the actual value. Expect several hops, and report the value, not the variable name.

4. Do not read whole decompiled files looking for secrets - they run to thousands of lines and output is truncated long before the interesting line. Search for candidates, then read only the surrounding lines of each hit.

5. Record each finding with the assembly, namespace, type and member it came from, and note whether that assembly is referenced by the client directly or transitively - a secret in a shared library usually means nobody realised it shipped at all.

### Exploit server trust in client material

**Objective.** Determine what the recovered material unlocks. A key is only a finding once you show what it grants.

**Techniques (4):**

1. Enumerate the API surface before choosing a target - the endpoint that trusts this material may not be the obvious one, and may appear in API metadata or a schema document you already have.

2. Reimplement the client's routine from the decompiled source exactly; the client code is the specification.

3. Exercise the endpoint with attacker-controlled input protected by the recovered material, and compare against what an unauthenticated caller gets without it.

4. Inspect responses for data the public API does not otherwise expose - credentials, tokens, internal identifiers, or fields absent from the documented contract.

---

## PHASE 03 — `a01_a07_access_auth`  (60 iterations)

### Object and function level access

**Objective.** Determine what can be reached without the right identity.

**Techniques (5):**

1. Request objects belonging to other identifiers and compare responses. Where a directory, index or lookup endpoint hands out identifiers, enumerate them and then RETRIEVE THE RECORDS THEMSELVES - that enumeration is possible is a finding, but the records are the loot. Record each one in full, including fields whose purpose is not yet clear: an opaque or credential-shaped value sitting inside a record you can already read is frequently the input to a later step, and worth more than the enumeration that found it.

2. Compare anonymous, low-privilege and high-privilege views of the same endpoint. Differences reveal missing checks; identical results for anonymous and authenticated mean the resource is simply public - say so rather than claiming a bypass.

3. Test privileged functionality directly rather than through the UI, including administrative routes discovered in client code or metadata.

4. Vary what you send, not merely what the client sends: exercise every HTTP method an endpoint accepts, and every parameter value it will take. Where a parameter looks like an index, offset, page or sequential id, WALK IT - 1, 2, 3 and outwards - because such endpoints commonly return one record per position and will enumerate the whole collection. Let entropy decide whether guessing is worth anything: small integers, short sequences and predictable defaults are worth brute forcing, while UUIDs, hashes and random tokens are not - never invent one, obtain it from the application instead.

5. Probe endpoints that dispatch, batch, proxy or import: reaching a handler indirectly frequently bypasses checks applied to its direct route. Compare the direct and indirect result explicitly.

### Authentication and session handling

**Objective.** Assess how identity is established and maintained.

**Techniques (4):**

1. Test for default, seeded or well-known credentials.

2. Examine the session representation: is it random, or does it encode or derive from something predictable or recoverable?

3. Assess protections against automated guessing, but do NOT run volumetric guessing here - note the absence of a control rather than proving it by force.

4. If credential material is recoverable elsewhere in the assessment, test it here for reuse across accounts and across every distinct authentication surface.

### Prove and bound the impact

**Objective.** Convert access findings into demonstrated, bounded impact.

**Techniques (3):**

1. For every claimed bypass, run and report the control test: the same request without the material or identity. A finding without a control result is not a finding.

2. Establish breadth - one object or all of them, one account or every account. Breadth drives severity more than technique.

3. Record what a compromised session actually grants: roles, privileged functions, other users' data.

### Verify before reporting

**Objective.** Apply the same evidence standard to every finding, so results are comparable across categories.

**Techniques (5):**

1. PROOF DISCIPLINE - label every finding DEMONSTRATED (you executed it and the response proves it, quote that response), INFERRED (follows from evidence but was not executed), or UNVERIFIED (suspected from a version, component or code pattern only). Identifying software is never a demonstration; never write 'confirmed' without having executed something.

2. RUN THE CONTROL TEST. Before claiming any access or bypass, repeat the request WITHOUT the credential, token, header or material you believe is responsible. If the result is the same, you have proven nothing - the resource was already reachable. State the control result alongside the finding. This single omission is the most common source of false critical findings.

3. BUDGET DISCIPLINE - rank leads by evidence strength (material in hand > observed behaviour > suspicion from a version string) and give each a step budget. STOP RULE: about 8-10 consecutive steps on one lead with no new evidence means move on, recording what you tried.

4. Record findings to notes as you go, with the endpoint, the request, the response and the control result, so later phases and the report can use them.

5. Stay non-destructive: prefer read-only proof, do not modify or delete data, do not lock accounts, and stop once the point is demonstrated.

---

## PHASE 04 — `a02_misconfiguration`  (60 iterations)

### Exposed interfaces and content

**Objective.** Find what should not be reachable.

**Techniques (4):**

1. Probe for administrative, debug, health, metrics, profiler and documentation interfaces, and determine whether each requires authentication.

2. Look for framework metadata, schema or introspection endpoints that disclose the full API surface to anonymous callers.

3. Check for default, sample or installer content left in place, and for directory listings.

4. Look for backup, temporary, versioned or editor artifacts beside known paths.

### Response hardening and policy

**Objective.** Assess configuration visible in responses.

**Techniques (4):**

1. Review security-relevant response headers and cookie attributes, and report what is missing rather than assuming exploitability.

2. Test CORS behaviour with unexpected and null origins, and check whether credentials are permitted cross-origin.

3. Check whether errors return stack traces, framework versions, file paths or internal hostnames.

4. Note TLS and transport configuration where observable.

### Prove impact, not presence

**Objective.** Distinguish a hardening gap from an exploitable flaw.

**Techniques (2):**

1. A missing header is a hardening finding, not a vulnerability, unless you demonstrate what it enables. Say which you are reporting.

2. For any exposed interface, show what it actually discloses or allows, and run the control test against an unauthenticated baseline.

### Verify before reporting

**Objective.** Apply the same evidence standard to every finding, so results are comparable across categories.

**Techniques (5):**

1. PROOF DISCIPLINE - label every finding DEMONSTRATED (you executed it and the response proves it, quote that response), INFERRED (follows from evidence but was not executed), or UNVERIFIED (suspected from a version, component or code pattern only). Identifying software is never a demonstration; never write 'confirmed' without having executed something.

2. RUN THE CONTROL TEST. Before claiming any access or bypass, repeat the request WITHOUT the credential, token, header or material you believe is responsible. If the result is the same, you have proven nothing - the resource was already reachable. State the control result alongside the finding. This single omission is the most common source of false critical findings.

3. BUDGET DISCIPLINE - rank leads by evidence strength (material in hand > observed behaviour > suspicion from a version string) and give each a step budget. STOP RULE: about 8-10 consecutive steps on one lead with no new evidence means move on, recording what you tried.

4. Record findings to notes as you go, with the endpoint, the request, the response and the control result, so later phases and the report can use them.

5. Stay non-destructive: prefer read-only proof, do not modify or delete data, do not lock accounts, and stop once the point is demonstrated.

---

## PHASE 05 — `a04_cryptographic`  (60 iterations)

### Find embedded and exposed key material

**Objective.** Anything shipped to a client is public.

**Techniques (5):**

1. Search decompiled or unpacked client artifacts - never the raw binaries or minified bundles, which hide literals.

2. Search along independent axes and iterate, designing patterns yourself: BY NAME (identifiers suggesting secrets), BY DECLARATION (compile-time constants and static fields), BY SHAPE (long unbroken high-entropy or base64/hex-like literals), BY USE (cryptographic and auth APIs and what is passed to them), BY CONFIG (endpoints, connection strings).

3. A name-based search is NOT evidence of absence: real secrets are often obfuscated so no dictionary word appears, and are declared under neutral names. The axes that ignore naming are the ones that find those.

4. Trace indirection: a crypto call usually references an identifier, not a literal. Follow it to the value, expecting several hops, and report the value rather than the variable name.

5. Secret scanners are worth running as an extra signal but detect mostly known provider credential formats; a clean scanner result must never be reported as 'no secrets present'.

### Assess how cryptography is used

**Objective.** Weak use of good primitives is as damaging as weak primitives.

**Techniques (3):**

1. Identify algorithms, modes, key sizes and IV or nonce handling, and whether integrity is protected as well as confidentiality.

2. Determine whether credentials are stored reversibly - encrypted or encoded rather than hashed. Reversible storage of a credential is a finding in itself.

3. Assess whether tokens are random or derived from something predictable or recoverable.

### Join the key to the material

**Objective.** The step that converts two moderate findings into a critical one.

**Techniques (4):**

1. STOP AND JOIN THEM - the moment you hold BOTH a secret AND any opaque stored value (encrypted token, protected field, cookie, unexplained blob), attempt to decode that value with that secret as your NEXT action, before writing either up. Reported separately they read as 'a key leaked' and 'some data leaked'; joined they are frequently FULL ACCOUNT TAKEOVER. Assume the join works and disprove it.

2. Apply the secret to every opaque value you hold, for every account, not only the first.

3. Reimplement the owner's routine exactly from recovered source, and enumerate accepted operations from that source before composing requests. Never invent an operation name: it is rejected as unknown even when the material is correct.

4. Obtain a value the TARGET produced before you build anything: round-tripping your own input proves your code, not a finding. Holding no such value is a retrieval task rather than a dead end - re-read the recorded surface, and treat a rejection on a parameterised route as a wrong or missing identifier rather than absent data. Prove the implementation on target-produced material before trusting any rejection.

### Verify before reporting

**Objective.** Apply the same evidence standard to every finding, so results are comparable across categories.

**Techniques (5):**

1. PROOF DISCIPLINE - label every finding DEMONSTRATED (you executed it and the response proves it, quote that response), INFERRED (follows from evidence but was not executed), or UNVERIFIED (suspected from a version, component or code pattern only). Identifying software is never a demonstration; never write 'confirmed' without having executed something.

2. RUN THE CONTROL TEST. Before claiming any access or bypass, repeat the request WITHOUT the credential, token, header or material you believe is responsible. If the result is the same, you have proven nothing - the resource was already reachable. State the control result alongside the finding. This single omission is the most common source of false critical findings.

3. BUDGET DISCIPLINE - rank leads by evidence strength (material in hand > observed behaviour > suspicion from a version string) and give each a step budget. STOP RULE: about 8-10 consecutive steps on one lead with no new evidence means move on, recording what you tried.

4. Record findings to notes as you go, with the endpoint, the request, the response and the control result, so later phases and the report can use them.

5. Stay non-destructive: prefer read-only proof, do not modify or delete data, do not lock accounts, and stop once the point is demonstrated.

---

## PHASE 06 — `a05_injection`  (60 iterations)

### Identify injection candidates

**Objective.** Find where input reaches an interpreter.

**Techniques (3):**

1. Work from the inventory: every parameter, header, cookie and body field is a candidate, including those only the client normally sets.

2. Note where input is reflected in responses, stored and rendered later, or appears to influence a query, path, command or template.

3. Prefer detection that is safe and reversible: syntax that would provoke a parse difference or an error, rather than anything destructive.

### Confirm by differential behaviour

**Objective.** Prove interpretation, not coincidence.

**Techniques (4):**

1. Confirm an injection by demonstrating a controlled difference between two inputs - an error that appears and disappears, a boolean condition that changes the result, a timing difference you can repeat. A single odd response is not proof.

2. For cross-site scripting, show the payload is stored or reflected AND rendered in a context where it would execute. Quote the response showing the unescaped payload.

3. Do not run destructive payloads, do not modify or drop data, and do not attempt command execution beyond a harmless, clearly identifiable proof.

4. For claimed code or command execution the proof is OUTPUT of a command you chose, returned by the target - not a payload you sent and not an error that looks interesting. Match the payload to the actual platform.

### Bound the impact

**Objective.** State what the injection actually reaches.

**Techniques (2):**

1. Establish what the injection can read or affect, and whether it crosses a trust boundary.

2. Run the control test: the same request with benign input, reported alongside.

### Verify before reporting

**Objective.** Apply the same evidence standard to every finding, so results are comparable across categories.

**Techniques (5):**

1. PROOF DISCIPLINE - label every finding DEMONSTRATED (you executed it and the response proves it, quote that response), INFERRED (follows from evidence but was not executed), or UNVERIFIED (suspected from a version, component or code pattern only). Identifying software is never a demonstration; never write 'confirmed' without having executed something.

2. RUN THE CONTROL TEST. Before claiming any access or bypass, repeat the request WITHOUT the credential, token, header or material you believe is responsible. If the result is the same, you have proven nothing - the resource was already reachable. State the control result alongside the finding. This single omission is the most common source of false critical findings.

3. BUDGET DISCIPLINE - rank leads by evidence strength (material in hand > observed behaviour > suspicion from a version string) and give each a step budget. STOP RULE: about 8-10 consecutive steps on one lead with no new evidence means move on, recording what you tried.

4. Record findings to notes as you go, with the endpoint, the request, the response and the control result, so later phases and the report can use them.

5. Stay non-destructive: prefer read-only proof, do not modify or delete data, do not lock accounts, and stop once the point is demonstrated.

---

## PHASE 07 — `a08_integrity`  (50 iterations)

### Find integrity assumptions

**Objective.** Locate where the application trusts data it should verify.

**Techniques (3):**

1. Identify endpoints accepting serialized objects, type hints, polymorphic payloads or object graphs, from recovered source where available.

2. Look for client-supplied values used in security decisions, pricing, identity or state transitions.

3. Check whether third-party assets are loaded without integrity verification, and whether update or plugin mechanisms verify signatures.

### Test carefully and honestly

**Objective.** Deserialization claims are where reports most often overstate.

**Techniques (3):**

1. If a deserializer accepts a type discriminator, first read the recovered source to learn the exact discriminator and the types actually permitted. Guessing a discriminator produces an 'unknown type' error that proves nothing.

2. A type that merely exists is not a gadget: a gadget chain must INVOKE something. If you cannot demonstrate invocation, the finding is UNVERIFIED and must be reported that way.

3. Test tampering with client-supplied values that influence server-side decisions, and show the changed outcome.

### Verify before reporting

**Objective.** Apply the same evidence standard to every finding, so results are comparable across categories.

**Techniques (5):**

1. PROOF DISCIPLINE - label every finding DEMONSTRATED (you executed it and the response proves it, quote that response), INFERRED (follows from evidence but was not executed), or UNVERIFIED (suspected from a version, component or code pattern only). Identifying software is never a demonstration; never write 'confirmed' without having executed something.

2. RUN THE CONTROL TEST. Before claiming any access or bypass, repeat the request WITHOUT the credential, token, header or material you believe is responsible. If the result is the same, you have proven nothing - the resource was already reachable. State the control result alongside the finding. This single omission is the most common source of false critical findings.

3. BUDGET DISCIPLINE - rank leads by evidence strength (material in hand > observed behaviour > suspicion from a version string) and give each a step budget. STOP RULE: about 8-10 consecutive steps on one lead with no new evidence means move on, recording what you tried.

4. Record findings to notes as you go, with the endpoint, the request, the response and the control result, so later phases and the report can use them.

5. Stay non-destructive: prefer read-only proof, do not modify or delete data, do not lock accounts, and stop once the point is demonstrated.

---

## PHASE 08 — `a09_logging_alerting`  (25 iterations)

### Exposed logs and leaked material

**Objective.** Logs are frequently reachable and frequently contain secrets.

**Techniques (3):**

1. Probe for log viewers, request-log endpoints, diagnostic or profiler interfaces, and downloadable log files.

2. If any log content is reachable, search it for credentials, tokens, session identifiers, keys and personal data - logged secrets are a finding in their own right.

3. Check whether error responses disclose material that belongs only in a log.

### Observable reaction to security events

**Objective.** Determine whether anything appears to notice.

**Techniques (3):**

1. Perform a small number of clearly security-relevant but non- destructive actions (a failed authentication, access to a forbidden object) and observe whether behaviour changes - throttling, challenge, lockout, or notification.

2. Test session collision: authenticate the same account from a second, independent context and observe whether the first session is invalidated, whether a notification is produced, and whether concurrent sessions are permitted silently. A browser tool helps here; if unavailable, approximate with two separate cookie jars and say which method was used.

3. Report absence of an observable reaction as exactly that: not observed from outside, which is not the same as not logged.

### Verify before reporting

**Objective.** Apply the same evidence standard to every finding, so results are comparable across categories.

**Techniques (5):**

1. PROOF DISCIPLINE - label every finding DEMONSTRATED (you executed it and the response proves it, quote that response), INFERRED (follows from evidence but was not executed), or UNVERIFIED (suspected from a version, component or code pattern only). Identifying software is never a demonstration; never write 'confirmed' without having executed something.

2. RUN THE CONTROL TEST. Before claiming any access or bypass, repeat the request WITHOUT the credential, token, header or material you believe is responsible. If the result is the same, you have proven nothing - the resource was already reachable. State the control result alongside the finding. This single omission is the most common source of false critical findings.

3. BUDGET DISCIPLINE - rank leads by evidence strength (material in hand > observed behaviour > suspicion from a version string) and give each a step budget. STOP RULE: about 8-10 consecutive steps on one lead with no new evidence means move on, recording what you tried.

4. Record findings to notes as you go, with the endpoint, the request, the response and the control result, so later phases and the report can use them.

5. Stay non-destructive: prefer read-only proof, do not modify or delete data, do not lock accounts, and stop once the point is demonstrated.

---

## PHASE 09 — `a10_exceptional`  (25 iterations)

### Probe boundaries and malformed input

**Objective.** Find where the application stops handling input gracefully.

**Techniques (3):**

1. For representative endpoints, submit wrong types, empty values, missing required fields, extra unexpected fields, boundary numbers, and structurally malformed bodies.

2. Try oversized values within reason - enough to test a limit, not enough to exhaust resources. Do not pursue denial of service.

3. Record unhandled exceptions, stack traces, inconsistent status codes, and any response that discloses internal structure.

### Does failure open or close?

**Objective.** The security-relevant question.

**Techniques (3):**

1. Determine whether an error path skips a control - whether a malformed request reaches a handler that a well-formed one could not, or whether a failed check results in access rather than denial.

2. Where an error reveals interpreter or framework detail, record it as an oracle for injection and integrity testing.

3. Run the control test: the same request well-formed, reported alongside.

### Verify before reporting

**Objective.** Apply the same evidence standard to every finding, so results are comparable across categories.

**Techniques (5):**

1. PROOF DISCIPLINE - label every finding DEMONSTRATED (you executed it and the response proves it, quote that response), INFERRED (follows from evidence but was not executed), or UNVERIFIED (suspected from a version, component or code pattern only). Identifying software is never a demonstration; never write 'confirmed' without having executed something.

2. RUN THE CONTROL TEST. Before claiming any access or bypass, repeat the request WITHOUT the credential, token, header or material you believe is responsible. If the result is the same, you have proven nothing - the resource was already reachable. State the control result alongside the finding. This single omission is the most common source of false critical findings.

3. BUDGET DISCIPLINE - rank leads by evidence strength (material in hand > observed behaviour > suspicion from a version string) and give each a step budget. STOP RULE: about 8-10 consecutive steps on one lead with no new evidence means move on, recording what you tried.

4. Record findings to notes as you go, with the endpoint, the request, the response and the control result, so later phases and the report can use them.

5. Stay non-destructive: prefer read-only proof, do not modify or delete data, do not lock accounts, and stop once the point is demonstrated.

---

## PHASE 10 — `consolidate_findings`  (40 iterations)

### Inventory the sources

**Objective.** Build the list of files to process. Do NOT read their contents in this phase.

**Techniques (5):**

1. Read the saved notes for this workspace first - that is the structured record, and it is usually incomplete. It is small; reading it whole is fine.

2. List, but do not open: the per-phase reports for this assessment, the phase log files, and the artifacts on disk (retrieved binaries, decompiled or unpacked source, captured responses).

3. Record the artifact paths to notes now, so later phases reuse them rather than fetching everything again.

4. Report the file list and their sizes. Anything over about 40 KB must be searched with grep rather than read whole in the next phase.

5. Do NOT cat a log or a report here. The whole point of this phase is to know what exists before opening anything.

### Process one source, record, then move on

**Objective.** Extract findings from each source individually and write them to notes BEFORE opening the next source.

**Techniques (4):**

1. Work through the inventory ONE FILE AT A TIME. For each file: extract its findings, write them to notes with the notes tool, and only then move to the next file. Never hold two large sources at once.

2. READ THE PHASE LOGS. This is the channel nothing else reads and the reason this phase exists. Search them for evidence that was stated but never recorded: recovered values, decoded output, tokens and credentials, status codes that changed, headers observed to be missing, error text, and any conclusion the assistant narrated about combining two things.

3. Write one note per distinct finding, naming it after the issue rather than the file it came from, so the same issue found twice collides instead of duplicating.

4. If a source yields nothing, say so and move on. Do not re-read a file you have already processed.

### Normalise into one list

**Objective.** One entry per distinct issue, deduplicated and comparable.

**Techniques (4):**

1. Produce one entry per distinct issue with: what it is, where it is (endpoint, or file, type and member), the evidence observed, whether a control test was run and its result, and the current proof level.

2. INCLUDE LOW-SEVERITY AND INFORMATIONAL OBSERVATIONS. Missing security headers, permissive cross-origin policy, verbose errors and stack traces, exposed metadata and version disclosure are routinely dropped between phases precisely because they are individually minor. They belong in the report, and several of them are also inputs to chaining.

3. Separate what has been demonstrated from what is asserted, and carry that distinction forward rather than flattening it.

4. Build an explicit UNCOMBINED MATERIAL list: every secret, key, token, hash, cookie or opaque value held, that has not yet been applied to anything. The next phase needs exactly this list, and material sitting unused is the most common missed critical.

### Record to notes

**Objective.** Write the consolidated list down. This is the entire output of the phase - an unrecorded finding does not survive to the next one.

**Techniques (2):**

1. Record every normalised finding using the notes tool, one note per finding, including its evidence and control result. Notes are the only channel later phases reliably receive.

2. Record the UNCOMBINED MATERIAL list as its own note so the following phase can act on it directly.

---

## PHASE 11 — `chain_findings`  (80 iterations)

### Inventory what is already known

**Objective.** Build a single list of everything previous passes discovered. Do not re-run reconnaissance - the work is already done and repeating it wastes the run.

**Techniques (8):**

1. START FROM THE CONSOLIDATED NOTES. A consolidation pass ran immediately before this one and wrote every finding gathered so far to notes, including material recovered from phase logs that exists nowhere else. Read those notes FIRST and treat them as the authoritative input - they are the complete record, and anything you do not carry out of this phase is lost for the rest of the assessment.

2. Count the consolidated entries and write the number down. You will be required to account for every one of them at the end of this playbook.

3. Read the saved notes and any findings recorded in this workspace, and list the artifacts already on disk (retrieved binaries, decompiled source, captured responses).

4. Read the decompiled source and captured output you already have rather than fetching anything again.

5. Write the inventory as two explicit lists: (1) CAPABILITIES - the keys, algorithms, credentials and sessions you hold; (2) MATERIAL - the opaque values the target has actually emitted (encrypted or encoded field values, blobs, cookies, tokens) together with the request that produced each one. Count both lists. If one of them is empty that is your next task, not a dead end: a capability with nothing to apply it to is an unfinished finding, and so is material you cannot yet read.

6. STOP RULE: if roughly 8-10 consecutive steps on one lead produce no NEW evidence - no new access, no new data, no change in the error you get back - abandon it, record what you tried and what it would take to confirm, and move to the next lead. Returning later with fresh information is fine; grinding is not.

7. COUNT REPETITION BY WHAT THE COMMAND DOES, NOT HOW IT IS SPELLED. Re-running the same tool against the same file or endpoint with a widened context window, a reordered pattern or an extra alternation is the SAME step, not a new one. Three attempts of that kind without new information means the information is not there: the identifier you are searching for does not exist in that file, or does not exist under that name. Change target or change approach - search a different file, list what the file actually defines, or ask the running service - rather than re-phrasing the same query a fourth time.

8. Before repeating any search, say what NEW thing the next attempt could reveal that the last one could not. If there is no answer, that is the signal to stop.

### Validate every finding against the live target

**Objective.** Turn hypotheses into demonstrated facts. An unvalidated secret is worth reporting only as a possibility.

**Techniques (14):**

1. For each piece of recovered MATERIAL, design a concrete test that proves whether it is live and accepted by the target. If the material is used by code you have decompiled, reimplement that code exactly - same algorithm, mode, padding, encoding and any envelope or timestamp structure. The recovered source is the specification; do not guess at the format. A RECOVERED CREDENTIAL IS ALREADY A FINDING - record it as one the moment it comes out, then try to get it accepted. Submit it to every route the application exposes for credentials rather than the first one you find, because applications commonly expose several and a protection enforced on one route frequently does not apply to the others. Acceptance is a SECOND and higher finding; refusal everywhere leaves the first one standing. Never hold back the recovery because its use is still unproven.

2. MEASURE THE MATERIAL AND USE THE COPY YOU MEASURED. Never count characters by eye - runs of repeated padding are miscounted and the machine is not. Read the literal out of the file with a command, hold it in a variable, print its length from that variable, and pass THAT SAME variable onward; retyping it into a second command is where a character is gained or lost. A plausible length is not a correct one: most ciphers accept several key sizes, so a bad extraction often lands on a legal one and simply produces garbage. IF THE LENGTH IS WRONG THE EXTRACTION IS WRONG, NOT THE SECRET - re-read it from the same file programmatically before doubting the value or reaching for a lower-level artifact.

3. SELF-TEST YOUR REIMPLEMENTATION BEFORE TRUSTING ANY RESULT. An incorrect implementation and correctly-rejected material produce the same rejection, so a failed request tells you nothing until you have proven your own code. Do both checks:
  (i) ROUND TRIP - transform a known value forward then back and confirm you recover the original exactly. This proves internal consistency, and nothing more.
  (ii) AGAINST THE TARGET'S OWN OUTPUT - take any value the TARGET produced using this material (a token, cookie, stored field, or a captured response) and process it with your implementation. Recovering sensible plaintext from something the server generated is the only proof your implementation matches theirs.

4. Sanity-check the SHAPE of what you produce against a real sample from the target: length, block alignment, whether a prefix such as an IV or nonce is present, and the encoding. A structurally plausible output that still fails is a strong hint the key bytes or their derivation are wrong, not the framing.

5. TREAT REJECTIONS AS AN ORACLE, AND AS EVIDENCE ABOUT YOUR REQUEST AT LEAST AS OFTEN AS ABOUT YOUR MATERIAL. Distinguish the failure stages: rejection during decryption or verification (your material or algorithm is wrong), acceptance followed by a parse or schema complaint (the crypto is RIGHT and your inner structure is wrong), and complaints about an unknown or unsupported operation (both are right and you named something the server does not offer). Moving from one class of error to another is progress. This matters most when the material came from the application's own stored data: such a value is very unlikely to be wrong, so a rejection points at the request shape first. Vary one thing at a time.

6. ENUMERATE THE ACCEPTED VALUES FROM THE SOURCE FIRST - required, not a precaution. Before composing any request to a dispatcher, router, command or batch style endpoint, read the decompiled handler for what it actually accepts: switch/case labels, if-else comparisons, enum members, dictionary keys or its route table. Write that list down before sending anything. NEVER invent an operation name - a placeholder such as 'Test' or a guessed resource is rejected as unknown even when your credentials and encryption are perfect, which wastes the attempt and looks like the material failed when it did not. Work the enumerated values in order of what returns the most data or touches the most sensitive handler; a value rejected as unknown while others are accepted tells you the dispatcher works and your envelope is valid.

7. ANSWER 'WHAT DOES THIS REQUEST NEED' BY SEARCHING BEFORE PROBING. Guessing a request's shape and reading the rejection is the slowest way to learn it and the easiest to misread, and earlier phases have usually already collected the answer. Before composing a request to any endpoint you have not successfully used, search in this order: saved notes and prior phase reports describing it; any machine-readable API description the target publishes (OpenAPI or Swagger documents, WSDL, GraphQL introspection, metadata or discovery endpoints); the decompiled source for the handler, its route attribute and its request type; and the client-side code for the call site. This applies to authentication requests especially, where it is most often skipped - such endpoints commonly need more than a username and password, such as a provider or scheme name, a realm, a client identifier, a CSRF or antiforgery token, or a specific content type.

8. Say where the shape came from and how sure you are of it. A field list read from a request type in source, or from a published specification, is reliable. A field list inferred from a URL or a guess is not, and a request built from one that fails has not tested anything. Record what you found so a later phase does not repeat the search.

9. OBSERVE THE APPLICATION DOING IT ITSELF. If a browser tool is available and the application has a user interface for the operation, drive that interface and capture the request it issues - route, method, headers, content type, every field name and its exact casing - then mirror it. A working example produced by the application is the most reliable specification obtainable, it costs one page load, and it settles questions that reading source can leave open.

10. ESTABLISH BOTH POLES BEFORE JUDGING A CREDENTIAL. A rejection says the request was not accepted; it does not say whether the credential, the field set, the route or the encoding was wrong, and without a reference for acceptance the only reading available is 'the material is bad' - which discards correct work. Get references first: read the route from source rather than guessing paths, since a guessed path returns the same rejection as a wrong credential; if any credentials are already known, authenticate with them once and keep the success response - status, headers, cookies, body; and send a deliberately wrong credential to the same route with the same shape and keep that response too.

11. With both references, a rejection is interpretable. If your attempt does not even match the FAILURE shape - a different status, a different error, a complaint about a missing field - then your request is malformed and the credential has not been tested yet. Only a response matching the failure shape exactly is evidence about the credential itself. State which of the two you observed. Take the credential from where it was produced rather than retyping it: if a script decrypted it, have that script write it to a file and read the file in the request.

12. Prefer a safe read-only proof first (something that returns data or is accepted) over anything that writes or changes state.

13. RECORD THE EVIDENCE THE MOMENT IT IS TRUE. As soon as something is shown to work - a value decrypts, a token is accepted, an endpoint returns what it should not - write the exact request and the exact response with the notes tool immediately, in that same step, before moving to the next lead. Do not save it up to write later. This is not bookkeeping: this phase can be cut off at any point when the step budget runs out, and anything not written down when that happens is lost for the rest of the assessment no matter how conclusively you proved it.

14. If validation fails, do not discard the finding immediately: check your reimplementation against the source, and distinguish 'my test was wrong' from 'the material is not accepted'. Say which one you concluded and why.

### Chain findings into higher severity

**Objective.** Look for combinations. Findings that are individually moderate are frequently critical together.

**Techniques (9):**

1. Cross every item of MATERIAL against every item of SURFACE and ask: does this material unlock, authenticate to, decrypt, sign for, or bypass a control on this surface?

2. Look specifically for surfaces that were previously refused, errored, or returned less data than expected - recovered material often turns exactly those into successes.

3. Watch for dispatch, batch, proxy or import style endpoints that forward requests internally: reaching a handler by that route can bypass the checks applied to its direct route. Compare what the direct route returns against what the indirect route returns.

4. STOP AND JOIN THEM - whenever you hold BOTH a secret AND an opaque stored value (encrypted token, protected field, cookie, unexplained blob), attempt the decode immediately, as the next action, before writing either up. Two findings recorded separately read as 'a key leaked' and 'some data leaked'; joined they are frequently FULL ACCOUNT TAKEOVER. Assume the join works and disprove it.

5. Try to decrypt or decode anything opaque you receive using the material you already recovered; matching a value back to a known algorithm is frequently the whole finding. Do this for every account or object you hold a value for, not just the first.

6. A RESULT PROVEN AGAINST ONE OBJECT IS A RESULT OF UNKNOWN SIZE. The moment a technique works on one account, record, file or record-holder, apply it to the others you can enumerate. Stopping at the first success answers 'is this possible' and leaves 'how much of the system does this reach' unanswered - and the second question is what determines severity and what a reader needs.

7. Cover the privileged cases deliberately. If the population includes accounts or objects with more authority than the one you proved - administrators, operators, service or system accounts, records belonging to other tenants - test those specifically rather than sampling whichever came first. A technique that reaches an ordinary account and one that reaches an administrative account are different findings.

8. Report the count and the composition: how many of the known population were tested, how many were affected, and which privileged ones were among them. If you could not enumerate the population, say what you did test and that the true breadth is unmeasured - that is a real limitation, not a detail to omit.

9. RECORD EACH LINK AS IT IS PROVEN, not once the whole chain is assembled. A chain that is three quarters demonstrated is still a serious finding; a chain you never wrote down is nothing. Write a note per proven step, and update it as the chain grows.

### Report chains with evidence and impact

**Objective.** Produce a defensible write-up of what was demonstrated.

**Techniques (12):**

1. Report each chain as an ordered sequence of steps, each with the request made and the response received.

2. State impact concretely - what data or capability was obtained, and for how many objects or accounts - rather than in the abstract.

3. Establish impact by contrast: show the same result cannot be obtained without the recovered material or the chained route.

4. Label every finding with its proof level and be strict about it: DEMONSTRATED (you executed it and the response proves it - quote that response), INFERRED (follows from evidence but was not executed), or UNVERIFIED (suspected from a version number, library name or code pattern only).

5. Identifying a framework, library or version is NOT a vulnerability finding. A known issue in that component is UNVERIFIED until you execute it against this target and observe the effect. Do not write 'confirmed' on the basis of what software is present, and do not cite an advisory identifier unless you have checked it applies to this deployment.

6. For code execution specifically, the proof is OUTPUT of a command you chose, returned by the target - not a payload you sent, and not an error that merely looks interesting. Match the payload to the actual platform; a Windows shell command against a Unix host proves nothing either way.

7. Set severity from what was DEMONSTRATED. An unproven critical theory is reported as a lead to investigate, never as a critical finding - overstating severity destroys the credibility of the whole report.

8. Name the specific root cause for each link in the chain (the assembly, type and member, or the endpoint and parameter) so it is directly actionable.

9. CARRY EVERY CONSOLIDATED FINDING FORWARD - not only the ones that chained. Chaining is additive: it creates new findings, it does not replace the inputs. A finding that did not combine with anything is still a finding, and the next phase can only review what reaches it.

10. Go back to the count you recorded in the first phase and reconcile against it explicitly. Every consolidated entry must end in exactly one of three states: folded into a chain (name the chain), carried forward unchanged, or dropped as a proven duplicate (name the entry it duplicates). There is no fourth state - if you cannot say which applies, it is carried forward.

11. Write the full carried-forward set to notes, one note per finding, preserving each finding's original evidence, proof level and severity. Do NOT summarise several findings into one note and do not drop the low-severity and informational ones - missing headers, verbose errors and version disclosure are exactly what falls out here, and they are both reportable and inputs to future chains.

12. Findings you could not validate are carried forward too, labelled UNVERIFIED with what you tried. Failing to prove something is a result; silently discarding it is not.

---

## PHASE 12 — `adversarial_review`  (75 iterations)

### Take the draft apart

**Objective.** Turn prose into a checkable list of claims.

**Techniques (5):**

1. Read the draft report and list every distinct claim: what is asserted, against which endpoint, with what evidence, and at what severity and proof level.

2. Separately read the raw notes and evidence from the assessment. List anything supported there that does NOT appear in the draft - omissions are as serious as errors.

3. RECONCILE AGAINST THE CONSOLIDATED SET. The notes contain a consolidated list of findings produced before chaining, and the chaining phase was required to carry every entry forward. Walk that list and account for each entry: present in the draft, folded into a chain that is in the draft, or MISSING.

4. Treat every missing entry as a finding in its own right and recover it - it reached consolidation on evidence, so it is supported until you disprove it. Say plainly in your output that it was dropped between phases; that is a defect in the assessment process and the operator needs to know the pipeline lost it, not just that the finding exists.

5. Identify duplicates: the same underlying issue reported as several findings, or one finding split across categories. Merge them and say so.

### Attempt to refute each claim

**Objective.** Reproduce independently. Assume the claim is wrong.

**Techniques (5):**

1. For every claim, reproduce it yourself against the live target rather than trusting the quoted evidence. Evidence in a draft may be stale, partial or misread.

2. REQUIRED for every access, bypass or authentication claim: run the CONTROL TEST - the identical request WITHOUT the credential, token, header or material said to be responsible. If the result is unchanged, the claim is REFUTED: the resource was already reachable. Report both results side by side.

3. For claimed code execution, require output of a chosen command returned by the target. A payload that was sent, or an interesting error, is not execution.

4. Where a claim is correct but overstated, say so precisely: confirm the part that holds and refute the part that does not.

5. Check severity against what was actually demonstrated and against breadth - one object or all, one account or every account.

### Return a verdict per claim

**Objective.** Evidence for every verdict, in both directions.

**Techniques (15):**

1. Assign each claim CONFIRMED, REFUTED or UNPROVEN.

2. CONFIRMED requires the request and response you obtained yourself, plus the control result showing it does not occur without the material.

3. REFUTED requires the evidence that disproves it - typically a control test producing the same result, or a reproduction attempt that fails.

4. UNPROVEN means you could not settle it: state exactly what additional access or step would settle it.

5. Add any finding you confirmed that the draft omitted, with the same evidence standard.

6. Give a corrected severity for every surviving finding, and list the merges you performed.

7. WRITE EACH VERDICT AS YOU REACH IT, not once every claim is settled. Create the file when you settle your FIRST claim and append each further verdict as it is decided. This phase can stop at any point, and a file written only at the end is the first thing lost when it does - a partial record of real verdicts is worth far more than a complete one that was never written.

8. WRITE THE VERDICT RECORD TO DISK before you finish, at `loot/assessments/<assessment>/adversarial_verdicts.md` (use the assessment directory this run is writing to). This file is the next phase's primary input; it will not re-read the drafts you have just been through, so anything you leave out of it is effectively dropped.

9. Give every entry the same shape, one per claim: ID and short title; VERDICT (CONFIRMED / REFUTED / UNPROVEN); SEVERITY; the EVIDENCE quoted verbatim - the request sent, the response received, any value recovered - not a reference to where the evidence lives; CONTROL result; SCOPE (how many objects or accounts, and whether that was tested or inferred); REPRODUCTION steps; and the two factor sections below.

10. COMPOUNDING FACTORS - what this finding combines with. Name the other findings that make this one worse, and what the combination yields that neither gives alone. Material recovered here that unlocks a surface found elsewhere belongs here, quoting the recovered value. This is where a chain is recorded, and recording it against each part means it survives even if the phase that built the chain is cut short. Write 'none identified' if there are none - never leave it out.

11. MITIGATING FACTORS - what this finding does NOT show. State the next step in the obvious attack that was not attempted or not achieved, any precondition an attacker still needs, and any control that limits it. Recovering a credential without authenticating with it, or reaching an endpoint without extracting from it, belongs here rather than being written up as though it were done. Write 'none identified' if there are none.

12. Quote evidence in full even when it is long. The next phase can only report what this file contains, and a pointer to a file it will not open is the same as no evidence at all.

13. REPRODUCIBILITY IS A PASS CONDITION, NOT A COURTESY. For every CONFIRMED finding, write the exact steps that reproduce it: the full request or command, the required preconditions, and the specific part of the response that demonstrates it. Someone with no access to this assessment must be able to follow them and get the same result. If you cannot write those steps, the finding is UNPROVEN no matter how confident you are.

14. State the SCOPE of every confirmed finding explicitly: how many objects, accounts or endpoints it affects, and whether you established that by testing or by inference. 'One account' and 'every account' are different findings at different severities, and an untested assumption about breadth must be labelled as one.

15. Before finishing, verify each confirmed finding carries all four: scope, validation (including its control test), evidence (the actual request and response), and reproduction steps. Name any finding missing one of them rather than passing it through silently - the final gate cannot report what it cannot check.

---

## PHASE 13 — `final_integrity_gate`  (45 iterations)

### Completeness check

**Objective.** Nothing that was found earlier may vanish silently between phases.

**Techniques (6):**

1. START FROM THE VERDICT RECORD. Read `adversarial_verdicts.md` in this assessment's directory, plus the notes. Those two are your primary input and together they carry the verdicts, the quoted evidence and the scope for every claim that survived review.

2. CHECK THE VERDICT RECORD IS ACTUALLY POPULATED before relying on it. If it is missing, or holds only a header with no verdicts, the review phase did not finish and you have no structured input. Say so plainly in your output and read the per-phase reports directly instead. An empty primary input is not a reason to report less; it is a reason to use the secondary one and record that the pipeline lost a step.

3. DO NOT RE-READ EVERY PER-PHASE REPORT OR PHASE LOG AS A MATTER OF COURSE. Consolidation and review have each already swept them; a third sweep is the single largest waste of this phase's budget and it is why previous runs stopped before finishing. Open a specific report or log only to resolve a NAMED gap - a finding the verdict record mentions without evidence, or a note with no corresponding verdict - and say which gap you are chasing.

4. Compare them. Every finding present before the chaining and review phases must appear in the reviewed set, be marked REFUTED with evidence, or be explicitly listed as dropped with the reason. Silent disappearance is not acceptable.

5. Check the notes for low-severity observations that never reached a verdict - missing security headers, permissive cross-origin policy, verbose errors and stack traces, version disclosure. These vanish because each is individually minor and nobody carries them forward. The notes already hold them, so this is a comparison against the verdict record, not another trawl through the logs.

6. Check that any material recovered during the assessment was actually applied to something. A secret, token or credential that was recovered and never used is either an untested lead that must be labelled as such, or a missed critical finding.

### Evidence integrity check

**Objective.** Apply a mechanical standard to every surviving finding. These are checks, not judgements - each either passes or does not.

**Techniques (6):**

1. CONTROL RESULT PRESENT - every finding claiming access, bypass or authentication must record the result of the same request made WITHOUT the credential, token, header or material said to be responsible. If that result is missing, obtain it now. If it matches the claimed result, the finding is REFUTED: the resource was already reachable.

2. QUOTED VALUES RE-READ AND LENGTH-CHECKED - for every secret, key or token quoted in the report, re-read it from the source artifact rather than from the draft, and assert its length is one the stated algorithm accepts. A value quoted at an impossible length is a transcription error: correct it from the artifact. Check the quoted length claim matches the value actually printed.

3. ALGORITHM CLAIMS CITE SOURCE - any statement about a cipher, mode, padding, hash or key derivation must cite the line of recovered source that sets it. Do not accept an inferred mode; read it. Being right about the vulnerability and wrong about the mechanism produces incorrect remediation advice.

4. EXECUTION CLAIMS SHOW RETURNED OUTPUT - any claimed code or command execution must show output of a command chosen by the tester, returned by the target. A payload that was sent, or an error that looks interesting, is not execution. Downgrade otherwise.

5. SEVERITY MATCHES DEMONSTRATION - severity is set by what was DEMONSTRATED, not by what is suspected. State breadth explicitly: one object or all of them, one account or every account. An unproven critical theory is a lead, not a critical finding.

6. Correct anything that fails a check rather than deleting it - downgrade the proof level, fix the transcription, or obtain the missing evidence, and say what was corrected.

### Emit the final deliverable

**Objective.** One report, honest about proof and about coverage.

**Techniques (13):**

1. Produce the final report with every finding carrying CONFIRMED, REFUTED or UNPROVEN, its evidence, and its control result.

2. QUOTE THE EVIDENCE, NEVER CITE IT. For every finding marked DEMONSTRATED or CONFIRMED, paste the actual artefact into the report: the request that was sent, the response that came back, and any value that was recovered. A filename, a note name or a phase name is a pointer, not evidence - the reader cannot open your working directory, and a pointer proves nothing.

3. If you cannot find and quote the concrete artefact for a finding, you may not mark it DEMONSTRATED. Downgrade it to UNPROVEN and say what is missing. This applies however confident an earlier phase sounded: a phase asserting something is not the same as a phase showing it.

4. CLAIM EXACTLY WHAT THE EVIDENCE SHOWS AND NOT ONE STEP MORE. The most common failure in this report is a demonstrated step being written up as the consequence it implies. Recovering a plaintext credential is not the same as authenticating with it; reaching an endpoint is not the same as extracting data from it; decrypting a token is not the same as taking over an account. Each of those is a separate step needing its own request and its own response.

5. Before writing any impact sentence, find the quoted evidence that supports it. If the evidence shows a decrypt but no authenticated response, the finding is 'credential recovered', and the takeover is stated as the untested consequence it is. Overstating one finding discredits the entire report.

6. Order findings by demonstrated severity, and state impact concretely - what data or capability was obtained and across how many accounts or objects.

7. EVERY FINDING CARRIES TWO REQUIRED SECTIONS, taken from the verdict record. COMPOUNDING FACTORS: which other findings make this worse and what the combination yields, quoting any recovered value that does the unlocking. MITIGATING FACTORS: what this finding does not show - the next step not attempted, the precondition still needed, the control that limits it.

8. Write 'None identified' rather than omitting a section. A section left out cannot be told apart from a question never asked, and these two are where an assessment is most often wrong in both directions - understating by leaving a chain implicit, overstating by folding an untested step into the impact sentence.

9. The compounding section is where a chain belongs. If material recovered in one finding was applied to a surface described in another, both findings say so and both quote the recovered value. A chain mentioned in neither is a chain the reader will not see.

10. Report chains as ordered steps with the request and response at each link, so a reader can follow and reproduce them.

11. State coverage honestly: which categories were assessed, which produced no findings, and which could not be assessed from outside. A category with nothing found is reported as such, not omitted.

12. List explicitly what was corrected or dropped during this gate and why, so the reader can see the report was checked rather than assembled.

13. Name the root cause of each finding precisely - file, type and member for embedded material; endpoint and parameter for exposure - so each is separately fixable.
