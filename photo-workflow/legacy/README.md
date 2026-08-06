# Synology Photo Ingest + DONE Workflow (v4.2)

EN:
Upscaling RAW/ARW and JPG photo workflow for Sony cameras on Synology NAS.  
Automated ingest, sorting, and cleanup using TEMP_SD, TEMP_IMAGES, and TEMP_DONE.

DE:
Upscaling‑Workflow für RAW/ARW‑ und JPG‑Fotos von Sony‑Kameras auf einem Synology‑NAS.
Automatisierte Aufnahme, Sortierung und Bereinigung mithilfe der Ordner TEMP_SD, TEMP_IMAGES und TEMP_DONE.

-------------------------------------------------------------------------------


## English Usage Instructions

### Step 1 – Copying RAW folders into TEMP_SD

1. Copy the top‑level Sony camera folders (in the original YYYYMMDD date‑only format) into the ingest folder:  
   TEMP_SD (e.g., /volume1/TEMP/TEMP_SD/20250315).

2. Start the script (e.g., via DSM Task Scheduler or CLI via SSH).  
   The script will scan TEMP_SD, TEMP_IMAGES, and TEMP_DONE automatically.

-------------------------------------------------------------------------------


### Phase 1 – Ingest and move to TEMP_IMAGES

During Phase 1, the script:

