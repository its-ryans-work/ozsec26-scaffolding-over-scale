"""Validate and chain findings produced by earlier playbook runs.

Runs LAST in a sequence. Earlier playbooks discover things in isolation - an
enumeration pass finds endpoints, a client-analysis pass finds secrets - and
each looks moderate on its own. Real severity usually comes from combining them.

This playbook does two things generic assessments habitually skip: it PROVES
each finding is live rather than theoretical, and it looks for combinations
that are worth more than the sum of their parts.
"""

from .base_playbook import BasePlaybook, Phase


class ChainFindingsPlaybook(BasePlaybook):
    name = "chain_findings"
    description = (
        "Take the findings already gathered in this workspace, validate each one "
        "against the live target, then look for chains where one finding unlocks "
        "or amplifies another. A finding that has not been demonstrated is a "
        "hypothesis, not a result."
    )
    mode = "agent"
    max_loops = 80

    phases = [
        Phase(
            name="Inventory what is already known",
            objective=(
                "Build a single list of everything previous passes discovered. "
                "Do not re-run reconnaissance - the work is already done and "
                "repeating it wastes the run."
            ),
            techniques=[
                "START FROM THE CONSOLIDATED NOTES. A consolidation pass ran "
                "immediately before this one and wrote every finding gathered so "
                "far to notes, including material recovered from phase logs that "
                "exists nowhere else. Read those notes FIRST and treat them as "
                "the authoritative input - they are the complete record, and "
                "anything you do not carry out of this phase is lost for the "
                "rest of the assessment.",
                "Count the consolidated entries and write the number down. You "
                "will be required to account for every one of them at the end of "
                "this playbook.",
                "Read the saved notes and any findings recorded in this "
                "workspace, and list the artifacts already on disk (retrieved "
                "binaries, decompiled source, captured responses).",
                "Read the decompiled source and captured output you already have "
                "rather than fetching anything again.",
                "Write the inventory as two explicit lists: (1) "
                "CAPABILITIES - the keys, algorithms, credentials and "
                "sessions you hold; (2) MATERIAL - the opaque values the "
                "target has actually emitted (encrypted or encoded field "
                "values, blobs, cookies, tokens) together with the "
                "request that produced each one. Count both lists. If one "
                "of them is empty that is your next task, not a dead end: "
                "a capability with nothing to apply it to is an "
                "unfinished finding, and so is material you cannot yet "
                "read. ",
                "STOP RULE: if roughly 8-10 consecutive steps on one lead produce "
                "no NEW evidence - no new access, no new data, no change in the "
                "error you get back - abandon it, record what you tried and what "
                "it would take to confirm, and move to the next lead. Returning "
                "later with fresh information is fine; grinding is not.",
                "COUNT REPETITION BY WHAT THE COMMAND DOES, NOT HOW IT IS "
                "SPELLED. Re-running the same tool against the same file or "
                "endpoint with a widened context window, a reordered pattern or "
                "an extra alternation is the SAME step, not a new one. Three "
                "attempts of that kind without new information means the "
                "information is not there: the identifier you are searching for "
                "does not exist in that file, or does not exist under that name. "
                "Change target or change approach - search a different file, list "
                "what the file actually defines, or ask the running service - "
                "rather than re-phrasing the same query a fourth time.",
                "Before repeating any search, say what NEW thing the next attempt "
                "could reveal that the last one could not. If there is no "
                "answer, that is the signal to stop.",
            ],
        ),
        Phase(
            name="Validate every finding against the live target",
            objective=(
                "Turn hypotheses into demonstrated facts. An unvalidated secret "
                "is worth reporting only as a possibility."
            ),
            techniques=[
                "For each piece of recovered MATERIAL, design a concrete test "
                "that proves whether it is live and accepted by the target. If "
                "the material is used by code you have decompiled, reimplement "
                "that code exactly - same algorithm, mode, padding, encoding and "
                "any envelope or timestamp structure. The recovered source is the "
                "specification; do not guess at the format.",
                "MEASURE THE MATERIAL AND USE THE COPY YOU MEASURED. "
                "Never count characters by eye - runs of repeated padding "
                "are miscounted and the machine is not. Read the literal "
                "out of the file with a command, hold it in a variable, "
                "print its length from that variable, and pass THAT SAME "
                "variable onward; retyping it into a second command is "
                "where a character is gained or lost. A plausible length "
                "is not a correct one: most ciphers accept several key "
                "sizes, so a bad extraction often lands on a legal one "
                "and simply produces garbage. IF THE LENGTH IS WRONG THE "
                "EXTRACTION IS WRONG, NOT THE SECRET - re-read it from "
                "the same file programmatically before doubting the value "
                "or reaching for a lower-level artifact. ",
                "SELF-TEST YOUR REIMPLEMENTATION BEFORE TRUSTING ANY RESULT. An "
                "incorrect implementation and correctly-rejected material produce "
                "the same rejection, so a failed request tells you nothing until "
                "you have proven your own code. Do both checks:\n"
                "  (i) ROUND TRIP - transform a known value forward then back and "
                "confirm you recover the original exactly. This proves internal "
                "consistency, and nothing more.\n"
                "  (ii) AGAINST THE TARGET'S OWN OUTPUT - take any value the "
                "TARGET produced using this material (a token, cookie, stored "
                "field, or a captured response) and process it with your "
                "implementation. Recovering sensible plaintext from something the "
                "server generated is the only proof your implementation matches "
                "theirs.",
                "Sanity-check the SHAPE of what you produce against a real sample "
                "from the target: length, block alignment, whether a prefix such "
                "as an IV or nonce is present, and the encoding. A structurally "
                "plausible output that still fails is a strong hint the key bytes "
                "or their derivation are wrong, not the framing.",
                "TREAT REJECTIONS AS AN ORACLE, AND AS EVIDENCE ABOUT YOUR "
                "REQUEST AT LEAST AS OFTEN AS ABOUT YOUR MATERIAL. Distinguish "
                "the failure stages: rejection during decryption or verification "
                "(your material or algorithm is wrong), acceptance followed by a "
                "parse or schema complaint (the crypto is RIGHT and your inner "
                "structure is wrong), and complaints about an unknown or "
                "unsupported operation (both are right and you named something "
                "the server does not offer). Moving from one class of error to "
                "another is progress. This matters most when the material came "
                "from the application's own stored data: such a value is very "
                "unlikely to be wrong, so a rejection points at the request shape "
                "first. Vary one thing at a time.",
                "ENUMERATE THE ACCEPTED VALUES FROM THE SOURCE FIRST - required, "
                "not a precaution. Before composing any request to a dispatcher, "
                "router, command or batch style endpoint, read the decompiled "
                "handler for what it actually accepts: switch/case labels, "
                "if-else comparisons, enum members, dictionary keys or its route "
                "table. Write that list down before sending anything. NEVER "
                "invent an operation name - a placeholder such as 'Test' or a "
                "guessed resource is rejected as unknown even when your "
                "credentials and encryption are perfect, which wastes the attempt "
                "and looks like the material failed when it did not. Work the "
                "enumerated values in order of what returns the most data or "
                "touches the most sensitive handler; a value rejected as unknown "
                "while others are accepted tells you the dispatcher works and "
                "your envelope is valid.",
                "ANSWER 'WHAT DOES THIS REQUEST NEED' BY SEARCHING BEFORE "
                "PROBING. Guessing a request's shape and reading the rejection is "
                "the slowest way to learn it and the easiest to misread, and "
                "earlier phases have usually already collected the answer. Before "
                "composing a request to any endpoint you have not successfully "
                "used, search in this order: saved notes and prior phase reports "
                "describing it; any machine-readable API description the target "
                "publishes (OpenAPI or Swagger documents, WSDL, GraphQL "
                "introspection, metadata or discovery endpoints); the decompiled "
                "source for the handler, its route attribute and its request "
                "type; and the client-side code for the call site. This applies "
                "to authentication requests especially, where it is most often "
                "skipped - such endpoints commonly need more than a username and "
                "password, such as a provider or scheme name, a realm, a client "
                "identifier, a CSRF or antiforgery token, or a specific content "
                "type.",
                "Say where the shape came from and how sure you are of it. A "
                "field list read from a request type in source, or from a "
                "published specification, is reliable. A field list inferred "
                "from a URL or a guess is not, and a request built from one that "
                "fails has not tested anything. Record what you found so a later "
                "phase does not repeat the search.",
                "OBSERVE THE APPLICATION DOING IT ITSELF. If a browser tool is "
                "available and the application has a user interface for the "
                "operation, drive that interface and capture the request it "
                "issues - route, method, headers, content type, every field name "
                "and its exact casing - then mirror it. A working example "
                "produced by the application is the most reliable specification "
                "obtainable, it costs one page load, and it settles questions "
                "that reading source can leave open.",
                "ESTABLISH BOTH POLES BEFORE JUDGING A CREDENTIAL. A rejection "
                "says the request was not accepted; it does not say whether the "
                "credential, the field set, the route or the encoding was wrong, "
                "and without a reference for acceptance the only reading "
                "available is 'the material is bad' - which discards correct "
                "work. Get references first: read the route from source rather "
                "than guessing paths, since a guessed path returns the same "
                "rejection as a wrong credential; if any credentials are already "
                "known, authenticate with them once and keep the success response "
                "- status, headers, cookies, body; and send a deliberately wrong "
                "credential to the same route with the same shape and keep that "
                "response too.",
                "With both references, a rejection is interpretable. If your "
                "attempt does not even match the FAILURE shape - a different "
                "status, a different error, a complaint about a missing field - "
                "then your request is malformed and the credential has not been "
                "tested yet. Only a response matching the failure shape exactly "
                "is evidence about the credential itself. State which of the two "
                "you observed. Take the credential from where it was produced "
                "rather than retyping it: if a script decrypted it, have that "
                "script write it to a file and read the file in the request.",
                "Prefer a safe read-only proof first (something that returns data "
                "or is accepted) over anything that writes or changes state.",
                "RECORD THE EVIDENCE THE MOMENT IT IS TRUE. As soon as something "
                "is shown to work - a value decrypts, a token is accepted, an "
                "endpoint returns what it should not - write the exact request "
                "and the exact response with the notes tool immediately, in that "
                "same step, before moving to the next lead. Do not save it up to "
                "write later. This is not bookkeeping: this phase can be cut off "
                "at any point when the step budget runs out, and anything not "
                "written down when that happens is lost for the rest of the "
                "assessment no matter how conclusively you proved it.",
                "If validation fails, do not discard the finding immediately: "
                "check your reimplementation against the source, and distinguish "
                "'my test was wrong' from 'the material is not accepted'. Say "
                "which one you concluded and why.",
            ],
        ),
        Phase(
            name="Chain findings into higher severity",
            objective=(
                "Look for combinations. Findings that are individually moderate "
                "are frequently critical together."
            ),
            techniques=[
                "Cross every item of MATERIAL against every item of SURFACE and "
                "ask: does this material unlock, authenticate to, decrypt, sign "
                "for, or bypass a control on this surface?",
                "Look specifically for surfaces that were previously refused, "
                "errored, or returned less data than expected - recovered "
                "material often turns exactly those into successes.",
                "Watch for dispatch, batch, proxy or import style endpoints that "
                "forward requests internally: reaching a handler by that route "
                "can bypass the checks applied to its direct route. Compare what "
                "the direct route returns against what the indirect route "
                "returns.",
                "STOP AND JOIN THEM - whenever you hold BOTH a secret AND an "
                "opaque stored value (encrypted token, protected field, cookie, "
                "unexplained blob), attempt the decode immediately, as the next "
                "action, before writing either up. Two findings recorded "
                "separately read as 'a key leaked' and 'some data leaked'; joined "
                "they are frequently FULL ACCOUNT TAKEOVER. Assume the join works "
                "and disprove it.",
                "Try to decrypt or decode anything opaque you receive using the "
                "material you already recovered; matching a value back to a known "
                "algorithm is frequently the whole finding. Do this for every "
                "account or object you hold a value for, not just the first.",
                "A RESULT PROVEN AGAINST ONE OBJECT IS A RESULT OF UNKNOWN SIZE. "
                "The moment a technique works on one account, record, file or "
                "record-holder, apply it to the others you can enumerate. Stopping "
                "at the first success answers 'is this possible' and leaves 'how "
                "much of the system does this reach' unanswered - and the second "
                "question is what determines severity and what a reader needs.",
                "Cover the privileged cases deliberately. If the population "
                "includes accounts or objects with more authority than the one "
                "you proved - administrators, operators, service or system "
                "accounts, records belonging to other tenants - test those "
                "specifically rather than sampling whichever came first. A "
                "technique that reaches an ordinary account and one that reaches "
                "an administrative account are different findings.",
                "Report the count and the composition: how many of the known "
                "population were tested, how many were affected, and which "
                "privileged ones were among them. If you could not enumerate the "
                "population, say what you did test and that the true breadth is "
                "unmeasured - that is a real limitation, not a detail to omit.",
                "RECORD EACH LINK AS IT IS PROVEN, not once the whole chain is "
                "assembled. A chain that is three quarters demonstrated is still "
                "a serious finding; a chain you never wrote down is nothing. "
                "Write a note per proven step, and update it as the chain grows.",
            ],
        ),
        Phase(
            name="Report chains with evidence and impact",
            objective="Produce a defensible write-up of what was demonstrated.",
            techniques=[
                "Report each chain as an ordered sequence of steps, each with the "
                "request made and the response received.",
                "State impact concretely - what data or capability was obtained, "
                "and for how many objects or accounts - rather than in the "
                "abstract.",
                "Establish impact by contrast: show the same result cannot be "
                "obtained without the recovered material or the chained route.",
                "Label every finding with its proof level and be strict about it: "
                "DEMONSTRATED (you executed it and the response proves it - quote "
                "that response), INFERRED (follows from evidence but was not "
                "executed), or UNVERIFIED (suspected from a version number, "
                "library name or code pattern only).",
                "Identifying a framework, library or version is NOT a "
                "vulnerability finding. A known issue in that component is "
                "UNVERIFIED until you execute it against this target and observe "
                "the effect. Do not write 'confirmed' on the basis of what "
                "software is present, and do not cite an advisory identifier "
                "unless you have checked it applies to this deployment.",
                "For code execution specifically, the proof is OUTPUT of a "
                "command you chose, returned by the target - not a payload you "
                "sent, and not an error that merely looks interesting. Match the "
                "payload to the actual platform; a Windows shell command against "
                "a Unix host proves nothing either way.",
                "Set severity from what was DEMONSTRATED. An unproven critical "
                "theory is reported as a lead to investigate, never as a "
                "critical finding - overstating severity destroys the "
                "credibility of the whole report.",
                "Name the specific root cause for each link in the chain (the "
                "assembly, type and member, or the endpoint and parameter) so it "
                "is directly actionable.",
                "CARRY EVERY CONSOLIDATED FINDING FORWARD - not only the ones "
                "that chained. Chaining is additive: it creates new findings, it "
                "does not replace the inputs. A finding that did not combine with "
                "anything is still a finding, and the next phase can only review "
                "what reaches it.",
                "Go back to the count you recorded in the first phase and "
                "reconcile against it explicitly. Every consolidated entry must "
                "end in exactly one of three states: folded into a chain (name "
                "the chain), carried forward unchanged, or dropped as a proven "
                "duplicate (name the entry it duplicates). There is no fourth "
                "state - if you cannot say which applies, it is carried forward.",
                "Write the full carried-forward set to notes, one note per "
                "finding, preserving each finding's original evidence, proof "
                "level and severity. Do NOT summarise several findings into one "
                "note and do not drop the low-severity and informational ones - "
                "missing headers, verbose errors and version disclosure are "
                "exactly what falls out here, and they are both reportable and "
                "inputs to future chains.",
                "Findings you could not validate are carried forward too, "
                "labelled UNVERIFIED with what you tried. Failing to prove "
                "something is a result; silently discarding it is not.",
            ],
        ),
    ]
