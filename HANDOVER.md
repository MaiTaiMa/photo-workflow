# Handover — photo-workflow — Neustart 2026-09-24 (v7.0)

## 🎯 NÄCHSTER GROSSER AUFTRAG: Phase 3 implementieren

**Das ist ab sofort der wichtigste offene Punkt, vor allen anderen unten
gelisteten Themen.**

### Ausgangslage (belegt am 2026-09-24, NAS-Testlauf)

Phase 3 ist im aktuellen Code (v1.4) nur ein Stub. Jeder Pipeline-Lauf zeigt:

```
[PIPELINE] Phase phase3 noch nicht implementiert
```

Kein Datei-Transfer, kein Metadaten-Handoff findet statt — unabhängig davon,
was in der Config steht.

### Ziel

Phase 3 so implementieren, dass sie zwei Dinge leistet:

1. **Datei-Transfer:** Freigegebene Batches aus `03_TEMP_DONE` nach
   `publish_root` (`/volume1/photo/<person>`) verschieben, gesteuert über
   `faces.target_folder` (Beispiel: Person „wirser" → bereits konfiguriert
   auf `/volume1/photo/wirser`).
2. **Metadaten-Handoff an Synology Photos:** Möglichst viele der in Phase 1/2
   erzeugten Metadaten (Tags, Rating/Keep-Score, erkannte Personen,
   Serien-Zugehörigkeit) sollen für Synology Photos sichtbar/nutzbar werden —
   nicht nur die reine Bilddatei.

### Nicht-Ziel (für den ersten Entwicklungsschritt)

