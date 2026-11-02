#!/usr/bin/env bash
# Run chain_findings ALONE from the pristine snapshot, then grade it.
#
# Usage: replay_chain.sh <variant-label> <rep-number> [max_iterations]
#
# Each repetition restores byte-identical inputs first, so the only thing varying
# between reps of the same variant is model sampling - which is exactly what we
# want to measure, since one run proves nothing about a behaviour this stochastic.
set -eu

VARIANT="${1:?variant label}"
REP="${2:?rep number}"
ITERS="${3:-80}"
ID=20260805_152549_http_127.0.0.1_5000
SNAP=~/replay/snapshot
OUT=~/replay/results/${VARIANT}-rep${REP}
TARGET=http://127.0.0.1:5000

cd ~/pentestagent
source venv/bin/activate

# ---- restore pristine inputs -------------------------------------------
L=loot/assessments/$ID
rm -rf "$L"
mkdir -p "$L/draft_playbook_reports" "$L/scratchpads" "$L/final_deliverable"
cp "$SNAP/draft_playbook_reports"/* "$L/draft_playbook_reports/"
cp -a "$SNAP/scratchpads"/* "$L/scratchpads/" 2>/dev/null || true
mkdir -p workspaces/vulnblazor/loot
cp "$SNAP/notes.json" workspaces/vulnblazor/loot/notes.json

mkdir -p "$OUT"
echo "[$(date '+%T')] $VARIANT rep$REP - inputs restored ($(python3 -c "import json;print(len(json.load(open('workspaces/vulnblazor/loot/notes.json'))))") notes)"

# ---- run chain_findings alone ------------------------------------------
START=$(date +%s)
PENTESTAGENT_ASSESSMENT_ID="$ID" \
PENTESTAGENT_AGENT_MAX_ITERATIONS="$ITERS" \
PENTESTAGENT_PLAYBOOK=chain_findings \
  pentestagent run -t "$TARGET" --playbook chain_findings --report \
  > "$OUT/chain_findings.log" 2>&1 || true
ELAPSED=$(( $(date +%s) - START ))

cp workspaces/vulnblazor/loot/notes.json "$OUT/notes.json" 2>/dev/null || true
cp "$L/draft_playbook_reports"/*chain_findings.md "$OUT/" 2>/dev/null || true

# ---- grade --------------------------------------------------------------
LOG="$OUT/chain_findings.log"
{
  echo "variant        : $VARIANT"
  echo "rep            : $REP"
  echo "elapsed_s      : $ELAPSED"
  echo "iterations     : $(grep -oE 'iter [0-9]+/[0-9]+' "$LOG" | tail -1)"
  echo "DECRYPTED      : $(grep -c 'p@55wOrd' "$LOG")"
  echo "accounts_decrypted: $(grep -oiE '(employee|manager|admin|test)@email\.com[^\n]{0,40}p@55wOrd' "$LOG" | grep -oiE '^(employee|manager|admin|test)' | sort -u | tr '\n' ' ')"
  echo "key_6at        : $(grep -c 'ecretKey!2026@@@@@@\"' "$LOG" || true)"
  echo "key_8at        : $(grep -c 'ecretKey!2026@@@@@@@@' "$LOG" || true)"
  echo "reread_literal : $(grep -ciE 'grep .*(DefaultProfile|Vu1nB1az0r).*\.cs|read.*decompiled.*\.cs' "$LOG" || true)"
  echo "hashcat_effort : $(grep -ci 'hashcat\|rockyou\|john ' "$LOG" || true)"
  echo "notes_written  : $(python3 -c "import json;print(len(json.load(open('$OUT/notes.json'))))" 2>/dev/null || echo '?')"
} | tee "$OUT/GRADE.txt"
