# Handover — photo-workflow — Neustart 2026-09-16 (v6.4)

## Startanweisung für den neuen Chat

Arbeite lokal-first, kleinpaketig und token-effizient. Behaupte niemals, dass eine
Änderung implementiert oder verifiziert ist, bevor der Nutzer den lokalen Output
von Ausführung und Tests geliefert hat. GitHub dient nur lesend zur Orientierung;
Änderungen entstehen lokal über `paste.txt`. Kein Commit oder Push ohne
ausdrückliche Anweisung.

Der Nutzer arbeitet gegebenenfalls mit einem reduzierten Modell. Keine komplexen
Mehrfachaufgaben. Immer diese Reihenfolge:

1. Kurz Ziel, Nicht-Ziel und Akzeptanzkriterien nennen.
2. Read-only-Kontext prüfen, falls die Änderungsstelle nicht sicher bekannt ist.
3. Ein kleines, vollständiges `paste.txt`-Skript liefern (bei langen Skripten als
   Datei im Panel liefern, Nutzer speichert sie als `paste.txt` — Terminal-Paste
   zerschneidet mehrzeilige Blöcke zuverlässig, belegt am 2026-09-16).
4. Konkrete lokale Prüfbefehle nennen.
5. Auf deren Ausgabe warten.
6. Erst bei grünem Output das Paket als verifiziert bezeichnen.

Bei Änderungen an Python-Dateien sichere Textanker und eine Zähl-Prüfung
verwenden (Anker muss exakt einmal vorkommen, bei Abweichung abbrechen). Keine
stillen Überschreibungen. Bei Löschungen von Daten: exakte Stückzahl, erwartete
Verteilung pro Zielort und eine Prefix-Allowlist als Schutzmechanismus angeben.

### Bewährte Anker-Praxis (Session-Fallen, vermeiden)

- Manche Dateien enden ohne abschließenden Zeilenumbruch — Endanker ohne `\n`
  formulieren.
- Anker nie umbrechen: Originalzeilen exakt übernehmen, auch wenn sie lang sind.
- Escaping in generierten Testdateien: Regex-Backslashes im äußeren String
  doppelt prüfen. Umlaute in Ankern als `\uXXXX`-Escapes schreiben (bewährt in
  A2.1/A2.2).
- `paste.txt` niemals zweimal ausführen: Der Anker-Schutz bricht den Zweitlauf
  saubar ab; bei unklarem Zwischenstand zuerst die Markierungen prüfen, dann
  nur die fehlenden Teile als Reparaturpaket liefern. Danach immer den
  Ist-Zustand read-only verifizieren, bevor weitere Pakete folgen.
- Alte `paste.txt`-Reste vergiften Folgepakete: vor der Ausführung `head -3
  paste.txt` prüfen (am 2026-09-16 hat ein F12-Altskript korrekt
  abgebrochen — der Schutzmechanismus funktioniert).
- Bei Mehrfachtreffern bewusst `count=N` im Schutzmechanismus verwenden.
- Ein generischer Header-Bump per Regex (`# VERSION:` + Eintrag in `# CHANGES:`)
  hat sich bewährt — der Lauf wird abgebrochen, wenn der Header fehlt.
- Chat-Anhänge können Dateinamen doppelt enthalten — vor Vergleichen die
  Dateigröße prüfen.
- Defaults nur an einer Stelle pflegen und per Test fixieren (die
  S1-Kalibrierungs-Abweichung 0,45/0,65 wurde so entdeckt). Policy-Fixierungen
  in `test_automation_config.py` mitwandern lassen.
- Grep-Falle: exakte Funktionsnamen verwenden; bei Negativbefunden zusätzlich
  die Dateiebene und vorhandene Artefakte prüfen, bevor „fehlt“ behauptet wird.
- Verifikation von Pfadangaben in der Dokumentation: lokaler `ls`-Output statt
  Annahme (der Auto-Learn-Pfad `samples/personal_training/reference/` wurde am
  2026-09-16 so bestätigt, obwohl der Handover ihn verkürzt notiert hatte).

---

## Lokaler Arbeitsort

- Repository: `MaiTaiMa/photo-workflow`; im Repository liegt der Code unter
  `photo-workflow/` (verschachtelte Wurzel).
- Lokaler Projektordner: `~/Programme/photo-workflow/photo-workflow/`
- Ausführung: `.venv/bin/python paste.txt` (venv über `source
  .venv/bin/activate` aktivieren).
- Tests: `pytest tests/unit/` · Kompilierung: `.venv/bin/python -m py_compile
  <datei>`
- `paste.txt` ist von Git ignoriert und wird nicht committet.
- Nach jeder Änderung: `git diff --check`, ein gezielter Test, danach `pytest
  tests/unit/`; vor Code-Commits die vollständige Suite `pytest tests/ -q`.

### Container-Umgebung (lokal vs. NAS)

- Lokal: Podman 4.9.3 mit CLI-Emulation; gangbarer Nachweis lokal:
  `docker build` / `docker run` (Emulation über buildah).
