#!/usr/bin/env bash
# Capture a complete PentestAgent run into report/<label>/ for the talk record.
#
#   ./capture-run.sh <label> <remote-run-log-basename> [playbook-file]
#   ./capture-run.sh aided-playbook-v6-2026-07-31 run9-playbook-v6.log blazor_wasm.py
#
# Pulls the session log, the agent's own report, the full loot tree (notes,
# artifacts, decompiled sources, downloaded assemblies), and the exact playbook
# used. Writes a facts file that a human summary can be written against.
set -euo pipefail

HOST="${PENTEST_HOST:-ryan@<LAB-GPU-HOST>}"
KEY="${PENTEST_KEY:-$HOME/.ssh/<lab-key>}"
REMOTE="${PENTEST_DIR:-~/pentestagent}"

LABEL="${1:?usage: capture-run.sh <label> <run-log-basename> [playbook-file]}"
RUNLOG="${2:?usage: capture-run.sh <label> <run-log-basename> [playbook-file]}"
PLAYBOOK="${3:-}"

DEST="$(cd "$(dirname "$0")" && pwd)/$LABEL"
mkdir -p "$DEST"/{logs,agent-report,loot,playbook}

ssh_() { ssh -i "$KEY" "$HOST" "$@"; }
scp_() { scp -q -i "$KEY" "$HOST:$1" "$2" 2>/dev/null || echo "  (missing: $1)"; }

echo "==> session log"
scp_ "$REMOTE/$RUNLOG" "$DEST/logs/"

echo "==> agent report (most recent)"
# Newer runs write to loot/runs/<timestamp>_<target>/ with their own notes.
# Fall back to the legacy flat loot/reports/ layout for older runs.
LATEST_RUN_DIR=$(ssh_ "ls -dt $REMOTE/loot/runs/*/ 2>/dev/null | head -1" || true)
if [ -n "$LATEST_RUN_DIR" ]; then
  echo "  per-run dir: $(basename "$LATEST_RUN_DIR")"
  scp_ "$LATEST_RUN_DIR/report.md" "$DEST/agent-report/"
  scp_ "$LATEST_RUN_DIR/notes.json" "$DEST/agent-report/"
else
  LATEST_REPORT=$(ssh_ "ls -t $REMOTE/loot/reports/*.md 2>/dev/null | head -1" || true)
  [ -n "$LATEST_REPORT" ] && scp_ "$LATEST_REPORT" "$DEST/agent-report/"
fi

echo "==> loot tree (notes, artifacts, decompiled, assemblies)"
ssh_ "cd $REMOTE && tar czf /tmp/loot-capture.tgz loot 2>/dev/null" || true
scp_ "/tmp/loot-capture.tgz" "$DEST/loot/"
if [ -f "$DEST/loot/loot-capture.tgz" ]; then
  tar xzf "$DEST/loot/loot-capture.tgz" -C "$DEST/loot" && rm "$DEST/loot/loot-capture.tgz"
fi
ssh_ "rm -f /tmp/loot-capture.tgz" || true

echo "==> playbook used"
if [ -n "$PLAYBOOK" ]; then
  scp_ "$REMOTE/pentestagent/playbooks/$PLAYBOOK" "$DEST/playbook/"
fi

echo "==> extracting facts"
{
  echo "# Run facts — $LABEL"
  echo
  echo "Captured: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo
  echo "## Outcome counters"
  LOG="$DEST/logs/$(basename "$RUNLOG")"
  REP=$(ls "$DEST"/agent-report/*.md 2>/dev/null | head -1 || true)
  for f in "$LOG" "$REP"; do
    [ -f "$f" ] || continue
    echo "- $(basename "$f"): $(wc -l < "$f") lines"
  done
  echo
  echo "## Key recovery"
  if [ -n "$REP" ] && grep -q 'Vu1nB1az0r' "$REP" 2>/dev/null; then
    echo "- KEY RECOVERED in agent report ($(grep -c 'Vu1nB1az0r' "$REP") occurrences)"
  else
    echo "- key NOT present in agent report"
  fi
  if grep -rq 'Vu1nB1az0r' "$DEST/loot" 2>/dev/null; then
    echo "- key present in captured loot"
  fi
  echo
  echo "## Agent status line"
  [ -n "$REP" ] && grep -aE 'maximum iterations|Status|Duration|Loops|Tools|Tokens' "$REP" | head -8
  echo
  echo "## Artifacts captured"
  find "$DEST/loot" -type f 2>/dev/null | sed "s|$DEST/||" | head -40
} > "$DEST/RUN-FACTS.md"

echo
echo "captured -> $DEST"
echo "  next: write SUMMARY.md (verdict, what worked, what failed, why)"
