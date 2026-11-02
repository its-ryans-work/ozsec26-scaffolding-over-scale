"""A02:2025 Security Misconfiguration (A05:2021)."""

from .base_playbook import BasePlaybook, Phase


class MisconfigurationPlaybook(BasePlaybook):
    name = "a02_misconfiguration"
    description = (
        "OWASP A02 Security Misconfiguration: exposed interfaces and "
        "metadata, verbose errors, default content, permissive CORS, missing "
        "hardening, and debug functionality reachable in production. "
    )
    mode = "agent"
    max_loops = 60

    phases = [
        Phase(
            name="Exposed interfaces and content",
            objective=(
                "Find what should not be reachable. "
            ),
            techniques=[
                "Probe for administrative, debug, health, metrics, profiler "
                "and documentation interfaces, and determine whether each "
                "requires authentication. ",
                "Look for framework metadata, schema or introspection "
                "endpoints that disclose the full API surface to anonymous "
                "callers. ",
                "Check for default, sample or installer content left in "
                "place, and for directory listings. ",
                "Look for backup, temporary, versioned or editor artifacts "
                "beside known paths. ",
            ],
        ),
        Phase(
            name="Response hardening and policy",
            objective=(
                "Assess configuration visible in responses. "
            ),
            techniques=[
                "Review security-relevant response headers and cookie "
                "attributes, and report what is missing rather than assuming "
                "exploitability. ",
                "Test CORS behaviour with unexpected and null origins, and "
                "check whether credentials are permitted cross-origin. ",
                "Check whether errors return stack traces, framework "
                "versions, file paths or internal hostnames. ",
                "Note TLS and transport configuration where observable. ",
            ],
        ),
        Phase(
            name="Prove impact, not presence",
            objective=(
                "Distinguish a hardening gap from an exploitable flaw. "
            ),
            techniques=[
                "A missing header is a hardening finding, not a "
                "vulnerability, unless you demonstrate what it enables. Say "
                "which you are reporting. ",
                "For any exposed interface, show what it actually discloses "
                "or allows, and run the control test against an "
                "unauthenticated baseline. ",
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
