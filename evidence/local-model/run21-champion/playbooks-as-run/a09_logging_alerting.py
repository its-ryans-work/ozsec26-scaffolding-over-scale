"""A09:2025 Security Logging and Alerting Failures (A09:2021).

Mostly not assessable remotely - report honestly what could and could not
be determined rather than inferring absence of logging from silence."""

from .base_playbook import BasePlaybook, Phase


class LoggingAlertingPlaybook(BasePlaybook):
    name = "a09_logging_alerting"
    description = (
        "OWASP A09 Security Logging and Alerting Failures, assessed from "
        "outside: exposed logs, credential material in logs, and whether "
        "security-relevant events produce any observable reaction. "
    )
    mode = "agent"
    max_loops = 25

    phases = [
        Phase(
            name="Exposed logs and leaked material",
            objective=(
                "Logs are frequently reachable and frequently contain "
                "secrets. "
            ),
            techniques=[
                "Probe for log viewers, request-log endpoints, diagnostic or "
                "profiler interfaces, and downloadable log files. ",
                "If any log content is reachable, search it for credentials, "
                "tokens, session identifiers, keys and personal data - logged "
                "secrets are a finding in their own right. ",
                "Check whether error responses disclose material that belongs "
                "only in a log. ",
            ],
        ),
        Phase(
            name="Observable reaction to security events",
            objective=(
                "Determine whether anything appears to notice. "
            ),
            techniques=[
                "Perform a small number of clearly security-relevant but non- "
                "destructive actions (a failed authentication, access to a "
                "forbidden object) and observe whether behaviour changes - "
                "throttling, challenge, lockout, or notification. ",
                "Test session collision: authenticate the same account from a "
                "second, independent context and observe whether the first "
                "session is invalidated, whether a notification is produced, "
                "and whether concurrent sessions are permitted silently. A "
                "browser tool helps here; if unavailable, approximate with "
                "two separate cookie jars and say which method was used. ",
                "Do NOT generate volume to test alerting - a handful of "
                "events is sufficient and anything more risks denial of "
                "service. ",
                "Report absence of an observable reaction as exactly that: "
                "not observed from outside, which is not the same as not "
                "logged. ",
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
