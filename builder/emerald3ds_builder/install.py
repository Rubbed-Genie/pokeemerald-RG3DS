"""Put the game on an RG DS running ROCKNIX: into its roms folder (the
`games-roms` network share, a games card's roms/, or any folder laid out like
one, to copy over by hand).

RG3DS targets the RG DS only. Azahar keeps its SD card in roms/3ds/azahar/sdmc
(start_azahar.sh makes it), so the data pack and the save live in
roms/3ds/azahar/sdmc/3ds/emerald3ds/, the game itself in roms/3ds/, and the
one-time setup (the Azahar launcher hook) in roms/ports/."""

from __future__ import annotations

import errno
import os
import shutil
import stat
import string
import sys
import time
import uuid
from pathlib import Path

from .errors import BuilderError

# Azahar's SD card inside the roms folder, and the game's folder on it.
SDMC_DIR = Path("3ds") / "azahar" / "sdmc"
APP_DIR = SDMC_DIR / "3ds" / "emerald3ds"
# The game, as EmulationStation lists it in the 3DS system.
GAME_PATH = Path("3ds") / "Pokemon Emerald RG3DS.3dsx"
# Ports > RG3DS Setup, run once: installs the launcher hook it keeps beside it.
SETUP_PATH = Path("ports") / "RG3DS Setup.sh"
SETUP_DIR = Path("ports") / "rg3ds"

# The player's save, real-time clock and Nuzlocke tracker, in the app folder.
SAVE_NAME = "emerald3ds.sav"
SAVE_FILES = (SAVE_NAME, "emerald3ds.clock", "emerald3ds.clock.tmp", "emerald3ds.clock.bak",
              "emerald3ds.nuzlocke", "emerald3ds.nuzlocke.tmp", "emerald3ds.nuzlocke.bak")
BACKUP_DIR = "backup"   # <app folder>/backup/<timestamp>/

# The 3DS sound firmware dump that homebrew needs for audio.
DSP_FIRM = SDMC_DIR / "3ds" / "dspfirm.cdc"
DSP_WARNING = ("The 3DS sound firmware dump (dspfirm.cdc) was not found at:\n%s\n\n"
               "The game was installed but has no sound until you put your own dump "
               "(made on a 3DS, for example with the DSP1 homebrew) at "
               "roms/3ds/azahar/sdmc/3ds/dspfirm.cdc.")

# ROCKNIX's network share of the roms folder (hostname ROCKNIX by default).
NETWORK_SHARE = r"\\ROCKNIX\games-roms"


def is_roms_folder(path: Path) -> bool:
    """A ROCKNIX roms folder: it already holds the 3DS or the ports system."""
    try:
        return (path / "3ds").is_dir() or (path / "ports").is_dir()
    except OSError:
        return False


def roms_folder(path: Path) -> Path:
    """The roms folder the player meant: a card or folder holding roms/ means
    that roms/ (a ROCKNIX games card's root, games-internal/ on its own card)."""
    path = Path(path)
    for inner in (path / "roms", path / "games-internal" / "roms", path / "games-external" / "roms"):
        if not is_roms_folder(path) and is_roms_folder(inner):
            return inner
    return path


def find_sd_cards() -> list[Path]:
    """Mounted volumes whose roms folder looks like ROCKNIX's.

    Only a suggestion: the builder never installs anywhere without the
    player choosing the destination."""
    candidates: list[Path] = []
    if os.name == "nt":
        roots = [Path("%s:\\" % letter) for letter in string.ascii_uppercase]
    elif sys.platform == "darwin":
        roots = list(Path("/Volumes").glob("*"))
    else:
        roots = [p for base in ("/media", "/run/media") for p in Path(base).glob("*/*")]
    for root in roots:
        try:
            found = roms_folder(root)
        except OSError:
            continue
        if found != root or is_roms_folder(root):
            candidates.append(found)
    return candidates


def placed_files(payload) -> dict[str, Path]:
    """Everything but the data pack, where it goes under the roms folder: the
    game (the release's engine-only 3DSX) and the Ports setup with its hook."""
    setup, hook = payload.rgds_files()
    return {GAME_PATH.as_posix(): payload.game, SETUP_PATH.as_posix(): setup,
            (SETUP_DIR / hook.name).as_posix(): hook}


_RETRY_HINT = ("Nothing already on the card was changed. Check that the card is still inserted, "
               "is not write-protected (the lock switch) and has free space, then try again.")


def _check_name(name) -> None:
    """Destination names must be plain file names: no folders, no drive letters."""
    if (not isinstance(name, str) or name in ("", ".", "..") or any(c in name for c in "/\\:\0")
            or Path(name).name != name):
        raise BuilderError("Refusing to install a file with an unsafe name: %r" % (name,),
                           code="install_failed")


