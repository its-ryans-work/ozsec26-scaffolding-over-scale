"""A01:2025 Broken Access Control + A07:2025 Authentication Failures
(A01:2021 and A07:2021 respectively).

Combined deliberately: an authorization gap and an authentication gap are
usually the same walk-through, and reporting them from one pass avoids the
duplicate findings that separate passes produce."""

from .base_playbook import BasePlaybook, Phase


class AccessAuthPlaybook(BasePlaybook):
    name = "a01_a07_access_auth"
    description = (
        "OWASP A01 Broken Access Control and A07 Authentication Failures, "
        "combined because authorization and authentication findings chain "
        "constantly. Covers IDOR, missing function-level checks, dispatcher "
        "bypass, weak session handling, and credential reuse. "
    )
    mode = "agent"
    max_loops = 60

    phases = [
        Phase(
            name="Object and function level access",
            objective=(
                "Determine what can be reached without the right identity. "
            ),
            techniques=[
                "Request objects belonging to other identifiers and compare "
                "responses. Enumerate identifiers where a directory or index "
                "endpoint offers them. ",
                "Compare anonymous, low-privilege and high-privilege views of "
                "the same endpoint. Differences reveal missing checks; "
                "identical results for anonymous and authenticated mean the "
                "resource is simply public - say so rather than claiming a "
                "bypass. ",
                "Test privileged functionality directly rather than through "
                "the UI, including administrative routes discovered in client "
                "code or metadata. ",
                "Exercise every HTTP method an endpoint accepts, not just the "
                "one the client uses. ",
                "Probe endpoints that dispatch, batch, proxy or import: "
                "reaching a handler indirectly frequently bypasses checks "
                "applied to its direct route. Compare the direct and indirect "
                "result explicitly. ",
            ],
        ),
        Phase(
            name="Authentication and session handling",
            objective=(
                "Assess how identity is established and maintained. "
            ),
            techniques=[
                "Test for default, seeded or well-known credentials. ",
                "Examine the session representation: is it random, or does it "
                "encode or derive from something predictable or recoverable? ",
                "Test whether a session survives logout, whether it expires, "
                "and whether it can be fixed or reused from another context. ",
                "Assess protections against automated guessing, but do NOT "
                "run volumetric guessing here - note the absence of a control "
                "rather than proving it by force. ",
                "If credential material is recoverable elsewhere in the "
                "assessment, test it here for reuse across accounts and "
                "across every distinct authentication surface. ",
            ],
        ),
        Phase(
            name="Prove and bound the impact",
            objective=(
                "Convert access findings into demonstrated, bounded impact. "
            ),
            techniques=[
                "For every claimed bypass, run and report the control test: "
                "the same request without the material or identity. A finding "
                "without a control result is not a finding. ",
                "Establish breadth - one object or all of them, one account "
                "or every account. Breadth drives severity more than "
                "technique. ",
                "Record what a compromised session actually grants: roles, "
                "privileged functions, other users' data. ",
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
