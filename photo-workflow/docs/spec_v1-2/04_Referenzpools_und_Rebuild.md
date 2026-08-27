# 5. Referenzpool-Verwaltung, Rebuild und Nutzen-Ranking

- **Status:** Pflicht, sobald der Geschmacks- oder Face-Adapter aktiviert ist.

## 5.1 Ziel

Die Referenzpool-Verwaltung ist die gemeinsame Regel für Geschmack und bekannte Gesichter. Sie stellt sicher, dass aktive Referenzen klein, qualitativ sinnvoll und divers bleiben. Sie trennt Vorschlagsdateien von aktiven Referenzen, erzwingt menschliche Freigabe, aktualisiert Wahrheitsdateien und baut bei jeder aktiven Änderung die Referenzbasis neu auf.

## 5.2 Geltungsbereich

Diese Regeln gelten für:
- Face-Referenzpools: `WORKFLOW_DATA/faces/<slug>` (je bekannte Person)
- Geschmacks-Referenzpool: `WORKFLOW_DATA/samples`

Nicht Gegenstand dieser Regel sind Manual Keep, technische Culling-Bilder (außerhalb der speziell konfigurierten Modellbasis) und unbekannte Gesichter.

## 5.3 Ordnerstruktur

Jeder Pool muss folgende Struktur haben:

```text
pool_root/
  reference/          # Aktive Referenzen (max. max_active)
  new/                # Vorschläge (max. max_new, max. max_new_per_batch pro Batch)
  selection.json      # EINZIGE Wahrheit für diesen Pool
```

- Face: `pool_root = WORKFLOW_DATA/faces/<slug>`, `new = new_faces`, Dateien = Face-Crops.
- Geschmack: `pool_root = WORKFLOW_DATA/samples`, `new = new_refs`, Dateien = Ganzbilder.

Bei Face-Pools werden neue Face-Crops automatisch ausschließlich in `new_faces/` gespeichert. Die manuelle Verschiebung nach `reference/` ist der einzige Aktivierungsschritt. Bei Geschmackspools werden Vorschläge in `new_refs/` gespeichert und ebenfalls nur manuell nach `reference/` aktiviert.

## 5.4 Wahrheitsdatei (`selection.json`)

Jeder Pool hat genau eine `selection.json` im Hauptordner. Sie ist die alleinige Wahrheit über aktive Referenzen, offene Vorschläge, Kapazitätsgrenzen, Auswahlfingerprint und Rangdetails.

**Pflichtfelder:**
- `schema_version`
- `pool_type`
- `slug` (nur Face)
- `updated_at`
- `selection_fingerprint`
- `pool_build_id`
- `rank_digits`
- `limits`
- `images`

**Verboten:** Embeddings, Bildbytes, Face-Crops oder andere binäre Daten in `selection.json`.

## 5.5 Bild-Metadaten

Jeder Eintrag in `images` muss folgende Felder enthalten:
- `source_id`
- `batch_id`
- `path` oder `crop_source`
- `status` (`active`, `new` oder `unknown`)
- `quality_score`
- `pool_utility_score` oder `candidate_utility_score`
- `pool_rank` nur bei `active`
- `approved_at` nur bei `active`

Face-spezifisch: `bounding_box`, `face_confidence`, `original_path`.
Geschmacksspezifisch: `base_score`.

`unknown` darf ausschließlich durch Recovery entstehen. Ein Eintrag mit `unknown` darf weder für Matching noch für Training verwendet werden.

## 5.6 Kapazitätsgrenzen

| Grenze | Typ | Wirkung |
|---|---|---|
| `max_active` | Hard Limit | Darf nicht überschritten werden; weitere Aktivierungen blockiert. |
| `max_new` | Hard Limit | Darf nicht überschritten werden; weitere Vorschläge blockiert. |
| `max_new_per_batch` | Hard Limit | Pro `batch_id` darf diese Grenze nicht überschritten werden. |
| `min_active` | Soft Limit | Wenn der Wert unterschritten wird, pausiert nur der betroffene Adapter. Sein Score wird `null`; der übrige Batch-Lauf wird fortgesetzt. Eine Reaktivierung erfolgt erst nach erfolgreichem Rebuild mit ausreichender aktiver Referenzmenge. |
| `target_active` | Ziel | Angestrebter Bereich; System meldet, wenn deutlich darunter oder darüber. |

