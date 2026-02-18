# Lip GUI (Skyrim)

Kleine grafische Oberfläche, um `LipGenerator.exe` stapelweise auf alle `.wav` Dateien in einem Ordner anzuwenden.

## Voraussetzungen

- Windows
- Der Ordner `LipGenerator/` liegt neben `lip_gui.py` und enthält:
	- `LipGenerator.exe`
	- `FonixData.cdf`
- Python (im Workspace ist bereits eine `.venv` konfiguriert)

## Start

Im Workspace-Root ausführen:

```powershell
".\.venv\Scripts\python.exe" .\lip_gui.py
```

## (Optional) Windows-EXE

Im Ordner `dist/` liegt (wenn gebaut) die EXE:

- `dist/LipGUI.exe`

Wichtig: Lege den Ordner `LipGenerator/` (mit `LipGenerator.exe` + `FonixData.cdf`) **neben** `LipGUI.exe`.
Also z.B.:

```text
dist/
	LipGUI.exe
	LipGenerator/
		LipGenerator.exe
		FonixData.cdf
```

## Weitergeben / GitHub Releases

Du kannst das Tool (GUI/EXE/FAQ) auf GitHub veröffentlichen.

Wichtig: `LipGenerator.exe` und `FonixData.cdf` sind sehr wahrscheinlich Drittanbieter-Dateien.
Bitte **nicht** mit ins GitHub-Repo oder Release packen, falls du dafür keine expliziten Rechte hast.
Stattdessen:

- Release enthält `LipGUI.exe`, `FAQ_EN.md`, `settings.json`
- Nutzer legen selbst `LipGenerator/` (mit `LipGenerator.exe` + `FonixData.cdf`) neben die EXE

### Automatischer Windows-Build (GitHub Actions)

Wenn du einen Tag wie `v0.3.0` pushst, baut GitHub Actions automatisch die EXE und hängt ein ZIP ans Release.

## Wichtig: Text wird benötigt

`LipGenerator.exe` benötigt neben der WAV-Datei immer auch den gesprochenen Text.
Die GUI bietet deshalb mehrere Varianten:

- **Aus `.txt`**: pro `foo.wav` muss es `foo.txt` geben (Inhalt = gesprochener Text)
- **Aus Dateiname**: `Hello_World.wav` → `Hello World`
- **Fester Text**: gleicher Text für alle Dateien
- **Aus Mapping-Datei (CSV/TSV)**: z.B. `FormID` → `Text`

### Mapping-Datei (CSV/TSV)

Wenn du den Text „nur“ in der übersetzten `*.esp` hast, ist der übliche Weg:

1. Exportiere die Dialog-/Untertiteltexte aus der ESP in eine Tabelle (CSV/TSV).
2. Stelle sicher, dass du pro Voice-Line eine ID hast, die zu deinem WAV-Dateinamen passt.

In Skyrim sind Voice-Dateien häufig nach der **FormID** der `INFO`-Zeile benannt (8 Hex-Zeichen), z.B. `000A1234.wav`.
Je nach Tool-Export kann der Schlüssel aber auch der **WAV-Dateiname** oder sogar ein **Pfad** sein — die GUI reduziert das automatisch auf den Dateinamen.

**Format-Beispiel (TSV empfohlen):**

```text
000A1234	Hallo, Reisender.
000A1235	Willkommen in Weißlauf.
```

Die GUI versucht bei WAV-Dateinamen, die mit 8 Hex-Zeichen anfangen, automatisch diese 8 Zeichen als Schlüssel zu nutzen.
Wenn kein Eintrag gefunden wird, fällt sie auf „Text aus Dateiname“ zurück und schreibt einen Warnhinweis ins Log.

### Praktischer Workflow (xTranslator + LazyVoiceFinder)

- **WAVs finden:** LazyVoiceFinder kann deine Voice-Dateien finden und als CSV exportieren.
- **Text bekommen:** Exportiere aus xTranslator (oder aus deinem Workflow) die übersetzten Untertitel/Zeilen.
- **Mapping erstellen:** Ideal ist eine Datei, die pro Voice-Line *einen* Schlüssel und *den* Text enthält.

Die GUI kommt mit typischen CSV/TSV-Exporten klar, solange irgendwo Spalten wie diese vorkommen:

- Schlüssel: `FormID` oder `FileName`/`WAV`/`Path`
- Text: `Text`/`Subtitle` oder `Translated`/`Target`

Optional (aber hilfreich, wenn Dateinamen nicht eindeutig sind):

- Ordner/Voice: `Voice Type`

Wenn `Voice Type` vorhanden ist, nutzt die GUI zusätzlich Schlüssel wie `voicetype/filename`.

### CSVs zusammenführen (wenn du pro Ordner exportierst)

Wenn du LazyVoiceFinder bisher pro Unterordner eine eigene CSV exportierst, kannst du sie automatisch zu einer Mapping-Datei zusammenführen:

- **Einfachste Variante:** In der GUI bei der Mapping-Datei **mehrere CSVs gleichzeitig auswählen** (die GUI merged intern automatisch).

1. Lege alle exportierten `*.csv` Dateien in **einen** Ordner, z.B. `exports/`
2. Führe aus:

```powershell
".\.venv\Scripts\python.exe" .\merge_lazyvoice_csv.py .\exports -o .\all_voices.tsv
```

3. Wähle in der GUI als Mapping-Datei dann `all_voices.tsv` aus.

## Output

- Output-Dateien werden als `.lip` geschrieben.
- Bei aktivierter Option **Ordnerstruktur beibehalten** werden Unterordner unter dem Output-Ordner nachgebildet.
