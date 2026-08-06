<!-- Projekt: Synology Photo Workflow; Pfad: NAS_EXAMPLE/TEMP/WORKFLOW_DATA/models/taste/README.md; Rolle: Lokales Geschmack-/Präferenzmodell -->
# taste

Dieser Ordner nimmt das lokale, aus eigenen Referenzen abgeleitete Präferenz- oder Geschmackmodell auf, sofern diese Funktion im Projekt aktiviert wird. Die hier liegenden Artefakte entstehen aus bewusst bestätigten Referenzen und beschreiben lokale Vorlieben, nicht eine allgemeine Gesichtserkennung. Der Ordner ist damit inhaltlich vom Face-Backend getrennt und dient einer anderen fachlichen Entscheidung. Er darf nicht mit Face-Modellen oder allgemeinen Laufzeitdaten vermischt werden. Wenn die Daten aus einem aktiven Referenzpool stammen, aber nicht als Präferenzmodell trainiert wurden, gehören sie zunächst in `samples/reference` oder `samples/newrefs`.

## Abgrenzung

Dieser Ordner ist nicht für Gesichtserkennung, Quarantäne, Archivierung oder Eingänge vorgesehen. Für Face-Modelle ist `models/family` zuständig, für dynamische Referenzen `samples/reference` und für neue Kandidaten `samples/newrefs`. Hier liegen nur Artefakte, die tatsächlich aus dem lokalen Präferenzprozess stammen.
