from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


REQUIRED_COLUMNS = {
    "voice type": "Voice Type",
    "file name": "File Name",
    "dialogue 2 - german": "Dialogue 2 - German",
}


def normalize_header(name: str) -> str:
    return name.strip().lower()


def detect_delimiter(text: str) -> str:
    # LazyVoiceFinder exports are typically comma-separated, but be tolerant.
    if "\t" in text:
        return "\t"
    # If semicolons dominate and commas are rare, prefer ';'
    if text.count(";") > text.count(","):
        return ";"
    return ","


@dataclass
class Row:
    voice_type: str
    file_name: str
    text: str

    @property
    def key(self) -> tuple[str, str]:
        # Case-insensitive and stable.
        return (self.voice_type.strip().lower(), Path(self.file_name.strip()).name.lower())


def read_lazyvoice_csv(path: Path) -> list[Row]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    delim = detect_delimiter(raw)
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if not lines:
        return []

    reader = csv.reader(lines, delimiter=delim)
    try:
        header_row = next(reader)
    except StopIteration:
        return []

    header_norm = [normalize_header(h) for h in header_row]

    def find_col(target_norm: str) -> int:
        for i, col in enumerate(header_norm):
            if col == target_norm:
                return i
        raise ValueError(
            f"In {path.name} fehlt die Spalte '{REQUIRED_COLUMNS[target_norm]}'. Gefunden: {header_row}"
        )

    idx_voice = find_col("voice type")
    idx_file = find_col("file name")
    idx_text = find_col("dialogue 2 - german")

    out: list[Row] = []
    for row in reader:
        if not row:
            continue
        # Pad short rows
        if len(row) <= max(idx_voice, idx_file, idx_text):
            row = row + [""] * (max(idx_voice, idx_file, idx_text) + 1 - len(row))

        voice_type = (row[idx_voice] or "").strip()
        file_name = (row[idx_file] or "").strip()
        text = (row[idx_text] or "").strip()

        if not voice_type or not file_name:
            continue
        if not text:
            continue

        out.append(Row(voice_type=voice_type, file_name=file_name, text=text))

    return out


def merge_rows(rows: list[Row]) -> dict[tuple[str, str], Row]:
    merged: dict[tuple[str, str], Row] = {}
    for r in rows:
        k = r.key
        if k not in merged:
            merged[k] = r
            continue
        # Prefer longer (usually more complete) text.
        if len(r.text) > len(merged[k].text):
            merged[k] = r
    return merged


def write_tsv(rows: list[Row], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Voice Type", "File Name", "Dialogue 2 - German"])
        for r in rows:
            writer.writerow([r.voice_type, Path(r.file_name).name, r.text])


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge LazyVoiceFinder CSV exports into one TSV mapping file.")
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Ordner mit *.csv Dateien (Default: aktueller Ordner)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="all_voices.tsv",
        help="Output TSV Pfad (Default: all_voices.tsv)",
    )
    args = parser.parse_args()

    in_dir = Path(args.input).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()

    if not in_dir.exists() or not in_dir.is_dir():
        raise SystemExit(f"Input ist kein Ordner: {in_dir}")

    csv_files = sorted(in_dir.glob("*.csv"), key=lambda p: p.name.lower())
    if not csv_files:
        raise SystemExit(f"Keine *.csv Dateien gefunden in: {in_dir}")

    all_rows: list[Row] = []
    for p in csv_files:
        all_rows.extend(read_lazyvoice_csv(p))

    merged = merge_rows(all_rows)
    out_rows = sorted(merged.values(), key=lambda r: (r.voice_type.lower(), Path(r.file_name).name.lower()))

    write_tsv(out_rows, out_path)

    total_in = len(all_rows)
    total_out = len(out_rows)
    print(f"CSV Dateien: {len(csv_files)}")
    print(f"Zeilen gelesen (mit Text): {total_in}")
    print(f"Einträge nach Merge (unique Voice+File): {total_out}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
