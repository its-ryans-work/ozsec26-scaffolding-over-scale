"""A10:2025 Mishandling of Exceptional Conditions (new in 2025).

Error behaviour is also an oracle for every other category, so record what
is learned here for the other playbooks."""

from .base_playbook import BasePlaybook, Phase


class ExceptionalConditionsPlaybook(BasePlaybook):
    name = "a10_exceptional"
    description = (
        "OWASP A10 Mishandling of Exceptional Conditions: behaviour under "
        "malformed, oversized, wrong-type, boundary and empty input, "
        "including whether failures open rather than close access. "
    )
    mode = "agent"
    max_loops = 25

    phases = [
        Phase(
            name="Probe boundaries and malformed input",
            objective=(
                "Find where the application stops handling input gracefully. "
            ),
            techniques=[
                "For representative endpoints, submit wrong types, empty "
                "values, missing required fields, extra unexpected fields, "
                "boundary numbers, and structurally malformed bodies. ",
                "Try oversized values within reason - enough to test a limit, "
                "not enough to exhaust resources. Do not pursue denial of "
                "service. ",
                "Record unhandled exceptions, stack traces, inconsistent "
                "status codes, and any response that discloses internal "
                "structure. ",
            ],
        ),
        Phase(
            name="Does failure open or close?",
            objective=(
                "The security-relevant question. "
            ),
            techniques=[
                "Determine whether an error path skips a control - whether a "
                "malformed request reaches a handler that a well-formed one "
                "could not, or whether a failed check results in access "
                "rather than denial. ",
                "Where an error reveals interpreter or framework detail, "
                "record it as an oracle for injection and integrity testing. ",
                "Run the control test: the same request well-formed, reported "
                "alongside. ",
            ],
        ),
        Phase(
            name="Verify before reporting",
            objective=(
                "Apply the same evidence standard to every finding, so "
                "results are comparable across categories."
            ),
            techniques=[
                "PROOF DISCIPLINE - label every finding DEMONSTRATED (you "
                "executed it and the response proves it, quote that "
                "response), INFERRED (follows from evidence but was not "
                "executed), or UNVERIFIED (suspected from a version, "
                "component or code pattern only). Identifying software is "
                "never a demonstration; never write 'confirmed' without "
                "having executed something. ",
                "RUN THE CONTROL TEST. Before claiming any access or bypass, "
                "repeat the request WITHOUT the credential, token, header or "
                "material you believe is responsible. If the result is the "
                "same, you have proven nothing - the resource was already "
                "reachable. State the control result alongside the finding. "
                "This single omission is the most common source of false "
                "critical findings. ",
                "BUDGET DISCIPLINE - rank leads by evidence strength "
                "(material in hand > observed behaviour > suspicion from a "
                "version string) and give each a step budget. STOP RULE: "
                "about 8-10 consecutive steps on one lead with no new "
                "evidence means move on, recording what you tried. ",
                "Record findings to notes as you go, with the endpoint, the "
                "request, the response and the control result, so later "
                "phases and the report can use them. ",
                "Stay non-destructive: prefer read-only proof, do not modify "
                "or delete data, do not lock accounts, and stop once the "
                "point is demonstrated. ",
            ],
        ),
    ]
