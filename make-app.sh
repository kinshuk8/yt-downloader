#!/bin/zsh
# Builds "YT Downloader.app" in ~/Applications so you can launch it from Spotlight, Launchpad or the Dock.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$HOME/Applications/YT Downloader.app"
mkdir -p "$HOME/Applications"
rm -rf "$APP"
osacompile -o "$APP" -e "do shell script quoted form of \"$DIR/launch.sh\" & \" > /dev/null 2>&1\""
echo "Built $APP"
echo "Open it from Spotlight (Cmd+Space, type \"YT Downloader\") or drag it to your Dock."
