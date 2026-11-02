"""Adversarial review of a draft report.

You did not write the draft under review and have no stake in it. Assume it
was produced carelessly: that findings were asserted without proof, that
control tests were skipped, that severities were inflated, that the same
issue was reported more than once, and that real findings present in the raw
notes were left out.

Your purpose is truth, not criticism. Confirming a genuine finding with
fresh evidence is as valuable as refuting a false one. Do not refuse to
confirm something merely because it looks impressive, and do not refute
something merely because reproducing it is inconvenient."""

from .base_playbook import BasePlaybook, Phase


class AdversarialReviewPlaybook(BasePlaybook):
    name = "adversarial_review"
    description = (
        "Adversarial verification of a draft report. Treats every finding as "
        "probably wrong until independently reproduced, requires a control "
        "test for each, checks for duplicates and for anything dropped from "
        "the raw notes, and returns CONFIRMED / REFUTED / UNPROVEN with "
        "evidence. "
    )
    mode = "agent"
    max_loops = 60

    phases = [
        Phase(
            name="Take the draft apart",
            objective=(
                "Turn prose into a checkable list of claims. "
            ),
            techniques=[
                "Read the draft report and list every distinct claim: what is "
                "asserted, against which endpoint, with what evidence, and at "
                "what severity and proof level. ",
                "Separately read the raw notes and evidence from the "
                "assessment. List anything supported there that does NOT "
                "appear in the draft - omissions are as serious as errors. ",
                "Identify duplicates: the same underlying issue reported as "
                "several findings, or one finding split across categories. "
                "Merge them and say so. ",
            ],
        ),
        Phase(
            name="Attempt to refute each claim",
            objective=(
                "Reproduce independently. Assume the claim is wrong. "
            ),
            techniques=[
                "For every claim, reproduce it yourself against the live "
                "target rather than trusting the quoted evidence. Evidence in "
                "a draft may be stale, partial or misread. ",
                "REQUIRED for every access, bypass or authentication claim: "
                "run the CONTROL TEST - the identical request WITHOUT the "
                "credential, token, header or material said to be "
                "responsible. If the result is unchanged, the claim is "
                "REFUTED: the resource was already reachable. Report both "
                "results side by side. ",
                "For claimed code execution, require output of a chosen "
                "command returned by the target. A payload that was sent, or "
                "an interesting error, is not execution. ",
                "For any claim resting on a component, version or advisory "
                "identifier, require that it was executed against this target "
                "with the effect observed. Otherwise it is UNPROVEN "
                "regardless of how plausible it is. ",
                "Where a claim is correct but overstated, say so precisely: "
                "confirm the part that holds and refute the part that does "
                "not. ",
                "Check severity against what was actually demonstrated and "
                "against breadth - one object or all, one account or every "
                "account. ",
            ],
        ),
        Phase(
            name="Return a verdict per claim",
            objective=(
                "Evidence for every verdict, in both directions. "
            ),
            techniques=[
                "Assign each claim CONFIRMED, REFUTED or UNPROVEN. ",
                "CONFIRMED requires the request and response you obtained "
                "yourself, plus the control result showing it does not occur "
                "without the material. ",
                "REFUTED requires the evidence that disproves it - typically "
                "a control test producing the same result, or a reproduction "
                "attempt that fails. ",
                "UNPROVEN means you could not settle it: state exactly what "
                "additional access or step would settle it. ",
                "Add any finding you confirmed that the draft omitted, with "
                "the same evidence standard. ",
                "Give a corrected severity for every surviving finding, and "
                "list the merges you performed. ",
            ],
        ),
    ]