- Keine Änderung an Phase 1/2-Scoring-Logik.
- Keine Aktivierung von `write_known_persons` oder `album_upsert` ohne
  erfolgreichen Pilotlauf (siehe Config-Kommentare — beide Flags sind
  explizit „nur nach erfolgreichem Pilotlauf auf true setzen").

### Relevante Config-Sektion (`config.nas.yaml`)

```
publish_root: /volume1/photo
faces.target_folder (Beispiel "wirser"): /volume1/photo/wirser
publish_to_synology_photos.enabled: <klären, aktuell unklar ob false>
synology_api:
  protocol: http
  write_rating: true
  write_tags: true
  # Endpunkt ohne Pilotlauf-Nachweis — siehe docs/spec_v1-2/06_SynologyPhotosAPI.md
max_active: 100   # weitere Aktivierung wird blockiert
```

**Wichtiger Bestandsschutz:** `docs/spec_v1-2/...` nicht verändern — nur
lesen. Die Spezifikation `06_SynologyPhotosAPI.md` beschreibt den
vorgesehenen Endpunkt/Ansatz, ist aber laut eigenem Kommentar **noch nicht
pilotiert**. Erster Schritt sollte ein kleiner, isolierter Pilotlauf sein
(ein einzelnes Testbild, kein Produktionsbatch), bevor die Funktion an echten
Batches aktiv wird.

### Zwei mögliche technische Wege für den Metadaten-Handoff (zu bewerten)

1. **XMP/EXIF-Sidecar-Schreiben** vor dem Datei-Move: Tags, Rating und
   Personennamen direkt in die Bilddatei bzw. `.xmp`-Sidecar schreiben
   (ExifTool ist im Container bereits installiert —
   `libimage-exiftool-perl`, siehe Dockerfile). Synology Photos liest EXIF/XMP
   beim Indexieren automatisch mit ein — kein API-Call nötig, robuster gegen
   API-Änderungen.
2. **Synology Photos API direkt ansprechen** (`synology_api`-Sektion,
   `write_rating`/`write_tags`): setzt Rating/Tags nach der Indexierung
   gezielt per API — genauer steuerbar, aber abhängig vom nicht pilotierten
   Endpunkt und ggf. von Login-Session-Handling.

**Empfehlung für den ersten Wurf:** Weg 1 (XMP/EXIF) zuerst, weil er ohne
zusätzliche Authentifizierung funktioniert und mit dem vorhandenen
`synoindex -A`/`synoindex -R`-Mechanismus (bereits im Abschlussbericht der
Pipeline als Hinweis dokumentiert) zusammenspielt. Weg 2 danach als Ergänzung
für Rating/Tags, die EXIF/XMP nicht abdeckt.

### Akzeptanzkriterien (bevor „implementiert" behauptet wird)

- Ein Testbatch mit 3–5 Bildern läuft vollständig durch `pipeline` und landet
  nachweislich unter `/volume1/photo/<person>/`.
- `ls -la` auf dem Zielordner zeigt die Dateien mit korrektem Eigentümer
  (matthias, dank `user: "1029:100"` in der Compose-Datei).
- Mindestens Tags oder Rating sind nach dem Move in den Dateien nachweisbar
  (`exiftool <datei>` zeigt die geschriebenen Felder).
- `sudo synoindex -A /volume1/photo/<ORDNER>` angestoßen, danach in der
  Synology Photos Weboberfläche geprüft, ob Tag/Rating sichtbar sind.
- Kein bestehender Test (`pytest tests/unit/`) wird durch die Änderung rot.

---

## Startanweisung für den neuen Chat (unverändert gültig)

Arbeite lokal-first, kleinpaketig und token-effizient. Behaupte niemals, dass
eine Änderung implementiert oder verifiziert ist, bevor der Nutzer den
lokalen Output von Ausführung und Tests geliefert hat. GitHub dient nur
lesend zur Orientierung; Änderungen entstehen lokal über `paste.txt`. Kein
Commit oder Push ohne ausdrückliche Anweisung.

Der Nutzer arbeitet gegebenenfalls mit einem reduzierten Modell. Keine
komplexen Mehrfachaufgaben. Immer diese Reihenfolge:

1. Kurz Ziel, Nicht-Ziel und Akzeptanzkriterien nennen.
2. Read-only-Kontext prüfen, falls die Änderungsstelle nicht sicher bekannt
   ist.
3. Ein kleines, vollständiges `paste.txt`-Skript liefern (bei langen
   Skripten als Datei im Panel liefern, Nutzer speichert sie als
   `paste.txt`).
4. Konkrete lokale Prüfbefehle nennen.
5. Auf deren Ausgabe warten.
6. Erst bei grünem Output das Paket als verifiziert bezeichnen.

Bei Änderungen an Python-Dateien sichere Textanker und eine Zähl-Prüfung
verwenden (Anker muss exakt einmal vorkommen, bei Abweichung abbrechen).
Keine stillen Überschreibungen. Bei Löschungen von Daten: exakte Stückzahl,
erwartete Verteilung pro Zielort und eine Prefix-Allowlist als
Schutzmechanismus angeben.

### Bewährte Anker-Praxis (Session-Fallen, vermeiden)

- Manche Dateien enden ohne abschließenden Zeilenumbruch — Endanker ohne
  `\n` formulieren.
- Anker nie umbrechen: Originalzeilen exakt übernehmen, auch wenn sie lang
  sind.
- Escaping in generierten Testdateien: Regex-Backslashes im äußeren String
  doppelt prüfen. Umlaute in Ankern als `\uXXXX`-Escapes schreiben.
- `paste.txt` niemals zweimal ausführen: Der Anker-Schutz bricht den
  Zweitlauf saubar ab; bei unklarem Zwischenstand zuerst die Markierungen
  prüfen, dann nur die fehlenden Teile als Reparaturpaket liefern. Danach
  immer den Ist-Zustand read-only verifizieren, bevor weitere Pakete folgen.
- Alte `paste.txt`-Reste vergiften Folgepakete: vor der Ausführung `head -3
  paste.txt` prüfen.
- Bei Mehrfachtreffern bewusst `count=N` im Schutzmechanismus verwenden.
- Ein generischer Header-Bump per Regex (`# VERSION:` + Eintrag in
  `# CHANGES:`) hat sich bewährt.
- Chat-Anhänge können Dateinamen doppelt enthalten — vor Vergleichen die
  Dateigröße prüfen.
- Defaults nur an einer Stelle pflegen und per Test fixieren.
- Grep-Falle: exakte Funktionsnamen verwenden; bei Negativbefunden
  zusätzlich die Dateiebene und vorhandene Artefakte prüfen.
- Verifikation von Pfadangaben in der Dokumentation: lokaler `ls`-Output
  statt Annahme.

---

## Lokaler Arbeitsort

- Repository: `MaiTaiMa/photo-workflow`; im Repository liegt der Code unter
  `photo-workflow/` (verschachtelte Wurzel).
- Lokaler Projektordner: `~/Programme/photo-workflow/photo-workflow/`
- Ausführung: `.venv/bin/python paste.txt` (venv über
  `source .venv/bin/activate` aktivieren).
- Tests: `pytest tests/unit/` · Kompilierung:
  `.venv/bin/python -m py_compile <datei>`
- `paste.txt` ist von Git ignoriert und wird nicht committet.
- Nach jeder Änderung: `git diff --check`, ein gezielter Test, danach
  `pytest tests/unit/`; vor Code-Commits die vollständige Suite
  `pytest tests/ -q`.

### Container-Umgebung (lokal vs. NAS)

- Lokal: Podman 4.9.3 mit CLI-Emulation.
- Zielplattform: Synology-NAS (Intel/amd64) mit Container Manager.
- **NAS-Deployment ist seit 2026-09-24 produktiv aufgesetzt** — siehe
  eigenständige Referenzdatei `NAS_DOCKER_DEPLOYMENT_REFERENCE_2026-09-24_v2.md`
  für alle Details (Pfade, Compose-Datei, Task Scheduler, Rechte-Fallstricke).
  Kurzfassung:
  - Projekt liegt unter `/volume2/docker/photo-workflow/`.
  - Aktive Config: `/volume1/TEMP/WORKFLOW_DATA/config/config.nas.yaml`.
  - Container läuft als `user: "1029:100"` (matthias), nicht mehr als root.
  - Task Scheduler eingerichtet und erfolgreich getestet (täglicher Lauf via
    `run_daily.sh`, Uhrzeit noch final festzulegen).
  - Image-Backup vorhanden: `/volume1/TEMP/99_BACKUP/photo-workflow-image_2026-09-24.tar`.

---

## Ausgangslage und Reset

- HEAD nach der Session vom 2026-09-16: `b1e9a0a` „A2: README schlank und
  belegbar", davor `96cebe5` (F12). Beide Commits sind gepusht, der
  Arbeitsbaum ist sauber, die Suite läuft mit 432/432 grün.
- Historisch: `842f8e5` (P7, Container), `0ba9254…` (P3–P6), `7117bf96…`
  (Paket 9a + 7/7b + X2), `468a383` (vor 9a), `acaa970` (Basis).
- Rollback: `git reset --hard <sha>`; vor jedem Reset `git status --short`
  ausführen und relevante JSON- bzw. Face-Pool-Dateien sichern.

---

## Verifizierter Stand

Suite: `tests/` läuft mit 432/432 grün (Stand 2026-09-16, unverändert seit
F12).

**NAS-Deployment (neu, 2026-09-24):** Build erfolgreich (12/12 Schritte,
Image ~468 MB), Smoke-Test mit echten Produktionsdaten bestanden
(`readiness-report` lieferte reale Werte), Task-Scheduler-Testlauf
erfolgreich (Exit-Code 0). Details siehe NAS-Referenzdatei.

### Session 2026-09-16 (Altbestand, weiterhin gültig)

- Erste Policy-1.3-Validierung gezählt: Batch vom 2026-04-24, Zählerstand
  1 von 3 benötigten 1.3-Batches.
- Haltelinien funktionieren (`readiness_not_ready` korrekt gestoppt am
  2026-04-25, 2026-09-05 **und erneut bestätigt am 2026-09-24** beim
  NAS-Testlauf, Batch `2025-11-01`, `full_auto`-Modus, Gate korrekt
  verweigert).
- Face-Review abgeschlossen, `new_faces` überall leer (Altbestand); am
  2026-09-24 erneut 20 neue Face-Vorschläge aus dem NAS-Testlauf offen
  (Lilly, Chris, Michele, Nelly, Finn).
- A2 abgeschlossen und gepusht (`b1e9a0a`).

---

## Offene Punkte (bewusst vertagt, mit Beleg)

Schweregrad-Logik: **hoch** = größter aktueller Baustein (Phase 3, siehe
oben). **Mittel** = blockiert das Zielbild, ist aber sicher. **Niedrig** =
Hygiene, Dokumentation, Aufräumarbeiten.

0. **[hoch] Phase 3 implementieren** — siehe Abschnitt ganz oben. Alle
   anderen Punkte sind nachrangig.
1. **[mittel] Evidenz unter Policy 1.3 sammeln (1/3):** Mindestens zwei
   weitere Batches reviewen → `03_TEMP_DONE` → AUTO-VALIDATE.
2. **[mittel] Evidenz-Qualität bewerten:** Nach etwa drei validierten
   1.3-Batches Übereinstimmung, `keep_precision`, `reject_precision` gegen
   Ziel ≥ 95 % prüfen. Aktuell (Stand 2026-09-24, NAS-Readiness-Report):
   `agreement 89,3–95,8 %`, `keep_precision 57–66,7 %` (Ziel verfehlt),
   `reject_precision 100 %`.
3. **[mittel] F10-Sync-Funktionstest:** `pending_review` muss beim nächsten
   Cull-Lauf auf null fallen.
4. **[mittel] `publish_to_synology_photos`-Schalter klären**, sobald an
   Phase 3 gearbeitet wird — Kommentar in der Config deutet an, dass `false`
   die komplette Phase 3 (nicht nur die API-Anbindung) beendet. Vor
   Implementierungsbeginn per `grep` mit korrektem YAML-Kontext gegenprüfen.
5. **[niedrig] `personal_score` diskriminiert kaum (M0):** unverändert.
6. **[niedrig] Zwei Fingerprint-Algorithmen** dokumentiert.
7. **[niedrig] `torch`/`transformers` im Container** bewusst nicht enthalten.
8. **[niedrig] Altes Image lokal:** `docker rmi 666ec969446e` — Status
   unbestätigt.
9. **[niedrig] Beleg der Pool-Regel** aus `family_recognition`.
10. **[niedrig] Task-Scheduler-Uhrzeit** final festlegen, E-Mail-Option
    bestätigen (Details: NAS-Referenzdatei).
11. **[niedrig] Hyper-Backup-Aufgabe** für `/volume1/TEMP` und
    `/volume1/photo` — Status unbestätigt.
12. **[niedrig] matthias ohne `sudo`/root laufen lassen** — zurückgestellt
    auf ausdrücklichen Wunsch.

---

## Verbleibende Arbeitspakete

### Phase 3 — siehe Abschnitt ganz oben (jetzt höchste Priorität)

### A3 — USER_MANUAL und Spezifikation abgrenzen

`USER_MANUAL` nicht kürzen; nur nachgewiesene sachliche Fehler korrigieren.
`docs/spec_v1-2/...` weder prüfen noch verändern (nur lesen, z. B. für die
Phase-3-API-Spezifikation).

### A4 — Implementierungsregeln, Header, Kommentare (optional, letzter Schritt)

Nur auf ausdrückliche Nutzeranweisung.

### Abschlussziel

Ein sauberes Repository: getesteter Code ✅, kompakte README ✅, erhaltenes
USER_MANUAL, unveränderte Spezifikation, funktionsfähiger Container ✅
(NAS-Deployment seit 2026-09-24 produktiv), **Phase 3 real implementiert
inkl. Metadaten-Handoff an Synology Photos** ⏳ (neuer Schwerpunkt).

---

## Tests und Beweisregeln

Eine Änderung gilt nur als erledigt, wenn der Nutzer den lokalen Output
liefert.

- Dateiänderung: `git diff --check` ohne Ausgabe.
- Syntax: `.venv/bin/python -m py_compile ...` mit Rückgabewert 0.
- Funktion: gezielter Unit-Test grün. Regression: `pytest tests/unit/` grün;
  vor Code-Commits `pytest tests/ -q`.
- Container: erfolgreicher Build plus dokumentierter, datenfreier
  Smoke-Test ✅ (erledigt 2026-09-24).
- **Phase 3 speziell:** zusätzlich zum Unit-Test ein realer Testbatch mit
  3–5 Bildern, der nachweislich im Zielordner landet UND lesbare
  Metadaten (Tags/Rating per `exiftool`) enthält, bevor „implementiert"
  behauptet wird.
- Aussagen über reale Dateien oder Pfade: lokaler Diagnose-Output, keine
  Annahme.
- Datenlöschungen: nur mit exakter Stückzahl, Verteilungsprüfung,
  Prefix-Allowlist und Manifest.

Bei einem Testfehlschlag nur einen kleinen Korrekturschritt anbieten; keine
parallelen Funktionserweiterungen.

---

## Unmittelbare nächste Schritte

1. **Phase 3 planen:** `docs/spec_v1-2/06_SynologyPhotosAPI.md` lesen (nicht
   verändern), `publish_to_synology_photos`-Schalter im Code gegenprüfen,
   Entscheidung XMP/EXIF vs. API-Weg treffen (Empfehlung: XMP/EXIF zuerst).
2. Stand prüfen: `git log --oneline -8` und `git status --short` (HEAD
   `b1e9a0a` erwartet; Push nur auf ausdrückliche Anweisung).
3. Ersten kleinen Phase-3-Baustein umsetzen (z. B. reiner Datei-Move
   `03_TEMP_DONE` → `publish_root`, noch ohne Metadaten), mit
   `paste.txt`-Paket und lokalem Testbatch verifizieren.
4. Danach Metadaten-Schreiben (XMP/EXIF) ergänzen, erneut mit `exiftool`
   verifizieren.
5. Erst danach zu den bestehenden Punkten 1–4 der „Offenen Punkte"
   zurückkehren (Policy-1.3-Evidenz, F10-Sync-Test).
