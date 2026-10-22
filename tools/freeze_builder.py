#!/usr/bin/env python3
"""Freeze the builder into the Windows executable (PyInstaller), on its own.

    python tools/freeze_builder.py            # -> builder/build/dist/Emerald3DS-Builder/

RG3DS: the GitHub workflow (.github/workflows/rg3ds-builder-exe.yml) runs this
on Windows, from the source alone - no ROM, no payload. tools/build_release.py
makes the payload on a machine that has the ROM and adds this folder to it
(--exe-dir). The modules the voxel generators import are bundled the same way
build_release.py lists them.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_release  # noqa: E402


def main() -> int:
    _, external = build_release.local_closure(build_release.PORT / "scripts", build_release.GENERATORS)
    build = ROOT / "builder" / "build"
    build.mkdir(parents=True, exist_ok=True)
    (build / "hidden-imports.txt").write_text("\n".join(sorted(external)) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(build / "dist"), "--workpath", str(build / "pyi"),
                    "emerald3ds-builder.spec"], cwd=ROOT / "builder", check=True)
    print("frozen: %s" % (build / "dist" / "Emerald3DS-Builder"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
