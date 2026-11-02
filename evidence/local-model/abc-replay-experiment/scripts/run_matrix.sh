#!/usr/bin/env bash
# Overnight replay matrix: A / B / C, interleaved by repetition.
#
# Interleaved so stopping at any hour leaves balanced coverage rather than five
# reps of A and none of C. Cells with a GRADE.txt are skipped, so this is
# restartable and the already-collected A-rep1 / B-rep1 are not repeated.
#
# Cell cost is highly variable (10-60 min) because a run that fails the decrypt
# falls back to hashcat against PBKDF2 hashes, which is slow and cannot succeed.
# Wall clock is therefore a leading indicator of failure, not just overhead.
set -u
REPS="${1:-5}"
ITERS=80

for rep in $(seq 1 "$REPS"); do
    for v in A B C; do
        OUT=~/replay/results/${v}-rep${rep}
        if [ -f "$OUT/GRADE.txt" ]; then
            echo "[$(date '+%F %T')] skip ${v}-rep${rep} (already graded)"
            continue
        fi
        echo "[$(date '+%F %T')] === ${v}-rep${rep} ==="
        if ! ~/apply_variant.sh "$v"; then
            echo "[$(date '+%F %T')] variant setup FAILED for $v - skipping cell"
            continue
        fi
        ~/replay_chain.sh "$v" "$rep" "$ITERS" || \
            echo "[$(date '+%F %T')] cell ${v}-rep${rep} errored; continuing"
    done
    echo "[$(date '+%F %T')] --- round $rep complete ---"
    for f in ~/replay/results/[ABC]-rep*/GRADE.txt; do
        [ -f "$f" ] || continue
        printf "    %-9s decrypted=%-4s key8=%-3s key6=%-3s reread=%-3s hashcat=%-4s %ss\n" \
          "$(basename "$(dirname "$f")")" \
          "$(awk -F': *' '/^DECRYPTED/{print $2}' "$f"|tr -d ' ')" \
          "$(awk -F': *' '/^key_8at/{print $2}' "$f"|tr -d ' ')" \
          "$(awk -F': *' '/^key_6at/{print $2}' "$f"|tr -d ' ')" \
          "$(awk -F': *' '/^reread_literal/{print $2}' "$f"|tr -d ' ')" \
          "$(awk -F': *' '/^hashcat_effort/{print $2}' "$f"|tr -d ' ')" \
          "$(awk -F': *' '/^elapsed_s/{print $2}' "$f"|tr -d ' ')"
    done
done

echo
echo "[$(date '+%F %T')] MATRIX COMPLETE"
for f in ~/replay/results/[ABC]-rep*/GRADE.txt; do
    echo "--- $(basename "$(dirname "$f")") ---"; cat "$f"; echo
done
