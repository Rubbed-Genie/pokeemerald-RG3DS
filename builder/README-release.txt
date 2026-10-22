Pokemon Emerald RG3DS
=====================

Pokemon Emerald 3Ds Dual Screen (ZallaxDev), tuned for the Anbernic RG DS
running ROCKNIX: a 4:3 top screen, both screens, 3D overworld. It runs in
ROCKNIX's Azahar emulator. This build targets the RG DS only.

This download does NOT contain the game. You need your own dump of your own
Pokemon Emerald (USA, Europe) cartridge. The builder reads that ROM on this
computer and generates the game's data pack from it. The ROM is not uploaded,
copied or modified. An Internet connection is only used to download the
optional follower sprites.

What you need
-------------
- An Anbernic RG DS with ROCKNIX.
- A clean ROM of Pokemon Emerald (USA, Europe),
  SHA-1 f3ae088181bf583e55daf962a92bb46f4f1d07b7.
- A way to copy files into the RG DS's roms folder: its network share
  \\RK3566.local\games-roms (Wi-Fi on, same network; if that name is not
  found, \\<its IP>\games-roms with the IP from ROCKNIX's network settings),
  a second games card, or however you usually add games.
- For sound: your own 3DS sound firmware dump, dspfirm.cdc (made on a real
  3DS, for example with the DSP1 homebrew). Without it the game is silent.

Install
-------
1. Extract this whole ZIP to a folder.
2. Run Emerald3DS-Builder.exe.
3. Choose your ROM. The builder checks that it is the supported one.
4. Choose where to install: press "Network" for \\RK3566.local\games-roms, pick a
   games card's roms folder, or pick any empty folder and copy what it writes
   into the RG DS's roms folder yourself.
5. Press Install. It writes, under roms/:
       3ds/Pokemon Emerald RG3DS.3dsx
       3ds/azahar/sdmc/3ds/emerald3ds/emerald3ds.pak
       ports/RG3DS Setup.sh
       ports/rg3ds/054-azahar-3dsx-stretch
6. For sound, put your dspfirm.cdc in roms/3ds/azahar/sdmc/3ds/.
7. On the RG DS: Start > Game settings > Update gamelists (or reboot).
8. Run Ports > RG3DS Setup once. It installs the small Azahar launcher hook
   that puts the game's two windows on the two screens (without it they sit
   side by side on the top screen) and stretches the 4:3 top screen to fit.
   It only acts on .3dsx homebrew; your retail 3DS games are left as they were.
9. Play "Pokemon Emerald RG3DS" from the 3DS system.

Saves are kept in roms/3ds/azahar/sdmc/3ds/emerald3ds/emerald3ds.sav.
Reinstalling or updating never touches it; the builder backs it up first.

Tip: a 2x resolution for this game in its per-game options on
EmulationStation looks sharper, at a small cost in speed.

Command line
------------
    emerald3ds-builder-cli.exe build   --rom "Pokemon Emerald.gba" --output out
    emerald3ds-builder-cli.exe install --rom "Pokemon Emerald.gba" --roms \\RK3566.local\games-roms
    emerald3ds-builder-cli.exe verify  --pak \\RK3566.local\games-roms\3ds\azahar\sdmc\3ds\emerald3ds\emerald3ds.pak

Updating
--------
Each release comes with its own builder. Run the new builder again with the
same ROM: a data pack only works with the release that generated it, and the
game tells you when they do not match.

Legal
-----
Pokemon Emerald RG3DS is an unofficial fan project, not affiliated with or
endorsed by Nintendo, Game Freak, Creatures or The Pokemon Company. Pokemon
and Pokemon Emerald are trademarks of their respective owners. See LICENSES/.
