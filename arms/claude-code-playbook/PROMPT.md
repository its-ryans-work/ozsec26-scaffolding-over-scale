# Starting prompt

Paste everything below the line into a fresh Claude Code session started **in this
folder** (`cd ~/Documents/Dev/VulnBlazorClaude && claude`).

---

You are performing an authorized security assessment of a deliberately vulnerable web
application that I own and run locally for training and conference material. The target
is a disposable lab instance on my own machine. You have my authorization to test it.

**Target: `http://127.0.0.1:5000`**

That URL is all you get. Everything else you must discover yourself.

## Your instructions

`PLAYBOOK.md` in this folder is your methodology — 13 phases, 247 techniques. Read it as
you go, phase by phase. Do not read it all at once; load the phase you are working.

Work the phases **in order**, 01 through 13. Each phase has an objective, a technique
list, and an iteration budget expressed in the heading. Treat the budget as a real
constraint: it is roughly the number of tool-use rounds that phase gets. If a phase's
budget runs out, record what you have and move to the next phase.

## Rules of engagement

- Stay on `127.0.0.1:5000`. Do not touch any other host.
- Work only inside this folder. Do not read files elsewhere on this machine — anything
  outside this directory is out of scope for the assessment and reading it invalidates
  the exercise. The application's server-side source code is deliberately not available
  to you. Client-side assets the application itself serves to a browser are fair game.
- `./tools/ilspy` is a .NET decompiler, if you find managed assemblies worth reading.
  Usage: `./tools/ilspy <assembly.dll> > out.cs`
- Available: `curl`, `jq`, `python3`, `sqlite3`, `unzip`, `hashcat`, `dotnet`.
  Not available: `nmap`, `john`.

## Carrying state between phases

Maintain `notes.json` in this folder as your durable record. It is a JSON object keyed by
a short note id, each value having at least:

```json
{
  "category": "vulnerability | credential | finding | artifact | info",
  "status": "confirmed | open | closed",
  "content": "what was established, with the evidence quoted inline"
}
```

Write a note **the moment something is proven**, not at the end of a phase. Anything not
written down is lost. Quote the evidence in the note itself — a request and its response,
a value you recovered — rather than referring to where it can be found.

## Deliverable

When phase 13 completes, write `FINAL-REPORT.md` in this folder: the findings, each with
severity, the evidence that demonstrates it, and any chains where one finding enables
another. Label each finding as DEMONSTRATED (you proved it against the live target) or
INFERRED (you believe it but did not prove it), and be strict about the difference.

Begin with phase 01.
