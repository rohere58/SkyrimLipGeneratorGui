from __future__ import annotations

import os
import json
import queue
import random
import re
import subprocess
import sys
import threading
import webbrowser
from csv import reader as csv_reader
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, DISABLED, NORMAL
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_NAME = "LipGUI"
APP_VERSION = "0.3.0"
FAQ_FILENAME = "FAQ_EN.md"
DEFAULT_DONATE_URL = "https://ko-fi.com/rore58"


SUPPORTED_LANGUAGES = [
    "USEnglish",
    "French",
    "German",
    "Spanish",
    "Italian",
    "Korean",
    "Japanese",
]


class UiLanguage:
    DE = "de"
    EN = "en"


class UiTheme:
    LIGHT = "light"
    DARK = "dark"


class TextSource:
    FILENAME = "filename"
    SIDECAR_TXT = "sidecar_txt"
    FIXED = "fixed"
    MAPPING_FILE = "mapping_file"


TRANSLATIONS: dict[str, dict[str, str]] = {
    UiLanguage.DE: {
        "title": "Skyrim Lip Batch Generator",
        "folders": "Ordner",
        "wav_folder": "WAV-Ordner:",
        "output_folder": "Output-Ordner:",
        "pick": "Auswählen…",
        "include_subfolders": "Unterordner einbeziehen",
        "preserve_structure": "Ordnerstruktur beibehalten",
        "settings": "Einstellungen",
        "language": "Sprache:",
        "gesture": "GestureExaggeration (optional):",
        "text_source": "Textquelle (Pflicht für LipGenerator)",
        "txt": "Aus .txt Datei (gleicher Name wie .wav)",
        "filename": "Aus Dateiname (z.B. Hello_World.wav → 'Hello World')",
        "fixed": "Fester Text (für alle WAVs)",
        "mapping": "Aus Mapping-Datei (CSV/TSV: Voice Type + File Name → Text)",
        "fixed_text": "Fester Text:",
        "mapping_file": "Mapping-Datei(en):",
        "generate": "LIP Dateien generieren",
        "test_mapping": "Mapping testen",
        "pause": "Pause",
        "resume": "Fortsetzen",
        "stop": "Stop",
        "log": "Log",
        "menu_settings": "Einstellungen",
        "menu_theme": "Theme",
        "menu_theme_light": "Hell",
        "menu_theme_dark": "Dunkel",
        "menu_lang": "Sprache",
        "menu_help": "Hilfe",
        "menu_about": "Über…",
        "menu_faq": "FAQ (English)",
        "menu_donate": "Donate…",
        "close": "Schließen",
        "err_need_wav": "Bitte einen gültigen WAV-Ordner auswählen.",
        "err_need_out": "Bitte einen gültigen Output-Ordner auswählen.",
        "err_need_mapping": "Bitte mindestens eine Mapping-Datei auswählen.",
        "info_no_wav": "Keine .wav Dateien gefunden.",
        "stop_requested": "Stop angefordert…",
        "paused": "Pausiert.",
        "resumed": "Fortgesetzt.",
        "donate_missing": "Keine Donate-URL konfiguriert.\n\nDu kannst sie in settings.json als 'donate_url' setzen.",
        "about": f"{APP_NAME} {APP_VERSION}\n\nBatch-GUI für LipGenerator.exe (Skyrim).\n\nAuthor: Winnie (rore58)",
    },
    UiLanguage.EN: {
        "title": "Skyrim Lip Batch Generator",
        "folders": "Folders",
        "wav_folder": "WAV folder:",
        "output_folder": "Output folder:",
        "pick": "Browse…",
        "include_subfolders": "Include subfolders",
        "preserve_structure": "Preserve folder structure",
        "settings": "Settings",
        "language": "Language:",
        "gesture": "GestureExaggeration (optional):",
        "text_source": "Text source (required for LipGenerator)",
        "txt": "From .txt file (same name as .wav)",
        "filename": "From filename (e.g. Hello_World.wav → 'Hello World')",
        "fixed": "Fixed text (for all WAVs)",
        "mapping": "From mapping file (CSV/TSV: Voice Type + File Name → Text)",
        "fixed_text": "Fixed text:",
        "mapping_file": "Mapping file(s):",
        "generate": "Generate LIP files",
        "test_mapping": "Test mapping",
        "pause": "Pause",
        "resume": "Resume",
        "stop": "Stop",
        "log": "Log",
        "menu_settings": "Settings",
        "menu_theme": "Theme",
        "menu_theme_light": "Light",
        "menu_theme_dark": "Dark",
        "menu_lang": "Language",
        "menu_help": "Help",
        "menu_about": "About…",
        "menu_faq": "FAQ (English)",
        "menu_donate": "Donate…",
        "close": "Close",
        "err_need_wav": "Please select a valid WAV folder.",
        "err_need_out": "Please select a valid output folder.",
        "err_need_mapping": "Please select at least one mapping file.",
        "info_no_wav": "No .wav files found.",
        "stop_requested": "Stop requested…",
        "paused": "Paused.",
        "resumed": "Resumed.",
        "donate_missing": "No donate URL configured.\n\nYou can set it in settings.json as 'donate_url'.",
        "about": f"{APP_NAME} {APP_VERSION}\n\nBatch GUI for LipGenerator.exe (Skyrim).\n\nAuthor: Winnie (rore58)",
    },
}


@dataclass(frozen=True)
class Job:
    wav_path: Path
    lip_path: Path
    text: str
    note: str = ""