## 5.7 Konfiguration

```yaml
reference_pools:
  common:
    max_active: 100
    min_active: 30
    target_active: 50
    max_new: 20
    max_new_per_batch: 5

  taste:
    min_quality_score: 0.70
    max_redundancy: 0.90
    base_score_pool_size: 50

  faces:
    min_quality_score: 0.70
    max_redundancy: 0.95
    crop_size: 256
    min_face_size: 128
```

## 5.8 Sinnvolle Wertebereiche

| Parameter | Sinnvoller Bereich | Empfohlener Startwert | Begründung |
|---|---|---|---|
| `max_active` (Face) | 30–200 | 100 | Genug Diversität ohne unnötige Rechenlast. |
| `max_active` (Geschmack) | 30–200 | 100 | Ähnlich wie Face; persönliche Präferenzen sind komplexer. |
| `min_active` | 20–50 | 30 | Mindestqualität für Training. |
| `target_active` | 30–100 | 50 | Zielbereich des Pools. |
| `max_new` | 10–50 | 20 | Begrenzte Anzahl offener Entscheidungen. |
| `max_new_per_batch` | 3–10 | 5 | Schutz vor Batch-Fluten. |
| `crop_size` (Face) | 128–512 | 256 | Gute Balance aus Genauigkeit und Effizienz. |
| `min_quality_score` | 0.6–0.8 | 0.7 | Filtert schlechte Bilder. |
| `max_redundancy` (Face) | 0.90–0.98 | 0.95 | Face-Crops können ähnlicher sein. |
| `max_redundancy` (Geschmack) | 0.85–0.95 | 0.90 | Geschmackspool soll diverser sein. |

## 5.9 Auswahl neuer Vorschläge

Die Auswahl neuer Vorschläge folgt derselben Logik:

1. Nur menschlich bestätigte `keep`-Bilder sind Kandidaten.
2. Kandidaten müssen `min_quality_score` erreichen.
3. Kandidaten dürfen bestehende aktive Referenzen nicht zu stark duplizieren.
4. Es wird nach Nutzen für den Pool sortiert.
5. Erst danach werden `max_new_per_batch` und `max_new` angewendet.
6. Nur die besten zulässigen Kandidaten werden als `new_refs/` oder `new_faces/` gespeichert.

Face-Kandidaten werden zusätzlich als quadratischer Gesichtsausschnitt gespeichert (z. B. 256×256 Pixel). Der Crop enthält nur das Gesicht, kein Umfeld. Die Metadaten enthalten Bounding Box, Gesichtskonfidenz und Originalreferenz.

## 5.10 Rebuild und Neu-Ranking

Ein Rebuild ist zwingend, wenn sich der aktive Referenzbestand ändert:

- Ein Bild wird von `new_*` nach `reference/` verschoben.
- Ein aktives Bild wird aus `reference/` entfernt.
- Eine aktive Referenzdatei wird verändert oder ihr Hash ändert sich.
- Die Auswahlparameter, das relevante Modell, die Vorverarbeitung oder der Auswahlfingerprint ändern sich.
- `selection.json` und der Ordnerinhalt stimmen nicht mehr überein.

Embeddings dürfen nie persistent gespeichert werden. Referenz-Embeddings werden nur bei Änderung des aktiven Referenzpools oder nach Container-Neustart neu aufgebaut. Innerhalb eines laufenden Container-Laufs dürfen sie bis zur nächsten Pooländerung ausschließlich im RAM gehalten werden. `selection_fingerprint` und `pool_build_id` müssen zur Cache-Validierung verglichen werden.

### Schritte