- Renames the folder from e.g. 20250315 to the standardized date format 2025-03-15.
- Creates an ARW subfolder and moves all *.ARW/*.arw files into it.
- Creates a SAVE subfolder and within it:
  - Generates a ZIP file named SAVE/2025-03-15_ALL_JPG.zip containing all JPG files.
  - Only recreates the ZIP if new JPGs are present or the folder has changed.
- Marks the folder as processed with a .DONE file.
- Attempts to move the processed folder into TEMP_IMAGES:
  - If the target folder TEMP_IMAGES/2025-03-15 does not exist, it is simply moved.
  - If the target exists, it tries to merge the contents using rsync (if available).
  - If the merge fails or rsync is not installed, the script uses a fallback:
    - 2025-03-15_MERGE (and incrementally 2025-03-15_MERGE_2, etc.) are created as alternative destination folders.

-------------------------------------------------------------------------------


### Step 2 – Manual sorting in TEMP_IMAGES

1. In TEMP_IMAGES, manually open each date folder (e.g., 2025-03-15).
2. Delete unwanted, bad, or low‑quality JPG files.
   - You may also rename the folder at this stage to add a descriptive title, e.g.:
     2025-03-15_Hiking_Trip.
3. Once you are satisfied with the JPG selection:
   - If the folder still contains an ARW subfolder (i.e., RAW files are present):
     - Move the entire folder into TEMP_DONE.
   - If the ARW folder is already empty or was deleted:
     - You may move this folder directly into your final photo library (outside of TEMP_*)).

-------------------------------------------------------------------------------


### Phase 2 – Post‑processing in TEMP_DONE

During Phase 2, the script processes all folders inside TEMP_DONE:

- Checks whether the folder contains an ARW subfolder; if not, it is skipped.
- Computes a hash of the JPG content (using folder_hash); if the hash has not changed since the last run, the folder is skipped.
- Moves any existing ZIP files from ARW/ into SAVE/.
- Renames any non‑JPG ZIPs in SAVE/ so that only *_ALL_JPG.zip and *_SORT_ARW.zip remain.
- Compares every *.ARW file with its corresponding JPG:
  - If there is no matching JPG file (upper‑ or lowercase), the ARW file is deleted.
- After cleanup, all remaining ARW files are:
  - Zipped into SAVE/<foldername>_SORT_ARW.zip.
  - Then the ARW subfolder is removed.
- Finally, the new hash is stored in .PROCESSED, and the folder is marked as fully post‑processed.

After Phase 2, the folder can safely be moved from TEMP_DONE into your main photo collection.

-------------------------------------------------------------------------------


## Deutsche Gebrauchsanleitung

### Schritt 1 – Kopieren der RAW‑Ordner in TEMP_SD

1. Kopiere die Kameraverzeichnisse im Sony‑Datum‑Format (reine YYYYMMDD‑Benennung) in den Eingangsordner:  
   TEMP_SD (z.B. /volume1/TEMP/TEMP_SD/20250315).

2. Starte das Skript (z.B. über den Task Scheduler von DSM oder per CLI über SSH).  
   Das Skript durchläuft automatisch alle Ordner in TEMP_SD, TEMP_IMAGES und TEMP_DONE.

-------------------------------------------------------------------------------


### Phase 1 – Ingest und Verschieben nach TEMP_IMAGES

Während Phase 1 führt das Skript folgendes aus:

- Umbenennung des Ordners z.B. von 20250315 in das standardisierte Datumsformat 2025-03-15.
- Erstellung eines ARW‑Unterordners und Verschieben aller *.ARW/*.arw‑Dateien dorthin.
- Erstellung eines SAVE‑Unterordners. In diesem:
  - Wird eine ZIP‑Datei namens SAVE/2025-03-15_ALL_JPG.zip erstellt, die alle JPG‑Dateien enthält.
  - Eine Neuerstellung erfolgt nur, wenn neue JPGs vorhanden sind oder sich der Ordner geändert hat.
- Der Ordner wird mit einer .DONE‑Datei als verarbeitet markiert.
- Anschließend wird versucht, den Ordner in TEMP_IMAGES zu verschieben:
  - Existiert TEMP_IMAGES/2025-03-15 nicht, wird der Ordner einfach verschoben.
  - Existiert das Ziel bereits, wird ein Mergen der Inhalte versucht (mittels rsync, falls vorhanden).
  - Fehlschlägt das Mergen oder fehlt rsync, nutzt das Skript einen Fallback:
    - 2025-03-15_MERGE (und bei Bedarf 2025-03-15_MERGE_2, usw.) werden als alternative Zielordner angelegt.

-------------------------------------------------------------------------------


### Schritt 2 – Manuelle Sortierung in TEMP_IMAGES

1. Öffne in TEMP_IMAGES jeden Datumsordner (z.B. 2025-03-15).
2. Lösche unerwünschte, schlechte oder qualitativ minderwertige JPG‑Dateien.
   - Du kannst den Ordner bei Bedarf auch umbenennen, um einen Titel hinzuzufügen, z.B.:
     2025-03-15_Wandertag.
3. Wenn du mit der JPG‑Auswahl zufrieden bist:
   - Enthält der Ordner noch einen ARW‑Unterordner (also RAW‑Dateien):
     - Verschiebe den gesamten Ordner nach TEMP_DONE.
   - Ist der ARW‑Ordner bereits leer oder wurde gelöscht:
     - Darfst du den Ordner direkt in deine endgültige Fotosammlung (außerhalb der TEMP_*‑Struktur) übernehmen.

-------------------------------------------------------------------------------


### Phase 2 – Nachbearbeitung in TEMP_DONE

Während Phase 2 verarbeitet das Skript alle Ordner innerhalb von TEMP_DONE:

- Prüft, ob der Ordner einen ARW‑Unterordner enthält; falls nicht, wird er übersprungen.
- Berechnet einen Hash der JPG‑Dateien; wenn sich der Hash seit dem letzten Lauf nicht geändert hat, wird der Ordner übersprungen.
- Verschiebt existierende ZIP‑Dateien aus dem ARW/‑Ordner nach SAVE/.
- Benennt alle nicht‑JPG‑ZIPs in SAVE/ so um, dass nur noch *_ALL_JPG.zip und *_SORT_ARW.zip übrig bleiben.
- Vergleicht jede *.ARW‑Datei mit der passenden JPG:
  - Existiert keine passende JPG (groß‑ oder kleingeschrieben), wird die ARW‑Datei gelöscht.
- Danach:
  - Alle verbleibenden ARW‑Dateien werden in SAVE/<Ordnername>_SORT_ARW.zip gepackt.
  - Der ARW‑Unterordner wird anschließend entfernt.
- Der neue Hash wird in .PROCESSED gespeichert, und der Ordner gilt als vollständig nachbearbeitet.

Nach Phase 2 kannst du den Ordner sicher aus TEMP_DONE in deine eigentliche Fotosammlung überführen.

-------------------------------------------------------------------------------


## Program specifics

- The script is idempotent for most steps:
  - If you run it multiple times, it will not reprocess stable folders or re‑create ZIPs without changes.
- Built‑in stability check:
  - Directories in TEMP_SD are only processed if:
    - A .DONE marker exists, or
    - The file list is considered “stable” after a delay ($WAIT_TIME).
- The script counts and logs:
  - Folders found in TEMP_SD and TEMP_DONE.
  - Folders processed, moved/merged, skipped, and errored.
- Logging:
  - All output is written to $LOGFILE.
  - Errors are additionally written to $ERRORLOG.
- Safety against multiple runs:
  - A lockfile ($LOCKFILE) prevents concurrent execution of the same script.
- Error handling:
  - set -euo pipefail and explicit ERR/EXIT traps are used to catch and log failures.
- Merging logic:
  - If rsync is available, folders are merged cleanly instead of just duplicated.
  - If merging fails, fallback‑named folders (_MERGE, _MERGE_2, etc.) are created.
- No mail integration:
  - The version described here does not send email notifications; it only uses file‑based logging.

-------------------------------------------------------------------------------


## Besonderheiten des Programms

- Das Skript ist für die meisten Schritte idempotent:
  - Wenn du es mehrfach ausführst, werden stabile Ordner nicht erneut verarbeitet und ZIP‑Dateien nur bei Änderungen neu erstellt.
- Integrierte Stabilitätsprüfung:
  - Ordner in TEMP_SD werden nur verarbeitet, wenn:
    - Eine .DONE‑Datei vorhanden ist, oder
    - Die Dateiliste nach einer Wartezeit ($WAIT_TIME) als „stabil“ gilt.
- Zählung und Protokollierung:
  - Das Skript zählt und protokolliert:
    - Gefundene Ordner in TEMP_SD und TEMP_DONE.
    - Verarbeitete, verschobene/merged, übersprungene und fehlerhafte Ordner.
- Logging:
  - Alle Ausgaben werden in $LOGFILE geschrieben.
  - Fehler werden zusätzlich in $ERRORLOG protokolliert.
- Schutz gegen mehrfache Ausführung:
  - Eine Lockdatei ($LOCKFILE) verhindert, dass das Skript gleichzeitig mehrfach gestartet wird.
- Fehlerbehandlung:
  - Mit set -euo pipefail und expliziten ERR/EXIT‑Traps werden Ausfälle erkannt und protokolliert.
- Merging‑Logik:
  - Ist rsync verfügbar, werden Ordner sauber zusammengeführt statt verdoppelt.
  - Fehlschlägt das Mergen, werden Fallback‑Namen (_MERGE, _MERGE_2 etc.) verwendet.
- Keine E‑Mail‑Integration:
  - Die beschriebene Version sendet keine E‑Mails, sondern verwendet ausschließlich Datei‑Logging.

-------------------------------------------------------------------------------


## Workflow Diagram (Text format)

START
|
+-- Check lockfile; if present, exit.
+-- Create lockfile; set traps (ERR, EXIT).
+-- Remove leftover *.tmp ZIPs from previous runs.
|
+-- PHASE 1: Process TEMP_SD
|   |
|   +-- Loop over $SRC/* (top‑level folders)
|        |
|        +-- Skip non‑directories.
|        +-- Check if folder name is valid RAW (8‑digit) or DONE (YYYY‑MM‑DD).
|        +-- If transfer is still running (not stable) → skip.
|        |
|        +-- Folder is .DONE‑marked?
|             Yes → merge_or_move_folder($dir, $DEST/$name)
|             No  → call process_folder($dir)
|                   |
|                   +-- Rename folder to YYYY-MM-DD.
|                   +-- Move ARW files into ARW/ subfolder.
|                   +-- Put JPGs into SAVE/ and create ZIP if needed.
|                   +-- Mark folder with .DONE.
|                   +-- Count + move/merge to TEMP_IMAGES.
|
+-- PHASE 2: Process TEMP_DONE
|   |
|   +-- Loop over $DONE/* (done containers)
|        |
|        +-- If folder is valid DONE name:
|             → process_done_folder($dir)
|        +-- If container:
|             → process_container_done($dir)
|                   |
|                   +-- Call process_done_folder for each valid subfolder.
|
+-- Write summary statistics to log.
+-- Remove lockfile on exit.
END


-------------------------------------------------------------------------------


## Ablaufdiagramm (Text‑Format)

START
|
+-- Prüfen, ob Lockdatei existiert; falls ja, Skript beenden.
+-- Lockdatei anlegen; ERR/EXIT‑Traps setzen.
+-- Restliche *.tmp‑ZIP‑Dateien aus früheren Läufen löschen.
|
+-- PHASE 1: TEMP_SD verarbeiten
|   |
|   +-- Schleife über $SRC/* (alle Ordner auf oberster Ebene)
|        |
|        +-- Nicht‑Verzeichnisse überspringen.
|        +-- Prüfen, ob der Ordnername gültiges RAW‑Format (8‑stellig) oder DONE‑Format (YYYY‑MM‑DD) hat.
|        +-- Falls Übertragung noch läuft (nicht stabil) → Ordner überspringen.
|        |
|        +-- Ist der Ordner bereits mit .DONE markiert?
|             Ja → merge_or_move_folder($dir, $DEST/$name)
|             Nein → process_folder($dir) aufrufen
|                   |
|                   +-- Ordner umbenennen nach YYYY-MM-DD.
|                   +-- ARW‑Dateien in den Unterordner ARW/ verschieben.
|                   +-- JPGs in den Ordner SAVE/ verschieben und ZIP bei Bedarf erstellen.
|                   +-- Ordner mit .DONE‑Datei markieren.
|                   +-- Zähler erhöhen und Ordner nach TEMP_IMAGES verschieben/mergen.
|
+-- PHASE 2: TEMP_DONE verarbeiten
|   |
|   +-- Schleife über $DONE/* (Done‑Container‑Ordner)
|        |
|        +-- Falls Ordner hat gültigen DONE‑Namen:
|             → process_done_folder($dir) aufrufen
|        +-- Falls Container‑Ordner:
|             → process_container_done($dir) aufrufen
|                   |
|                   +-- Für jeden gültigen Unterordner process_done_folder aufrufen.
|
+-- Zusammenfassende Statistik in das Log‑File schreiben.
+-- Lockdatei beim Beenden wieder entfernen.
ENDE