def find_wav_files(folder: Path, recursive: bool) -> list[Path]:
    if not folder.exists():
        return []
    pattern = "**/*.wav" if recursive else "*.wav"
    files = [p for p in folder.glob(pattern) if p.is_file()]
    # Case-insensitive safety (glob is case-sensitive on some platforms)
    files.extend([p for p in folder.glob(pattern.replace(".wav", ".WAV")) if p.is_file()])
    # De-dup
    unique: dict[str, Path] = {str(p.resolve()): p for p in files}
    return sorted(unique.values(), key=lambda p: str(p).lower())


def text_from_filename(wav_path: Path) -> str:
    return wav_path.stem.replace("_", " ").replace("-", " ").strip()


def text_from_sidecar_txt(wav_path: Path) -> str:
    txt_path = wav_path.with_suffix(".txt")
    if not txt_path.exists():
        raise FileNotFoundError(f"Fehlende Textdatei: {txt_path}")
    content = txt_path.read_text(encoding="utf-8", errors="replace").strip()
    if not content:
        raise ValueError(f"Textdatei ist leer: {txt_path}")
    return content


_FORMID_PREFIX_RE = re.compile(r"^([0-9A-Fa-f]{8})")
_FORMID_ANYWHERE_RE = re.compile(r"([0-9A-Fa-f]{8})")


def normalize_mapping_key(raw_key: str) -> str:
    key = raw_key.strip()
    if not key:
        return ""
    key = key.removeprefix("0x").removeprefix("0X").strip()
    m = _FORMID_PREFIX_RE.match(key)
    if m:
        return m.group(1).upper()
    return key.lower()


def mapping_keys_from_wav(wav_path: Path) -> list[str]:
    stem = wav_path.stem
    keys: list[str] = []

    # 1) Exact stem (common with LazyVoiceFinder exports)
    keys.append(stem.lower())

    # 1b) Folder + stem (when CSV provides Voice Type / folder)
    try:
        parent = wav_path.parent.name.strip().lower()
    except Exception:
        parent = ""
    if parent:
        keys.append(f"{parent}/{stem.lower()}")
        keys.append(f"{parent}\\{stem.lower()}")

    # 2) FormID patterns
    m_prefix = _FORMID_PREFIX_RE.match(stem)
    if m_prefix:
        keys.append(m_prefix.group(1).upper())
    else:
        m_any = _FORMID_ANYWHERE_RE.search(stem)
        if m_any:
            keys.append(m_any.group(1).upper())

    # De-dup preserving order
    seen: set[str] = set()
    out: list[str] = []
    for k in keys:
        if k and k not in seen:
            out.append(k)
            seen.add(k)
    return out


def load_text_mapping(mapping_file: Path) -> dict[str, str]:
    if not mapping_file.exists():
        raise FileNotFoundError(f"Mapping-Datei nicht gefunden: {mapping_file}")

    raw = mapping_file.read_text(encoding="utf-8", errors="replace")
    # Heuristic delimiter detection: prefer tab, then semicolon, then comma
    delimiter = "\t" if "\t" in raw else (";" if ";" in raw and "," not in raw else ",")

    rows = [r for r in csv_reader(raw.splitlines(), delimiter=delimiter) if any((c or "").strip() for c in r)]
    if not rows:
        raise ValueError("Mapping-Datei ist leer.")

    def _norm_header(name: str) -> str:
        # Keep '-' so we can still do substring checks like 'dialogue2-german'
        return name.strip().lower().replace(" ", "").replace("_", "")

    header = [_norm_header(c) for c in rows[0]]
    has_header = any(
        token in header
        for token in {
            "formid",
            "id",
            "key",
            "filename",
            "file",
            "wav",
            "path",
            "voicefile",
            "subtitle",
            "text",
            "dialogue",
            "translated",
            "translation",
            "target",
        }
    )

    key_idx: int | None = None
    text_idx: int | None = None
    voice_idx: int | None = None

    if has_header:
        def _first_index(candidates: set[str]) -> int | None:
            for i, col in enumerate(header):
                if col in candidates:
                    return i
            return None

        def _first_index_contains(needles: list[str]) -> int | None:
            for i, col in enumerate(header):
                for needle in needles:
                    if needle in col:
                        return i
            return None

        key_idx = _first_index({"formid", "id", "key"})
        if key_idx is None:
            key_idx = _first_index({"filename", "file", "wav", "path", "voicefile"})
        if key_idx is None:
            key_idx = _first_index_contains(["filename", "file", "wav", "path", "voice"])

        voice_idx = _first_index({"voicetype", "voice", "voicename"})
        if voice_idx is None:
            voice_idx = _first_index_contains(["voicetype", "voice"])

        # Prefer translated/target text columns, fall back to subtitle/text
        text_idx = _first_index({"translated", "translation", "target", "targettext", "translatedtext"})
        if text_idx is None:
            text_idx = _first_index({"subtitle", "subtitles", "text", "dialogue", "line"})
        if text_idx is None:
            # Handles headers like "Dialogue2-German" / "Dialogue 2 - German"
            text_idx = _first_index_contains([
                "translated",
                "translation",
                "target",
                "subtitle",
                "dialogue",
                "text",
            ])

        # If both detected but point to same column, prefer finding another text column
        if key_idx is not None and text_idx is not None and key_idx == text_idx:
            alt = _first_index_contains(["dialogue", "subtitle", "translated", "target", "text"])
            if alt is not None and alt != key_idx:
                text_idx = alt

    start_row = 1 if has_header else 0

    def _extract_key(cell: str) -> str:
        raw_cell = (cell or "").strip()
        if not raw_cell:
            return ""
        # If it's a path or filename, reduce to stem
        lowered = raw_cell.lower()
        if "\\" in raw_cell or "/" in raw_cell or lowered.endswith(".wav"):
            try:
                stem = Path(raw_cell).stem
            except Exception:
                stem = raw_cell
            return normalize_mapping_key(stem)
        return normalize_mapping_key(raw_cell)

    mapping: dict[str, str] = {}
    for row in rows[start_row:]:
        if not row:
            continue

        # Fallback behavior: if we couldn't detect indices, use first two columns
        if key_idx is None or text_idx is None:
            if len(row) < 2:
                continue
            raw_key, raw_text = row[0], row[1]
            raw_voice = ""
        else:
            if key_idx >= len(row) or text_idx >= len(row):
                continue
            raw_key, raw_text = row[key_idx], row[text_idx]
            raw_voice = row[voice_idx] if (has_header and voice_idx is not None and voice_idx < len(row)) else ""

        key = _extract_key(str(raw_key))
        if not key:
            continue

        text = str(raw_text).strip()
        if not text:
            continue

        # Ignore header-ish rows even if delimiter guessing failed
        if key in {"formid", "id", "key", "filename", "file", "wav", "path", "voicefile"}:
            continue

        mapping[key] = text

        # Extra composite keys for LazyVoiceFinder-style exports:
        # Voice Type (folder) + File Name stem
        voice = str(raw_voice).strip().lower()
        if voice:
            # When key is a stem-like string, prefer composing with that
            # (If key is already a FormID, this still doesn't hurt; it just won't match most WAVs.)
            mapping[f"{voice}/{key}"] = text
            mapping[f"{voice}\\{key}"] = text

    if not mapping:
        raise ValueError(
            "Mapping-Datei enthält keine verwertbaren Zeilen. Erwartet wird entweder: "
            "(a) 2 Spalten: ID<TAB>Text oder (b) CSV/TSV mit Header-Spalten wie FormID/FileName + Text/Subtitle."
        )
    return mapping


