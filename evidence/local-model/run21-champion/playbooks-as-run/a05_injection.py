"""A05:2025 Injection (A03:2021), including cross-site scripting."""

from .base_playbook import BasePlaybook, Phase


class InjectionPlaybook(BasePlaybook):
    name = "a05_injection"
    description = (
        "OWASP A05 Injection: SQL, NoSQL, command, template, LDAP and "
        "header/log injection, plus cross-site scripting, using safe "
        "detection before any impactful proof. "
    )
    mode = "agent"
    max_loops = 60

    phases = [
        Phase(
            name="Identify injection candidates",
            objective=(
                "Find where input reaches an interpreter. "
            ),
            techniques=[
                "Work from the inventory: every parameter, header, cookie and "
                "body field is a candidate, including those only the client "
                "normally sets. ",
                "Note where input is reflected in responses, stored and "
                "rendered later, or appears to influence a query, path, "
                "command or template. ",
                "Prefer detection that is safe and reversible: syntax that "
                "would provoke a parse difference or an error, rather than "
                "anything destructive. ",
            ],
        ),
        Phase(
            name="Confirm by differential behaviour",
            objective=(
                "Prove interpretation, not coincidence. "
            ),
            techniques=[
                "Confirm an injection by demonstrating a controlled "
                "difference between two inputs - an error that appears and "
                "disappears, a boolean condition that changes the result, a "
                "timing difference you can repeat. A single odd response is "
                "not proof. ",
                "For cross-site scripting, show the payload is stored or "
                "reflected AND rendered in a context where it would execute. "
                "Quote the response showing the unescaped payload. ",
                "Do not run destructive payloads, do not modify or drop data, "
                "and do not attempt command execution beyond a harmless, "
                "clearly identifiable proof. ",
                "For claimed code or command execution the proof is OUTPUT of "
                "a command you chose, returned by the target - not a payload "
                "you sent and not an error that looks interesting. Match the "
                "payload to the actual platform. ",
            ],
        ),
        Phase(
            name="Bound the impact",
            objective=(
                "State what the injection actually reaches. "
            ),
            techniques=[
                "Establish what the injection can read or affect, and whether "
                "it crosses a trust boundary. ",
                "Run the control test: the same request with benign input, "
                "reported alongside. ",
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
