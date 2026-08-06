# 0. Geltungsbereich und Zielbild

## 0.1 Geltungsbereich und Zielsetzung

Diese Spezifikation definiert den produktiv sinnvollen Kern des Photo Workflow. Die Implementierung soll eine vorhandene Codebasis gezielt prüfen und nur die hier beschriebenen Funktionen ergänzen oder reparieren. Sie soll nicht zu einer großen allgemeinen Foto- oder Gesichtsdatenplattform ausgebaut werden.

Der Workflow verfolgt drei gleichrangige Ziele:
1. Originaldaten vor Verlust schützen.
2. Den wiederkehrenden manuellen Aufwand klein halten.
3. Die Qualität der Entscheidungen über nachvollziehbare Lernbeispiele verbessern.

Bei Zielkonflikten gilt die Abwägungslogik aus 0.2.2.

## 0.2 Lesart und Vorrang

### 0.2.1 Normative Schlüsselwörter

Die Schlüsselwörter **MUSS**, **DARF NICHT**, **SOLL** und **KANN** sind normativ.

- **MUSS** kennzeichnet eine zwingende Anforderung.
- **DARF NICHT** kennzeichnet ein ausdrückliches Verbot.
- **SOLL** kennzeichnet eine empfohlene Praxis.
- **KANN** kennzeichnet eine optionale Möglichkeit.

### 0.2.2 Abwägungslogik

Bei Zielkonflikten gilt **zuerst** und **vorrangig vor allen anderen Regeln** folgende Abwägungslogik:

1. **Sicherheit:** Keine unkontrollierten Dateiänderungen, Datenverluste oder unzulässigen Datenübertragungen. Geschützte Bilddaten, Face-Crops, Embeddings und Referenzbilder verlassen nie die erlaubten NAS-Datenbereiche. Lokale, ausdrücklich aktivierte Metadatenaufrufe an Synology Photos sind zulässig, sofern keine Bilddaten oder Geheimnisse übertragen werden.
2. **Stabilität:** Ein einzelnes fehlerhaftes Foto, ein Modellfehler oder ein defekter Ordner stoppt nicht den übrigen sicheren Lauf.
3. **Nutzen:** Jede Funktion muss Fotos besser vorsortieren, Nachvollziehbarkeit oder Betriebssicherheit erhöhen.
4. **Einfachheit:** Wenige verständliche Optionen; keine technische Doppelstruktur ohne nachgewiesenen Nutzen.
5. **Performance:** Ein langsamer, begrenzter und über mehrere Tage fortsetzbarer Betrieb ist akzeptabel.

**Nichtnormativer Performance-Richtwert:** Auf einer typischen NAS (z. B. 2–4 Kerne, 4–8 GB RAM) sind ca. 500–1000 Bilder pro Tag realistisch. Embeddings werden nicht persistent gespeichert. Referenz-Embeddings werden nach einer Änderung des aktiven Referenzpools oder nach einem Container-Neustart neu aufgebaut. Innerhalb eines laufenden Container-Laufs dürfen sie nur im RAM gecacht werden.

Diese Reihenfolge ist **verbindlich** und darf durch keine andere Regel, keine Konfiguration und keine Implementierungsentscheidung überstimmt werden. Sie gilt projektweit, für Fachlogik, Architektur, Konfiguration, Betrieb und Tests.

### 0.2.3 Sekundäre Vorranghierarchie

Erst **nach** Anwendung der Abwägungslogik aus 0.2.2 gilt in dieser Reihenfolge:

1. Datenintegrität, Schutz von Originalen, Datenschutz und Sicherheitsgrenzen.
2. Ausdrückliche Verbote.
3. Haupttext der Spezifikation.
4. Normative Anhänge.
5. Nichtnormative Referenzwerte.

Ein Entwickler darf interne Algorithmen austauschen, wenn alle externen Verträge, Artefaktformate, Sicherheitsgrenzen und Abnahmekriterien erhalten bleiben und die Abwägungslogik aus 0.2.2 nicht verletzt wird.

## 1. Zielbild, Schutzgrenzen

### 1.1 Zielbild

Der Workflow verarbeitet Foto-Batches auf einem Synology-NAS in drei Phasen:

- **Phase 1** analysiert, bewertet und bereitet die menschliche Prüfung vor.
- **Phase 2** archiviert und bereinigt ARWs erst nach einer nachweislich sicheren Endentscheidung.
- **Phase 3** prüft einen erfolgreich abgeschlossenen Phase-2-Batch und kann ihn – nur bei aktivierter Veröffentlichungsoption – aus `03_TEMP_DONE` in einen konfigurierten, von Synology Photos indexierten Zielpfad übertragen. Nach erfolgreicher Indexierung kann sie Ratings, kontrollierte Tags und optional Beschreibungen über einen Synology-Photos-API-Adapter anwenden. PHASE3 ist vollständig nachgelagert. Sie darf nur für Batches mit `phase2_completed` starten. Sie darf keine ARWs, ZIP-Archive, Review-Records, Referenzpools oder Kalibrierungsdaten verändern. Ein Fehler in PHASE3 darf eine erfolgreiche PHASE2 weder zurücksetzen noch Bilddaten löschen.