def merge_text_mappings(mappings: list[dict[str, str]]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for m in mappings:
        for k, v in m.items():
            if k not in merged or len(v) > len(merged[k]):
                merged[k] = v
    return merged


def load_text_mappings(files: list[Path]) -> dict[str, str]:
    if not files:
        raise ValueError("Bitte mindestens eine Mapping-Datei auswählen.")
    mappings = [load_text_mapping(p) for p in files]
    return merge_text_mappings(mappings)


def build_jobs(
    input_folder: Path,
    output_folder: Path,
    recursive: bool,
    preserve_structure: bool,
    text_source: str,
    fixed_text: str,
    mapping_file: Path | None,
) -> list[Job]:
    wav_files = find_wav_files(input_folder, recursive)

    mapping: dict[str, str] | None = None
    if text_source == TextSource.MAPPING_FILE:
        if mapping_file is None:
            raise ValueError("Bitte eine Mapping-Datei auswählen.")
        mapping = load_text_mapping(mapping_file)

    jobs: list[Job] = []
    for wav_path in wav_files:
        if preserve_structure:
            rel = wav_path.relative_to(input_folder)
            lip_path = (output_folder / rel).with_suffix(".lip")
        else:
            lip_path = (output_folder / f"{wav_path.stem}.lip")

        note = ""

        if text_source == TextSource.FILENAME:
            text = text_from_filename(wav_path)
        elif text_source == TextSource.SIDECAR_TXT:
            text = text_from_sidecar_txt(wav_path)
        elif text_source == TextSource.FIXED:
            text = fixed_text.strip()
            if not text:
                raise ValueError("Der feste Text ist leer.")
        elif text_source == TextSource.MAPPING_FILE:
            assert mapping is not None
            text = ""
            for key in mapping_keys_from_wav(wav_path):
                text = mapping.get(key, "").strip()
                if text:
                    break
            if not text:
                # Fallback: still produce something usable, but warn.
                text = text_from_filename(wav_path)
                note = "WARN: Kein Mapping-Eintrag gefunden, nutze Dateiname als Text."
        else:
            raise ValueError("Unbekannte Textquelle.")

        jobs.append(Job(wav_path=wav_path, lip_path=lip_path, text=text, note=note))

    return jobs


def run_lipgenerator(
    lipgenerator_dir: Path,
    exe_path: Path,
    job: Job,
    language: str,
    gesture_exaggeration: str,
) -> subprocess.CompletedProcess[str]:
    job.lip_path.parent.mkdir(parents=True, exist_ok=True)

    args: list[str] = [
        str(exe_path),
        str(job.wav_path),
        job.text,
        f"-Language:{language}",
        f"-OutputFileName:{job.lip_path}",
    ]
    gesture_exaggeration = gesture_exaggeration.strip()
    if gesture_exaggeration:
        args.append(f"-GestureExaggeration:{gesture_exaggeration}")

    return subprocess.run(
        args,
        cwd=str(lipgenerator_dir),
        capture_output=True,
        text=True,
        check=False,
    )


def run_lipgenerator_background(
    lipgenerator_dir: Path,
    exe_path: Path,
    job: Job,
    language: str,
    gesture_exaggeration: str,
    stop_event: threading.Event,
    pause_event: threading.Event,
) -> tuple[subprocess.CompletedProcess[str], bool]:
    """Run LipGenerator without popping up a console window (Windows) and allow canceling mid-file.

    Returns (CompletedProcess, was_killed).
    """
    job.lip_path.parent.mkdir(parents=True, exist_ok=True)

    args: list[str] = [
        str(exe_path),
        str(job.wav_path),
        job.text,
        f"-Language:{language}",
        f"-OutputFileName:{job.lip_path}",
    ]
    gesture_exaggeration = gesture_exaggeration.strip()
    if gesture_exaggeration:
        args.append(f"-GestureExaggeration:{gesture_exaggeration}")

    creationflags = 0
    startupinfo = None
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
        except Exception:
            startupinfo = None

    proc = subprocess.Popen(
        args,
        cwd=str(lipgenerator_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creationflags,
        startupinfo=startupinfo,
    )

    was_killed = False
    try:
        # Poll loop so we can pause/stop responsively.
        while True:
            if stop_event.is_set():
                was_killed = True
                try:
                    proc.terminate()
                except Exception:
                    pass
                break

            # If paused, wait here but still allow stopping.
            if not pause_event.is_set():
                if stop_event.wait(timeout=0.2):
                    continue
                continue

            rc = proc.poll()
            if rc is not None:
                break
            stop_event.wait(timeout=0.2)

        try:
            stdout, stderr = proc.communicate(timeout=5)
        except Exception:
            was_killed = True
            try:
                proc.kill()
            except Exception:
                pass
            stdout, stderr = proc.communicate()

        cp = subprocess.CompletedProcess(args=args, returncode=proc.returncode or (1 if was_killed else 0), stdout=stdout or "", stderr=stderr or "")
        return cp, was_killed
    finally:
        try:
            if proc.poll() is None:
                proc.kill()
        except Exception:
            pass


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self._base_dir = self._compute_base_dir()
        self._settings_path = self._base_dir / "settings.json"
        self._settings = self._load_settings()

        self.ui_language_var = tk.StringVar(value=self._settings.get("ui_language", UiLanguage.DE))
        self.ui_theme_var = tk.StringVar(value=self._settings.get("ui_theme", UiTheme.LIGHT))

        self.title(self._t("title"))
        self.minsize(780, 520)

        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._stop_requested = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # set = running, clear = paused

        default_root = self._base_dir
        self.lipgenerator_dir = default_root / "LipGenerator"
        self.exe_path = self.lipgenerator_dir / "LipGenerator.exe"
        self.cdf_path = self.lipgenerator_dir / "FonixData.cdf"

        self.input_folder_var = tk.StringVar(value="")
        self.output_folder_var = tk.StringVar(value="")
        self.recursive_var = tk.BooleanVar(value=False)
        self.preserve_structure_var = tk.BooleanVar(value=True)

        self.text_source_var = tk.StringVar(value=TextSource.SIDECAR_TXT)
        self.fixed_text_var = tk.StringVar(value="")
        self.mapping_file_var = tk.StringVar(value="")
        self._mapping_files: list[Path] = []

        self.language_var = tk.StringVar(value="German")
        self.gesture_var = tk.StringVar(value="")

        self._build_menu()
        self._build_ui()
        self._apply_theme(self.ui_theme_var.get())
        self.after(100, self._drain_queue)

    def _compute_base_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    def _t(self, key: str) -> str:
        lang = self.ui_language_var.get() if hasattr(self, "ui_language_var") else UiLanguage.DE
        table = TRANSLATIONS.get(lang, TRANSLATIONS[UiLanguage.DE])
        return table.get(key, TRANSLATIONS[UiLanguage.DE].get(key, key))

    def _load_settings(self) -> dict[str, str]:
        try:
            if self._settings_path.exists():
                return json.loads(self._settings_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"ui_language": UiLanguage.DE, "ui_theme": UiTheme.LIGHT, "donate_url": DEFAULT_DONATE_URL}

    def _save_settings(self) -> None:
        try:
            data = {
                "ui_language": self.ui_language_var.get(),
                "ui_theme": self.ui_theme_var.get(),
                "donate_url": str(self._settings.get("donate_url", DEFAULT_DONATE_URL)),
            }
            self._settings_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            # Non-fatal
            pass

    def _rebuild_ui(self) -> None:
        if self._worker and self._worker.is_alive():
            messagebox.showinfo(APP_NAME, "Bitte zuerst Stop drücken (oder warten, bis der Lauf fertig ist).")
            return
        for child in list(self.winfo_children()):
            # keep menu bar on root; child widgets are frames
            child.destroy()
        self.title(self._t("title"))
        self._build_menu()
        self._build_ui()
        self._apply_theme(self.ui_theme_var.get())

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)

        settings_menu = tk.Menu(menubar, tearoff=False)

        theme_menu = tk.Menu(settings_menu, tearoff=False)
        theme_menu.add_radiobutton(
            label=self._t("menu_theme_light"),
            variable=self.ui_theme_var,
            value=UiTheme.LIGHT,
            command=self._on_theme_changed,
        )
        theme_menu.add_radiobutton(
            label=self._t("menu_theme_dark"),
            variable=self.ui_theme_var,
            value=UiTheme.DARK,
            command=self._on_theme_changed,
        )
        settings_menu.add_cascade(label=self._t("menu_theme"), menu=theme_menu)

        lang_menu = tk.Menu(settings_menu, tearoff=False)
        lang_menu.add_radiobutton(
            label="Deutsch",
            variable=self.ui_language_var,
            value=UiLanguage.DE,
            command=self._on_language_changed,
        )
        lang_menu.add_radiobutton(
            label="English",
            variable=self.ui_language_var,
            value=UiLanguage.EN,
            command=self._on_language_changed,
        )
        settings_menu.add_cascade(label=self._t("menu_lang"), menu=lang_menu)

        menubar.add_cascade(label=self._t("menu_settings"), menu=settings_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label=self._t("menu_faq"), command=self._open_faq)
        help_menu.add_command(label=self._t("menu_about"), command=self._show_about)
        help_menu.add_separator()
        help_menu.add_command(label=self._t("menu_donate"), command=self._open_donate)
        menubar.add_cascade(label=self._t("menu_help"), menu=help_menu)

        self.config(menu=menubar)

    def _on_theme_changed(self) -> None:
        self._apply_theme(self.ui_theme_var.get())
        self._save_settings()

    def _on_language_changed(self) -> None:
        self._save_settings()
        self._rebuild_ui()

    def _open_faq(self) -> None:
        faq_path = self._base_dir / FAQ_FILENAME
        if not faq_path.exists():
            messagebox.showinfo(APP_NAME, f"Nicht gefunden: {faq_path}")
            return
        try:
            content = faq_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_NAME, str(exc))
            return

        win = tk.Toplevel(self)
        win.title("FAQ (English)")
        win.minsize(720, 520)

        frame = ttk.Frame(win, padding=10)
        frame.pack(fill=BOTH, expand=True)

        text = tk.Text(frame, wrap="word")
        text.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(frame, command=text.yview)
        scroll.pack(side=RIGHT, fill=Y)
        text.configure(yscrollcommand=scroll.set)

        btn_row = ttk.Frame(win, padding=(10, 0, 10, 10))
        btn_row.pack(fill=X)
        ttk.Button(btn_row, text=self._t("close"), command=win.destroy).pack(side=RIGHT)

        # Basic Markdown-ish rendering: headings, bullets, fenced code blocks.
        text.tag_configure("h1", font=("Segoe UI", 14, "bold"))
        text.tag_configure("h2", font=("Segoe UI", 12, "bold"))
        text.tag_configure("bullet", lmargin1=18, lmargin2=36)
        text.tag_configure("code", font=("Consolas", 10), background="#f4f4f4")

        in_code = False
        for raw_line in content.splitlines():
            line = raw_line.rstrip("\r\n")
            if line.strip().startswith("```"):
                in_code = not in_code
                continue

            if in_code:
                text.insert(END, line + "\n", ("code",))
                continue

            if line.startswith("# "):
                text.insert(END, line[2:].strip() + "\n", ("h1",))
                text.insert(END, "\n")
                continue
            if line.startswith("## "):
                text.insert(END, line[3:].strip() + "\n", ("h2",))
                continue
            if line.startswith("- "):
                text.insert(END, "• " + line[2:].strip() + "\n", ("bullet",))
                continue

            text.insert(END, line + "\n")

        text.configure(state=DISABLED)

    def _show_about(self) -> None:
        messagebox.showinfo(APP_NAME, self._t("about"))

    def _open_donate(self) -> None:
        url = str(self._settings.get("donate_url", "")).strip()
        if not url:
            messagebox.showinfo(APP_NAME, self._t("donate_missing"))
            return
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_NAME, str(exc))

    def _apply_theme(self, theme: str) -> None:
        style = ttk.Style(self)

        def _set_default_light() -> None:
            # Prefer native on Windows if available
            for candidate in ("vista", "xpnative", "winnative", "default"):
                if candidate in style.theme_names():
                    try:
                        style.theme_use(candidate)
                        return
                    except Exception:
                        continue

        if theme == UiTheme.DARK:
            if "clam" in style.theme_names():
                try:
                    style.theme_use("clam")
                except Exception:
                    _set_default_light()
            else:
                _set_default_light()

            bg = "#2b2b2b"
            fg = "#f0f0f0"
            field = "#3c3f41"
            select_bg = "#4b6eaf"

            try:
                self.configure(background=bg)
            except Exception:
                pass

            style.configure(".", background=bg, foreground=fg)
            style.configure("TFrame", background=bg)
            style.configure("TLabel", background=bg, foreground=fg)
            style.configure("TLabelframe", background=bg, foreground=fg)
            style.configure("TLabelframe.Label", background=bg, foreground=fg)
            style.configure("TCheckbutton", background=bg, foreground=fg)
            style.configure("TRadiobutton", background=bg, foreground=fg)
            style.configure("TButton", background=bg, foreground=fg)
            style.configure("TEntry", fieldbackground=field, foreground=fg)

            try:
                self.log.configure(background=field, foreground=fg, insertbackground=fg, selectbackground=select_bg)
            except Exception:
                pass
        else:
            _set_default_light()
            try:
                self.configure(background=None)
            except Exception:
                pass
            try:
                self.log.configure(background="white", foreground="black", insertbackground="black")
            except Exception:
                pass

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill=BOTH, expand=True)

        # Paths
        paths = ttk.LabelFrame(top, text=self._t("folders"), padding=10)
        paths.pack(fill=X)

        in_row = ttk.Frame(paths)
        in_row.pack(fill=X)
        ttk.Label(in_row, text=self._t("wav_folder")).pack(side=LEFT)
        ttk.Entry(in_row, textvariable=self.input_folder_var).pack(side=LEFT, fill=X, expand=True, padx=8)
        ttk.Button(in_row, text=self._t("pick"), command=self._pick_input).pack(side=RIGHT)

        out_row = ttk.Frame(paths)
        out_row.pack(fill=X, pady=(8, 0))
        ttk.Label(out_row, text=self._t("output_folder")).pack(side=LEFT)
        ttk.Entry(out_row, textvariable=self.output_folder_var).pack(side=LEFT, fill=X, expand=True, padx=8)
        ttk.Button(out_row, text=self._t("pick"), command=self._pick_output).pack(side=RIGHT)

        opt_row = ttk.Frame(paths)
        opt_row.pack(fill=X, pady=(8, 0))
        ttk.Checkbutton(opt_row, text=self._t("include_subfolders"), variable=self.recursive_var).pack(side=LEFT)
        ttk.Checkbutton(opt_row, text=self._t("preserve_structure"), variable=self.preserve_structure_var).pack(side=LEFT, padx=12)

        # Settings
        settings = ttk.LabelFrame(top, text=self._t("settings"), padding=10)
        settings.pack(fill=X, pady=(10, 0))

        lang_row = ttk.Frame(settings)
        lang_row.pack(fill=X)
        ttk.Label(lang_row, text=self._t("language")).pack(side=LEFT)
        ttk.OptionMenu(lang_row, self.language_var, self.language_var.get(), *SUPPORTED_LANGUAGES).pack(side=LEFT, padx=8)
        ttk.Label(lang_row, text=self._t("gesture")).pack(side=LEFT, padx=(16, 0))
        ttk.Entry(lang_row, textvariable=self.gesture_var, width=12).pack(side=LEFT, padx=8)

        # Text source
        text_frame = ttk.LabelFrame(top, text=self._t("text_source"), padding=10)
        text_frame.pack(fill=X, pady=(10, 0))

        rb_row = ttk.Frame(text_frame)
        rb_row.pack(fill=X)
        ttk.Radiobutton(
            rb_row,
            text=self._t("txt"),
            value=TextSource.SIDECAR_TXT,
            variable=self.text_source_var,
            command=self._sync_text_source_state,
        ).pack(anchor="w")
        ttk.Radiobutton(
            rb_row,
            text=self._t("filename"),
            value=TextSource.FILENAME,
            variable=self.text_source_var,
            command=self._sync_text_source_state,
        ).pack(anchor="w")
        ttk.Radiobutton(
            rb_row,
            text=self._t("fixed"),
            value=TextSource.FIXED,
            variable=self.text_source_var,
            command=self._sync_text_source_state,
        ).pack(anchor="w")
        ttk.Radiobutton(
            rb_row,
            text=self._t("mapping"),
            value=TextSource.MAPPING_FILE,
            variable=self.text_source_var,
            command=self._sync_text_source_state,
        ).pack(anchor="w")

        fixed_row = ttk.Frame(text_frame)
        fixed_row.pack(fill=X, pady=(6, 0))
        ttk.Label(fixed_row, text=self._t("fixed_text")).pack(side=LEFT)
        self.fixed_entry = ttk.Entry(fixed_row, textvariable=self.fixed_text_var)
        self.fixed_entry.pack(side=LEFT, fill=X, expand=True, padx=8)

        mapping_row = ttk.Frame(text_frame)
        mapping_row.pack(fill=X, pady=(6, 0))
        ttk.Label(mapping_row, text=self._t("mapping_file")).pack(side=LEFT)
        self.mapping_entry = ttk.Entry(mapping_row, textvariable=self.mapping_file_var)
        self.mapping_entry.pack(side=LEFT, fill=X, expand=True, padx=8)
        ttk.Button(mapping_row, text=self._t("pick"), command=self._pick_mapping_file).pack(side=RIGHT)

        # Actions + progress
        actions = ttk.Frame(top)
        actions.pack(fill=X, pady=(10, 0))
        self.start_btn = ttk.Button(actions, text=self._t("generate"), command=self._start)
        self.start_btn.pack(side=LEFT)
        self.test_btn = ttk.Button(actions, text=self._t("test_mapping"), command=self._test_mapping)
        self.test_btn.pack(side=LEFT, padx=8)
        self.pause_btn = ttk.Button(actions, text=self._t("pause"), command=self._toggle_pause, state=DISABLED)
        self.pause_btn.pack(side=LEFT)
        self.stop_btn = ttk.Button(actions, text=self._t("stop"), command=self._stop, state=DISABLED)
        self.stop_btn.pack(side=LEFT)

        self.progress = ttk.Progressbar(actions, mode="determinate")
        self.progress.pack(side=RIGHT, fill=X, expand=True, padx=(12, 0))
        self.progress_label = ttk.Label(actions, text="0/0")
        self.progress_label.pack(side=RIGHT, padx=(0, 8))

        # Log
        log_frame = ttk.LabelFrame(top, text=self._t("log"), padding=10)
        log_frame.pack(fill=BOTH, expand=True, pady=(10, 0))

        self.log = tk.Text(log_frame, height=12, wrap="word")
        self.log.pack(side=LEFT, fill=BOTH, expand=True)
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        scroll.pack(side=RIGHT, fill=Y)
        self.log.configure(yscrollcommand=scroll.set)

        self._sync_text_source_state()

    def _sync_text_source_state(self) -> None:
        source = self.text_source_var.get()
        self.fixed_entry.configure(state=NORMAL if source == TextSource.FIXED else DISABLED)
        self.mapping_entry.configure(state=NORMAL if source == TextSource.MAPPING_FILE else DISABLED)

    def _pick_input(self) -> None:
        folder = filedialog.askdirectory(title=self._t("wav_folder"))
        if folder:
            self.input_folder_var.set(folder)
            if not self.output_folder_var.get().strip():
                self.output_folder_var.set(folder)

    def _pick_output(self) -> None:
        folder = filedialog.askdirectory(title=self._t("output_folder"))
        if folder:
            self.output_folder_var.set(folder)

    def _pick_mapping_file(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title=self._t("mapping_file"),
            filetypes=[
                ("CSV/TSV", "*.csv *.tsv *.txt"),
                ("Alle Dateien", "*.*"),
            ],
        )
        if not file_paths:
            return

        self._mapping_files = [Path(p) for p in file_paths]
        if len(self._mapping_files) == 1:
            self.mapping_file_var.set(str(self._mapping_files[0]))
        else:
            first = self._mapping_files[0]
            if self.ui_language_var.get() == UiLanguage.EN:
                self.mapping_file_var.set(f"{len(self._mapping_files)} files selected (e.g. {first.name})")
            else:
                self.mapping_file_var.set(f"{len(self._mapping_files)} Dateien ausgewählt (z.B. {first.name})")

    def _append_log(self, text: str) -> None:
        self.log.insert(END, text + "\n")
        self.log.see(END)

    def _validate_prereqs(self) -> bool:
        if not self.exe_path.exists():
            messagebox.showerror(
                "Fehler",
                f"Nicht gefunden: {self.exe_path}\n\n" "Erwartet wird der Ordner 'LipGenerator' neben lip_gui.py.",
            )
            return False
        if not self.cdf_path.exists():
            messagebox.showerror(
                "Fehler",
                f"Nicht gefunden: {self.cdf_path}\n\n" "FonixData.cdf muss im gleichen Ordner wie LipGenerator.exe liegen.",
            )
            return False
        return True

    def _start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        if not self._validate_prereqs():
            return

        input_folder = Path(self.input_folder_var.get().strip())
        output_folder = Path(self.output_folder_var.get().strip())
        if not input_folder.exists():
            messagebox.showerror("Fehler", self._t("err_need_wav"))
            return
        if not output_folder:
            messagebox.showerror("Fehler", self._t("err_need_out"))
            return

        self.log.delete("1.0", END)
        self._stop_requested.clear()
        self._pause_event.set()
        self.start_btn.configure(state=DISABLED)
        self.stop_btn.configure(state=NORMAL)
        self.pause_btn.configure(state=NORMAL, text="Pause")
        self.test_btn.configure(state=DISABLED)

        # Build jobs (may raise for missing txt etc.)
        try:
            jobs = build_jobs(
                input_folder=input_folder,
                output_folder=output_folder,
                recursive=self.recursive_var.get(),
                preserve_structure=self.preserve_structure_var.get(),
                text_source=self.text_source_var.get(),
                fixed_text=self.fixed_text_var.get(),
                mapping_file=self._mapping_files[0] if (self.text_source_var.get() == TextSource.MAPPING_FILE and len(self._mapping_files) == 1) else None,
            )
        except Exception as exc:  # noqa: BLE001
            self.start_btn.configure(state=NORMAL)
            self.stop_btn.configure(state=DISABLED)
            messagebox.showerror("Fehler", str(exc))
            return

        # For mapping mode, support multiple mapping files by building a merged mapping and replacing job texts.
        if self.text_source_var.get() == TextSource.MAPPING_FILE and len(self._mapping_files) > 1:
            try:
                mapping = load_text_mappings(self._mapping_files)
            except Exception as exc:  # noqa: BLE001
                self.start_btn.configure(state=NORMAL)
                self.stop_btn.configure(state=DISABLED)
                messagebox.showerror("Fehler", str(exc))
                return

            remapped: list[Job] = []
            for j in jobs:
                text = ""
                for key in mapping_keys_from_wav(j.wav_path):
                    text = mapping.get(key, "").strip()
                    if text:
                        break
                if not text:
                    text = text_from_filename(j.wav_path)
                    note = "WARN: Kein Mapping-Eintrag gefunden, nutze Dateiname als Text."
                else:
                    note = ""
                remapped.append(Job(wav_path=j.wav_path, lip_path=j.lip_path, text=text, note=note))
            jobs = remapped

        if not jobs:
            self.start_btn.configure(state=NORMAL)
            self.stop_btn.configure(state=DISABLED)
            messagebox.showinfo("Info", self._t("info_no_wav"))
            return

        self.progress.configure(maximum=len(jobs), value=0)
        self.progress_label.configure(text=f"0/{len(jobs)}")

        language = self.language_var.get().strip() or "USEnglish"
        gesture = self.gesture_var.get().strip()

        self._worker = threading.Thread(
            target=self._worker_run,
            args=(jobs, language, gesture),
            daemon=True,
        )
        self._worker.start()

    def _stop(self) -> None:
        self._stop_requested.set()
        self._pause_event.set()
        self._append_log(self._t("stop_requested"))

    def _toggle_pause(self) -> None:
        if self.pause_btn.cget("state") == DISABLED:
            return
        if self._pause_event.is_set():
            self._pause_event.clear()
            self.pause_btn.configure(text=self._t("resume"))
            self._append_log(self._t("paused"))
        else:
            self._pause_event.set()
            self.pause_btn.configure(text=self._t("pause"))
            self._append_log(self._t("resumed"))

    def _test_mapping(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        input_folder = Path(self.input_folder_var.get().strip())
        if not input_folder.exists():
            messagebox.showerror("Fehler", "Bitte einen gültigen WAV-Ordner auswählen.")
            return

        if not self._mapping_files:
            messagebox.showerror("Fehler", "Bitte eine Mapping-Datei auswählen.")
            return

        try:
            mapping = load_text_mappings(self._mapping_files)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Fehler", str(exc))
            return

        wav_files = find_wav_files(input_folder, self.recursive_var.get())
        if not wav_files:
            messagebox.showinfo("Info", "Keine .wav Dateien gefunden.")
            return

        sample_n = 10 if len(wav_files) >= 10 else len(wav_files)
        sample = random.sample(wav_files, k=sample_n)

        self.log.delete("1.0", END)
        self._stop_requested.clear()
        self._pause_event.set()
        self.start_btn.configure(state=DISABLED)
        self.test_btn.configure(state=DISABLED)
        self.stop_btn.configure(state=NORMAL)
        self.pause_btn.configure(state=DISABLED, text="Pause")

        self.progress.configure(maximum=sample_n, value=0)
        self.progress_label.configure(text=f"0/{sample_n}")

        self._worker = threading.Thread(
            target=self._worker_test_mapping,
            args=(mapping, wav_files, sample),
            daemon=True,
        )
        self._worker.start()

    def _worker_test_mapping(self, mapping: dict[str, str], all_wavs: list[Path], sample: list[Path]) -> None:
        total = len(all_wavs)
        found_total = 0
        missing_total = 0
        for wav in all_wavs:
            if any(mapping.get(k, "").strip() for k in mapping_keys_from_wav(wav)):
                found_total += 1
            else:
                missing_total += 1

        self._queue.put(("log", f"Mapping-Einträge: {len(mapping)}"))
        self._queue.put(("log", f"WAVs gefunden: {total} (Match: {found_total}, Kein Match: {missing_total})"))
        self._queue.put(("log", "--- Stichprobe (10 zufällige Dateien) ---"))

        for idx, wav_path in enumerate(sample, start=1):
            if self._stop_requested.is_set():
                self._queue.put(("log", "Abgebrochen."))
                break

            keys = mapping_keys_from_wav(wav_path)
            text = ""
            used_key = ""
            for k in keys:
                t = mapping.get(k, "").strip()
                if t:
                    text = t
                    used_key = k
                    break

            if text:
                preview = text.replace("\n", " ").strip()
                if len(preview) > 120:
                    preview = preview[:117] + "..."
                self._queue.put(("log", f"[{idx}/{len(sample)}] OK   {wav_path.name}  (Key: {used_key})"))
                self._queue.put(("log", f"        → {preview}"))
            else:
                self._queue.put(("log", f"[{idx}/{len(sample)}] FEHL {wav_path.name}  (Keys: {', '.join(keys)})"))

            self._queue.put(("progress", str(idx)))

        self._queue.put(("done", "Mapping-Test fertig."))

    def _worker_run(self, jobs: list[Job], language: str, gesture: str) -> None:
        total = len(jobs)
        ok = 0
        failed = 0

        for idx, job in enumerate(jobs, start=1):
            if self._stop_requested.is_set():
                self._queue.put(("log", f"Abgebrochen. Fertig: {idx-1}/{total}"))
                break

            # Pause point between files
            while not self._pause_event.is_set() and not self._stop_requested.is_set():
                self._stop_requested.wait(timeout=0.2)

            self._queue.put(("log", f"[{idx}/{total}] {job.wav_path.name} → {job.lip_path.name}"))
            if job.note:
                self._queue.put(("log", f"  {job.note}"))

            try:
                cp, was_killed = run_lipgenerator_background(
                    lipgenerator_dir=self.lipgenerator_dir,
                    exe_path=self.exe_path,
                    job=job,
                    language=language,
                    gesture_exaggeration=gesture,
                    stop_event=self._stop_requested,
                    pause_event=self._pause_event,
                )
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self._queue.put(("log", f"  FEHLER: {exc}"))
                self._queue.put(("progress", str(idx)))
                continue

            if was_killed and self._stop_requested.is_set():
                failed += 1
                self._queue.put(("log", "  Abgebrochen (Prozess beendet)."))
                self._queue.put(("progress", str(idx)))
                break

            if cp.returncode == 0 and job.lip_path.exists():
                ok += 1
            else:
                failed += 1

            if cp.stdout.strip():
                self._queue.put(("log", "  " + cp.stdout.strip().replace("\n", "\n  ")))
            if cp.stderr.strip():
                self._queue.put(("log", "  " + cp.stderr.strip().replace("\n", "\n  ")))

            self._queue.put(("progress", str(idx)))

        self._queue.put(("done", f"Fertig. OK: {ok}, Fehler: {failed}"))

    def _drain_queue(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "progress":
                    current = int(payload)
                    maximum = int(self.progress.cget("maximum") or 0)
                    self.progress.configure(value=current)
                    self.progress_label.configure(text=f"{current}/{maximum}")
                elif kind == "done":
                    self._append_log(payload)
                    self.start_btn.configure(state=NORMAL)
                    self.test_btn.configure(state=NORMAL)
                    self.pause_btn.configure(state=DISABLED, text="Pause")
                    self.stop_btn.configure(state=DISABLED)
        except queue.Empty:
            pass
        self.after(120, self._drain_queue)


def main() -> None:
    # Helps Tk look correct on Windows high DPI
    try:
        from ctypes import windll  # type: ignore

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