- Zielplattform: Synology-NAS (Intel/amd64) mit Container Manager; das Image
  ist OCI-kompatibel; Deployment optional über `docker save | ssh` und
  `docker load`.

---

## Ausgangslage und Reset

- HEAD nach der Session vom 2026-09-16: `b1e9a0a` „A2: README schlank und
  belegbar“, davor `96cebe5` (F12). Beide Commits sind gepusht, der
  Arbeitsbaum ist sauber, die Suite läuft mit 432/432 grün.
- Historisch: `842f8e5` (P7, Container), `0ba9254…` (P3–P6), `7117bf96…`
  (Paket 9a + 7/7b + X2), `468a383` (vor 9a), `acaa970` (Basis).
- Bekannte Historie: Die S1-Kalibrierung liegt doppelt vor (`ac400d9` und
  `2a1d647`, ein Amend-Rest, kein Defekt — HEAD enthält beide Teile).
- Rollback: `git reset --hard <sha>`; vor jedem Reset `git status --short`
  ausführen und relevante JSON- bzw. Face-Pool-Dateien sichern.

---

## Verifizierter Stand

Suite: `tests/` läuft mit 432/432 grün (Stand 2026-09-16, unverändert seit
F12 — A2 war eine reine Markdown-Änderung).

### Session 2026-09-16 (dieser Stand)

- **Erste Policy-1.3-Validierung gezählt:** Batch vom 2026-04-24 über
  AUTO-VALIDATE in Phase 2 (manuell, kein Handoff-Token nötig). Report:
  `WORKFLOW_DATA/runtime/automation/validation/2026-04-24.json` —
  `policy_version 1.3`, `status evaluable`, 122 von 122 ausgewertet,
  `overall_agreement 0,9583`, `reject_precision 1,0` (21/21),
  `keep_precision 0,6667` (nur 2 von 3 bestätigt, Stichprobe zu klein für eine
  Bewertung), `unreviewed_predictions 0` nach der Auswertung. Die
  F12-Warnung erschien nicht (Batch-ID und Ordnername stimmten überein).
- **Haltelinien funktionieren:** Am 2026-04-25 und am 2026-09-05 wurde
  korrekt am Gate gestoppt (`readiness_not_ready`, 0 von 3 Batches, 0 von 100
  Vorhersagen). Die acht älteren Validierungsreports zählen nicht (ältere
  Policy-Version) — das Fail-Closed-Verhalten arbeitet korrekt. Zählerstand:
  **1 von 3 benötigten 1.3-Batches**.
- **Face-Review abgeschlossen:** Alle Vorschläge wurden vom Nutzer akzeptiert
  und in die jeweiligen Referenzordner verschoben; `new_faces` ist überall
  leer. `selection.json` zeigt weiterhin offene neue Einträge an — die
  F10-Synchronisation läuft erst beim nächsten Cull-Lauf (dieser Lauf hatte
  `batches=0`, daher fand keine Synchronisation statt).
- **A2 abgeschlossen und gepusht (`b1e9a0a`):** README mit Links relativ zum
  Dateiort, Selbstverweise entfernt; neue Abschnitte zu Serienerkennung,
  Bewertung und Schlagwörtern (Lächeln-Score 0,05, Schlagwort ab 0,45,
  CLIP-Entscheidung), Face-Sync (F10) mit Live-`pending_review` (F9),
  AUTO-VALIDATE mit fixierter Policy 1.3, Gate-Schwellen, F11/F12 und
  Benennungsregel, sowie Synology-Indexierung (S2). Der Auto-Learn-Pfad
  `samples/personal_training/reference/` ist per `ls`-Ausgabe belegt.
  Bekannte Kosmetik: drei doppelte Leerzeilen (bewusst belassen).

### Altbestand (unverändert gültig, Details siehe v6.3)

Serienlogik (committet, real belegt), F7–F12, S1 mit Kalibrierung 0,45, S2,
A1.1–A1.5 mit Waisen-Bereinigung, F10-Sync-Implementierung,
Predictions-Persistenz (`write_prediction_batch`, 522 Prognosen unter Policy
1.3, davon 127 Ablehnungen), CLIP-Entscheidung (deaktiviert lassen), Container
schlank gehalten (etwa 500 MB).

---

## Offene Punkte (bewusst vertagt, mit Beleg)

Schweregrad-Logik: **mittel** bedeutet, der Punkt blockiert das Zielbild
(KI-Assistent mit echter Evidenz), ist aber sicher. **Niedrig** bedeutet
Hygiene, Dokumentation oder Aufräumarbeiten.

1. **[mittel] Evidenz unter Policy 1.3 sammeln (1/3):** Mindestens zwei
   weitere Batches reviewen → `03_TEMP_DONE` → AUTO-VALIDATE. Danach auch das
   Minimum von 100 Vorhersagen im Blick behalten (122 sind bereits
   ausgewertet).
