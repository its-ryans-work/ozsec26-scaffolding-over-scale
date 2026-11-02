#!/usr/bin/env bash
# Build a pristine, replayable pre-chain_findings state from run33.
#
# chain_findings is a separate process that reads (a) the accumulated notes file,
# (b) the per-assessment draft reports written by phases 01-10, and (c) artifacts
# left on disk by earlier phases - notably the decompiled source, which is the
# thing the fix under test has to send it back to.
#
# run33 conveniently snapshots the notes at the end of every phase, so
# consolidate_findings_notes.json IS the exact pre-chain state. Everything
# chain_findings and later produced is excluded so each repetition starts identical.
set -eu

SRC=~/prior-runs-archive/run33-final/20260805_152549_http_127.0.0.1_5000
SNAP=~/replay/snapshot
ID=20260805_152549_http_127.0.0.1_5000

rm -rf "$SNAP"
mkdir -p "$SNAP/draft_playbook_reports" "$SNAP/scratchpads"

# Notes as they stood when consolidate_findings finished.
CN=$(ls "$SRC/draft_playbook_reports"/*consolidate_findings_notes.json | head -1)
[ -n "$CN" ] || { echo "no consolidate notes snapshot found" >&2; exit 1; }
cp "$CN" "$SNAP/notes.json"

# Draft reports from phases 01-10 only.
for f in "$SRC/draft_playbook_reports"/*; do
    b=$(basename "$f")
    case "$b" in
        *chain_findings*|*adversarial_review*|*final_integrity_gate*) continue ;;
    esac
    cp "$f" "$SNAP/draft_playbook_reports/"
done

# Scratchpads from phases 01-10 only.
for d in "$SRC/scratchpads"/*; do
    b=$(basename "$d")
    case "$b" in
        chain_findings|adversarial_review|final_integrity_gate) continue ;;
    esac
    cp -a "$d" "$SNAP/scratchpads/"
done

echo "snapshot built at $SNAP"
echo "  notes keys      : $(python3 -c "import json;print(len(json.load(open('$SNAP/notes.json'))))")"
echo "  draft reports   : $(ls -1 "$SNAP/draft_playbook_reports" | wc -l)"
echo "  scratchpads     : $(ls -1 "$SNAP/scratchpads" | wc -l)"
echo "  decompiled src  : $(ls /tmp/a04_blazor/decompiled/ACorpBlazor/*.cs 2>/dev/null | wc -l) file(s)"
echo "  key in that src : $(grep -ohE 'Vu1nB1az0r[^\"]*' /tmp/a04_blazor/decompiled/ACorpBlazor/*.cs 2>/dev/null | head -1)"
