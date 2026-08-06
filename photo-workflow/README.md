# Synology Photo Workflow – Python/Docker Migration

## Überblick
Diese Python-Version übernimmt den bekannten Ablauf mit `TEMP_SD`, `TEMP_IMAGES` und `TEMP_DONE` und ergänzt ihn um ein KI-gestütztes JPG-Culling.
Sie ist so aufgebaut, dass auch Nutzer ohne Python-Kenntnisse den täglichen Ablauf verstehen und auf einer Synology NAS über den DSM Task Scheduler betreiben können.

## Für Einsteiger
Der Workflow arbeitet in drei Arbeitsbereichen:
- `TEMP_SD`: Hier landen neue Kameraordner direkt nach dem Kopieren.
- `TEMP_IMAGES`: Hier sichtest du die Ergebnisse und kannst Bilder manuell zurückholen oder weiter aussortieren.
- `TEMP_DONE`: Hier wird entschieden, welche ARW-Dateien endgültig bleiben.

Die wichtigste Regel ist: **Nur JPGs im Hauptordner gelten als aktiv ausgewählt.**
Bilder in `_Review/` oder `_Rejected/` sind bewusst ausgelagert. Wenn du eines davon wieder in den Hauptordner zurückschiebst, bleibt später auch das passende ARW erhalten.

## Phase 1 einfach erklärt
1. Der Ordner in `TEMP_SD` wird geprüft, damit keine noch laufende Übertragung verarbeitet wird.
2. Ein Rohordner im Kameraformat wie `20250707` wird mit der Legacy-Bash-Logik in ein Datumsformat wie `2025-07-07` umbenannt; die Jahresdekade bleibt dabei über `workflow.date_reconstruction` konfigurierbar.
3. Alle ARW-Dateien werden in den Unterordner `ARW/` verschoben.
4. Alle ursprünglichen JPGs werden zuerst in `SAVE/<datum>_ALL_JPG.zip` gesichert.
5. Danach bewertet das System die JPGs und verteilt sie in Hauptordner, `_Review/` oder `_Rejected/`.
6. Anschließend wird der gesamte Ordner nach `TEMP_IMAGES` verschoben.

## Bedeutung der Ordner
- Hauptordner: Aktive Auswahl, zählt später für ARW-Erhalt.
- `_Review/`: Unsichere Fälle, die du kurz prüfen solltest.
- `_Rejected/`: Bilder unter dem Mindestscore, aber manuell rückholbar.
- `ARW/`: Original-RAW-Dateien.
- `SAVE/`: ZIP-Dateien, Score-Listen und Zusammenfassungen.

## Phase 2 einfach erklärt
In `TEMP_DONE` prüft das System, welche JPGs noch aktiv im Hauptordner liegen.
Nur für diese JPGs wird das passende ARW behalten. Fehlende Basename-JPGs führen dazu, dass das zugehörige ARW entfernt wird.
Danach werden die verbleibenden ARWs in `SAVE/<folder>_SORT_ARW.zip` gepackt; existiert bereits ein gleichnamiges Artefakt, wird kollisionssicher auf `SAVE/<folder>_SORT_ARW_EXTRA_<n>.zip` ausgewichen. Anschließend wird der `ARW/`-Ordner entfernt.

## Rückfallebene mit Bash
Das bestehende Bash-Skript nutzt denselben Grundworkflow mit `TEMP_SD`, `TEMP_IMAGES` und `TEMP_DONE`.
Dadurch kann es als Rückfallebene dienen, wenn du den Python-Workflow vorübergehend abschaltest.
Wichtig ist aber: Das Bash-Skript kennt `_Review/`, `_Rejected/`, `culling_scores.csv` und `culling_summary.json` nicht aktiv. Es ist daher eine operative Rückfallebene für den Ordnerfluss, aber kein vollwertiger Ersatz für die KI-Logik.

## Logging und DSM Scheduler
Das Bash-Skript schreibt ausführliche Startinformationen, Statusmeldungen und eine Zusammenfassung in die Standardausgabe; genau diese Ausgabe kann der DSM Task Scheduler als E-Mail versenden. Das Python-Projekt gibt jetzt ebenfalls einen Startblock, laufende Statusmeldungen und einen Abschlussblock mit Zählern auf `stdout` aus.

Dadurch erhältst du im Scheduler eine E-Mail mit unter anderem:
- Startzeit,
- Skriptname und Version,
- verwendeten Pfaden,
- Anzahl gefundener Ordner,
- Anzahl verarbeiteter Ordner,
- Anzahl Move/Merge-Vorgänge,
- Anzahl übersprungener Ordner,
- Anzahl Fehler,
- Pfad zu Logfile und Error-Log.

## Empfohlene DSM-Task-Nutzung
Für Synology ist eine tägliche oder stündliche Aufgabe sinnvoll, je nach Kopierhäufigkeit.
Sinnvoller Startbefehl:

