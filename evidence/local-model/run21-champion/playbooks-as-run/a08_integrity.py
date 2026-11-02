"""A08:2025 Software or Data Integrity Failures (A08:2021)."""

from .base_playbook import BasePlaybook, Phase


class IntegrityPlaybook(BasePlaybook):
    name = "a08_integrity"
    description = (
        "OWASP A08 Software or Data Integrity Failures: unsafe "
        "deserialization, unverified updates and assets, and trust placed in "
        "client-supplied or third-party data. "
    )
    mode = "agent"
    max_loops = 50

    phases = [
        Phase(
            name="Find integrity assumptions",
            objective=(
                "Locate where the application trusts data it should verify. "
            ),
            techniques=[
                "Identify endpoints accepting serialized objects, type hints, "
                "polymorphic payloads or object graphs, from recovered source "
                "where available. ",
                "Look for client-supplied values used in security decisions, "
                "pricing, identity or state transitions. ",
                "Check whether third-party assets are loaded without "
                "integrity verification, and whether update or plugin "
                "mechanisms verify signatures. ",
            ],
        ),
        Phase(
            name="Test carefully and honestly",
            objective=(
                "Deserialization claims are where reports most often "
                "overstate. "
            ),
            techniques=[
                "If a deserializer accepts a type discriminator, first read "
                "the recovered source to learn the exact discriminator and "
                "the types actually permitted. Guessing a discriminator "
                "produces an 'unknown type' error that proves nothing. ",
                "A type that merely exists is not a gadget: a gadget chain "
                "must INVOKE something. If you cannot demonstrate invocation, "
                "the finding is UNVERIFIED and must be reported that way. ",
                "Presence of a vulnerable-looking component or version is not "
                "an integrity finding. Do not cite an advisory identifier "
                "unless you have executed it against this target and observed "
                "the effect. ",
                "Test tampering with client-supplied values that influence "
                "server-side decisions, and show the changed outcome. ",
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
