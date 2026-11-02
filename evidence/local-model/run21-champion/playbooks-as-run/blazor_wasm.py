"""Client-side .NET assembly exposure playbook.

Any .NET application that executes on the client ships real, decompilable
assemblies. Blazor WebAssembly is the common case, but the procedure applies to
anything that delivers .NET IL to an untrusted endpoint. Anything compiled into
a client-referenced project — including `const` strings — is retrievable by an
anonymous visitor.

Generic web playbooks miss this because they only reason about server-side
endpoints.
"""

from .base_playbook import BasePlaybook, Phase


class BlazorWasmPlaybook(BasePlaybook):
    name = "blazor_wasm"
    description = (
        "Assess a .NET application that ships assemblies to the client (Blazor "
        "WebAssembly and similar) for exposed secrets, and for server endpoints "
        "that trust client-derived material. The client download is "
        "unauthenticated: treat every assembly the browser receives as public, "
        "readable source. Decompile before analysing — searching raw binaries is "
        "not a substitute."
    )
    mode = "agent"
    max_loops = 60

    phases = [
        Phase(
            name="Fingerprint the client-side .NET delivery",
            objective=(
                "Decide whether .NET assemblies are shipped to the client, and "
                "find the manifest or loader that lists them. Filenames and "
                "layout vary by .NET version and by product — investigate what "
                "is actually served rather than assuming a fixed path."
            ),
            techniques=[
                "Read the site root and app host pages and look at how the app "
                "boots. A loader referencing WebAssembly means assemblies ship; a "
                "server-side render mode means they do not and this playbook does "
                "not apply. Newer unified loaders can mean either - determine "
                "which rather than guessing.",
                "Asset names are frequently fingerprinted with a content hash, so "
                "match on stems and patterns, not exact filenames.",
                "Respect any <base href> - the framework directory is relative to "
                "it, so probe both the site root and the base path.",
                "Find the assembly inventory by whatever route exists: a boot "
                "manifest file, a boot config embedded in or fetched by the "
                "runtime JavaScript, or the loader script itself. If one route "
                "does not exist on this target, try the next; the loader must "
                "reference the assets somehow.",
                "The same exposure applies to other client-side .NET delivery "
                "(hybrid app web assets, WASM UI frameworks, ClickOnce, legacy "
                "plugin archives, or any exposed build-output directory). If IL "
                "is reachable by any route, continue.",
            ],
        ),
        Phase(
            name="Prepare the decompilation toolchain",
            objective=(
                "Get a working IL decompiler BEFORE analysing anything, then stop "
                "thinking about tooling. Skipping this produces false negatives; "
                "over-investing in it wastes the entire step budget."
            ),
            techniques=[
                "Check what is already available in ONE compound command rather "
                "than a sequence of separate probes: look for common decompilers "
                "on PATH, in per-user tool directories, and for a .NET runtime. "
                "Batch independent checks - you may also issue several tool calls "
                "in a single turn.",
                "If a decompiler is present, immediately prove it actually runs "
                "(invoke its help or version). If it works, the toolchain is DONE: "
                "stop, record it, and move to the next phase. Do not install "
                "anything and do not evaluate alternatives. Toolchain hunting is "
                "the single largest time sink in this assessment.",
                "Record the exact working invocation - including any environment "
                "prefix - both as a note and to a file on disk. THIS PHASE IS "
                "ONCE-ONLY: before any later tooling check or install, read that "
                "back and reuse it verbatim. A decompiler proven earlier in the "
                "session stays valid even if you no longer recall proving it.",
                "A .NET decompiler distributed as a managed tool needs a matching "
                "runtime. If it is found but refuses to launch complaining the "
                "runtime is missing, the runtime is usually present but "
                "undiscovered - set the appropriate environment variable to point "
                "at it and retry once before concluding it is unavailable.",
                "Only if nothing usable exists, install by the least invasive "
                "route available: an existing SDK's tool installer, the vendor's "
                "rootless install script, a distro package if the repo carries "
                "one, or a container image that already has the SDK. Stop at the "
                "first success.",
                "Do not hunt for .NET decompilers on language package indexes "
                "unrelated to .NET, and do not build a decompiler from source - "
                "both reliably waste the run. IL disassemblers are an acceptable "
                "fallback if a C# decompiler cannot be obtained; say so in your "
                "findings if you had to fall back.",
                "Time-box this. Working decompiler: move on. Several routes "
                "failed: proceed with the best fallback and note the limitation.",
            ],
        ),
        Phase(
            name="Retrieve the shipped assemblies",
            objective="Download what the browser actually receives.",
            techniques=[
                "Read manifests with a real GET. A HEAD request returns headers "
                "only and tells you nothing about contents.",
                "Prioritise application assemblies over framework/runtime ones. "
                "Shared libraries referenced by both client and server are the "
                "highest-value targets, because developers often forget that half "
                "of a shared project ships to the browser.",
                "Take names from the manifest rather than guessing - they are "
                "usually content-hashed and change between builds.",
                "Assets may be served in different container formats depending on "
                "build settings; unwrap or convert to a normal assembly before "
                "decompiling if needed.",
                "Verify each download is a real assembly and not an error page or "
                "empty file - check size and leading bytes. Keep everything in ONE "
                "working directory and do not re-download assemblies you already "
                "have; repeated downloads into new directories waste the budget.",
            ],
        ),
        Phase(
            name="Decompile to source before searching",
            objective=(
                "Convert retrieved assemblies to readable source. Do this first - "
                "analysis of raw binaries is unreliable."
            ),
            techniques=[
                "Decompile each assembly as the NEXT action after retrieving it. "
                "Do not search, grep or triage the binaries first.",
                "Raw-binary searching is unreliable because .NET stores string "
                "literals in metadata in a wide encoding that ASCII-oriented tools "
                "miss, and because constants are inlined in ways raw bytes do not "
                "show. A clean result over a binary is NOT evidence of absence.",
                "Know whether your invocation produced a directory of sources or a "
                "single file, and remember which - later searching a path as if it "
                "were the other form silently returns nothing and looks like the "
                "decompile failed.",
                "Verify the output really is source before trusting it. A zero "
                "exit code can hide a failure when output was redirected into a "
                "file, leaving the error text in place of code.",
                "If a decompile appears to fail, FIX AND RETRY immediately rather "
                "than abandoning decompilation - typical causes are a missing "
                "output directory, an unset environment variable, or an error "
                "swallowed by a pipe. Never fall back to searching binaries.",
                "Decompile EVERY application assembly retrieved, not just the "
                "first or the most obviously named. The entry-point client "
                "assembly often holds only UI code while the interesting material "
                "sits in a referenced shared library.",
            ],
        ),
        Phase(
            name="Hunt secrets in the decompiled source",
            objective=(
                "Find embedded credentials and sensitive material. Search along "
                "several INDEPENDENT axes and iterate — no single pattern is "
                "sufficient, and you are expected to devise your own."
            ),
            techniques=[
                "Search the decompiled SOURCE, never the binaries, and always with "
                "line numbers so you can navigate to hits.",
                "Cover these independent axes, designing patterns yourself and "
                "refining them as you learn what this codebase looks like:\n"
                "  - BY NAME: identifiers and comments suggesting credentials.\n"
                "  - BY DECLARATION: compile-time constants and static readonly "
                "fields, which is where embedded values structurally live.\n"
                "  - BY SHAPE: string literals that look like key material - long, "
                "unbroken, high-entropy, base64/hex-like, or padded/repeating.\n"
                "  - BY USE: cryptographic and auth APIs, and what gets passed to "
                "them.\n"
                "  - BY CONFIG: endpoints, hostnames and connection strings.",
                "ITERATE. Treat each pass as a hypothesis: run it, look at what "
                "came back, then broaden, narrow or re-target based on the actual "
                "results. Keep going until a pass yields no new candidates. If an "
                "axis returns too much noise, constrain it (scope to application "
                "assemblies rather than large third-party ones); if it returns "
                "nothing, loosen it. One search is never enough.",
                "CRITICAL - a name-based search is NOT evidence of absence. Real "
                "embedded secrets are often obfuscated so that no dictionary word "
                "appears in the value, and are commonly declared under neutral "
                "names like Profile, Default, Config or Seed. The axes that ignore "
                "naming are the ones that find these, which is why you must not "
                "rely on naming alone.",
                "Purpose-built secret scanners may be available and are worth "
                "running as an extra signal, but they largely detect known "
                "credential formats belonging to known providers. They routinely "
                "report nothing for bespoke keys in decompiled code. A clean "
                "scanner result must never be reported as 'no secrets present'.",
                "TRACE INDIRECTION. A crypto call usually references an identifier "
                "rather than a literal. That is a lead, not an answer: search for "
                "that identifier's definition and repeat until you reach the "
                "actual value. Expect several hops, and report the value, not the "
                "variable name.",
                "Do not read whole decompiled files looking for secrets - they run "
                "to thousands of lines and output is truncated long before the "
                "interesting line. Search for candidates, then read only the "
                "surrounding lines of each hit.",
                "Record each finding with the assembly, namespace, type and member "
                "it came from, and note whether that assembly is referenced by the "
                "client directly or transitively - a secret in a shared library "
                "usually means nobody realised it shipped at all.",
            ],
        ),
        Phase(
            name="Exploit server trust in client material",
            objective=(
                "Determine what the recovered material unlocks. A key is only a "
                "finding once you show what it grants."
            ),
            techniques=[
                "Enumerate the API surface before choosing a target - the endpoint "
                "that trusts this material may not be the obvious one, and may "
                "appear in API metadata or a schema document you already have.",
                "Reimplement the client's routine from the decompiled source "
                "exactly; the client code is the specification.",
                "Exercise the endpoint with attacker-controlled input protected by "
                "the recovered material, and compare against what an "
                "unauthenticated caller gets without it.",
                "Consider the full range of trust a client secret can carry: "
                "authentication, authorisation, signing, encryption, or addressing "
                "internal functionality.",
                "Inspect responses for data the public API does not otherwise "
                "expose - credentials, tokens, internal identifiers, or fields "
                "absent from the documented contract.",
                "Establish impact by contrast: show the same result cannot be "
                "obtained without the recovered material.",
            ],
        ),
    ]