```bash
python /app/app/photo_workflow.py --config /app/config/config.yaml phase1
python /app/app/photo_workflow.py --config /app/config/config.yaml phase2
```

Alternativ kann ein Wrapper-Skript genutzt werden.

## Training des persönlichen Modells
Das Training liest JPG/XMP-Ratings aus vorhandenen Bildbewertungen.
Dadurch lernt das Modell grob deinen Geschmack, statt nur mit einem allgemeinen Ästhetikscore zu arbeiten.
Ohne persönliches Modell läuft das System weiterhin, dann nur mit dem generischen Score.

## Sicherheit
- Alle produktiven Pfade liegen innerhalb von `base_dir`.
- Löschungen sind nur in `ARW/` erlaubt.
- Lockfiles verhindern parallele Läufe.
- Symlinks werden bei relevanten Prüfungen ignoriert.
- Vor produktivem Einsatz sollte immer ein Test mit Kopien echter Ordner erfolgen.

## Dateien im Projekt
- `app/photo_workflow.py`: Hauptworkflow.
- `app/aesthetic.py`: generische Bildbewertung.
- `app/metadata_rating.py`: liest Ratings aus XMP/JPG.
- `app/training.py`: trainiert das persönliche Modell.
- `config/config.yaml`: zentrale Konfiguration.
- `REPAIR_CHECK_REPORT.md` und `REPAIR_CHECK_REPORT.json`: letzter technischer Reparatur- und Testbericht.

## zweistufige Ausgabe
Das Projekt erzeugt pro Lauf bewusst zwei Ausgabeformen, damit der Synology DSM Scheduler eine kurze, gut lesbare Mail erhält und parallel eine technische Historie erhalten bleibt.

1. Scheduler-Mail auf `stdout`: Startblock, Pfade, Statusmeldungen und kompakte Abschlusszusammenfassung.
2. JSON-Zusammenfassung pro Lauf: strukturierte Datei im Ordner `output/photo_workflow_project/run_summaries` für Historie, Auswertung und spätere Automatisierung.

Für Synology-Deployments kann dieser Pfad später auf `/volume1/TEMP/run_summaries` angepasst werden.


## Familien-Gesichtserkennung
Das Projekt unterstützt jetzt optional eine Familien-Gesichtserkennung für nahe Angehörige wie `Vater`, `Mutter`, `Kind1` und `Kind2`.

### Ziel
Die Funktion soll Bilder mit wichtigen Familienmitgliedern im Culling bevorzugen und möglichst nativ in Synology Photos nutzbar machen.

### Grundprinzip
- Referenzbilder liegen in `family_faces/<Person>/`.
- In Phase 1 kann das System erkannte Familienmitglieder als zusätzlichen Score verwenden.
- Erkannte Familienbilder können vor hartem `reject` geschützt und stattdessen mindestens nach `_Review/` verschoben werden.
- Wenn `exiftool` verfügbar ist, schreibt das System die Erkennung direkt als eingebettete Tags in die JPG-Datei.

### Tag-Schema
Es werden bewusst normale, portable Tags verwendet, damit Synology Photos diese möglichst nativ lesen kann.
Beispiele:
- `person:Vater`
- `person:Mutter`
- `person:Kind1`
- `person:Kind2`
- `family:close`
- `family:has_face_match`

### Warum normale Tags?
Normale Keywords in XMP/IPTC sind für Synology Photos und andere Systeme robuster als eine rein interne People-Datenbank.
Optionale Face-Regionen können später ergänzt werden, sind aber nicht die führende Projektwahrheit.

### Referenzbilder vorbereiten
Lege pro Person mehrere klare Beispielbilder in diese Ordner:
- `family_faces/Vater/`
- `family_faces/Mutter/`
- `family_faces/Kind1/`
- `family_faces/Kind2/`

Empfehlung:
- 10 bis 30 gute Beispielbilder pro Person,
- verschiedene Lichtbedingungen,
- möglichst eindeutige Frontal- oder Halbprofilbilder.

### Technische Hinweise
- Für echte Gesichtserkennung wird eine kompatible Face-Recognition-Bibliothek benötigt.
- Für natives Schreiben der Tags in JPG-Metadaten wird `exiftool` empfohlen.
- Wenn eine dieser Komponenten fehlt, bleibt der Workflow lauffähig und überspringt den Schritt kontrolliert.

### Konfiguration
Der neue Block `family_recognition` in `config/config.yaml` steuert diese Funktion.
Wichtige Felder:
- `enabled`
- `reference_dir`
- `protect_detected_family`
- `score_boost_weight`
- `write_native_tags`
- `write_face_regions`
- `exiftool_path`
- `person_weights`

