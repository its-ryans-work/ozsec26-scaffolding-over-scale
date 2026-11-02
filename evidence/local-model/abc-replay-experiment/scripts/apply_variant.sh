#!/usr/bin/env bash
# Put one variant's files in place. Idempotent; verifies before returning.
#
#   A  baseline            chain_findings 44 techniques, checkpoint unchanged
#   B  merged prompt       chain_findings 43 (#2+#3 merged into one 125w rule)
#   C  relocated demand    chain_findings 44 (BASELINE prompt) + checkpoint item 4
#
# C deliberately keeps the BASELINE playbook. The earlier C stacked the merge and
# the checkpoint together, so a null result could not distinguish "the checkpoint
# does nothing" from "the merge cancelled it out". Each arm now changes exactly
# one thing against A.
set -eu
V="${1:?variant A|B|C}"
VD=~/replay/variants
PBD=~/pentestagent/pentestagent/playbooks
AGD=~/pentestagent/pentestagent/agents

case "$V" in
  A) cp "$VD/A-chain_findings.py" "$PBD/chain_findings.py"; cp "$VD/A-base_agent.py" "$AGD/base_agent.py" ;;
  B) cp "$VD/B-chain_findings.py" "$PBD/chain_findings.py"; cp "$VD/A-base_agent.py" "$AGD/base_agent.py" ;;
  C) cp "$VD/A-chain_findings.py" "$PBD/chain_findings.py"; cp "$VD/C-base_agent.py" "$AGD/base_agent.py" ;;
  *) echo "unknown variant $V" >&2; exit 1 ;;
esac

cd ~/pentestagent && source venv/bin/activate
python3 - "$V" <<'PY'
import ast, sys
v = sys.argv[1]
src = open("pentestagent/playbooks/chain_findings.py").read()
n = sum(len(k.value.elts)
        for node in ast.walk(ast.parse(src))
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Phase"
        for k in node.keywords if k.arg == "techniques")
cp = "Did you retype a recovered value" in open("pentestagent/agents/base_agent.py").read()
want_n = 43 if v == "B" else 44
want_cp = (v == "C")
ok = (n == want_n) and (cp == want_cp)
print(f"  variant {v}: chain_findings={n} techniques (want {want_n}), "
      f"checkpoint_item4={cp} (want {want_cp})  {'OK' if ok else 'MISMATCH'}")
sys.exit(0 if ok else 1)
PY
