"""First-pass web surface discovery.

Runs before any category playbook. Its job is to produce a complete,
reusable inventory - not to exploit anything. Exploitation belongs to the
per-category playbooks that follow, which have the verification discipline
this phase deliberately omits."""

from .base_playbook import BasePlaybook, Phase


class WebDiscoveryPlaybook(BasePlaybook):
    name = "web_discovery"
    description = (
        "First-pass discovery of a web application's attack surface: "
        "technology, endpoints, parameters, authentication mechanisms, and "
        "everything shipped to the client. Produces the inventory that the "
        "per-category playbooks are assessed against. Finds surface; does not "
        "attempt exploitation. "
    )
    mode = "crew"
    max_loops = 40

    phases = [
        Phase(
            name="Fingerprint the stack",
            objective=(
                "Identify what is running so later playbooks can be selected "
                "sensibly. "
            ),
            techniques=[
                "Identify server, framework and client technology from "
                "headers, cookies, error pages, asset names and response "
                "shapes. ",
                "Note the authentication mechanism and session representation "
                "(cookie names, token formats, headers). ",
                "Record the stack explicitly: it determines which stack- "
                "specific playbook should run next (for example a client-side "
                ".NET or SPA bundle, or a particular reverse proxy). ",
                "Identify API style and locate any metadata, schema or "
                "documentation endpoint (OpenAPI, GraphQL introspection, "
                "framework metadata). ",
            ],
        ),
        Phase(
            name="Enumerate the surface",
            objective=(
                "Map endpoints, parameters and inputs. "
            ),
            techniques=[
                "Enumerate routes and endpoints from metadata documents, "
                "client code, sitemaps and directory discovery. ",
                "Record every parameter and input point, including headers "
                "and cookies, and which are reflected in responses. ",
                "For each endpoint note whether it responds without "
                "authentication, and what differs when authenticated. This "
                "baseline is what later control tests compare against - "
                "capture it carefully. ",
                "Note any endpoint that dispatches, batches, proxies or "
                "forwards requests internally, as these bypass controls "
                "applied to direct routes. ",
            ],
        ),
        Phase(
            name="Collect the client payload",
            objective=(
                "Everything the browser receives is public and must be "
                "retrieved. "
            ),
            techniques=[
                "Download what the client downloads: scripts, bundles, source "
                "maps, compiled binaries, WebAssembly, configuration blobs. ",
                "Compiled or minified client code must be unpacked or "
                "decompiled before it can be searched. A clean search over a "
                "binary or a minified bundle is NOT evidence of absence. ",
                "Record where artifacts were written so later playbooks reuse "
                "them rather than downloading again. ",
            ],
        ),
        Phase(
            name="Write the inventory",
            objective=(
                "Leave a durable, structured record. "
            ),
            techniques=[
                "Save to notes: technology stack, endpoints with auth status, "
                "parameters, client artifacts and their paths, and any "
                "credential-bearing material observed. ",
                "Do not attempt exploitation here. Flag candidates for the "
                "category playbooks instead, with the evidence that makes "
                "them candidates. ",
            ],
        ),
    ]
