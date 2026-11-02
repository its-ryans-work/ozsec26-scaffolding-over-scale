"""Last word: confirm nothing was dropped and that evidence holds up.

Runs after adversarial review. Its scope is integrity, not re-testing: it
checks that every finding which existed earlier still appears or is explicitly
accounted for, and that each surviving finding meets a mechanical evidence
standard before it reaches the deliverable.

Every check here exists because a real report failed it. A report has claimed
ECB where the source set CBC; printed a key one character longer than the
algorithm accepts while calling it the correct length; rated an endpoint as a
critical bypass without ever requesting it without the token; and silently
dropped observations that appeared in earlier phases. Each of those is caught by
a specific check below, and each is mechanical - no judgement required.
"""

from .base_playbook import BasePlaybook, Phase


class FinalIntegrityGatePlaybook(BasePlaybook):
    name = "final_integrity_gate"
    description = (
        "Final gate before delivery. Confirms every finding recorded earlier "
        "either survives or is explicitly accounted for, and enforces a "
        "mechanical evidence standard: control results present, quoted secrets "
        "re-read and length-checked, algorithm claims citing source lines, "
        "execution claims showing returned output. Emits the final report."
    )
    mode = "agent"
    max_loops = 30

    phases = [
        Phase(
            name="Completeness check",
            objective=(
                "Nothing that was found earlier may vanish silently between "
                "phases."
            ),
            techniques=[
                "Read the consolidated findings recorded in notes, the per-phase "
                "reports, and the output of the adversarial review.",
                "Compare them. Every finding present before the chaining and "
                "review phases must appear in the reviewed set, be marked "
                "REFUTED with evidence, or be explicitly listed as dropped with "
                "the reason. Silent disappearance is not acceptable.",
                "Re-read the phase logs once more for anything never recorded in "
                "any structured form. Low-severity observations - missing "
                "security headers, permissive cross-origin policy, verbose errors "
                "and stack traces, version disclosure - are the ones that vanish, "
                "because each is individually minor and nobody carries them "
                "forward.",
                "Check that any material recovered during the assessment was "
                "actually applied to something. A secret, token or credential "
                "that was recovered and never used is either an untested lead "
                "that must be labelled as such, or a missed critical finding.",
            ],
        ),
        Phase(
            name="Evidence integrity check",
            objective=(
                "Apply a mechanical standard to every surviving finding. These "
                "are checks, not judgements - each either passes or does not."
            ),
            techniques=[
                "CONTROL RESULT PRESENT - every finding claiming access, bypass "
                "or authentication must record the result of the same request "
                "made WITHOUT the credential, token, header or material said to "
                "be responsible. If that result is missing, obtain it now. If it "
                "matches the claimed result, the finding is REFUTED: the resource "
                "was already reachable.",
                "QUOTED VALUES RE-READ AND LENGTH-CHECKED - for every secret, "
                "key or token quoted in the report, re-read it from the source "
                "artifact rather than from the draft, and assert its length is "
                "one the stated algorithm accepts. A value quoted at an "
                "impossible length is a transcription error: correct it from the "
                "artifact. Check the quoted length claim matches the value "
                "actually printed.",
                "ALGORITHM CLAIMS CITE SOURCE - any statement about a cipher, "
                "mode, padding, hash or key derivation must cite the line of "
                "recovered source that sets it. Do not accept an inferred mode; "
                "read it. Being right about the vulnerability and wrong about the "
                "mechanism produces incorrect remediation advice.",
                "EXECUTION CLAIMS SHOW RETURNED OUTPUT - any claimed code or "
                "command execution must show output of a command chosen by the "
                "tester, returned by the target. A payload that was sent, or an "
                "error that looks interesting, is not execution. Downgrade "
                "otherwise.",
                "SEVERITY MATCHES DEMONSTRATION - severity is set by what was "
                "DEMONSTRATED, not by what is suspected. State breadth "
                "explicitly: one object or all of them, one account or every "
                "account. An unproven critical theory is a lead, not a critical "
                "finding.",
                "Correct anything that fails a check rather than deleting it - "
                "downgrade the proof level, fix the transcription, or obtain the "
                "missing evidence, and say what was corrected.",
            ],
        ),
        Phase(
            name="Emit the final deliverable",
            objective="One report, honest about proof and about coverage.",
            techniques=[
                "Produce the final report with every finding carrying CONFIRMED, "
                "REFUTED or UNPROVEN, its evidence, and its control result.",
                "Order findings by demonstrated severity, and state impact "
                "concretely - what data or capability was obtained and across how "
                "many accounts or objects.",
                "Report chains as ordered steps with the request and response at "
                "each link, so a reader can follow and reproduce them.",
                "State coverage honestly: which categories were assessed, which "
                "produced no findings, and which could not be assessed from "
                "outside. A category with nothing found is reported as such, not "
                "omitted.",
                "List explicitly what was corrected or dropped during this gate "
                "and why, so the reader can see the report was checked rather "
                "than assembled.",
                "Name the root cause of each finding precisely - file, type and "
                "member for embedded material; endpoint and parameter for "
                "exposure - so each is separately fixable.",
            ],
        ),
    ]
