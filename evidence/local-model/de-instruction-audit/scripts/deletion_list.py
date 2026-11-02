"""Separate rules that are DEAD from rules that are merely UNREACHED.

"Never fired" has three causes and they need opposite fixes:

  UNREACHED   the phase holding it is past where the budget runs out. Deleting it
              removes a rule that was never given a chance. Fix: relocate.
  PRECONDITION the rule covers a situation this target never presented (the
              decompiler-install ladder, with ilspycmd already on the box). It was
              tested working when the situation did occur. Fix: keep.
  DEAD        its own phase demonstrably ran - a sibling technique in the SAME
              phase left a verbatim trace - and this one still left nothing.
              Fix: delete.

Only the third is deletable on evidence.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rule_firing_audit as A

# Rebuild the scored results by re-running the audit's own logic.
techniques = A.load_techniques()
logs = sorted(p for p in A.LOGS.rglob("[0-9][0-9]-*.log"))
seen, kept = {}, []
for p in logs:
    k = (p.name, p.stat().st_size)
    if k not in seen:
        seen[k] = 1
        kept.append(p)
logs = kept

NS = (10, 8, 6, 5, 4)
index = {pb: {n: {} for n in NS} for pb in A.IN_PIPELINE}
tokens_seen = {pb: Counter() for pb in A.IN_PIPELINE}
for p in logs:
    pb = p.stem.split("-", 1)[1] if "-" in p.stem else p.stem
    if pb not in index:
        continue
    words = A.normalize(A.strip_banner(p.read_text(errors="replace"))).split()
    for w in set(words):
        tokens_seen[pb][w] += 1
    for n in NS:
        for h in A.ngram_hashes(words, n):
            index[pb][n][h] = 1

tech_df = Counter()
for t in techniques:
    for w in set(A.words_of(t["text"])):
        if w not in A.STOP and len(w) > 2:
            tech_df[w] += 1
cut = max(3, int(0.06 * len(techniques)))

scored = []
for t in techniques:
    pb, words = t["playbook"], A.normalize(t["text"]).split()
    best = 0
    for n in NS:
        if len(words) >= n and any(
            hash(tuple(words[i:i + n])) in index[pb][n]
            for i in range(len(words) - n + 1)
        ):
            best = n
            break
    sig = sorted((w for w in set(words)
                  if w not in A.STOP and len(w) > 2 and tech_df[w] <= cut),
                 key=lambda w: (tech_df[w], -len(w)))[:6]
    cov = (sum(1 for w in sig if tokens_seen[pb][w]) / len(sig)) if sig else 0.0
    tier = "RESTATED" if best else ("TOPICAL" if sig and cov >= 0.5 else "NO-TRACE")
    scored.append({**t, "tier": tier})

# --- classify -----------------------------------------------------------
phase_order = defaultdict(list)
for t in scored:
    if t["phase"] not in phase_order[t["playbook"]]:
        phase_order[t["playbook"]].append(t["phase"])

# A phase "demonstrably ran" if MOST of its techniques left some trace.
# The looser "any sibling restated" test called a phase engaged on the strength of
# one hit in one run out of nine, which is not enough to call its neighbours dead.
per_phase = defaultdict(list)
for t in scored:
    per_phase[(t["playbook"], t["phase"])].append(t)
ran, ran_loose = set(), set()
for key, ts in per_phase.items():
    live = sum(1 for t in ts if t["tier"] != "NO-TRACE")
    if live / len(ts) >= 0.5:
        ran.add(key)
    if any(t["tier"] == "RESTATED" for t in ts):
        ran_loose.add(key)
print(f"[sensitivity] phases engaged: {len(ran)} (majority test) "
      f"vs {len(ran_loose)} (any-sibling test) of {len(per_phase)}\n")

PRECONDITION_PHASES = {
    ("blazor_wasm", "Prepare the decompilation toolchain"),
}

buckets = defaultdict(list)
for t in scored:
    if t["tier"] != "NO-TRACE":
        continue
    key = (t["playbook"], t["phase"])
    if key in PRECONDITION_PHASES:
        buckets["PRECONDITION"].append(t)
    elif key in ran:
        buckets["DEAD"].append(t)
    else:
        buckets["UNREACHED"].append(t)

total_dead = sum(len(v) for v in buckets.values())
print(f"{total_dead} NO-TRACE techniques, classified:\n")
for b in ("DEAD", "UNREACHED", "PRECONDITION"):
    print(f"  {b:13} {len(buckets[b]):3}")

print("\n" + "=" * 78)
print("UNREACHED - do NOT delete; the phase never ran. Relocate or re-budget.")
print("=" * 78)
byphase = Counter((t["playbook"], t["phase"]) for t in buckets["UNREACHED"])
for (pb, ph), c in byphase.most_common():
    pos = phase_order[pb].index(ph) + 1
    print(f"  {c:3}  {pb}/{ph}  (phase {pos} of {len(phase_order[pb])})")

print("\n" + "=" * 78)
print("DEAD - the phase demonstrably ran and these still left no trace. Delete.")
print("=" * 78)
for t in sorted(buckets["DEAD"], key=lambda x: (x["playbook"], x["phase"], x["idx"])):
    print(f"\n  {t['playbook']}/{t['phase']}#{t['idx']}  "
          f"({len(t['text'].split())}w)")
    print(f"    {t['text'][:300]}")

words_dead = sum(len(t["text"].split()) for t in buckets["DEAD"])
words_all = sum(len(t["text"].split()) for t in scored)
print(f"\n  deleting these removes {words_dead:,} of {words_all:,} technique words "
      f"({words_dead / words_all * 100:.0f}%)")