### Auswirkungen auf die Bewertung
Die Familienerkennung ergänzt die bisherige Ästhetik- und persönliche Bewertung.
Sie ist kein vollständiger Ersatz, sondern ein zusätzlicher Relevanzfaktor für Familienfotos.

## Family-Cache
Für größere Familienbestände mit vielen Referenzbildern wird ein persistenter Cache unter `models/family_faces/` verwendet.

### Warum?
Wenn du 20 bis 30 Personen mit 50 bis 200 Referenzbildern pro Person pflegst, wäre ein komplettes Neu-Einlesen bei jedem Scheduler-Lauf unnötig langsam.
Der Cache speichert daher die berechneten Gesichtsmerkmale und nutzt sie erneut, solange sich die Referenzbilder nicht geändert haben.

### Speicherort
- Referenzbilder: `family_faces/<Person>/`
- Cache und Modellartefakte: `models/family_faces/`

### Ablauf
1. Beim Lauf prüft das System, ob der Cache noch zum aktuellen Stand von `family_faces/` passt.
2. Wenn ja, werden die Encodings direkt aus `models/family_faces/` geladen.
3. Wenn nein, wird der Cache neu aufgebaut und gespeichert.
4. Dieser Status erscheint im Log, im Scheduler-Output und in den JSON-Run-Summaries.

### CLI
Zusätzlich gibt es jetzt das Kommando:
- `rebuild-family-cache`

Damit kannst du den Cache gezielt neu aufbauen, zum Beispiel nach vielen neuen Referenzbildern.


## Legacy-Datumslogik
Die Kamera liefert weiterhin das alte 8-stellige Namensformat, das schon im Bash-Skript verarbeitet wurde. Im Standardmodus `legacy_bash` rekonstruiert die Python-Version daraus das Jahr über einen konfigurierbaren Dekaden-Präfix und die konfigurierbare Jahresziffer-Position.

```yaml
workflow:
  date_reconstruction:
    mode: legacy_bash
    decade_prefix: '202'
    year_digit_index: 3
```

Für spätere Dekaden genügt es, `decade_prefix` anzupassen, etwa auf `'203'`. Der alternative Modus `full_year` ist nur für echte `YYYYMMDD`-Ordnernamen gedacht.

## ZIP-Kollisionsschutz
ZIP-Dateien aus `ARW/` werden in `SAVE/` nicht mehr blind umbenannt oder überschrieben. Stattdessen klassifiziert der Workflow vorhandene Archive in `ALL_JPG`, `SORT_ARW` oder `UNSORTED` und vergibt bei Namenskollisionen eindeutige Folgezielnamen wie `_ALL_JPG_EXTRA_2.zip`, `_SORT_ARW_EXTRA_2.zip` oder `_UNSORTED_1.zip`.

Jede solche Umbenennung wird zusätzlich geloggt und in der JSON-Zusammenfassung unter `zip_conflicts` erfasst. So bleibt ein möglicher Fehlerfall vor einem späteren Backup sichtbar.

## Serienprüfung
Die Serienprüfung wurde wieder als eigener Culling-Baustein eingeführt. Dabei werden ähnliche JPGs innerhalb eines Ordners visuell gruppiert und innerhalb jeder Serie nach `final_score` sortiert.

Das beste Bild einer Serie bleibt standardmäßig `keep`. Weitere Bilder derselben Serie werden je nach Abstand zum Bestbild auf `review` oder `reject` gesetzt. Dadurch wird die frühere Serienauswahl wieder mit dem heutigen Workflow aus `_Review/`, `_Rejected/` und `SAVE/` verbunden.

Die CSV-Datei `SAVE/culling_scores.csv` enthält jetzt zusätzlich:
- `series_id`
- `series_size`
- `series_rank`
- `series_best`
- `series_margin_to_best`
- `star_rating`
- `decision_reason`

## Culling-Metadaten
Culling-Entscheidungen können jetzt unabhängig von der Familienerkennung in Metadaten geschrieben werden. Dafür nutzt das Projekt `exiftool` und schreibt optional `XMP:Rating` sowie Keywords wie `AI_CULL`, `DECISION_KEEP`, `SERIES_BEST` oder `SERIES_MEMBER`.

Die Schalter dafür liegen in `config/config.yaml` unter `metadata_culling`.


## Score-Gewichtung
Die finale Culling-Bewertung kombiniert jetzt drei Bereiche: `base_score`, `personal_score` und `family_score`. Der `base_score` nutzt wieder die ältere, bewährte Gewichtung aus Schärfe, Ästhetik, Belichtung, Augen und optionalem Referenzscore.

Standardgewichte im Projekt:
- `culling.component_weights`: Basis 0.65, Personal 0.25, Familie 0.10
- `culling.base_weights`: Sharp 0.32, Aesth 0.32, Exposure 0.18, Eyes 0.10, Reference 0.10

