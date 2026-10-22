#!/bin/bash
# Contest autopilot (macOS): keep the Mac awake, log in, preflight, wait for go-live with golive.py, then hand the
# live contest to an autonomous Claude Code session (docs/strategy/autopilot-prompt.md) that solves every level.
#
#   bash arena/autopilot.sh                     # contest: start any time before 15:45 Romania, it waits for 16:00
#   bash arena/autopilot.sh --schedule 15:30    # one-shot: macOS opens Terminal and runs the line above at 15:30 today
#   bash arena/autopilot.sh --unschedule        # remove that job
#   bash arena/autopilot.sh --train             # rehearsal: fresh Birds Challenge run, same hand-off
#   ... --headless                              # `claude -p` instead of the interactive window (log: <run>/autopilot.log)
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO" || exit 1
MODE=contest; HEADLESS=0; RUN=contest; END="20:00 Romania time (17:00 UTC)"
LABEL=com.theposers.ccc-autopilot
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

while [ $# -gt 0 ]; do
  case "$1" in
    --train) MODE=train ;;
    --headless) HEADLESS=1 ;;
    --unschedule)
      launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null; rm -f "$PLIST"; echo "autopilot schedule removed"; exit 0 ;;
    --schedule)
      H="${2%%:*}"; M="${2##*:}"
      CMD="$REPO/arena/.autopilot.command"
      printf '#!/bin/bash\ncd "%s" && bash arena/autopilot.sh\n' "$REPO" > "$CMD"; chmod +x "$CMD"
      cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/usr/bin/open</string><string>-a</string><string>Terminal</string><string>$CMD</string></array>
  <key>StartCalendarInterval</key><dict><key>Month</key><integer>$(date +%-m)</integer><key>Day</key><integer>$(date +%-d)</integer><key>Hour</key><integer>$((10#$H))</integer><key>Minute</key><integer>$((10#$M))</integer></dict>
</dict></plist>
EOF
      launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
      launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "autopilot scheduled for $(date +%Y-%m-%d) $2 (Terminal opens by itself; keep the lid open)"
      exit 0 ;;
    *) echo "unknown option $1"; exit 2 ;;
  esac
  shift
done

say_() { command -v say >/dev/null && say "$1" & }
caffeinate -dimsu -w $$ &          # no sleep while this script (and the Claude session it becomes) runs

echo "== autopilot $MODE $(date '+%H:%M:%S')"
git pull --rebase -q || echo "WARN: git pull failed (continuing)"
python3 arena/ccc.py login --http || echo "WARN: HTTP login failed; golive retries and falls back to the browser"

if [ "$MODE" = train ]; then
  RUN="birds-auto-$(date +%H%M)"; END="240 minutes after now ($(date -v+4H '+%H:%M'))"
  python3 arena/ccc.py train ccc-2025.11-ai-birds --mode challenge --name "$RUN" || exit 1
  python3 arena/ccc.py info | grep -q "level1: PASSED" && \
    echo "WARN: this account's Birds Challenge is already finished; go will skip every submit (nothing graded)"
  LIVE_OUT="arena/runs/$RUN/live-out.txt"
  python3 arena/ccc.py fetch 1 2>&1 | tee "$LIVE_OUT"; STATUS=${PIPESTATUS[0]}
else
  mkdir -p "arena/runs/$RUN"; LIVE_OUT="arena/runs/$RUN/live-out.txt"
  python3 arena/golive.py --browser 2>&1 | tee "$LIVE_OUT"; STATUS=${PIPESTATUS[0]}   # blocks until live + level 1
fi
say_ "Contest is live. Claude is solving."

PROMPT="$(sed -e "s#{{MODE}}#$MODE#g" -e "s#{{RUN}}#$RUN#g" -e "s#{{LIVE_OUT}}#$LIVE_OUT#g" \
              -e "s#{{GOLIVE_STATUS}}#$STATUS#g" -e "s#{{END}}#$END#g" docs/strategy/autopilot-prompt.md)"
echo "== handing over to Claude ($(date '+%H:%M:%S')), run $RUN"
if [ "$HEADLESS" = 1 ]; then
  claude -p --dangerously-skip-permissions --model opus "$PROMPT" > "arena/runs/$RUN/autopilot.log" 2>&1
  echo "== Claude finished ($(date '+%H:%M:%S')); log arena/runs/$RUN/autopilot.log"
else
  claude --dangerously-skip-permissions --model opus "$PROMPT"
fi
