#!/bin/zsh
# Double-click in Finder to launch (opens a Terminal window). The Mac app (build-dmg.sh) needs no Terminal.
exec "$(dirname "$0")/launch.sh"
