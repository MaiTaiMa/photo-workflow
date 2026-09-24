# Handover — photo-workflow — Neustart 2026-09-24 (v7.1)

## 🎯 NÄCHSTER GROSSER AUFTRAG: Phase 3 implementieren

**Das ist weiterhin der wichtigste offene Punkt.** Heute (2026-09-24) wurde
Phase 3 erstmals live auf dem NAS getestet — die Sicherheitslage ist jetzt
mit echtem Output belegt, nicht mehr nur Code-Lektüre.

### Heutige Testreihe (2026-09-24, 15:26–15:35 Uhr, alle mit `--dry-run`)

| # | Befehl (`--folder` / `--target`) | Ergebnis |
|---|---|---|
| 1 | `--folder BATCHNAME` (Platzhalter-Test) | `Batch-Ordner existiert nicht: BATCHNAME` — Docker-Syntax bestätigt korrekt |
| 2 | `--folder 2025-11-01` (nur Batch-Name) | `Batch-Ordner existiert nicht: 2025-11-01` — bare Name wird NICHT mit `TEMP_DONE` verknüpft |
| 3 | `--folder /volume1/TEMP/03_TEMP_DONE/2025-11-01` (voller Pfad) | weiterhin „existiert nicht" — Batch lag nicht mehr dort |
| 4 | `--folder /volume1/TEMP/04_TEMP_FINAL/2025-11-01` (voller Pfad, korrekter Ort) | **`[PHASE3] Ergebnis: finalization_disabled`** — Ordner gefunden, aber sauber gestoppt |

### Ergebnis: Phase 3 ist heute dreifach als sicher verifiziert

1. **Pipeline-Dispatcher:** `run_phase3(cfg, folder)` ist im `pipeline`-Befehl
   fest auskommentiert (`app/photo_workflow.py`) — der tägliche Task-
   Scheduler-Lauf kann Phase 3 nie real auslösen.
2. **Config-Schalter:** `publish_to_synology_photos.enabled: false` in
   `config.nas.yaml` — Kommentar im Original: „false beendet PHASE3 ohne
   Datei- oder API-Aktion". Genau das trat heute ein.
3. **Live-Test mit echtem Batch:** Direkter `phase3`-Subbefehl mit realem,
   existierendem Batch (`2025-11-01`) endete nachweislich bei
   `{'status': 'finalization_disabled', 'batch_id': '2025-11-01'}` —
   `Moved/Merged: 0`, `Finalized: 0`, `Errors: 0`. Kein `synoindex`-Aufruf,
   kein API-Call, keine Dateibewegung.

