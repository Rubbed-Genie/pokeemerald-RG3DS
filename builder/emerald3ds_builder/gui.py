"""The builder's window: pick the ROM, pick the RG DS's roms folder, Install."""

from __future__ import annotations

import queue
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .build import Payload, build_pack, default_payload
from .errors import BuilderError
from .install import NETWORK_SHARE, find_sd_cards, install, is_roms_folder, placed_files, roms_folder
from .rom import load_rom

TITLE = "Pokemon Emerald RG3DS Builder"
DONE = ("Done. Pokemon Emerald RG3DS is in\n%s\n\n"
        "On the RG DS:\n"
        "1. Start > Game settings > Update gamelists (or reboot).\n"
        "2. Run Ports > RG3DS Setup once (it puts the game's two windows on the two screens).\n"
        "3. Play it from the 3DS system.")


class App:
    def __init__(self, root: tk.Tk, payload: Payload):
        self.root = root
        self.payload = payload
        self.events: queue.Queue = queue.Queue()
        self.warnings: list[str] = []   # non-fatal, shown with the result (main thread only)
        self.busy = False
        root.title("%s %s" % (TITLE, __version__))
        root.resizable(False, False)
        frame = ttk.Frame(root, padding=16)
        frame.grid(sticky="nsew")

        ttk.Label(frame, text="Pokemon Emerald ROM (your own cartridge dump)").grid(
            row=0, column=0, columnspan=2, sticky="w")
        self.rom = tk.StringVar()
        ttk.Entry(frame, textvariable=self.rom, width=56).grid(row=1, column=0, sticky="we")
        ttk.Button(frame, text="Browse...", command=self.pick_rom).grid(row=1, column=1, padx=(8, 0))
        self.rom_status = ttk.Label(frame, text="")
        self.rom_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(2, 10))

        ttk.Label(frame, text="Install to your RG DS's roms folder (the games-roms network share, "
                              "a games card, or any folder to copy over)").grid(
            row=3, column=0, columnspan=2, sticky="w")
        self.sd = tk.StringVar()
        self.sd_box = ttk.Combobox(frame, textvariable=self.sd, width=53)
        self.sd_box.grid(row=4, column=0, sticky="we")
        buttons = ttk.Frame(frame)
        buttons.grid(row=4, column=1, padx=(8, 0))
        ttk.Button(buttons, text="Browse...", command=self.pick_sd).grid(row=0, column=0)
        ttk.Button(buttons, text="Network", command=lambda: self.sd.set(NETWORK_SHARE)).grid(
            row=0, column=1, padx=(4, 0))
        self.sd_status = ttk.Label(frame, text="")
        self.sd_status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 10))

        self.bar = ttk.Progressbar(frame, length=420, maximum=1000)
        self.bar.grid(row=6, column=0, columnspan=2, sticky="we")
        self.step = ttk.Label(frame, text="")
        self.step.grid(row=7, column=0, columnspan=2, sticky="w", pady=(2, 10))

        self.button = ttk.Button(frame, text="Install", command=self.start)
        self.button.grid(row=8, column=0, columnspan=2)
        ttk.Label(frame, text="The ROM never leaves this computer and is not copied; only the "
                              "generated data pack is written.", foreground="#555",
                  wraplength=460).grid(row=9, column=0, columnspan=2, pady=(12, 0))

        self.rom.trace_add("write", lambda *a: self.check_rom())
        self.sd.trace_add("write", lambda *a: self.check_sd())
        self.refresh_cards()
        root.after(100, self.poll)

    # -- inputs -------------------------------------------------------------
    def pick_rom(self):
        path = filedialog.askopenfilename(title="Pokemon Emerald ROM",
                                          filetypes=[("GBA ROM", "*.gba *.zip"), ("All files", "*.*")])
        if path:
            self.rom.set(path)

    def pick_sd(self):
        path = filedialog.askdirectory(title="The RG DS's roms folder, or an output folder")
        if path:
            self.sd.set(path)

    def refresh_cards(self):
        cards = [str(c) for c in find_sd_cards()]
        self.sd_box["values"] = cards
        if cards and not self.sd.get():
            self.sd.set(cards[0])

    def check_rom(self):
        path = self.rom.get().strip()
        if not path:
            self.rom_status.config(text="", foreground="")
            return
        try:
            rom = load_rom(Path(path))
        except BuilderError as exc:
            self.rom_status.config(text="X  " + exc.message, foreground="#b00020")
            return
        self.rom_status.config(text="OK  %s - SHA-1 verified" % rom.title, foreground="#1b7a1b")

    def check_sd(self):
        path = Path(self.sd.get().strip()) if self.sd.get().strip() else None
        if path is None:
            self.sd_status.config(text="")
            return
        roms = roms_folder(path)
        if is_roms_folder(roms):
            self.sd_status.config(text="OK  ROCKNIX roms folder: %s" % roms, foreground="#1b7a1b")
        elif path.is_dir():
            self.sd_status.config(text="Not a ROCKNIX roms folder: the files are written into it for you "
                                       "to copy into roms on the RG DS.", foreground="#8a6d00")
        else:
            self.sd_status.config(text="X  Folder not found (is the RG DS on and on the same network?)",
                                  foreground="#b00020")

    # -- work -----------------------------------------------------------------
    def start(self):
        if self.busy:
            return
        rom, sd = self.rom.get().strip(), self.sd.get().strip()
        if not rom or not sd:
            messagebox.showwarning(TITLE, "Choose the ROM and the destination first.")
            return
        dest = roms_folder(Path(sd))
        if not messagebox.askokcancel(TITLE, "Pokemon Emerald RG3DS will be installed into:\n\n%s\n\n"
                                             "Continue?" % dest):
            return
        self.busy = True
        self.warnings = []
        self.button.state(["disabled"])
        threading.Thread(target=self.work, args=(Path(rom), dest), daemon=True).start()

    def work(self, rom: Path, sd: Path):
        def progress(fraction, message):
            self.events.put(("progress", fraction, message))
        try:
            self.payload.check()
            with tempfile.TemporaryDirectory(prefix="emerald3ds-") as tmp:
                pak_path = Path(tmp) / "emerald3ds.pak"
                info = build_pack(rom, self.payload, pak_path, lambda f, m: progress(f * 0.9, m),
                                  need_executables=True)
                install(sd, {"emerald3ds.pak": pak_path},
                        lambda f: progress(0.9 + 0.1 * f, "Copying to the RG DS"),
                        warn=lambda message: self.events.put(("warning", message)),
                        placed=placed_files(info["payload"]))
            self.events.put(("done", str(sd)))
        except BuilderError as exc:
            self.events.put(("error", str(exc)))
        except Exception as exc:  # the player gets a message, never a traceback
            self.events.put(("error", "Unexpected error: %s" % exc))

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "progress":
                    self.bar["value"] = int(event[1] * 1000)
                    self.step.config(text=event[2])
                elif event[0] == "warning":
                    self.warnings.append(event[1])
                elif event[0] == "done":
                    self.finish()
                    text = DONE % event[1]
                    if self.warnings:
                        messagebox.showwarning(TITLE, text + "\n\nWarning:\n" + "\n\n".join(self.warnings))
                    else:
                        messagebox.showinfo(TITLE, text)
                    self.warnings = []
                elif event[0] == "error":
                    self.finish()
                    messagebox.showerror(TITLE, event[1])
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def finish(self):
        self.busy = False
        self.button.state(["!disabled"])
        self.step.config(text="")
        self.bar["value"] = 0


def main(payload: Path | None = None) -> int:
    root = tk.Tk()
    App(root, Payload(payload or default_payload()))
    root.mainloop()
    return 0
