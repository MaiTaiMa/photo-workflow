# Lokaler Automations- und Finalisierungsvertrag v1.4

**Status:** Verbindlicher v1.4-Erweiterungsvertrag
**Geltung:** Lokaler Photo-Workflow einschließlich Phase 3 (lokaler Transfer)
**Zweck:** Definiert sichere KI-Assistenz, Vollautomatik, kontrollierte Phase-2-Übergabe, lokale Finalisierung und Phase-3-Transfer.
**Erstellt:** 2026-08-14
**Version:** 1.2.0 (2026-09-02: Phase 3 ergänzt)
**Requires:** `docs/IMPLEMENTATION_RULES.md`, `docs/spec_v1-1/`, lokale Phase-1/2/3-Verträge

## Änderungsprotokoll

- 2026-09-02 | 1.2.0 | Phase 3 (lokaler Transfer) ergänzt; Synology-Photos-API als capability-gated vorbereitet
- 2026-08-14 | 1.0.0 | Initialer Vertrag für lokale Automation und Finalisierung in v1.2

## 1. Vorrang und Geltungsbereich

Dieser Vertrag ergänzt die Spezifikation v1.1 für `release/v1.4`. Bei Konflikten gilt zuerst die Sicherheits- und Abwägungslogik aus der Spezifikation: Sicherheit vor Stabilität vor Nutzen vor Einfachheit vor Performance.

Der Vertrag gilt für lokale Phase 1, Phase 2 und Phase 3 (lokaler Transfer). Phase 3 umfasst den Transfer von `04_TEMP_FINAL` nach `target_folder` (Synology-Photos-Zielpfad), Indexierung und vorbereitete Album-Operationen. Der Vertrag umfasst keine Synology-Photos-API-Schreiboperationen, Cloud-KI, API-Credentials oder API-Logs. Bestehende Synology-Module werden durch v1.4 nicht erweitert, gelöscht oder aufgerufen; die API-Integration ist capability-gated und vorbereitet, aber nicht vollständig implementiert.

Alle Modelle bleiben lokal. Bildbytes, Face-Crops, Referenzbilder, Embeddings, Secrets und Tokens dürfen nicht in JSON, CSV, Logs, Reports, Metadaten oder sonstigen persistenten Artefakten gespeichert werden. Embeddings sind nur während eines aktiven Laufs im RAM zulässig.

## 2. Lokaler Workflow

Die v1.2-Endablage ist lokal und endet nach erfolgreich abgeschlossener Phase 2:

```text
01_TEMP_SD
  -> Phase 1
  -> 02_TEMP_IMAGES
  -> manuelle Freigabe oder automatic_handoff
  -> Phase 2
  -> 04_TEMP_FINAL
```

`02_TEMP_IMAGES` bleibt im manuellen und assistierten Betrieb der sichtbare Review-Bereich. `03_TEMP_DONE` bleibt der kontrollierte Phase-2-Eingang für manuell freigegebene Batches. Im automatischen Betrieb ersetzt `automatic_handoff` den manuellen Move nach `03_TEMP_DONE` nur für vollständig freigegebene Batches.

Ein Batch darf erst nach `04_TEMP_FINAL` übergeben werden, wenn Phase 2 vollständig, archivgesichert und ohne blockierenden Fehler abgeschlossen ist. Eine automatische oder manuelle Finalisierung darf keine Originale, Archive, menschliche Entscheidungen oder Recovery-Nachweise still überschreiben oder löschen.

## 3. Automationsmodi