**Damit ist die ursprüngliche Sorge des Nutzers („hat die NAS von sich aus
einen Init-Befehl gesendet, der die Synology-Indexierung ausgelöst hat")
für den heutigen Tag mit echtem Output widerlegt.** Die hohe NAS-Last vom
Nachmittag kam von unabhängigen Synology-Diensten (Photos-Indexierung,
Drive-Sync, Thumbnail-Erzeugung — siehe `top`-Output), nicht vom Workflow.
Der einzige zusätzliche Lauf um 16:17 Uhr wurde vom Nutzer selbst bewusst
über die DSM-Weboberfläche ausgelöst.

### Zwei Dokumentations-Lücken, live gefunden (zu korrigieren)

1. **`--folder`-Argument erwartet einen vollen Pfad**, nicht nur den
   Batch-Namen. `run_phase3()` führt bei explizit übergebenem `--folder`
   lediglich `Path(folder)` aus, **ohne** Verknüpfung mit
   `paths.temp_done`/`temp_final` — anders als der automatische Modus ohne
   `--folder` (der intern bereits den vollen Pfad aus der Batch-Liste holt).
   Das README-Beispiel (`phase3 --folder 2025-11-01 --target ...`) ist damit
   irreführend. Fix-Kandidat: entweder Doku korrigieren (vollen Pfad
   verlangen) oder Code so anpassen, dass ein bare Name automatisch mit
   `temp_final` verknüpft wird — Entscheidung für den nächsten
   Implementierungsschritt offen.
2. **Abgeschlossene Batches liegen nach Phase 2 in `04_TEMP_FINAL`**, nicht
   wie in `docs/spec_v1-2/00_Geltungsbereich_und_Zielbild.md` beschrieben in
   `03_TEMP_DONE`. Die Spezifikation nennt `03_TEMP_DONE` explizit als
   PHASE3-Quelle — das widerspricht dem live beobachteten Zustand. Vor dem
   nächsten Implementierungsschritt klären, ob die Spezifikation veraltet
   ist oder ob `04_TEMP_FINAL` versehentlich zum Endpunkt wurde, wo eigentlich
   PHASE3 selbst hätte greifen sollen.

### Empfohlener nächster Schritt (noch nicht ausgeführt)

Ein **kontrollierter Pilotlauf mit `enabled: true` + `--dry-run`**, um zu
sehen, ob der eigentliche Transfer-Pfad (`[PHASE3] Dry-Run: <source> ->
<target>`) korrekt greift, wenn der Schalter kurzzeitig aktiviert wird:

1. In `config.nas.yaml` temporär `publish_to_synology_photos.enabled: true`
   setzen (nur lokal auf dem NAS, nicht committen).
2. Denselben Befehl wie Testreihe #4 erneut mit `--dry-run` ausführen.
3. Erwartung: `[PHASE3] Dry-Run: /volume1/TEMP/04_TEMP_FINAL/2025-11-01 ->
   /volume1/photo/wirser` — weiterhin keine echte Dateibewegung, aber jetzt
   sichtbar, ob der Transfer-Pfad grundsätzlich funktioniert.
4. Schalter danach sofort wieder auf `false` zurücksetzen.
5. Erst danach über einen echten (nicht-Dry-Run) Piloten mit einem kleinen
   Testbatch nachdenken — inklusive Metadaten-Handoff-Weg (XMP/EXIF
   empfohlen, siehe unten).

### Ziel (unverändert)

Phase 3 so implementieren, dass sie zwei Dinge leistet: Datei-Transfer
`04_TEMP_FINAL` (korrigierter Ort, siehe oben) → `publish_root`, und
Metadaten-Handoff an Synology Photos (Tags, Rating, erkannte Personen,
Serien-Zugehörigkeit).

### Relevante Config-Sektion (`config.nas.yaml`, bestätigt am 2026-09-24)

```
publish_root: /volume1/photo
faces.target_folder (Person "wirser"): /volume1/photo/wirser
finalization.enabled: true
finalization.mode: copy          # "move/copy, verify, source removal — copy erhält die Quelle"
publish_to_synology_photos.enabled: false   # Hauptschalter — aktuell AUS
album_upsert: false               # "nur nach erfolgreichem Pilotlauf auf true setzen"
synology_api:
  protocol: http
  write_rating: true
  write_tags: true
  # Endpunkt ohne Pilotlauf-Nachweis — siehe docs/spec_v1-2/06_Synology_Photos_API.md
```

### Zwei mögliche technische Wege für den Metadaten-Handoff (unverändert, zu bewerten)

1. **XMP/EXIF-Sidecar-Schreiben** vor dem Datei-Move (ExifTool bereits im
   Container installiert — `libimage-exiftool-perl`). Synology Photos liest
   EXIF/XMP beim Indexieren automatisch mit ein. **Empfehlung: zuerst
   diesen Weg verfolgen.**
2. **Synology Photos API direkt ansprechen** (`synology_api`-Sektion) —
   laut Spezifikation „Adapter ist vorbereitet, aber `apply_metadata()`
   noch nicht vollständig implementiert". Genauer steuerbar, aber
   abhängig vom nicht pilotierten Endpunkt.

### Akzeptanzkriterien (bevor „implementiert" behauptet wird)

- Pilotlauf mit `enabled: true` + `--dry-run` zeigt korrekte
  Dry-Run-Zeile mit Quelle/Ziel (siehe „Empfohlener nächster Schritt").
- Ein Testbatch mit 3–5 Bildern läuft vollständig durch und landet
  nachweislich unter `/volume1/photo/<person>/` mit korrektem Eigentümer.
- Mindestens Tags oder Rating sind nach dem Move in den Dateien
  nachweisbar (`exiftool <datei>`).
- `sudo synoindex -A /volume1/photo/<ORDNER>` angestoßen, Sichtprüfung in
  der Synology Photos Weboberfläche.
- Kein bestehender Test (`pytest tests/unit/`) wird rot.
- Die beiden Dokumentations-Lücken (Pfad-Erwartung `--folder`,
  `03_TEMP_DONE` vs. `04_TEMP_FINAL`) sind vor dem Implementierungsschritt
  bewusst aufgelöst (Entscheidung dokumentiert, nicht nur übersehen).

---

## Startanweisung für den neuen Chat (unverändert gültig)

Arbeite lokal-first, kleinpaketig und token-effizient. Behaupte niemals,
dass eine Änderung implementiert oder verifiziert ist, bevor der Nutzer den
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
  prüfen, dann nur die fehlenden Teile als Reparaturpaket liefern.
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
  statt Annahme — bewahrheitet sich erneut am 2026-09-24 (Phase-3-Pfadtest).
- **Neu (2026-09-24): Shell-Syntax in Testbefehlen prüfen.** Platzhalter
  wie `<NAME>` werden von `sh` als Ein-/Ausgabe-Umleitung interpretiert
  (`-sh: NAME: No such file or directory`). In Beispielbefehlen nie
  spitze Klammern für Platzhalter verwenden.
- **Neu (2026-09-24): CLI-Argumente nicht ungeprüft aus README übernehmen.**
  `--folder <name>` ohne vollen Pfad funktioniert bei Phase 3 nicht wie
  dokumentiert — vor jedem CLI-Test kurz im Code gegenprüfen, was der
  Parameter wirklich erwartet.

---

## Lokaler Arbeitsort

- Repository: `MaiTaiMa/photo-workflow`; im Repository liegt der Code unter
  `photo-workflow/` (verschachtelte Wurzel). Default-Branch: `main`.
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
- **NAS-Deployment seit 2026-09-24 produktiv**, inklusive erfolgreichem
  Phase-3-Sicherheitstest (siehe oben). Details zu Pfaden, Compose-Datei,
  Task Scheduler, Rechte-Fallstricken: separate Referenzdatei
  `NAS_DOCKER_DEPLOYMENT_REFERENCE_2026-09-24_v2.md`.
- Projekt liegt unter `/volume2/docker/photo-workflow/`.
- Aktive Config: `/app/config/config.nas.yaml` (im Container gemountet aus
  `./config` relativ zur `docker-compose.yml`).
- Container läuft als `user: "1029:100"` (matthias) für den regulären
  `pipeline`-Befehl; Ad-hoc-Testbefehle mit `sudo docker compose run`
  laufen unter dem aufrufenden Systembenutzer.
- Docker-Compose-Kern:
  ```yaml
  services:
    photo_workflow:
      build: .
      container_name: synology_photo_workflow
      volumes:
        - /volume1/TEMP:/volume1/TEMP
        - ./config:/app/config
      working_dir: /app
      command: ["--config", "/app/config/config.yaml", "pipeline"]
      restart: "no"
  ```
- Manueller Phase-3-Testaufruf-Muster (siehe Testreihe oben):
  ```bash
  sudo docker compose run --rm photo_workflow --config /app/config/config.nas.yaml phase3 --folder <VOLLER_PFAD> --target /volume1/photo/<PERSON> --dry-run
  ```
- Diagnose „was sieht der Container wirklich" (Mount-/Namensprüfung ohne
  Workflow-Logik):
  ```bash
  sudo docker compose run --rm --entrypoint sh photo_workflow -c "ls -la /volume1/TEMP/04_TEMP_FINAL/"
  ```

---

## Ausgangslage und Reset

- HEAD nach der Session vom 2026-09-16: `b1e9a0a` „A2: README schlank und
  belegbar", davor `96cebe5` (F12). Beide Commits sind gepusht, der
  Arbeitsbaum ist sauber, die Suite läuft mit 432/432 grün.
- Historisch: `842f8e5` (P7, Container), `0ba9254…` (P3–P6), `7117bf96…`
  (Paket 9a + 7/7b + X2), `468a383` (vor 9a), `acaa970` (Basis).
- Rollback: `git reset --hard <sha>`; vor jedem Reset `git status --short`
  ausführen und relevante JSON- bzw. Face-Pool-Dateien sichern.
- Am 2026-09-24 wurden **keine Code-Änderungen committet** — die gesamte
  Session war Diagnose/Test auf dem NAS, kein Push.

---

## Verifizierter Stand

Suite: `tests/` läuft mit 432/432 grün (Stand 2026-09-16, unverändert seit
F12).

**NAS-Deployment (2026-09-24):** Build erfolgreich, Smoke-Test bestanden,
Task-Scheduler-Testlauf erfolgreich (drei manuelle Läufe: 15:47, 15:49,
16:17 Uhr — letzterer bewusst über die DSM-Weboberfläche ausgelöst).
**Phase-3-Sicherheitstest (2026-09-24, neu):** Vier `--dry-run`-Aufrufe,
letzter mit echtem Batch endet korrekt bei `finalization_disabled` — siehe
Abschnitt ganz oben für die volle Testreihe und Beweislage.

### Session 2026-09-16 (Altbestand, weiterhin gültig)

- Erste Policy-1.3-Validierung gezählt: Zählerstand 1 von 3 benötigten
  1.3-Batches.
- Haltelinien funktionieren (`readiness_not_ready` korrekt gestoppt am
  2026-04-25, 2026-09-05 und erneut am 2026-09-24 bei Batch `2025-11-01`,
  `full_auto`-Modus).
- Face-Review: 20 neue Vorschläge aus dem heutigen NAS-Testlauf offen
  (Lilly, Chris, Michele, Nelly, Finn).
- A2 abgeschlossen und gepusht (`b1e9a0a`).

---

## Offene Punkte (bewusst vertagt, mit Beleg)

Schweregrad-Logik: **hoch** = größter aktueller Baustein. **Mittel** =
blockiert das Zielbild, ist aber sicher. **Niedrig** = Hygiene/Doku.

0. **[hoch] Phase 3 implementieren** — siehe Abschnitt ganz oben.
   Sicherheitslage heute dreifach verifiziert; nächster Schritt ist der
   Pilotlauf mit `enabled: true` + `--dry-run` (noch nicht ausgeführt).
0b. **[hoch, neu] Zwei Doku/Code-Diskrepanzen aus dem heutigen Test
    klären**, bevor an der echten Implementierung weitergearbeitet wird:
    `--folder`-Pfaderwartung und `03_TEMP_DONE` vs. `04_TEMP_FINAL` als
    PHASE3-Quelle (Details oben).
1. **[mittel] Evidenz unter Policy 1.3 sammeln (1/3):** unverändert.
2. **[mittel] Evidenz-Qualität bewerten:** Stand 2026-09-24:
   `agreement 89,3–95,8 %`, `keep_precision 57–66,7 %` (Ziel ≥95 % verfehlt),
   `reject_precision 100 %`.
3. **[mittel] F10-Sync-Funktionstest:** unverändert.
4. **[niedrig] `personal_score` diskriminiert kaum (M0):** unverändert.
5. **[niedrig] Zwei Fingerprint-Algorithmen** dokumentiert.
6. **[niedrig] `torch`/`transformers` im Container** bewusst nicht enthalten.
7. **[niedrig] Altes Image lokal:** `docker rmi 666ec969446e` — Status
   unbestätigt.
8. **[niedrig] Beleg der Pool-Regel** aus `family_recognition`.
9. **[niedrig] Task-Scheduler-Uhrzeit** final festlegen.
10. **[niedrig] Hyper-Backup-Aufgabe** — Status unbestätigt.
11. **[niedrig] matthias ohne `sudo`/root laufen lassen** — zurückgestellt.

---

## Verbleibende Arbeitspakete

### Phase 3 — höchste Priorität (siehe ganz oben)

Nächster konkreter Schritt: Pilotlauf mit `enabled: true` + `--dry-run`,
danach Entscheidung zu den zwei Doku/Code-Diskrepanzen, danach erster
kleiner `paste.txt`-Baustein für den Metadaten-Handoff (XMP/EXIF-Weg
empfohlen).

### A3 — USER_MANUAL und Spezifikation abgrenzen

`USER_MANUAL` nicht kürzen. `docs/spec_v1-2/...` weder prüfen noch
verändern außer für die heute gefundene `03_TEMP_DONE`/`04_TEMP_FINAL`-
Diskrepanz, die explizit zur Klärung vorgemerkt ist.

### A4 — Implementierungsregeln, Header, Kommentare (optional)

Nur auf ausdrückliche Nutzeranweisung.

### Abschlussziel

Getesteter Code ✅, kompakte README ✅, erhaltenes USER_MANUAL,
funktionsfähiger Container ✅, **Phase 3 real implementiert inkl.
Metadaten-Handoff an Synology Photos** ⏳ — Sicherheitslage heute
verifiziert, Implementierung selbst steht noch aus.

---

## Tests und Beweisregeln

Eine Änderung gilt nur als erledigt, wenn der Nutzer den lokalen Output
liefert.

- Dateiänderung: `git diff --check` ohne Ausgabe.
- Syntax: `.venv/bin/python -m py_compile ...` mit Rückgabewert 0.
- Funktion: gezielter Unit-Test grün. Regression: `pytest tests/unit/`
  grün; vor Code-Commits `pytest tests/ -q`.
- Container: erfolgreicher Build plus datenfreier Smoke-Test ✅.
- **Phase 3 speziell:** zusätzlich ein realer Testbatch mit 3–5 Bildern,
  der nachweislich im Zielordner landet UND lesbare Metadaten enthält,
  bevor „implementiert" behauptet wird. Vorstufe (Pilotlauf mit
  `enabled: true` + `--dry-run`) noch offen.
