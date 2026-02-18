## Download
- **Windows:** `LipGUI-windows.zip` (enthält `LipGUI.exe`)

## Enthalten im ZIP
- `LipGUI.exe`
- `FAQ_EN.md`
- `settings.json`
- `LipGenerator/PUT_LipGenerator_FILES_HERE.txt` (Platzhalter)

## Wichtig: Drittanbieter-Dateien (nicht enthalten)
Dieses Release enthält **nicht** `LipGenerator.exe` und `FonixData.cdf` (vermutlich Drittanbieter-Dateien).

Du musst diese Dateien selbst bereitstellen und so ablegen:

```text
LipGUI.exe
LipGenerator/
  LipGenerator.exe
  FonixData.cdf
```

## Quickstart
1. ZIP entpacken
2. `LipGenerator.exe` + `FonixData.cdf` wie oben in `LipGenerator/` ablegen
3. `LipGUI.exe` starten
4. Input-Ordner (WAV), Output-Ordner wählen, Textquelle (z.B. Mapping CSV/TSV) auswählen, **Start**

## Highlights
- Batch-Generierung von `.lip` aus `.wav` via `LipGenerator.exe`
- Textquelle via Mapping (CSV/TSV), inkl. LazyVoiceFinder/xTranslator-Workflows
- Mehrere Mapping-Dateien auswählbar (internes Merge) + „Mapping testen“
- Pause/Resume/Stop, ohne nervige Konsolenfenster
- UI: DE/EN + Light/Dark
