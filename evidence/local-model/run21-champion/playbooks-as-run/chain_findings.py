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
    max_loops = 60

    phases = [
        Phase(
            name="Inventory what is already known",
            objective=(
                "Build a single list of everything previous passes discovered. "
                "Do not re-run reconnaissance - the work is already done and "
                "repeating it wastes the run."
            ),
            techniques=[
                "Read the saved notes and any findings recorded in this "
                "workspace, and list the artifacts already on disk (retrieved "
                "binaries, decompiled source, captured responses).",
                "Read the decompiled source and captured output you already have "
                "rather than fetching anything again.",
                "Write the inventory down as two explicit lists: (1) MATERIAL - "
                "secrets, keys, tokens, credentials, algorithms recovered; "
                "(2) SURFACE - endpoints, parameters, and behaviours observed, "
                "including anything that errored or was refused.",
                "Note for each item where it came from, so evidence can be cited "
                "later.",
                "BUDGET DISCIPLINE - you have a limited number of steps for the "
                "WHOLE assessment, not for one idea. Before going deep, rank the "
                "leads by how much evidence already supports them: material you "
                "hold in hand outranks a behaviour you observed, which outranks "
                "something suspected from a version number or a library name.",
                "Work the ranked list in order and give each lead a rough step "
                "budget up front. Spend depth where evidence justifies it, and "
                "give a weak lead a few cheap probes rather than an open-ended "
                "investigation.",
                "STOP RULE: if roughly 8-10 consecutive steps on one lead produce "
                "no NEW evidence - no new access, no new data, no change in the "
                "error you get back - abandon it, record what you tried and what "
                "it would take to confirm, and move to the next lead. Returning "
                "later with fresh information is fine; grinding is not.",
                "Never let one lead consume the run while others are untouched. "
                "It is better to demonstrate three findings solidly than to fail "
                "to prove one impressive-sounding theory.",
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
                "that proves whether it is live and accepted by the target.",
                "If the material is used by code you have decompiled, reimplement "
                "that code exactly - same algorithm, mode, padding, encoding and "
                "any envelope or timestamp structure. The recovered source is the "
                "specification; do not guess at the format.",
                "CHECK THE MATERIAL ITSELF BEFORE USING IT. Extraction routinely "
                "corrupts a secret by a byte or two - a trailing newline, quote, "
                "or shell escaping - and a value that is right except for its "
                "length behaves exactly like a wrong value. Before any "
                "cryptographic use: strip surrounding whitespace and quotes, "
                "print the length and the raw bytes, and ASSERT the length is one "
                "the algorithm actually accepts (for example a block cipher key "
                "must be one of its permitted sizes). If the length is invalid, "
                "you have an extraction bug, not a wrong secret - go back to the "
                "source and re-read the literal exactly.",
                "Prefer taking the value from the decompiled source verbatim over "
                "reconstructing it through an intermediate encoding. If you do "
                "convert via hex or base64, decode it back and compare against "
                "the original literal character for character before proceeding.",
                "SELF-TEST YOUR REIMPLEMENTATION BEFORE TRUSTING ANY RESULT. An "
                "incorrect implementation and correctly-rejected material produce "
                "the same rejection from the target, so a failed request tells you "
                "nothing until you have proven your own code. Do both checks:\n"
                "  (i) ROUND TRIP - transform a known value forward then back and "
                "confirm you recover the original exactly. This proves internal "
                "consistency, and nothing more.\n"
                "  (ii) AGAINST THE TARGET'S OWN OUTPUT - take any value the "
                "TARGET produced using this material (a token, cookie, stored "
                "field, or a response body you already captured) and process it "
                "with your implementation. Recovering sensible plaintext from "
                "something the server generated is the only proof your "
                "implementation actually matches theirs.",
                "Sanity-check the SHAPE of what you produce against a real sample "
                "from the target: length, block alignment, whether a prefix such "
                "as an IV or nonce is present, and the encoding. A structurally "
                "plausible output that still fails is a strong hint the key bytes "
                "or their derivation are wrong, not the framing.",
                "Treat the target's error responses as an ORACLE and distinguish "
                "the failure stages: rejection during decryption/verification "
                "(your material or algorithm is wrong), acceptance followed by a "
                "parse or schema complaint (crypto is RIGHT, your inner structure "
                "is wrong), and complaints about an unknown or unsupported "
                "operation (crypto and structure are right, you named something "
                "the server does not offer). Read the message text carefully - "
                "moving from one class of error to another is progress and tells "
                "you which part to fix next.",
                "ENUMERATE THE ACCEPTED VALUES FROM THE SOURCE FIRST - this is a "
                "required step, not a precaution. Before composing any request to "
                "a dispatcher, router, command or batch style endpoint, go back "
                "to the decompiled code for that handler and read what it "
                "actually accepts: the switch/case labels, if-else comparisons, "
                "enum members, dictionary keys or route table it dispatches on. "
                "Write that list down explicitly before you send anything.",
                "NEVER invent an operation name. Placeholder values such as "
                "'Test', 'Ping' or a guessed resource name will be rejected as "
                "unknown even when your credentials and encryption are perfectly "
                "correct - which wastes the attempt and, worse, can look like the "
                "material failed when it did not. Every request must name a value "
                "you read from the source.",
                "Work through the enumerated values systematically, starting with "
                "whichever returns the most data or touches the most sensitive "
                "handler. If a value is rejected as unknown while others are "
                "accepted, that tells you the dispatcher is working and your "
                "envelope is valid - use it as a positive signal.",
                "Prefer a safe read-only proof first (something that returns data "
                "or is accepted) over anything that writes or changes state.",
                "Record the exact request and response that demonstrates the "
                "finding - that evidence is what makes the report credible.",
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
                "When a response contains further material (tokens, identifiers, "
                "encrypted blobs), feed it back in and repeat - chains are often "
                "several steps long, and the last step is usually the severe one.",
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
                "Enumerate breadth once a chain works: establish whether it "
                "affects one object or every object, since that distinction "
                "drives severity more than the technique does.",
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
            ],
        ),
    ]