| Modus | Prediction | Finale Bildentscheidung | Phase-2-Start | Erlaubte Wirkung |
|---|---|---|---|---|
| `off` | Keine operative Prediction | Bestehende deterministische Regeln | Nur manuell | Keine KI-Assistenz |
| `shadow` | Diagnose wird persistenzsicher dokumentiert | Unverändert | Nur manuell | Lernen und Messung |
| `assisted` | Vorschlag mit Grund sichtbar | Mensch entscheidet | Nur manuell | Review-Unterstützung |
| `auto_phase1` | Versionierte, validierte Prediction | Nur bei erfüllten Gates; sonst `review` | Nur manuell | Automatische Phase-1-Vorsortierung |
| `auto_phase2` | Wie `auto_phase1` | Wie `auto_phase1` | Nur bei `automatic_handoff` und allen Phase-2-Gates | Lokale automatische Phase 1 und 2 |
| `full_auto` | Wie `auto_phase2` | Wie `auto_phase2` | Nur bei `automatic_handoff` und allen Phase-2-Gates | Vollständiger lokaler v1.2-Lauf bis `04_TEMP_FINAL` (wenn `phase2.move_to_temp_final: true`) |

`shadow` und `assisted` dürfen niemals `keep`, `review`, `reject`, Dateimoves, Archivierung, ARW-Aktionen oder States verändern. Ein `ready`-Status der Readiness-Auswertung aktiviert keinen Modus selbst. Jeder operative Modus muss explizit in der Konfiguration aktiviert sein.

## 4. Lern-, Readiness- und Policy-Vertrag

Das System lernt ausschließlich aus manuell bestätigten Entscheidungen. Eine Prediction ist keine bestätigte Wahrheit und darf nicht als Trainingslabel behandelt werden.

Operative Automation verlangt mindestens:

- einen positiven, aktuellen Readiness-Status;
- eine ausreichende Anzahl manuell bewerteter Predictions und unabhängiger Batches;
- nachgewiesene Gesamtübereinstimmung sowie getrennte Keep- und Reject-Precision gemäß aktiver Policy;
- eine versionierte Automation-Policy und Modellversion;
- eine explizite Nutzeraktivierung des jeweiligen Automationsmodus;
- nachvollziehbare, secrets-freie Auditfelder für Prediction, Policy, Modell und Gate-Ergebnis.

Eine modellinterne Sicherheit von beispielsweise 95 Prozent ist allein kein Freigabekriterium. Sie muss durch historische, manuell bestätigte Entscheidungen kalibriert sein. Keep- und Reject-Entscheidungen werden getrennt bewertet. Reject-Automation ist wegen möglicher nachfolgender ARW-Bereinigung strenger abzusichern als Keep-Automation.

## 5. Fail-closed und Schutzregeln

Bei fehlendem Score, Modellfehler, ungültiger Policy, fehlender Readiness, unklarem State, unvollständigem Manifest, fehlerhafter Archivprüfung, Lock-Konflikt, Pause-/Resume-Unklarheit oder jeder sonstigen Validierungsabweichung gilt fail-closed:

```text
Entscheidung: review
automatic_handoff: nicht ausführen
Phase 2: nicht automatisch starten
ARW-Aktion: nicht ausführen
```

MANUAL_KEEP hat immer Vorrang vor jeder automatischen Entscheidung. Es erzwingt `keep` und darf durch Scoring, Serienculling, Reporting, Readiness oder Automation nicht abgeschwächt werden. Familien- und sonstige bestehende Schutzregeln bleiben ebenfalls vorrangig.

## 6. Automatic Handoff

`automatic_handoff` ersetzt ausschließlich den manuellen Move eines vollständig geeigneten Batches von `02_TEMP_IMAGES` nach `03_TEMP_DONE`. Er ist nur zulässig, wenn alle folgenden Bedingungen erfüllt sind:

- Der operative Automationsmodus ist explizit aktiviert.
- Die aktive Policy und das Modell sind readyness-freigegeben und versioniert.
- Kein Bild hat `analysis_error`.
- Kein Bild verbleibt mit finaler Entscheidung `review`.
- MANUAL_KEEP ist angewendet und persistenzsicher dokumentiert.
- Phase-1-Manifest, State und sichtbare Batch-Struktur sind vollständig und valide.
- Es liegt kein aktiver Lock-Konflikt vor.
- Der Batch wurde nicht pausiert, nur teilweise verarbeitet oder als recovery-unklar markiert.