Wenn einzelne Komponenten nicht verfügbar sind, werden nur die aktiven Gewichte automatisch neu normiert.

## Debug-Konfiguration
Zusätzlich liegt jetzt `config/config-debug-local.yaml` im Projekt. Diese Datei enthält lokale Testpfade für den bestehenden Entwicklungsaufbau und kann bei Bedarf manuell nach `config.yaml` kopiert oder umbenannt werden.


## Entscheidungslogik
Die finale Entscheidung nutzt jetzt eine hybride Logik. Zuerst wird aus `final_score`, `keep_threshold` und `reject_threshold` eine scorebasierte Klasse (`keep`/`review`/`reject`) gebildet. Danach wirkt die Serienlogik nur noch korrigierend: Das beste Serienbild darf um höchstens eine Stufe angehoben werden, nahe Bilder bleiben `review`, und deutlich schwächere Nicht-Bestbilder werden je nach `series_detection.demote_non_best_to` weich oder hart abgestuft.

## Sternebewertung
Die Sterne hängen jetzt nicht mehr direkt an `keep`/`review`/`reject`, sondern am numerischen `final_score`. Standardmäßig gilt: 0.00-0.19 = 0 Sterne, 0.20-0.39 = 1 Stern, 0.40-0.59 = 2 Sterne, 0.60-0.74 = 3 Sterne, 0.75-0.89 = 4 Sterne, 0.90-1.00 = 5 Sterne. Die Schwellen liegen in `culling.star_rating_bands`.

## Debugging und Transparenz
`culling_scores.csv` enthält jetzt zusätzlich `score_decision` und `score_reason`. Dadurch ist sichtbar, welche scorebasierte Grundentscheidung vorlag und wie die Serienlogik das Endergebnis verändert hat.


## Dynamische Regewichtung
Die finale Bewertung verwendet jetzt eine dynamische Regewichtung über `base_score`, `eye_score`, `personal_score` und `family_score`. Fehlen optionale Komponenten, werden ihre Gewichte nicht als Null interpretiert, sondern proportional auf die tatsächlich verfügbaren Komponenten umgelegt.

## Eye Score
`eye_score` ist jetzt ein eigenständiger optionaler Final-Score-Baustein und wird nicht mehr innerhalb von `base_score` mitgewichtet. Dadurch zählt die Augenbewertung nicht doppelt und kann, falls vorhanden, sauber in die Regewichtung einfließen.

## Standardgewichte
Wenn alle Komponenten vorhanden sind, gilt standardmäßig: `base_score` 0.55, `eye_score` 0.10, `personal_score` 0.20 und `family_score` 0.15. Wenn zum Beispiel nur `base_score` und `eye_score` vorliegen, werden nur diese beiden Anteile auf 100 Prozent normiert.


## Personal scoring and keyword schema

- A single sample image directory can now drive both `reference_score` and `personal_score`.
- `reference_score` still measures direct visual similarity to the sample images.
- `personal_score` now supports an automatic cached prototype model rebuild whenever the sample image directory changes.
- New config section: `personal_scoring`, with `source_dir` intentionally pointing to the same folder as `training.sample_images_dir` or `culling.reference_scoring.folder`.
- Metadata keywords now use a namespaced schema such as `workflow:ai_cull`, `decision:keep`, `series:id:series_4`, `family:match:true`, and `person:Kind1`.
- Optional score-band keywords are written as `score_band:<component>:<band>`, while exact raw scores remain in CSV/JSON outputs by default.

## Face-recognition tuning

- `family_recognition.match_tolerance` is standardized to `0.55` across configs to make family matching less strict than `0.48`.
- `default_person_weight` remains moderate at `0.35`; only `Kind1` and `Kind2` are boosted to `0.55` so recognition tuning and scoring stay separated.
- `force_cache_rebuild` remains `false` in committed configs; set it to `true` for one run after changing face references, then switch it back.
- `personal_scoring` is present in the configs so the same sample-image folder can continue to feed both `reference_score` and `personal_score`.

## Reference profile cache

- `reference_score` is now backed by a cached reference profile built from `culling.reference_scoring.folder`.
- The workflow logs a CLI status line like `[REFERENCE PROFILE] status=cache_used ...` or `[REFERENCE PROFILE] status=cache_rebuilt ...`.
- New config fields under `culling.reference_scoring`: `cache_enabled`, `cache_dir`, and `force_cache_rebuild`.
- Set `force_cache_rebuild: true` for one run after changing the reference-image folder, then switch it back to `false`.

## Debug path strategy

- In `config-debug-local.yaml`, runtime paths should be relative to the project layout.
- `TEMP` stays under `../example_nas_environment/TEMP`.
- Models and sample-image sources stay under `../project/...`.
- This keeps the debug config portable and aligned to the ZIP/project structure.