1. Anzahl aktiver Dateien zählen.
2. `rank_digits` berechnen.
3. Nutzenranking berechnen.
4. Temporäre Dateien erzeugen.
5. Finale Namen setzen.
6. Neue `selection.json` validieren.
7. `selection.json` atomar ersetzen.
8. `rank_digits` und `pool_build_id` schreiben.

**Nutzenbasiertes Ranking:**
- `pool_utility_score` beschreibt den marginalen Nutzen eines Bildes für den aktuellen Pool.
- **Rang 1 = höchster Nutzen**.
- **Rang n = geringster Nutzen**.

## 5.11 Dynamische Stellenzahl

Die Stellenzahl der Rangzahl (`rank_digits`) wird automatisch an die Anzahl aktiver Dateien angepasst:

1. Anzahl aktiver Dateien in `reference/` zählen.
2. `rank_digits = max(1, ceil(log10(n + 1)))` berechnen.
3. Dateinamen formatieren als `{rank_zfill}__{original_name}_{suffix}.{ext}`.

## 5.12 Atomare Umbenennung

Nach erfolgreichem Rebuild werden alle Dateien in `reference/` neu benannt:

1. Anzahl zählen.
2. Stellenzahl berechnen.
3. Nutzenrang aller aktiven Referenzen neu berechnen.
4. Temporäre eindeutige Namen verwenden.
5. Finale Namen `0001__...`, `0002__...`, ... setzen.
6. Neue `selection.json` temporär erzeugen und validieren.
7. `selection.json` atomar ersetzen.
8. `rank_digits` und `pool_build_id` schreiben.

Scheitert ein Schritt, bleibt die vorherige Poolversion aktiv; der Fehler wird in der Run-Summary gemeldet.

## 5.13 Manuelle Bedienung

| Aktion des Menschen | Systemwirkung |
|---|---|
| Bild aus `new_*` nach `reference/` verschieben | Konsistenzprüfung, Rebuild, neues Ranking. |
| Bild aus `new_*` löschen | Eintrag aus `selection.json` entfernen; kein Rebuild, solange `reference/` unverändert bleibt. |
| Aktive Datei aus `reference/` löschen | Konsistenzprüfung, Rebuild, neues Ranking. |
| `max_new` erreicht | Keine neuen Vorschläge; Run-Summary meldet Handlungsbedarf. |
| `max_active` erreicht | Keine neue Aktivierung; Run-Summary meldet manuelles Bereinigen. |

## 5.14 Run-Summary-Meldungen

**Meldung: `max_new` erreicht**
```json
{
  "severity": "warning",
  "type": "reference_pool_new_limit_reached",
  "pool": "faces/max_mustermann",
  "message": "Die Höchstzahl offener Vorschläge (max_new=20) ist erreicht; es werden keine weiteren neuen Gesichter gespeichert.",
  "action": "Bitte new_faces/ prüfen: relevante Bilder nach reference/ verschieben, übrige Bilder löschen."
}
```

**Meldung: `max_new_per_batch` erreicht**
```json
{
  "severity": "info",
  "type": "reference_pool_batch_limit_reached",
  "pool": "samples",
  "batch_id": "2024-08-15_Geburtstag+a3f7c2e1",
  "message": "Die Höchstzahl offener Vorschläge pro Batch (max_new_per_batch=5) für Batch '2024-08-15_Geburtstag+a3f7c2e1' ist erreicht.",
  "action": "Bitte new_refs/ prüfen: relevante Bilder nach reference/ verschieben."
}
```

**Meldung: `max_active` erreicht**
```json
{
  "severity": "info",
  "type": "reference_pool_active_limit_reached",
  "pool": "faces/max_mustermann",
  "message": "Die Höchstzahl aktiver Referenzen (max_active=100) ist erreicht; es sind keine weiteren Aktivierungen möglich.",
  "action": "Bitte reference/ prüfen: weniger nützliche Bilder entfernen, um Platz für neue Referenzen zu schaffen."
}
```