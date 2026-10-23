#!/bin/bash
# Import the second Mac's self-play batches into the driver's training data, read-only on git:
# git fetch + git show (no pull, no checkout, the driver's working tree and index are never touched).
# Each new file lands as env4/data/g3h.part2NN.npz, inside the driver's 'data/g3h.part*.npz' training glob.
REPO=/Users/iustinepanu/ccc/ccc-ai-engineer-data-ai; D=$REPO/arena/runs/contest/level4/env4/data
SEEN=$REPO/arena/runs/contest/level4/iustin2/tlogs/mac2_seen.txt; touch "$SEEN"
LOG=$REPO/arena/runs/contest/level4/iustin2/tlogs/import_mac2.log
cd "$REPO" || exit 1
while [ "$(date +%H%M)" -lt 1940 ]; do
  git fetch -q origin main 2>>"$LOG"
  for p in $(git ls-tree -r --name-only origin/main arena/runs/contest/level4/mac2/data/ 2>/dev/null | grep '\.npz$'); do
    grep -qxF "$p" "$SEEN" && continue
    n=$(( 200 + $(wc -l < "$SEEN") ))
    if git show "origin/main:$p" > "$D/.mac2.tmp" 2>>"$LOG"; then
      mv "$D/.mac2.tmp" "$D/g3h.part$n.npz" && echo "$p" >> "$SEEN" && echo "$(date +%H:%M:%S) $p -> data/g3h.part$n.npz" >> "$LOG"
    fi
  done
  sleep 60
done
