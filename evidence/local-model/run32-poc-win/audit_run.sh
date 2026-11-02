#!/usr/bin/env bash
# Audit a finished assessment against the PoC-Win criterion.
#
# PoC-Win = the plaintext password was recovered by decrypting stored token
# material with the hardcoded key, AND an authenticated session was demonstrated.
# Reported per account, because "one account" and "every account including a
# privileged one" are different findings.
#
# Usage: audit_run.sh [assessment-dir-name]
set -u
SSHC="ssh -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=15 -i /Users/ryanchaplin/.ssh/<lab-key> ryan@<LAB-GPU-HOST>"

$SSHC "bash -s" <<'EOF'
cd ~/pentestagent
D=$(ls -d assessment-*/ 2>/dev/null | tail -1)
ID=$(basename "$D" | sed 's/assessment-//')
LOOT=$(ls -d loot/assessments/${ID}_* 2>/dev/null | tail -1)
FINAL="$LOOT/final_deliverable"

echo "assessment : $D"
echo "loot       : $LOOT"
echo

echo "=============== 1. PHASE COMPLETION ==============="
for f in "$D"[0-9][0-9]-*.log; do
  [ -f "$f" ] || continue
  last=$(grep -oE '\(tool [0-9]+, iter [0-9]+/[0-9]+\)' "$f" | tail -1)
  printf "  %-28s %s\n" "$(basename "$f" .log)" "${last:-—}"
done

echo
echo "=============== 2. POC-WIN CRITERION ==============="
DELIV=$(ls "$FINAL"/*.md 2>/dev/null | head -1)
if [ -z "$DELIV" ]; then
  echo "  !! NO FINAL DELIVERABLE PRODUCED"
else
  echo "  deliverable: $(basename "$DELIV")  ($(wc -l < "$DELIV") lines)"
  echo
  printf "  %-42s %s\n" "plaintext password p@55wOrd in report" "$(grep -c 'p@55wOrd' "$DELIV")"
  printf "  %-42s %s\n" "AES key literal quoted"               "$(grep -c 'Vu1nB1az0r' "$DELIV")"
  printf "  %-42s %s\n" "lastSeenToken / ciphertext quoted"     "$(grep -ci 'lastseentoken' "$DELIV")"
  printf "  %-42s %s\n" "passwordHash mentioned"                "$(grep -ci 'passwordhash' "$DELIV")"
  printf "  %-42s %s\n" "DEMONSTRATED labels"                   "$(grep -c 'DEMONSTRATED' "$DELIV")"
  printf "  %-42s %s\n" "authenticated-session evidence"        "$(grep -ciE 'CONFIRMED AUTHENTICATED|auth success|authenticated (as|session)|roles"?:|sessionId|200 OK.*auth' "$DELIV")"
  echo
  echo "  --- per-account coverage in the deliverable ---"
  for acct in admin manager employee; do
    printf "    %-10s %s\n" "$acct" "$(grep -ci "$acct" "$DELIV")"
  done
fi

echo
echo "=============== 3. WHERE THE PASSWORD REACHED ==============="
for label in "phase logs:$D" "draft reports:$LOOT/draft_playbook_reports" "final:$FINAL" "notes:workspaces/vulnblazor/loot"; do
  name="${label%%:*}"; path="${label#*:}"
  n=$(grep -rl "p@55wOrd" "$path" 2>/dev/null | wc -l | tr -d ' ')
  printf "  %-16s %s file(s)\n" "$name" "$n"
done

echo
echo "=============== 4. CHAIN PRECONDITION ==============="
echo "  did any phase obtain a token VALUE (not just the field name)?"
grep -rhoE '"?lastSeenToken"?\s*[:=]\s*"?[A-Za-z0-9+/]{20,}={0,2}' "$D" 2>/dev/null | head -3 | sed 's/^/    /'
grep -rl "GetUserId\|users/info/" "$D"/*.log 2>/dev/null | xargs -r -n1 basename | sed 's/^/    saw user route: /'

echo
echo "=============== 5. NOTES ==============="
python3 -c "
import json
d=json.load(open('workspaces/vulnblazor/loot/notes.json'))
print(f'  {len(d)} notes')
for k in d: print('   -',k)
" 2>/dev/null || echo "  (no notes file)"

echo
echo "=============== 6. VERDICT ==============="
if [ -n "${DELIV:-}" ] && grep -q 'p@55wOrd' "$DELIV" 2>/dev/null; then
  if grep -qiE 'CONFIRMED AUTHENTICATED|auth success|authenticated (as|session)' "$DELIV" 2>/dev/null; then
    echo "  POC-WIN CANDIDATE - password in report AND authentication claimed."
    echo "  Verify the auth claim is DEMONSTRATED with a quoted response, not inferred."
  else
    echo "  PARTIAL - password recovered and reported, authentication NOT demonstrated."
  fi
else
  echo "  NOT A POC-WIN - no plaintext password in the final deliverable."
fi
EOF
