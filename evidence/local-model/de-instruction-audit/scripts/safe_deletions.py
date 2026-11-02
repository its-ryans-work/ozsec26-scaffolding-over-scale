"""The recency correction, and the final deletion list.

A rule can only be said to have never fired across the runs in which it EXISTED.
Without that correction the audit condemns exactly the rules most recently added -
including two that fixed known, diagnosed failures:

  "CHECK THE VERDICT RECORD IS ACTUALLY POPULATED"  added after run28's gate broke
  "QUOTE THE EVIDENCE, NEVER CITE IT"               the run26 change that first got
                                                    the decrypt into the deliverable

Both read NO-TRACE for the same reason: almost no run in the corpus had them.
Deleting them would have re-opened two solved bugs.

So: date every technique from the playbook snapshots, count only the runs that
started after it appeared, and require a minimum exposure before judging it.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import rule_firing_audit as A

SNAP = A.SC / "snapshots"
MIN_RUNS = 3          # judge nothing that has had fewer than this many chances

# Assessment start times, from the archive directory names.
RUNS = {
    "run20": "2026-08-02 00:10", "run21": "2026-08-02 10:04",
    "run22": "2026-08-02 20:25", "run23": "2026-08-03 07:41",
    "run24": "2026-08-03 14:32", "run25": "2026-08-03 19:24",
    "run26": "2026-08-04 01:10", "run27": "2026-08-04 08:05",
    "run28": "2026-08-04 14:39",
}
import datetime as _dt
RUN_TS = {k: _dt.datetime.fromisoformat(v).timestamp() for k, v in RUNS.items()}


def techniques_in(path):
    """Normalised technique texts present in one playbook source file."""
    out = set()
    try:
        import ast
        tree = ast.parse(Path(path).read_text())
    except Exception:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Phase":
            for kw in node.keywords:
                if kw.arg != "techniques":
                    continue
                for elt in kw.value.elts:
                    try:
                        out.add(" ".join(A.words_of(ast.literal_eval(elt))))
                    except Exception:
                        pass
    return out


# --- build the version timeline per playbook ---------------------------
mtimes = {}
for line in (SNAP / "kali-orig-mtimes.txt").read_text().splitlines():
    if "|" in line:
        f, ts = line.rsplit("|", 1)
        mtimes[f] = int(ts)

versions = defaultdict(list)   # playbook -> [(timestamp, set-of-techniques)]
for f, ts in mtimes.items():
    pb = f.split(".py")[0]
    versions[pb].append((ts, techniques_in(SNAP / "kali-orig" / f)))
run21_ts = _dt.datetime.fromisoformat("2026-08-02 15:02").timestamp()
for p in (SNAP / "run21").glob("*.py"):
    versions[p.stem].append((run21_ts, techniques_in(p)))
for pb in A.IN_PIPELINE:
    versions[pb].sort(key=lambda x: x[0])

# --- date each current technique --------------------------------------
techniques = A.load_techniques()
appeared = {}
for t in techniques:
    key = " ".join(A.words_of(t["text"]))
    vs = versions.get(t["playbook"], [])
    first = None
    for ts, texts in vs:
        if key in texts:
            first = ts
            break
    if first is None:
        # Absent from every snapshot: added after the newest one for this playbook.
        first = max((ts for ts, _ in vs), default=0) if vs else 0
        first = first or _dt.datetime.fromisoformat("2026-08-04 19:17").timestamp()
    appeared[(t["playbook"], t["phase"], t["idx"])] = first

exposure = {k: sum(1 for r, ts in RUN_TS.items() if ts >= v)
            for k, v in appeared.items()}

print("EXPOSURE - how many runs each technique was actually present for\n")
hist = Counter(exposure.values())
for n in sorted(hist):
    print(f"  present for {n} run(s): {hist[n]:3} techniques")
young = [k for k, v in exposure.items() if v < MIN_RUNS]
print(f"\n  {len(young)} techniques have had fewer than {MIN_RUNS} runs and cannot "
      f"be judged yet.\n")

# --- re-read the DEAD list and apply the correction --------------------
dead_lines = []
sec = Path(A.SC / "deletion-out.txt").read_text()
sec = sec.split("DEAD - the phase demonstrably ran")[1]
import re
for m in re.finditer(r"^  ([a-z0-9_]+)/(.+?)#(\d+)\s+\((\d+)w\)", sec, re.M):
    dead_lines.append((m.group(1), m.group(2), int(m.group(3)), int(m.group(4))))

keep_young, safe = [], []
for pb, ph, idx, w in dead_lines:
    k = (pb, ph, idx)
    (safe if exposure.get(k, 0) >= MIN_RUNS else keep_young).append((pb, ph, idx, w, exposure.get(k, 0)))

print("=" * 78)
print(f"SPARED BY THE RECENCY CORRECTION - too new to judge ({len(keep_young)})")
print("=" * 78)
for pb, ph, idx, w, e in sorted(keep_young):
    print(f"  {e} run(s)   {pb}/{ph}#{idx}")

print("\n" + "=" * 78)
print(f"SAFE TO DELETE - present for >={MIN_RUNS} runs, phase engaged, no trace ({len(safe)})")
print("=" * 78)
tech_by_key = {(t["playbook"], t["phase"], t["idx"]): t for t in techniques}
for pb, ph, idx, w, e in sorted(safe):
    t = tech_by_key[(pb, ph, idx)]
    print(f"\n  [{e} runs, {w}w]  {pb}/{ph}#{idx}")
    print(f"    {t['text'][:260]}")
print(f"\n  total {sum(x[3] for x in safe):,} technique words removed")

# --- artifact-channel exclusion ---------------------------------------
# Rules that govern the shape of the WRITTEN REPORT leave their trace in the
# deliverable, not in the phase log. Measured in the run22/25/26 deliverables:
# DEMONSTRATED labels 17/15/21, key literal quoted 15-17x, control test 11/6/2.
# They are live; the log is simply the wrong place to look for them.
ARTIFACT_PHASES = {
    ("final_integrity_gate", "Emit the final deliverable"),
    ("final_integrity_gate", "Evidence integrity check"),
}
final = [x for x in safe if (x[0], x[1]) not in ARTIFACT_PHASES]
excluded = [x for x in safe if (x[0], x[1]) in ARTIFACT_PHASES]

print("\n" + "=" * 78)
print(f"EXCLUDED - artifact-governed, judged by the wrong channel ({len(excluded)})")
print("=" * 78)
for pb, ph, idx, w, e in sorted(excluded):
    print(f"  {pb}/{ph}#{idx}")

import json
json.dump([{"playbook": p, "phase": ph, "idx": i, "words": w, "runs": e}
           for p, ph, i, w, e in sorted(final)],
          open("final-deletions.json", "w"), indent=1)
print(f"\nFINAL DELETION LIST: {len(final)} techniques, "
      f"{sum(x[3] for x in final):,} words -> final-deletions.json")
