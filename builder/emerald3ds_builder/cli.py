"""Command line: the same build the window runs, for scripts, CI and Linux/macOS.

    emerald3ds-builder build   --rom ROM --output DIR       (a roms/ folder to copy over)
    emerald3ds-builder install --rom ROM --roms \\\\RK3566.local\\games-roms
    emerald3ds-builder verify  --pak FILE
    emerald3ds-builder detect
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import __version__, followers, pak
from .build import Payload, build_pack, default_payload, select_payload
from .errors import BuilderError
from .install import find_sd_cards, install, placed_files, roms_folder
from .recipe import Recipe
from .rom import load_rom


def _progress(fraction: float, message: str) -> None:
    sys.stdout.write("\r[%3d%%] %-72s" % (int(fraction * 100), message))
    sys.stdout.flush()
    if fraction >= 1.0:
        sys.stdout.write("\n")


def _warn(message: str) -> None:
    """A non-fatal warning: shown, but the command still succeeds."""
    print("Warning: %s" % message, file=sys.stderr)


def cmd_build(args) -> int:
    payload = Payload(args.payload)
    out_root = Path(args.output) / "roms"
    # Pick the ROM's variant before the output folder is touched. A language
    # subfolder must bring its own executables (the English ones would not run
    # its pack), so a release missing them leaves earlier files alone. The
    # default variant may stay recipe-only, as before: its missing executables
    # are skipped below.
    rom = load_rom(Path(args.rom))
    variant = select_payload(payload, rom.sha1)
    need_executables = variant.language is not None
    if need_executables:
        variant.check(need_executables=True)
    out_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="emerald3ds-") as tmp:
        pak_path = Path(tmp) / "emerald3ds.pak"
        info = build_pack(Path(args.rom), payload, pak_path, _progress, args.keep_workdir,
                          rom=rom, need_executables=need_executables)
        print("Times (%s): %s" % (info["rom"], ", ".join("%s %.1f s" % t for t in info["timings"])))
        placed = {rel: src for rel, src in placed_files(info["payload"]).items() if src.exists()}
        install(out_root, {"emerald3ds.pak": pak_path}, placed=placed)
    print("Data pack: %d files, %.1f MiB, release %s" % (info["entries"], info["bytes"] / 1048576,
                                                         info["release"]))
    if info.get("followers"):
        f = info["followers"]
        print("Followers: %d sprites, %d texts (%d downloaded)%s" % (f["sprites"], f.get("texts", 0), f["downloaded"],
              ", %d not available" % len(f["missing"]) if f["missing"] else ""))
    print("Copy everything in %s into your RG DS's roms folder (the games-roms network share)."
          % out_root)
    return 0


def cmd_install(args) -> int:
    payload = Payload(args.payload)
    payload.check()
    roms = roms_folder(Path(args.roms))
    with tempfile.TemporaryDirectory(prefix="emerald3ds-") as tmp:
        pak_path = Path(tmp) / "emerald3ds.pak"
        info = build_pack(Path(args.rom), payload, pak_path, _progress, need_executables=True)
        install(roms, {"emerald3ds.pak": pak_path}, lambda f: _progress(f, "Copying to the RG DS"),
                warn=_warn, placed=placed_files(info["payload"]))
    print("Installed to %s. On the RG DS: Start > Game settings > Update gamelists (or reboot), "
          "then run Ports > RG3DS Setup once." % roms)
    return 0


def cmd_verify(args) -> int:
    payload = Payload(args.payload)
    with pak.PakReader(Path(args.pak)) as reader:
        # The pack names the ROM it was built from: check it against that variant.
        recipe = Recipe.load(payload.for_rom(reader.rom_sha1.hex()).recipe)
        count = reader.verify()
        expected = {pak.path_id(e["path"]): e for e in recipe.entries + recipe.generated}
        # The optional follower sprites (followers.py) are not the recipe's.
        optional = {pak.path_id(p) for p in followers.pack_paths()}
        for pid, entry in reader.entries.items():
            if pid in optional:
                continue
            want = expected.get(pid)
            if want is None or want["crc"] != entry.crc32 or want["size"] != entry.raw_size:
                raise BuilderError("The data pack does not match this release.")
        if len(set(reader.entries) - optional) != len(expected) or reader.abi != recipe.engine_abi:
            raise BuilderError("The data pack does not match this release.")
    print("OK: %d entries, ABI %08x, release %s" % (count, recipe.engine_abi, recipe.release))
    return 0


def cmd_detect(args) -> int:
    cards = find_sd_cards()
    if not cards:
        print("No card with a ROCKNIX roms folder was found.")
    for card in cards:
        print(card)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="emerald3ds-builder", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("--payload", type=Path, default=default_payload(),
                    help="folder with the release payload (default: next to the builder)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="write a roms/ folder to copy onto the RG DS")
    b.add_argument("--rom", required=True)
    b.add_argument("--output", required=True)
    b.add_argument("--keep-workdir", action="store_true", help=argparse.SUPPRESS)
    i = sub.add_parser("install", help="install straight into the RG DS's roms folder")
    i.add_argument("--rom", required=True)
    i.add_argument("--roms", "--sd", dest="roms", required=True,
                   help="the roms folder: the games-roms share, or a games card")
    v = sub.add_parser("verify", help="check a data pack against this release")
    v.add_argument("--pak", required=True)
    sub.add_parser("detect", help="list cards that hold a ROCKNIX roms folder")
    args = ap.parse_args(argv)
    try:
        return {"build": cmd_build, "install": cmd_install, "verify": cmd_verify,
                "detect": cmd_detect}[args.cmd](args)
    except BuilderError as exc:
        sys.stdout.write("\n")
        print("Error: %s" % exc, file=sys.stderr)
        return 1
