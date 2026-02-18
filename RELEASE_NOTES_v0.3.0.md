## Download
- **Windows:** `LipGUI-windows.zip` (contains `LipGUI.exe`)

## Included in the ZIP
- `LipGUI.exe`
- `FAQ_EN.md`
- `settings.json`
- `LipGenerator/PUT_LipGenerator_FILES_HERE.txt` (placeholder)

## Important: third-party files (not included)
This release does **not** include `LipGenerator.exe` and `FonixData.cdf` (likely third-party files).

You must provide these files yourself and place them like this:

```text
LipGUI.exe
LipGenerator/
  LipGenerator.exe
  FonixData.cdf
```

## Quickstart
1. Unzip the download
2. Put `LipGenerator.exe` + `FonixData.cdf` into `LipGenerator/` as shown above
3. Start `LipGUI.exe`
4. Choose input folder (WAV), output folder, select a text source (e.g. mapping CSV/TSV), then click **Start**

## Highlights
- Batch-generate `.lip` from `.wav` via `LipGenerator.exe`
- Text source via mapping (CSV/TSV), compatible with LazyVoiceFinder/xTranslator workflows
- Select multiple mapping files (internal merge) + “Test mapping”
- Pause/Resume/Stop without annoying console windows
- UI: DE/EN + Light/Dark
