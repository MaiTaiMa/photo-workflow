# AP22.0 Regel-Audit

## Zweck

Der Audit prüft die projektweiten Regeln aus `98AP_IMPLEMENTATION_RULES.md`, ohne Quelldateien zu verändern. Er ist eine Prüfgrundlage für die folgenden Style- und Dokumentationspakete.

## Ausführung

```bash
python tools/style_audit.py photo-workflow
```

Der Prozess schreibt einen JSON-Befund nach stdout. Exit-Code `0` bedeutet, dass der Audit keine Befunde erzeugt hat. Exit-Code `1` bedeutet, dass mindestens eine Datei geprüft werden muss.

## Prüfungen

- Python- und Bash-Header mit Skriptname, Zweck, Version und Änderungshistorie.
- Versionsnummer im Header.
- Mindestmaß an Funktionskommentaren.
- Maximale Zeilenlänge von 100 Zeichen.
- JSON-Wurzel als Objekt.
- `schema_version` und `producer_version` in JSON-Artefakten.
- Verbotene persistierte Felder wie Embeddings, Bildbytes und Secrets.

## Grenzen

Der Audit bewertet Kommentarstruktur und Kommentarquote heuristisch. Er ersetzt keine fachliche Prüfung der Spezifikation und keine menschliche Prüfung von Funktionsnamen, README-Inhalten oder der tatsächlichen NAS-Sicherheit.

## Nächster Schritt

AP22.1 überarbeitet zuerst die neuen Python-Kernmodule. Danach werden Legacy-Dateien, Shell-/Docker-Dateien, Configs und READMEs in getrennten Arbeitspaketen korrigiert.