2. **[mittel] Evidenz-Qualität bewerten:** Nach etwa drei validierten
   1.3-Batches Übereinstimmung, `keep_precision` und `reject_precision` gegen
   das Ziel von jeweils mindestens 95 % prüfen. Die Ablehnungsquote der
   Prognosen liegt bei etwa 24 % (127 von 522) — beobachten, ob die
   Präzision das trägt. Jede Schwellenänderung erfordert einen neuen
   Policy-Bump.
3. **[mittel] F10-Sync-Funktionstest:** Beim nächsten Cull-Lauf muss
   `pending_review` auf null fallen und `selection.json` (inklusive
   Fingerprints, A1.5) aktualisiert werden. Andernfalls die Sync-Verdrahtung
   in `cull_folder` gezielt prüfen.
4. **[mittel] Beobachtungspunkt `unreviewed_predictions`:** Im Readiness-
   bzw. Gate-Block des Abschlussberichts beim nächsten Haltelinien-Lauf
   prüfen, ob der Aggregatzähler korrekt läuft (er liegt im Gate-Output, nicht
   im Run-Summary-JSON — dort nicht suchen, belegt am 2026-09-16).
5. **[niedrig] `personal_score` diskriminiert kaum (M0):** Streuung von 0,100
   über 811 Bilder, seit F11 unschädlich. Auslöser für eine erneute Prüfung:
   `keep_precision` dauerhaft unter 95 %.
6. **[niedrig] Zwei Fingerprint-Algorithmen** sind dokumentiert.
7. **[niedrig] `torch`/`transformers` im Container** bewusst nicht enthalten.
8. **[niedrig] Altes Image lokal:** `docker rmi 666ec969446e` — Erfolg noch
   unbestätigt (`docker images | grep photo-workflow`).
9. **[niedrig] Beleg der Pool-Regel:** Soll-Größen aus `family_recognition`
   (Maximum/Minimum 200/3) — nicht erfinden, sondern belegen.
10. **[niedrig] Optional:** Den Batch vom 2026-04-24 mit der Lächeln-Schwelle
    0,45 erneut taggen — nur auf Nutzerwunsch; gemeinsame
    Landmark-Berechnung für Augen und Lächeln als mögliche
    Laufzeitoptimierung.

---

## Verbleibende Arbeitspakete

### A3 — USER_MANUAL und Spezifikation abgrenzen

`USER_MANUAL` nicht kürzen; nur nachgewiesene sachliche Fehler bei separatem
Bedarf korrigieren (Kandidat: ein kurzer Verhaltenshinweis zur
Benennungsregel, inzwischen auch in der README verankert).
`docs/spec_v1-2/...` weder prüfen noch verändern.

### A4 — Implementierungsregeln, Header, Kommentare (optional, letzter Schritt)

Nur auf ausdrückliche Nutzeranweisung: projektweit read-only prüfen, Funde
zunächst als Bericht liefern, danach kleine Korrekturen mit Tests.

### Abschlussziel

Ein sauberes Repository: getesteter Code ✅, kompakte und belegbare README ✅
(A2 erledigt), erhaltenes USER_MANUAL, unveränderte Spezifikation,
nachvollziehbare Header und Kommentare, funktionsfähiger Container.

---

## Tests und Beweisregeln

Eine Änderung gilt nur als erledigt, wenn der Nutzer den lokalen Output
liefert.

- Dateiänderung: `git diff --check` ohne Ausgabe.
- Syntax: `.venv/bin/python -m py_compile ...` mit Rückgabewert 0.
- Funktion: gezielter Unit-Test grün. Regression: `pytest tests/unit/` grün;
  vor Code-Commits `pytest tests/ -q`.
- Container: erfolgreicher Build plus dokumentierter, datenfreier
  Smoke-Test.
- Aussagen über reale Dateien oder Pfade: lokaler Diagnose-Output, keine
  Annahme.
- Datenlöschungen: nur mit exakter Stückzahl, Verteilungsprüfung,
  Prefix-Allowlist und Manifest; Abbruch bei jeder Abweichung.

Bei einem Testfehlschlag nur einen kleinen Korrekturschritt anbieten; keine
parallelen Funktionserweiterungen.

---

## Unmittelbare nächste Schritte

1. Stand prüfen: `git log --oneline -8` und `git status --short` (HEAD
   `b1e9a0a` erwartet; Push nur auf ausdrückliche Anweisung).
2. Den nächsten Batch verarbeiten und reviewen → `03_TEMP_DONE`. Dabei
   beobachten:
   a) F10-Sync: `pending_review` muss auf null fallen (die akzeptierten
      Vorschläge liegen bereits in den Referenzordnern).
   b) AUTO-VALIDATE unter Policy 1.3 → zweite Validierung; Zählerstand 2/3.
   c) Readiness-Block: das Aggregat `unreviewed_predictions` prüfen.
3. Nach drei validierten 1.3-Batches: Evidenz-Qualität bewerten (siehe
   offener Punkt 2).
4. A3 und A4 nur auf ausdrückliche Anweisung durchführen.