- Aussagen über reale Dateien oder Pfade: lokaler Diagnose-Output, keine
  Annahme (heute mehrfach bestätigt als richtige Vorgehensweise).
- Datenlöschungen: nur mit exakter Stückzahl, Verteilungsprüfung,
  Prefix-Allowlist und Manifest.

---

## Unmittelbare nächste Schritte

1. **Pilotlauf:** `publish_to_synology_photos.enabled` temporär auf `true`
   setzen, denselben `phase3`-Befehl mit `--dry-run` und dem Pfad
   `/volume1/TEMP/04_TEMP_FINAL/2025-11-01` erneut ausführen, Ausgabe
   prüfen (`[PHASE3] Dry-Run: ... -> ...` erwartet). Schalter danach sofort
   zurück auf `false`.
2. Die zwei Doku/Code-Diskrepanzen entscheiden: `--folder`-Pfaderwartung
   und `03_TEMP_DONE` vs. `04_TEMP_FINAL`.
3. Stand prüfen: `git log --oneline -8` und `git status --short` (HEAD
   `b1e9a0a` erwartet; Push nur auf ausdrückliche Anweisung).
4. Ersten kleinen Phase-3-Baustein umsetzen (Datei-Move, danach
   Metadaten-Schreiben), mit `paste.txt`-Paket und lokalem Testbatch
   verifizieren.
5. Erst danach zu den bestehenden Punkten 1–3 der „Offenen Punkte"
   zurückkehren (Policy-1.3-Evidenz, F10-Sync-Test).