Vor einem sichtbaren Move wird der erforderliche Übergangsstate atomar geschrieben. Erst nach vollständig erfolgreichem Move und validierter Übergabe darf Phase 2 beginnen. Ein Abbruch innerhalb dieser Grenze darf niemals einen Abschlusszustand vortäuschen.

## 7. Automatische Phase 2 und lokale Finalisierung

Eine automatische Phase 2 darf nur nach gültigem `automatic_handoff` beginnen. Zusätzlich gelten alle bestehenden Phase-2-Schutzregeln uneingeschränkt:

- Phase-1-Manifest und Endentscheidungen sind valide.
- Die erforderlichen JPG- und ARW-Archive sind vollständig erzeugt, geprüft und atomar aktiviert.
- Jede ARW-Aktion erfolgt erst nach erfolgreicher Archivaktivierung und vollständiger Dokumentation.
- `review_state_invalid` oder ein anderer blockierender Zustand verhindert jede ARW-Aktion.
- Bei jedem Fehler bleiben ARWs erhalten.

Nach vollständig erfolgreicher Phase 2 wird der Batch kontrolliert nach `04_TEMP_FINAL` übergeben. Diese lokale Endablage ist kein Synology-Transfer, keine API-Aktion und keine Phase 3. Sie beendet den v1.2-Workflow.

## 8. Pause, Limits und Resume

Ein pausierter, unvollständiger oder recovery-pflichtiger Batch hat immer Vorrang vor neuen Batches. Die spätere Auswahlreihenfolge `oldest_first` oder `newest_first` gilt ausschließlich für neue, noch nicht begonnene Batches.

Bei Signal, Zeit- oder Mengenlimit darf kein neuer teurer Schritt beginnen. Der laufende sichere Schritt wird kontrolliert beendet; danach werden mindestens Batch-ID, WorkUnit-/Checkpoint-Referenz, Pausegrund, Zeitstempel, Config-Fingerprint und geeigneter Resume-Status atomar persistiert. Ein pausierter Teilbatch darf nicht als Phase-1-, Phase-2- oder Finalisierungsabschluss markiert werden.

## 9. Nichtbestandteil von v1.4

Nicht Bestandteil dieses Vertrags und aller v1.2-Umsetzungspakete sind:

- Synology-Photos-API-Schreiboperationen (`apply_metadata()` ist vorbereitet, aber nicht vollständig implementiert);
- API-Credentials, API-Logging oder Capability-Gates (vorbereitet, aber nicht aktiv);
- API-Credentials, API-Logging oder Capability-Gates;
- Cloud-basierte KI oder Datenübertragung;
- Cloud-basierte KI oder Datenübertragung;
- Erstellung, Wiederherstellung oder Aktualisierung eines `CHANGELOG.md`.

Ein späteres separates Zusatzprojekt darf nur über einen eigenständigen, versionierten und secrets-freien Exportvertrag an einen stabilen, getesteten v1.4-Stand anschließen.

## 10. Abnahmekriterien

- Die Moduswirkung ist für `off`, `shadow`, `assisted`, `auto_phase1`, `auto_phase2` und `full_auto` eindeutig definiert.
- Kein Diagnosemodus verändert finale Entscheidungen oder Dateioperationen.
- `automatic_handoff` und automatische Phase 2 sind fail-closed.
- MANUAL_KEEP und Schutzregeln bleiben vorrangig.
- Die lokale Endablage `04_TEMP_FINAL` ist von Phase 3 (lokaler Transfer) getrennt.
- Phase 3 ist standardmäßig deaktiviert (`finalization.enabled: false`).
- Phase-3-Transfer ist atomar, verifiziert und idempotent.
- Pause und Resume haben Vorrang vor der Auswahl neuer Batches.
- Persistierte Artefakte enthalten keine Bildbytes, Embeddings, Referenzen, Secrets oder Tokens.
- Kein Bestandteil verlangt eine Änderung an `CHANGELOG.md`.
