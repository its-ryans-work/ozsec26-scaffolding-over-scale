"""Do the agents ever REACH the later phases, or does the budget run out first?

The firing audit found dead rules clustering in each playbook's last phase. Two
explanations fit that: the rules are useless, or the phase is never reached. They
call for opposite fixes, so distinguish them before deleting anything.

Test: does the agent's own post-banner output ever name a given phase? Phase names
are distinctive multi-word strings ("Verify before reporting", "Chain findings into
higher severity") and the orchestrator narrates the phase it is working.
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rule_firing_audit import (IN_PIPELINE, LOGS, load_techniques, normalize,
                               strip_banner)

techs = load_techniques()
phases_of = {}
for t in techs:
    phases_of.setdefault(t["playbook"], [])
    if t["phase"] not in phases_of[t["playbook"]]:
        phases_of[t["playbook"]].append(t["phase"])

logs = sorted(p for p in LOGS.rglob("[0-9][0-9]-*.log"))
seen = {}
kept = []
for p in logs:
    k = (p.name, p.stat().st_size)
    if k in seen:
        continue
    seen[k] = 1
    kept.append(p)

bodies = {}
for p in kept:
    pb = p.stem.split("-", 1)[1] if "-" in p.stem else p.stem
    if pb not in IN_PIPELINE:
        continue
    bodies.setdefault(pb, []).append(normalize(strip_banner(p.read_text(errors="replace"))))

print("How many of a playbook's runs mention each phase in the agent's own output")
print("(phase order is execution order; the budget is spent top to bottom)\n")
print(f"{'playbook':24} {'phase':46} {'runs mentioning':>15}")
for pb in IN_PIPELINE:
    bs = bodies.get(pb, [])
    if not bs:
        continue
    for i, ph in enumerate(phases_of[pb], 1):
        needle = " ".join(normalize(ph).split())
        n = sum(1 for b in bs if needle in b)
        flag = "   <-- NEVER" if n == 0 else ""
        print(f"{pb if i == 1 else '':24} {str(i) + '. ' + ph[:42]:46} {n:>7}/{len(bs)}{flag}")
    print()
