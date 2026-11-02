# Talk materials

**Scaffolding Over Scale: Unauthenticated Account Takeover in Blazor with a Local LLM**
OzSec 2026 · Ryan Chaplin, Lead Penetration Tester, Raxis

| File | What it is |
|---|---|
| `ozsec2026-scaffolding-over-scale.pptx` | The slides as presented, 17 slides. |

## The argument, in short

A real engagement produced an unauthenticated account takeover in a mature .NET Blazor
application: three years of recurrent pentesting, latest modern .NET, no deserialization
vulnerability, no weak credentials, and no off-the-shelf tool that chained the path. The
chain that worked was six steps and crossed two unrelated subsystems. A key named for
telemetry decrypted something that looked like session state and turned out to be a
password.

Pointed at a replica of that target, LLM agents land in a clear order:

- **Chat interface, no tools.** About three of the six steps, consistently. It struggles
  precisely at chaining and escalation, and specifically at checking for credential reuse.
  Hallucination is a serious problem at this tier.
- **Agentic, generic prompt.** Better. Sometimes all the way.
- **Agentic, with a stack-specific playbook and real tooling.** Reliably all the way.
- **A local 27B model with that same playbook and tooling.** Beats the frontier model given
  a generic prompt, and loses to the frontier model given the same scaffolding.

So the leverage is in the scaffolding, not the parameter count. If you are using a chat
interface or a generic prompt, the upgrade that pays is an agentic workflow, even on a
model you run yourself. A smaller model you control can beat a larger one you do not, given
the right skills and tools.

The defensive half: treat every DLL under `/_framework` as public, audit decompiled IL
rather than source, put secret scanning in CI, and use a WAF that can spot AI user agents
performing malicious actions.

## Caveats stated in the talk

- The methodology is human-led and LLM-supplemented, not autonomous, and not pointed at
  production applications.
- Frontier agents escape sandboxes. The risk of unintended consequences is real, and is part
  of why local models you control are interesting beyond cost.
- The success rates are five runs each. See the honest-limits discussion in the root
  [`README`](../README.md#results) and the controlled experiment in
  [`../evidence/local-model/abc-replay-experiment/`](../evidence/local-model/abc-replay-experiment/),
  which shows why five is not enough.

## Reusing these

The slides are the author's own work and are included here for reference rather than reuse.
Ask first.
