#!/bin/bash
# Contest autopilot (macOS): keep the Mac awake, log in, preflight, wait for go-live with golive.py, then hand the
# live contest to an autonomous Claude Code session (docs/strategy/autopilot-prompt.md) that solves every level.
#
#   bash arena/autopilot.sh                     # contest: start any time before 15:45 Romania, it waits for 16:00
#   bash arena/autopilot.sh --schedule 15:30    # one-shot: macOS opens Terminal and runs the line above at 15:30 today
#   bash arena/autopilot.sh --unschedule        # remove that job
#   bash arena/autopilot.sh --train             # rehearsal: fresh Birds Challenge run, same hand-off
#   bash arena/autopilot.sh --shadow            # teammate laptop: solve the driver's open level in parallel, never
#                                               # submit, hand solvers over via git (arena/duo.py; any OS: python arena/duo.py shadow)
#   ... --run NAME                              # run name (default: contest; --train: birds-auto-HHMM); driver and shadow must match
#   ... --headless                              # `claude -p` instead of the interactive window (log: <run>/autopilot.log)
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
ARGS=; SCHED=; AGENT=auto; MODEL=; MODE=contest; HEADLESS=0; RUN=; END="20:00 Romania time (17:00 UTC)"
LABEL=com.theposers.ccc-autopilot
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

while [ $# -gt 0 ]; do
  case "$1" in
    --train) MODE=train; ARGS="$ARGS $1" ;;
    --shadow) MODE=shadow; ARGS="$ARGS $1" ;;
    --run) RUN="$2"; ARGS="$ARGS $1 $2"; shift ;;
    --headless) HEADLESS=1; ARGS="$ARGS $1" ;;
    --agent) AGENT="$2"; ARGS="$ARGS $1 $2"; shift ;;   # claude | cursor (Cursor CLI `agent`); default: whichever is installed
    --model) MODEL="$2"; ARGS="$ARGS $1 $2"; shift ;;
    --unschedule)
      launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null; rm -f "$PLIST"; echo "autopilot schedule removed"; exit 0 ;;
    --schedule) SCHED="$2"; shift ;;   # HH:MM (today) or YYYY-MM-DD HH:MM; keeps the other flags
    *) echo "unknown option $1"; exit 2 ;;
  esac
  shift
done
if [ -n "$SCHED" ]; then
  WHEN="$SCHED"; DAY="$(date +%Y-%m-%d)"
  case "$WHEN" in *" "*) DAY="${WHEN%% *}"; WHEN="${WHEN##* }" ;; esac
  H="${WHEN%%:*}"; M="${WHEN##*:}"; MO="$(date -j -f %Y-%m-%d "$DAY" +%-m)"; DD="$(date -j -f %Y-%m-%d "$DAY" +%-d)"
  CMD="$REPO/arena/.autopilot.command"
  printf '#!/bin/bash\ncd "%s" && bash arena/autopilot.sh%s\n' "$REPO" "$ARGS" > "$CMD"; chmod +x "$CMD"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/usr/bin/open</string><string>-a</string><string>Terminal</string><string>$CMD</string></array>
  <key>StartCalendarInterval</key><dict><key>Month</key><integer>$MO</integer><key>Day</key><integer>$DD</integer><key>Hour</key><integer>$((10#$H))</integer><key>Minute</key><integer>$((10#$M))</integer></dict>
</dict></plist>
EOF
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
  launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "autopilot$ARGS scheduled for $DAY $WHEN (Terminal opens by itself; keep the lid open)"
  exit 0
fi

SIG="$(cat .claude/signature.local 2>/dev/null)"
[ -n "$SIG" ] || { echo "ERROR: write your name into .claude/signature.local (iustin or gurita)"; exit 2; }
if [ "$MODE" = shadow ]; then
  exec python3 arena/duo.py shadow --run "${RUN:-contest}" --agent "$AGENT" ${MODEL:+--model "$MODEL"} \
    $([ "$HEADLESS" = 1 ] && echo --headless)
fi

say_() { command -v say >/dev/null && say "$1" & }
caffeinate -dimsu -w $$ &          # no sleep while this script (and the Claude session it becomes) runs

echo "== autopilot $MODE $(date '+%H:%M:%S')"
git pull --rebase -q || echo "WARN: git pull failed (continuing)"
python3 arena/ccc.py login --http || echo "WARN: HTTP login failed; golive retries and falls back to the browser"

if [ "$MODE" = train ]; then
  RUN="${RUN:-birds-auto-$(date +%H%M)}"; END="240 minutes after now ($(date -v+4H '+%H:%M'))"
  python3 arena/ccc.py train ccc-2025.11-ai-birds --mode challenge --name "$RUN" || exit 1
  python3 arena/ccc.py info | grep -q "level1: PASSED" && \
    echo "WARN: this account's Birds Challenge is already finished; go will skip every submit (nothing graded)"
  LIVE_OUT="arena/runs/$RUN/live-out.txt"
  python3 arena/ccc.py fetch 1 2>&1 | tee "$LIVE_OUT"; STATUS=${PIPESTATUS[0]}
else
  RUN="${RUN:-contest}"; mkdir -p "arena/runs/$RUN"; LIVE_OUT="arena/runs/$RUN/live-out.txt"
  python3 arena/golive.py --browser 2>&1 | tee "$LIVE_OUT"; STATUS=${PIPESTATUS[0]}   # blocks until live + level 1
fi
say_ "Contest is live. The agent is solving."
python3 arena/duo.py share "$RUN" || echo "WARN: share failed (the shadow laptop waits for level 1 via git)"

PROMPT="$(sed -e "s#{{MODE}}#$MODE#g" -e "s#{{RUN}}#$RUN#g" -e "s#{{LIVE_OUT}}#$LIVE_OUT#g" \
              -e "s#{{GOLIVE_STATUS}}#$STATUS#g" -e "s#{{END}}#$END#g" -e "s#{{SIG}}#$SIG#g" docs/strategy/autopilot-prompt.md)"
if [ "$AGENT" = auto ]; then command -v claude >/dev/null && AGENT=claude || AGENT=cursor; fi
if [ "$AGENT" = claude ]; then
  RUNNER=(claude --dangerously-skip-permissions --model "${MODEL:-opus}"); P=(-p)
else                               # Cursor CLI (https://cursor.com/cli): --force runs commands without asking
  EXE="$(command -v agent || command -v cursor-agent)"
  [ -n "$EXE" ] || { echo "ERROR: neither claude nor the Cursor CLI (agent) is installed: https://cursor.com/cli"; exit 2; }
  RUNNER=("$EXE" --force ${MODEL:+--model "$MODEL"}); P=(-p --output-format text)
fi
echo "== handing over to $AGENT ($(date '+%H:%M:%S')), run $RUN"
if [ "$HEADLESS" = 1 ]; then
  "${RUNNER[0]}" "${P[@]}" "${RUNNER[@]:1}" "$PROMPT" > "arena/runs/$RUN/autopilot.log" 2>&1
  echo "== $AGENT finished ($(date '+%H:%M:%S')); log arena/runs/$RUN/autopilot.log"
else
  "${RUNNER[@]}" "$PROMPT"
fi