Original-JPGs und ARWs dürfen weder still überschrieben noch gelöscht werden. Bekannte Gesichtserkennung verarbeitet nur bewusst gepflegte bekannte Personen. Unbekannte Gesichter dürfen nicht gespeichert, geclustert, indexiert, getaggt, als Kandidat protokolliert oder als Referenz aktiviert werden. Ein Gesichtstreffer darf technische Mindestqualität, Manual Keep oder Schutzregeln niemals überstimmen.

### 1.2 Schutzgrenzen

Folgende Datenklassen unterliegen unterschiedlichen Schutzregeln:

| Klasse | Inhalt | Schutzregel |
|---|---|---|
| Originale | Kamera-JPGs und ARWs | Nur im geregelten Phasenablauf veränderbar. Nie still überschreiben oder löschen. |
| Abgeleitete Medien | Crops, ZIPs, Vorschauen, Kopien | Nur mit Herkunft, Hash und dokumentierter Aktion. |
| Steuerdaten | Manifeste, Zustände, Logs, Indizes, Caches | Schema-validiert, atomar, rekonstruierbar. |
| Modellartefakte und Konfiguration | Modellgewichte, Config mit Pfaden | Dürfen separat verwaltet werden, sofern keine geschützten Bildinhalte exfiltriert werden. |

**Wichtig:** Bilddaten, Face-Crops, Embeddings und Referenzbilder werden nicht persistent außerhalb der erlaubten Datenbereiche gespeichert. Modellartefakte und Konfigurationsdaten dürfen extern verwaltet werden, solange keine geschützten Bildinhalte übertragen oder persistiert werden.

Automatisch erzeugte Face-Crops dürfen ausschließlich in `WORKFLOW_DATA/faces/<slug>/new_faces/` persistent gespeichert werden. Die Verschiebung von `new_faces/` nach `reference/` erfolgt ausschließlich manuell durch den Menschen. Erst danach gilt der Face-Crop als aktive Referenz und darf in `reference/` persistent liegen.

Bildbytes und Embeddings dürfen nie in JSON, Cache, Log, Manifest, CSV, Report, eingebetteten Metadaten oder API-Aufrufen persistiert werden. Embeddings sind ausschließlich während des aktiven Container-Laufs im RAM zulässig.

### 1.3 Sicherheits- und Compliance-Grenzen

- Alle produktiven Arbeits-, Daten-, Archiv- und Referenzpfade müssen innerhalb von `paths.basedir` liegen.
- Ausschließlich `finalization.publish_to_synology_photos.target_folder` darf innerhalb der separat validierten Wurzel `paths.publish_root` liegen.
- `paths.publish_root` muss ein lokaler NAS-Pfad sein, der von Synology Photos indexiert werden kann, für den Workflow schreibbar ist und keine Symlink-Auflösung außerhalb der erlaubten Wurzel zulässt.
- `target_folder` muss innerhalb von `paths.publish_root` liegen.
- Die Pfadprüfung muss kanonische Pfade vergleichen und `..`-Traversal, unerlaubte Symlinks und unerlaubte Mountwechsel blockieren.
- Persistente Daten liegen außerhalb des Container-Images.
- Private Bilder, Laufzeitdaten, lokale Secrets und Caches gehören nicht in Git.
- Die zentrale `config.yaml` bleibt secrets-frei.
- API-Credentials und Session-Token werden ausschließlich über Container-Umgebungsvariablen bereitgestellt. Sie dürfen weder in Dateien noch in Batch-Manifests, CSVs, Logs, Reports oder Run-Summaries gespeichert werden.
- PHASE3 darf Quellpfade nur innerhalb von `paths.basedir` und Veröffentlichungszielpfade nur innerhalb von `paths.publish_root` verwenden.
- Bei deaktiviertem Transfer darf PHASE3 keine Bilddatei aus `03_TEMP_DONE` verschieben, kopieren, löschen oder umbenennen.
- Die API darf nur bereits vorhandene lokale Workflow-Metadaten übertragen. Bildbytes, Face-Crops, Embeddings und Referenzbilder dürfen nicht an die API übermittelt werden.
- API-Fehler dürfen niemals eine Löschung, ein Überschreiben, einen Rücktransfer oder eine sonstige unkontrollierte Dateiaänderung auslösen.