"""Gather every finding from every channel and record it durably.

Runs immediately before any phase that would otherwise lose input, and is
deliberately small: it gathers, it does not test.

Findings live in three channels and later phases reliably see only one of them:
saved notes (which agents seldom write), tool results (kept only for a recent
window, so early findings age out), and the assistant's own narration (never
captured anywhere). A conclusion stated only in narration - "this value decrypts
to that, which authenticates as those accounts" - can exist nowhere else and is
lost at the next handoff.

This phase reads all three, normalises what it finds, and writes it to notes,
which is the only channel that survives to later phases.
"""

from .base_playbook import BasePlaybook, Phase


class ConsolidateFindingsPlaybook(BasePlaybook):
    name = "consolidate_findings"
    description = (
        "Sweep notes, per-phase reports, phase logs and artifacts on disk for "
        "every finding produced so far, normalise them into one list, and "
        "record them to notes so the next phase receives a complete input. "
        "Gathers only - does not test, does not chase new leads."
    )
    mode = "agent"
    max_loops = 25

    phases = [
        Phase(
            name="Read every channel",
            objective=(
                "Collect what previous phases produced, including the material "
                "that no automated step reads."
            ),
            techniques=[
                "Read the saved notes for this workspace first - that is the "
                "structured record, and it is usually incomplete.",
                "Read the per-phase reports produced so far. Each phase writes "
                "its own report; later phases do not read them.",
                "READ THE PHASE LOGS. This is the channel nothing else reads and "
                "the reason this phase exists. Locate the log files for this "
                "assessment on disk and search them for evidence that was stated "
                "but never recorded: recovered values, decoded output, tokens and "
                "credentials, status codes that changed, headers observed to be "
                "missing, error text, and any conclusion the assistant narrated "
                "about combining two things.",
                "Pay particular attention to narration panels - the assistant "
                "frequently states a completed chain or a confirmed result in "
                "prose without ever recording it as a finding. Those statements "
                "are findings and must be captured.",
                "List the artifacts on disk (retrieved binaries, decompiled or "
                "unpacked source, captured responses) and note their paths so "
                "later phases reuse them rather than fetching again.",
            ],
        ),
        Phase(
            name="Normalise into one list",
            objective="One entry per distinct issue, deduplicated and comparable.",
            techniques=[
                "Produce one entry per distinct issue with: what it is, where it "
                "is (endpoint, or file, type and member), the evidence observed, "
                "whether a control test was run and its result, and the current "
                "proof level.",
                "Merge duplicates. Different phases routinely describe the same "
                "underlying issue from different angles, and one issue split "
                "across several entries inflates the apparent finding count.",
                "INCLUDE LOW-SEVERITY AND INFORMATIONAL OBSERVATIONS. Missing "
                "security headers, permissive cross-origin policy, verbose errors "
                "and stack traces, exposed metadata and version disclosure are "
                "routinely dropped between phases precisely because they are "
                "individually minor. They belong in the report, and several of "
                "them are also inputs to chaining.",
                "Separate what has been demonstrated from what is asserted, and "
                "carry that distinction forward rather than flattening it.",
                "Build an explicit UNCOMBINED MATERIAL list: every secret, key, "
                "token, hash, cookie or opaque value held, that has not yet been "
                "applied to anything. The next phase needs exactly this list, and "
                "material sitting unused is the most common missed critical.",
            ],
        ),
        Phase(
            name="Record to notes",
            objective=(
                "Write the list down. This is the entire output of the phase - "
                "an unrecorded finding does not survive to the next one."
            ),
            techniques=[
                "Record every normalised finding using the notes tool, one note "
                "per finding, including its evidence and control result. Notes "
                "are the only channel later phases reliably receive.",
                "Record the UNCOMBINED MATERIAL list as its own note so the "
                "following phase can act on it directly.",
                "Do NOT re-test anything, do not attempt exploitation, and do not "
                "chase new leads here. If something looks promising but unproven, "
                "record it as a lead with the evidence that makes it one and move "
                "on - the phases after this one will act on it.",
                "Finish as soon as everything is recorded. This phase has a small "
                "budget by design; spending it on investigation starves the "
                "phases that do the work.",
            ],
        ),
    ]
