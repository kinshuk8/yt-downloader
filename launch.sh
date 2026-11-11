#!/bin/zsh
# Starts YT Downloader (setting it up on first run) and opens it in the browser.
# Browser version, run from source; start.command calls it.
set -e
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
URL="http://127.0.0.1:5055"

notify() { osascript -e "display notification \"$1\" with title \"YT Downloader\"" 2>/dev/null || true; }

# Already running? Just open it.
if curl -s -o /dev/null "$URL"; then
  open "$URL"
  exit 0
fi

if ! command -v ffmpeg >/dev/null; then
  if command -v brew >/dev/null; then
    notify "Installing ffmpeg (first run only, takes a minute)…"
    brew install ffmpeg
  else
    osascript -e 'display alert "YT Downloader needs ffmpeg" message "Install Homebrew from https://brew.sh, then open the app again."'
    exit 1
  fi
fi

if [ ! -x .venv/bin/python ]; then
  notify "Setting up (first run only)…"
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
else
  # YouTube changes often; a fresh yt-dlp keeps downloads working.
  .venv/bin/pip install -q -U yt-dlp >/dev/null 2>&1 || true
fi

nohup .venv/bin/python app.py > server.log 2>&1 &

for _ in {1..30}; do
  curl -s -o /dev/null "$URL" && break
  sleep 0.3
done
open "$URL"
