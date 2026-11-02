#!/usr/bin/env bash
# Full assessment pipeline v2.
#
# Discovery -> stack-specific -> per-category OWASP -> consolidate -> chain ->
# consolidate -> adversarial review -> final integrity gate.
#
# The two consolidation passes sit at the handoffs where findings are otherwise
# lost: a finding stated only in an assistant narration panel reaches neither
# notes nor the report window, and vanishes at the next phase. Consolidation
# reads the phase logs and writes what it finds to notes, which is the only
# channel later phases reliably receive.
#
# a06_insecure_design_DANGEROUS is deliberately excluded: it tests for the
# ABSENCE of rate limiting and account lockout, which means provoking the
# conditions those controls exist to prevent. Run it separately, only against a
# disposable target, and never against production.
set -u

cd "$HOME/pentestagent" || exit 1
source venv/bin/activate

TARGET="${1:-http://127.0.0.1:5000}"
STAMP=$(date +%Y%m%d_%H%M%S)
SAFE_TARGET=$(echo "$TARGET" | sed 's|://|_|; s|[/:]|_|g')

# Every phase writes into one assessment directory.
export PENTESTAGENT_ASSESSMENT_ID="${STAMP}_${SAFE_TARGET}"

LOGDIR="$HOME/pentestagent/assessment-$STAMP"
mkdir -p "$LOGDIR"

echo "================================================================"
echo "  FULL ASSESSMENT v2   target=$TARGET"
echo "  assessment id: $PENTESTAGENT_ASSESSMENT_ID"
echo "  started $(date '+%F %T')"
echo "  phase logs -> $LOGDIR"
echo "  reports    -> loot/assessments/$PENTESTAGENT_ASSESSMENT_ID/"
echo "================================================================"

run_phase() {
  local n="$1" playbook="$2" iters="$3"
  echo
  echo "----------------------------------------------------------------"
  echo "  PHASE $n  $playbook  (max_iterations=$iters)"
  echo "  start $(date '+%T')"
  echo "----------------------------------------------------------------"
  PENTESTAGENT_AGENT_MAX_ITERATIONS="$iters" \
  PENTESTAGENT_PLAYBOOK="$playbook" \
    pentestagent run -t "$TARGET" --playbook "$playbook" --report \
    > "$LOGDIR/${n}-${playbook}.log" 2>&1
  echo "  end   $(date '+%T')  exit=$?  ->  ${n}-${playbook}.log"
}

# Surface discovery (crew mode, parallel workers)
run_phase 01 web_discovery          40

# Stack-specific. Swap per whatever phase 01 identified.
run_phase 02 blazor_wasm            60

# OWASP categories, one focused pass each
run_phase 03 a01_a07_access_auth    60
run_phase 04 a02_misconfiguration   60
run_phase 05 a04_cryptographic      60
run_phase 06 a05_injection          60
run_phase 07 a08_integrity          50
run_phase 08 a09_logging_alerting   25
run_phase 09 a10_exceptional        25

# Gather everything before chaining, so chaining sees a complete input
run_phase 10 consolidate_findings   25

# Cross-category chaining
run_phase 11 chain_findings         60

# Gather again before review, so review sees what chaining produced
run_phase 12 consolidate_findings   25

# Adversarial verification of the draft
run_phase 13 adversarial_review     60

# Last word: completeness + mechanical evidence checks, emits the deliverable
run_phase 14 final_integrity_gate   30

echo
echo "================================================================"
echo "  ASSESSMENT COMPLETE  $(date '+%F %T')"
echo "================================================================"
echo "Phase logs: $LOGDIR"
echo
echo "Draft playbook reports:"
ls -1 "loot/assessments/$PENTESTAGENT_ASSESSMENT_ID/draft_playbook_reports/" 2>/dev/null | sed 's/^/  /'
echo
echo "Final deliverable:"
ls -1 "loot/assessments/$PENTESTAGENT_ASSESSMENT_ID/final_deliverable/" 2>/dev/null | sed 's/^/  /'