def _check_relative(rel) -> Path:
    """A placed file's path under the roms folder: plain names, no way out of it."""
    parts = Path(rel).parts if isinstance(rel, (str, Path)) else ()
    if not parts or Path(rel).is_absolute():
        raise BuilderError("Refusing to install a file with an unsafe name: %r" % (rel,),
                           code="install_failed")
    for part in parts:
        _check_name(part)
    return Path(*parts)


def _create_temp(dest: Path, name: str) -> tuple[Path, int]:
    """A new, uniquely named file next to `name`; never reuses an existing file."""
    for _ in range(100):
        tmp = dest / ("%s.%s.partial" % (name, uuid.uuid4().hex[:12]))
        try:
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o666)
        except FileExistsError:
            continue
        return tmp, fd
    raise FileExistsError("could not create a temporary file in %s" % dest)


def _remove(paths) -> None:
    for path in paths:
        try:
            path.unlink()
        except OSError:
            pass


def _backup_stamp() -> str:
    """Local time, to the second; uniqueness comes from _make_backup_dir."""
    return time.strftime("%Y%m%d-%H%M%S")


def _existing_saves(dest: Path) -> list[tuple[str, Path, os.stat_result]]:
    """The save files to back up: none unless the save itself exists, then the
    save plus whichever clock and Nuzlocke companions exist (base, .tmp and
    .bak files, as listed in SAVE_FILES). Only reads metadata."""
    found = []
    for name in SAVE_FILES:
        path = dest / name
        try:
            st = path.stat()
        except (FileNotFoundError, NotADirectoryError):
            if name == SAVE_NAME:
                return []   # do not inspect companions without a save
            continue
        except OSError as exc:
            raise BuilderError("The existing save file could not be read:\n%s\n(%s)" % (path, exc),
                               "Nothing was changed on the destination.", code="install_failed") from exc
        if not stat.S_ISREG(st.st_mode):
            raise BuilderError("The existing save file is not a regular file:\n%s" % path,
                               "Nothing was changed on the destination.", code="install_failed")
        found.append((name, path, st))
    return found


def _make_backup_dir(dest: Path) -> tuple[Path, bool]:
    """Reserve <dest>/backup/<stamp>[-N].partial/ exclusively.

    The partial directory reserves its final name among concurrent backups.
    Skip names whose final backup already exists, including empty folders.
    Returns the staging directory and whether backup/ was created here."""
    parent = dest / BACKUP_DIR
    created_parent = False
    try:
        parent.mkdir()
        created_parent = True
    except FileExistsError:
        pass
    stamp = _backup_stamp()
    for n in range(1, 1000):
        final = parent / (stamp if n == 1 else "%s-%d" % (stamp, n))
        folder = final.with_name(final.name + ".partial")
        try:
            folder.mkdir()
        except FileExistsError:
            continue
        except BaseException:
            if created_parent:
                _rmdir(parent)
            raise
        if os.path.lexists(final):
            _rmdir(folder)
            continue
        return folder, created_parent
    if created_parent:
        _rmdir(parent)
    raise FileExistsError("could not create a new backup folder in %s" % parent)


def _rmdir(path: Path) -> None:
    try:
        path.rmdir()   # only ever succeeds on an empty folder
    except OSError:
        pass


def _backup_saves(dest: Path, saves, advance) -> Path:
    """Copy (and sync) every file in `saves` into a new backup folder.

    The originals are only opened for reading. Either every file is copied in
    full before the staging folder is atomically renamed to its final name,
    or cleanup is attempted and the error raised. If cleanup fails, leftovers
    remain visibly marked .partial; other backups are never touched."""
    folder, created_parent = _make_backup_dir(dest)
    written: list[Path] = []
    try:
        for name, src, st in saves:
            target = folder / name
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o666)
            written.append(target)
            copied = 0
            with os.fdopen(fd, "wb") as fout, src.open("rb") as fin:
                while True:
                    chunk = fin.read(1 << 20)
                    if not chunk:
                        break
                    fout.write(chunk)
                    copied += len(chunk)
                    advance(len(chunk))
                fout.flush()
                os.fsync(fout.fileno())
            if copied != st.st_size:
                raise OSError(errno.EIO, "%s changed size while it was being backed up" % name)
            try:
                os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns))
            except OSError:
                pass   # keeping the original time is a courtesy only
        final = folder.with_name(folder.name.removesuffix(".partial"))
        folder.rename(final)
    except BaseException:
        _remove(written)
        _rmdir(folder)
        if created_parent:
            _rmdir(dest / BACKUP_DIR)
        raise
    return final


def _warn_missing_dsp(sd_root: Path, warn) -> None:
    if warn is None:
        return
    firm = sd_root / DSP_FIRM
    try:
        present = firm.is_file()
    except OSError:
        present = False
    if not present:
        try:
            warn(DSP_WARNING % firm)
        except Exception:
            pass   # the install already succeeded; a broken display must not undo that


