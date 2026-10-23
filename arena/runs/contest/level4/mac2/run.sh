#!/bin/bash
# Second Mac: continuous L4 self-play for the driver. Never uploads, never talks to the contest platform.
# usage (from the repo root): bash arena/runs/contest/level4/mac2/run.sh      [GAMES=400 SIMS=150 by default]
# Each batch is pushed to arena/runs/contest/level4/mac2/data/; the driver Mac imports it into its training data.
set -u
ROOT="$(cd "$(dirname "$0")/../../../../.." && pwd)"; cd "$ROOT" || exit 1
L4=arena/runs/contest/level4; E=$L4/env4; M=$L4/mac2
git config user.email >/dev/null || git config user.email "mac2@theposers.local"
git config user.name >/dev/null || git config user.name "mac2"
if [ ! -x "$E/.venv/bin/python" ]; then
  echo "== installing the engine (once)"
  (cd "$E" && python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt) || { echo "ERROR: install failed (needs Python 3.11+ on Apple Silicon)"; exit 1; }
fi
NP=$(( $(sysctl -n hw.ncpu) - 1 )); RUNID=$(date +%H%M); i=0
echo "== self-play with $NP processes, ${GAMES:-400} games/batch at ${SIMS:-150} sims"
while true; do
  git pull -q --rebase || echo "WARN: pull failed"
  MODELS=$(cat "$M/models/CURRENT")
  for f in $MODELS; do cp "$M/models/$f" "$E/"; done
  i=$((i + 1)); B="m2_${RUNID}_$i"; t0=$(date +%s)
  if ! (cd "$E" && NPROC=$NP SIMS=${SIMS:-150} .venv/bin/python ../mac2/selfplay_n.py "data/$B" "${GAMES:-400}" $MODELS > "data/$B.log" 2>&1); then
    echo "WARN: batch $B failed (see $E/data/$B.log)"; sleep 10; continue
  fi
  mkdir -p "$M/data" && cp "$E/data/$B".part*.npz "$M/data/"
  git add -f "$M/data/$B".part*.npz && git commit -qm "[mac2] L4 self-play $B ($MODELS)" && { git pull -q --rebase; git push -q; } \
    && echo "$(date +%H:%M:%S) batch $B pushed ($(( $(date +%s) - t0 )) s)" || echo "WARN: push failed for $B (retried with the next batch)"
done
