# 6. Betrieb, Konfiguration, Reporting, Abnahme

## 6.1 Konfiguration

- **Schema:** YAML mit strikter Validierung; unbekannte Schlüssel sind Fehler (außer `extensions`).
- **Fingerprint:** Effektive Konfiguration wird mit SHA256-Fingerprint im Run dokumentiert.
- **Sicherheit:** Keine Geheimnisse, keine Produktionspfade in Git.
- **Config-Schlüssel:** Durchgängig snake_case.

## 6.2 Betrieb

- **Scheduler:** Container mit persistentem NAS-Mount starten; globaler Lock verhindert parallele Läufe.
- **Fehlerisolation:** Ein defekter Batch wird quarantänisiert statt den ganzen Lauf zu stoppen.
- **Ressourcenverhalten:** Auf Ziel-NAS dokumentieren.
- **Not-Stop:** Bei Zeitbudget oder SIGTERM keinen neuen teuren Schritt beginnen; sicheren aktuellen Schritt abschließen, Status `paused` atomar schreiben, kontrolliert beenden.

## 6.3 Reporting

- **Status:** Pflicht.
- **Zweck:** Macht jedem Lauf auf einen Blick klar, was passiert ist und was der Mensch tun muss.
- **Ablauf:** JSON-Run-Summary, Scheduler-Ausgabe, CSV, Logs, `user_actions_required`.

## 6.4 Abnahme

Die Implementierung ist nur abnahmefähig, wenn mindestens folgende Prüfungen erfolgreich sind:

- `batch_id` wird durchgängig verwendet; `batchid` kommt nicht mehr vor.
- `paths.publish_root` und `target_folder` werden separat und kanonisch validiert.
- `04_TEMP_FINAL` ist vorhanden und seine Rolle in PHASE3 ist eindeutig beschrieben.
- `phase1_moving` ist im Zustandsweg enthalten.
- Stilles Scoring ist definiert und verboten.
- `review_state_invalid` verhindert jede ARW-Aktion.
- Das JPG-Sicherungs-ZIP enthält alle JPGs aus Hauptordner, `Review` und `Rejected`.
- Das ARW-Entscheidungs-ZIP wird vor jeder geschützten ARW-Löschung verifiziert.
- Ein `move` setzt `copy → verify → source removal` um.
- PHASE3 ist bei deaktivierter Veröffentlichung dateilos.
- Index-Timeouts sind resume-fähig.
- API-Secrets werden ausschließlich über Umgebungsvariablen bereitgestellt.
- Unbekannte Gesichter und Embeddings werden nicht unzulässig persistent gespeichert.
- Face-Crops werden automatisch nur in `new_faces` gespeichert und nur manuell nach `reference` aktiviert.
- `unknown` ist ausschließlich im Recovery-Fall zulässig.
- Bei `min_active` wird nur der betroffene Adapter pausiert; sein Score ist `null`.
- Eine Referenzpooländerung invalidiert den RAM-Cache und löst einen Rebuild aus.

## 7. Stil- und Formatvereinheitlichung

- Überschriften als Markdown-Header.
- Listen mit Bindestrichen.
- Tabellen mit Header und Trennlinie.
- Codeblöcke mit Sprachangabe.
- Zitate mit `>`.

## 8. Wichtige Regeln

1. Git enthält nie Modellgewichte, private Bilder, Referenzen, Face-Crops, Embeddings, Laufzeitdaten, Caches, Logs oder Secrets.
2. NAS enthält alle Workflow-Daten und Konfiguration mit Produktionspfaden.
3. Docker-Container enthält nur Code und mountet NAS-Pfade.