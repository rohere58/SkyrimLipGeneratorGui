# Lip GUI (Skyrim)

A small GUI wrapper to run `LipGenerator.exe` in batch mode on all `.wav` files in a folder (Skyrim lip generation).

## Requirements

- Windows
- A `LipGenerator/` folder next to `lip_gui.py` that contains:
	- `LipGenerator.exe`
	- `FonixData.cdf`
- Python (this workspace already contains a configured `.venv`)

Tip: If you have Skyrim Special Edition installed via Steam, these files are often located under:

```text
...\steam\steamapps\common\Skyrim Special Edition\Tools\LipGen\LipGenerator
```

## Run from source

From the workspace root:

```powershell
".\.venv\Scripts\python.exe" .\lip_gui.py
```

## (Optional) Windows EXE

If you built it locally, the EXE is located at:

- `dist/LipGUI.exe`

Important: put the `LipGenerator/` folder (with `LipGenerator.exe` + `FonixData.cdf`) **next to** `LipGUI.exe`.
Example layout:

```text
dist/
	LipGUI.exe
	LipGenerator/
		LipGenerator.exe
		FonixData.cdf
```

## Sharing / GitHub Releases

You can publish the tool (GUI/EXE/FAQ) on GitHub.

Important: `LipGenerator.exe` and `FonixData.cdf` are very likely third‑party files.
Do **not** include them in your GitHub repo or releases unless you explicitly have the rights to redistribute them.
Instead:

- Releases contain `LipGUI.exe`, `FAQ_EN.md`, `settings.json`
- Users place their own `LipGenerator/` (with `LipGenerator.exe` + `FonixData.cdf`) next to the EXE

### Automated Windows builds (GitHub Actions)

When you push a tag like `v0.3.0`, GitHub Actions automatically builds the EXE and attaches a ZIP to the GitHub Release.

## Important: text is required

`LipGenerator.exe` always needs the spoken text in addition to the WAV file.
The GUI supports multiple text sources:

- **From `.txt`**: for `foo.wav` there must be a `foo.txt` (content = spoken text)
- **From filename**: `Hello_World.wav` → `Hello World`
- **Fixed text**: same text for all files
- **From a mapping file (CSV/TSV)**: e.g. `FormID` → `Text`

### Mapping file (CSV/TSV)

If your text only exists inside the translated `*.esp`, the usual approach is:

1. Export the dialogue/subtitle text from the ESP into a table (CSV/TSV).
2. Ensure each voice line has an ID that matches your WAV filename.

In Skyrim, voice files are often named after the **INFO FormID** (8 hex characters), e.g. `000A1234.wav`.
Depending on the export tool, the key might be the **WAV filename** or even a **path** — the GUI normalizes this down to the filename automatically.

**Example format (TSV recommended):**

```text
000A1234	Hello, traveler.
000A1235	Welcome to Whiterun.
```

The GUI tries to use the first 8 hex characters as the key when the filename starts with them.
If no mapping entry is found, it falls back to “Text from filename” and writes a warning to the log.

### Practical workflow (xTranslator + LazyVoiceFinder)

- **Find WAVs:** LazyVoiceFinder can scan your voice assets and export CSV.
- **Get text:** Export your translated lines from xTranslator (or your workflow).
- **Build mapping:** ideally one file that contains *one* key per voice line + the text.

The GUI works with many CSV/TSV exports as long as it can find columns similar to:

- Key: `FormID` or `FileName`/`WAV`/`Path`
- Text: `Text`/`Subtitle` or `Translated`/`Target`

Optional (but helpful if filenames are not unique):

- Folder/voice: `Voice Type`

If `Voice Type` exists, the GUI also tries composite keys like `voicetype/filename`.

### Merging CSV exports (if you exported per folder)

If you exported one LazyVoiceFinder CSV per subfolder, you can combine them into a single mapping:

- **Simplest:** In the GUI, you can select **multiple CSVs at once** for the mapping input (the GUI merges them internally).

1. Put all exported `*.csv` files into **one** folder, e.g. `exports/`
2. Run:

```powershell
".\.venv\Scripts\python.exe" .\merge_lazyvoice_csv.py .\exports -o .\all_voices.tsv
```

3. In the GUI, choose `all_voices.tsv` as your mapping file.

## Output

- Output files are written as `.lip`.
- If **Preserve folder structure** is enabled, subfolders are recreated under the output folder.
