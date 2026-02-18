# LipGUI – FAQ (English)

## What is this tool?

LipGUI is a small batch GUI that calls `LipGenerator.exe` to generate Skyrim `.lip` files for many `.wav` files.

## Why does it need text?

`LipGenerator.exe` requires the spoken text in addition to the WAV file. LipGUI can load the text from a mapping CSV/TSV (e.g., exported via LazyVoiceFinder).

## My mapping is a CSV with many columns. Will it work?

Yes, LipGUI tries to auto-detect common columns:

- Key: `Voice Type` (optional), `File Name` / `WAV` / `Path`, or `FormID`
- Text: `Dialogue 2 - German`, `Text`, `Subtitle`, `Translated`, `Target`

You can also select multiple CSV files at once; LipGUI merges them automatically.

## Why do I see missing mappings?

If a WAV filename does not match any key from the mapping file, LipGUI falls back to using the filename as text and prints a warning in the log.

## Can I pause/stop the run?

Yes:

- **Pause** stops between files (and keeps the UI responsive).
- **Stop** cancels the current file and ends the batch.

## Where are settings stored?

Next to the executable/script in `settings.json` (theme + UI language). If you want a Donate link, set `donate_url` there.