def install(sd_root: Path, files: dict[str, Path], progress=None, warn=None,
            placed: dict[str, Path] | None = None) -> Path:
    """Copy `files` ({name: source}) into <sd_root>/APP_DIR, and `placed`
    ({path under sd_root: source}: the game, the setup) where they say.

    Every file is first copied (and synced) under a new, unique temporary name.
    Only when all of them are copied are they renamed into place, so a failed
    copy leaves the files already installed untouched and removes its own
    temporary files. The renames themselves are not one transaction: if one of
    them fails, the install can be left part old, part new, and the error says
    so. Behaviour when a card is pulled out or loses power is not verified.

    If a save (emerald3ds.sav) is already there, it and any clock companions
    (emerald3ds.clock, emerald3ds.clock.tmp, emerald3ds.clock.bak) and Nuzlocke
    tracker companions (emerald3ds.nuzlocke, emerald3ds.nuzlocke.tmp,
    emerald3ds.nuzlocke.bak) are first copied, in full, into a new folder
    backup/<timestamp>/ next to them; if that backup fails, nothing
    is replaced. The originals are never written, older backups never removed.

    `warn(message)`, if given, receives non-fatal warnings after a successful
    install (currently: <sd_root>/DSP_FIRM is missing)."""
    sd_root = Path(sd_root)
    if not sd_root.is_dir():
        raise BuilderError("The destination folder does not exist:\n%s" % sd_root)
    for name in files:
        _check_name(name)
    dest = sd_root / APP_DIR
    # Every file as (folder, name, source): the app folder's, then the placed ones.
    targets = [(dest, name, src) for name, src in files.items()]
    for rel, src in (placed or {}).items():
        rel = _check_relative(rel)
        targets.append((sd_root / rel.parent, rel.name, src))
    need = 0
    for _, _, src in targets:
        try:
            st = Path(src).stat()
        except OSError as exc:
            raise BuilderError("A file to install could not be read:\n%s\n(%s)" % (src, exc),
                               "Nothing was changed on the destination.", code="install_failed") from exc
        if not stat.S_ISREG(st.st_mode):
            raise BuilderError("A file to install is not a regular file:\n%s" % src,
                               "Nothing was changed on the destination.", code="install_failed")
        need += st.st_size
    saves = _existing_saves(dest)
    need += sum(st.st_size for _, _, st in saves)   # the backup is written to the same card
    try:
        free = shutil.disk_usage(sd_root).free
    except OSError:
        free = None   # free space unknown: skip this advisory check, the copy still reports errors
    if free is not None and free < need + (4 << 20):
        raise BuilderError("There is not enough free space on the destination (%d MiB needed)."
                           % ((need >> 20) + 4))
    for folder in dict.fromkeys(folder for folder, _, _ in targets + [(dest, None, None)]):
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise BuilderError("Could not create the folder %s:\n%s" % (folder, exc), _RETRY_HINT,
                               code="install_failed") from exc

    staged: list[tuple[Path, Path]] = []
    done = 0

    def advance(count: int) -> None:
        nonlocal done
        done += count
        if progress:
            progress(done / max(need, 1))

    name = None
    folder = dest
    try:
        for folder, name, src in targets:
            tmp, fd = _create_temp(folder, name)
            staged.append((tmp, folder / name))
            with os.fdopen(fd, "wb") as fout, Path(src).open("rb") as fin:
                while True:
                    chunk = fin.read(1 << 20)
                    if not chunk:
                        break
                    fout.write(chunk)
                    advance(len(chunk))
                fout.flush()
                os.fsync(fout.fileno())
    except OSError as exc:
        _remove(tmp for tmp, _ in staged)
        raise BuilderError("Copying %s to %s failed:\n%s" % (name, folder, exc), _RETRY_HINT,
                           code="install_failed") from exc
    except BaseException:
        _remove(tmp for tmp, _ in staged)
        raise

    # Back up the save set, complete, before any game file is replaced.
    if saves:
        try:
            _backup_saves(dest, saves, advance)
        except OSError as exc:
            _remove(tmp for tmp, _ in staged)
            raise BuilderError("Backing up the save in %s failed, so the game was not updated:\n%s"
                               % (dest, exc), _RETRY_HINT, code="install_failed") from exc
        except BaseException:
            _remove(tmp for tmp, _ in staged)
            raise

    committed = 0
    try:
        for tmp, final in staged:
            os.replace(tmp, final)
            committed += 1
    except OSError as exc:
        _remove(tmp for tmp, _ in staged[committed:])
        if committed == 0:
            raise BuilderError("Putting %s in place in %s failed:\n%s" % (staged[0][1].name, dest, exc),
                               _RETRY_HINT, code="install_failed") from exc
        raise BuilderError("The install in %s is incomplete: %d of %d files were updated before "
                           "an error (%s)." % (dest, committed, len(staged), exc),
                           "The game may not start until it is installed again. Check the card, "
                           "then run the install again.", code="install_failed") from exc
    except BaseException:
        _remove(tmp for tmp, _ in staged[committed:])
        raise
    _warn_missing_dsp(sd_root, warn)
    return dest
