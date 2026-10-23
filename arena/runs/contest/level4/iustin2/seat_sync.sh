#!/bin/bash
# When the driver uploads a new seat model, publish it to level4/mac2/models (CURRENT = new x2 + n2b) from a
# throwaway git worktree, so the second Mac self-plays with the newest seat. Never touches the driver's tree.
REPO=/Users/iustinepanu/ccc/ccc-ai-engineer-data-ai; ENV=$REPO/arena/runs/contest/level4/env4
TR=$HOME/.claude/projects/-Users-iustinepanu-ccc-ccc-ai-engineer-data-ai/b14c4474-1bc1-48f4-a6e4-ffd3bb6867da.jsonl
LOG=$REPO/arena/runs/contest/level4/iustin2/tlogs/seat_sync.log; WT=/private/tmp/claude-501/seat_sync_wt
last=n5.onnx
while [ "$(date +%H%M)" -lt 1935 ]; do
  cur=$(grep -o 'upload4.py \.\./level4/env4/[A-Za-z0-9_]*\.onnx' "$TR" | tail -1 | sed 's#.*/##')
  if [ -n "$cur" ] && [ "$cur" != "$last" ] && [ -f "$ENV/$cur" ]; then
    rm -rf "$WT"; cd "$REPO" && git fetch -q origin && git worktree add -q --detach "$WT" origin/main \
      && cp "$ENV/$cur" "$WT/arena/runs/contest/level4/mac2/models/" \
      && echo "$cur $cur n2b.onnx" > "$WT/arena/runs/contest/level4/mac2/models/CURRENT" \
      && (cd "$WT" && git add -f arena/runs/contest/level4/mac2/models && git commit -qm "[iustin] mac2: self-play with new seat $cur" -m "Signed-off-by: iustin" && git push -q origin HEAD:main) \
      && echo "$(date +%H:%M:%S) mac2 now uses $cur" >> "$LOG" && last=$cur
    cd "$REPO" && git worktree remove --force "$WT" 2>/dev/null
  fi
  sleep 60
done
