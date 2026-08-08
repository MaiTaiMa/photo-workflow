# Implementierung eines Arbeitspakets

Implementiere das Arbeitspaket aus:

`[AP-DATEI].md`

im bereits analysierten und empfohlenen Repository.

## Verbindliche Grundlagen

Nutze als Grundlage ausschließlich:

1. `00AP.md` – verbindliche Gesamtarchitektur
2. `[AP-DATEI].md` – Spezifikation des aktuellen Arbeitspakets
3. den bestehenden Repository-Code und dessen Tests

Die vollständige Spezifikation v1.1 und v10.2 sind nur dann zusätzlich zu konsultieren, wenn die oben genannten Dokumente eine konkrete Frage nicht eindeutig beantworten.

## Aufgabe

Setze **ausschließlich das angegebene Arbeitspaket** vollständig um.

Dabei:

- bestehende Architektur einhalten,
- definierte Schnittstellen unverändert verwenden,
- definierte Datenmodelle einhalten,
- bestehende Funktionalität nicht unnötig verändern,
- keine zusätzlichen Features entwickeln,
- keine zukünftigen Funktionen aus v10.2 implementieren,
- kein ungeplantes Refactoring durchführen.

Analysiere vor der Änderung nur die für das Arbeitspaket relevanten Dateien und deren direkte Abhängigkeiten.

## Implementierung

Alle im AP definierten Dateien, Funktionen, Klassen und Schnittstellen müssen tatsächlich implementiert und in den vorgesehenen Workflow integriert werden.

Keine Stubs, ungenutzten Funktionen oder nicht verdrahteten Module hinterlassen.

Falls die Umsetzung eine Änderung an `00AP.md`, einer bestehenden Schnittstelle oder einem anderen abgeschlossenen AP erfordern würde:

**nicht eigenständig ändern**, sondern den Konflikt melden und vor der Änderung anhalten.

## Tests

Führe die im AP definierten Tests aus bzw. ergänze sie.

Prüfe mindestens:

- Importierbarkeit der geänderten Module
- relevante Unit-Tests
- relevante Integrationstests
- bestehende Tests, soweit sie durch die Änderung betroffen sein können
- einen geeigneten Smoke-Test

Behebe Fehler nur, wenn sie durch dieses Arbeitspaket verursacht werden oder für dessen korrekte Implementierung notwendig sind.

## Abschluss

Gib nach der Implementierung kompakt aus:

**Geändert:**
- neue/geänderte Dateien

**Umgesetzt:**
- wichtigste implementierte Funktionen

**Tests:**
- ausgeführte Tests
- Ergebnis

**Abweichungen/Probleme:**
- nur falls vorhanden

**AP-Status:**
- ABGESCHLOSSEN
- oder BLOCKIERT mit Begründung

Implementiere anschließend **kein weiteres Arbeitspaket** und warte auf die Freigabe für das nächste AP.