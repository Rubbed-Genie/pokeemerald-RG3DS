# Releasing RG3DS

An RG3DS release is a GitHub release on `Rubbed-Genie/pokeemerald-RG3DS`, tagged `rg3ds-vX.Y` after
`RG3DS_VERSION` in `3ds_port/Makefile`. Nothing in it contains the ROM or anything made from it: the player's builder
makes the data pack from their own ROM.

| Asset | What it is |
|---|---|
| `RG3DS-vX.Y-Windows.zip` | the builder (exe), `payload/` (engine-only 3DSX, recipe, voxel generators, `rgds/` setup + hook), `README.txt`, `LICENSES/` |
| `SHA256SUMS.txt` | SHA-256 of the assets |

The 3DS console's assets (CIA forwarder, web payload, smdh) are upstream's and are not published here.

## Steps

The payload needs the ROM, devkitARM and the original game's ELF, so it is made on the maintainer's machine. The
Windows builder needs neither, so GitHub freezes it.

1. **Version.** Bump `RG3DS_VERSION` in `3ds_port/Makefile`, commit, push `rg3ds-dev`.
2. **The exe.** Actions > *RG3DS builder (Windows exe)* > Run workflow on `rg3ds-dev` (a pushed `rg3ds-v*` tag runs
   it too). Download its artifact `Emerald3DS-Builder-windows` and extract it, e.g. to `build/exe/`:
   `gh run download -R Rubbed-Genie/pokeemerald-RG3DS -n Emerald3DS-Builder-windows -D build/exe`
3. **The reference ELF** (once per pinned upstream, `upstream.lock`): a clean clone of pret/pokeemerald at that commit
   built with [agbcc](https://github.com/pret/agbcc). Its `pokeemerald.gba` must have the ROM's SHA-1.
4. **The release**, in a bootstrapped tree (`tools/bootstrap.py --dir build/rg3ds-dev`), inside the devkitARM
   container (Python 3.11 there):

   ```sh
   make -C 3ds_port clean
   python3 tools/build_release.py --version X.Y --rom baserom.gba --gba-elf ../gba-ref/pokeemerald.elf \
       --nm $DEVKITARM/bin/arm-none-eabi-nm --make "make -j8 PYTHON=python3" \
       --skip-cia --exe-dir ../exe
   ```

   It always builds `TOP_WIDTH=320`, copies `rocknix/RG3DS Setup.sh` and `rocknix/054-azahar-3dsx-stretch` into
   `payload/rgds/`, audits every ZIP against the ROM (`release_audit.py --strict`) and writes `SHA256SUMS.txt`.
   The recipe step takes about 15 minutes. Afterwards the tree's dependency files point at the container's paths:
   `rm -rf 3ds_port/build` before a normal build there.
5. **Test like a player**, ideally on a clean Windows PC: extract the ZIP, run the builder with the ROM into an
   empty folder, copy `roms/` to the RG DS, Update gamelists, Ports > RG3DS Setup, play.
6. **Publish**: `gh release create rg3ds-vX.Y --title "RG3DS X.Y" --notes-file notes.md
   dist/RG3DS-vX.Y-Windows.zip dist/SHA256SUMS.txt`.

## Known traps

- **Python version.** The relief generator's output differs on Python 3.14 (Lilycove's entry drops out), so a
  from-source build on 3.14 fails the release check. The exe bundles 3.12; build releases with 3.11-3.13.
- **Generator order.** `gen_voxel_relief.py` reads `romfs/voxel/buildings.bin` (`voxel_terraces.modelled`), so the
  builder runs it after the buildings (`AFTER` in `builder/emerald3ds_builder/voxel.py`) and `full.mk` orders them.
  A release built in a tree without a fresh `buildings.bin` would ship a recipe no player can match.
- **Window placement** is ROCKNIX's, not the game's: on stock ROCKNIX a `.3dsx` runs at full speed but its two windows
  share the top screen until the hook is in. Judge it only from a launch made in EmulationStation; an SSH launch leaves
  the top window behind EmulationStation even for retail games.
