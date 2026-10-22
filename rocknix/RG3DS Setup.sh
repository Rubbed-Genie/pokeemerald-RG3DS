#!/bin/bash
# Pokemon Emerald RG3DS - one-time setup on the RG DS (ROCKNIX), from Ports.
#
# Installs the Azahar launcher hook that RG3DS needs (rg3ds/054-azahar-3dsx-stretch,
# beside this script) into /storage/.config/autostart, where ROCKNIX runs it at
# every boot, and applies it now. Without it Azahar shows the game's two windows
# side by side on the top screen: its bottom-screen window is titled plain
# "Azahar", which the stock sway rule for second windows does not match.
# Running it again is harmless. What it did is in rg3ds/setup.log.
HERE="$(cd "$(dirname "$0")" && pwd)"
HOOK=054-azahar-3dsx-stretch
LOG="$HERE/rg3ds/setup.log"
{
  echo "RG3DS Setup $(date '+%F %T')"
  if [ ! -f "$HERE/rg3ds/$HOOK" ]; then
    echo "ERROR: $HERE/rg3ds/$HOOK is missing - copy the whole roms folder from the builder again"
    exit 1
  fi
  mkdir -p /storage/.config/autostart
  cp "$HERE/rg3ds/$HOOK" "/storage/.config/autostart/$HOOK"
  chmod +x "/storage/.config/autostart/$HOOK"
  echo "hook installed in /storage/.config/autostart/$HOOK"
  sh "/storage/.config/autostart/$HOOK"
  tail -n 1 /storage/.config/logs/054-azahar-3dsx-stretch.log 2>/dev/null
  if [ -f "$HERE/../3ds/azahar/sdmc/3ds/dspfirm.cdc" ]; then
    echo "sound firmware found"
  else
    echo "NOTE: no roms/3ds/azahar/sdmc/3ds/dspfirm.cdc - the game has no sound without your own dump"
  fi
} > "$LOG" 2>&1
exit 0
