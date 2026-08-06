# 4. Scoring, Serien, Metadaten, Manual Keep, Face-Backend, Kalibrierung

## 4.1 Technisches Culling (basescore)

- **Status:** Pflicht.
- **Zweck:** Ressourcenschonende Basisbewertung ohne Pflicht-KI-Modell. Bewertet Schärfe, Belichtung und einfache ästhetische Merkmale. Ergebnis ist `base_score`.

### Ablauf

1. Kleine technische Vorschau erzeugen (256–512 Pixel längste Kante).
2. Teilscores für Schärfe (Kantenvarianz), Belichtung (Clipping), Helligkeitsbalance und Ästhetik (Kontrast, Sättigung, Bildbalance) berechnen.
3. Teilscores mit konfigurierbaren Gewichten (`culling.base_weights`) zu `base_score` kombinieren.
4. Nicht lesbare oder fehlerhafte Bilder erhalten `analysis_error`, aber keinen stillen Ersatzscore.

**Score-Vertrag:** `base_score` ist eine Fließkommazahl im Bereich [0,0 bis 1,0]. `analysis_error` wird als `null` oder spezieller Wert `-1` repräsentiert, nie als 0.0.

## 4.2 Persönlicher Geschmack (lokales CLIP, personal_score)

- **Status:** Pflicht.
- **Zweck:** Ergänzt die technische Bewertung um eine gelernte, persönliche Präferenz. Bewertet Bilder gegen positive/negative Text-Prompts oder aktive Referenzbilder.

### Ablauf

1. CLIP-Modell lädt nur bei aktiviertem Adapter.
2. Bild wird gegen aktive Referenzen aus `samples/reference` oder gegen Prompt-Listen bewertet.
3. Ergebnis ist ausschließlich `personal_score`; es wird nicht in `base_score` gemischt.
4. Bilder, die `keep` sind, höchste Sternklasse erreichen und die aktive Auswahl messbar erweitern, werden automatisch nach `samples/new_refs` vorgeschlagen.
5. Nur ein manuelles Kopieren nach `samples/reference` aktiviert sie und löst ein Retraining aus.

**Score-Vertrag:** `personal_score` ist eine Fließkommazahl im Bereich [0,0 bis 1,0] oder `None` bei deaktiviertem/fehlerhaftem Adapter.

## 4.3 Serienerkennung (series_id, series_rank, series_best)

- **Status:** Pflicht.
- **Zweck:** Verhindert, dass mehrere technisch ähnliche Aufnahmen alle gleich behandelt werden. Hebt das beste Bild einer Serie hervor.

### Ablauf

1. Gruppierung über Aufnahmezeit, Bild-Embedding, visuelle Ähnlichkeit oder deterministische Dateinamenlogik als Fallback.
2. Pro Bild werden Serien-ID, -Größe, -Rang, `series_best`-Flag und Abstand zum Besten gespeichert.
3. Das Bestbild darf höchstens um eine Klasse aufgewertet werden.
4. Andere Bilder dürfen nur mit dokumentierter Distanz zum Bestbild abgewertet werden.

**Serien-Vertrag:** `series_id` ist eine eindeutige Zeichenkette pro Serie innerhalb eines Batches. `series_rank` ist 1-basiert (1 = bestes Bild). `series_best` ist ein boolescher Wert.

## 4.4 Eye-Score (geschlossene Augen)

- **Status:** Pflicht.
- **Zweck:** Erkennt geschlossene Augen als leichtes Korrektursignal.

### Ablauf

1. Nur bei genau einem ausreichend großem Gesicht im Bild.
2. ONNX-Zweiklassen-Modell liefert `P(offen)`.
3. Ergebnis ist `eye_score` (eigene Komponente, nicht Teil von `base_score`).

**Score-Vertrag:** `eye_score` ist eine Fließkommazahl im Bereich [0,0 bis 1,0] (Wahrscheinlichkeit für offene Augen) oder `None`.

## 4.5 Bekannte Gesichtserkennung (Familie, `family_score`)

- **Status:** Pflicht, sobald der Face-Adapter aktiviert ist.
- **Zweck:** Liefert ein moderates positives Signal für bewusst gepflegte, bekannte Personen. Keine allgemeine Gesichtserkennung, kein Clustering unbekannter Gesichter.

### Ablauf

1. Das registrierte Backend erzeugt ein Embedding ausschließlich flüchtig im RAM.
2. Der Vergleich erfolgt gegen aktive Referenzen einer Person unter `faces/<slug>/reference` mit `selection.json` und Status `active`.
3. Nur bei eindeutigem Match mit Schwelle und Sicherheitsmarge zum Zweitbesten wird `family_score` gesetzt und ein Personentag vergeben.
4. Neue Face-Crop-Vorschläge werden ausschließlich unter `faces/<slug>/new_faces` persistent gespeichert.
5. Die Verschiebung eines Vorschlags von `new_faces` nach `reference` erfolgt ausschließlich manuell durch den Menschen. Automatische Aktivierung ist verboten.

**Schutzgrenzen:** Bildbytes und Embeddings dürfen nie in JSON, Cache, Log, Manifest, CSV, Metadaten oder Report persistiert werden. Automatisch erzeugte Face-Crops dürfen nur in `new_faces` geschrieben werden. Nach manueller Aktivierung dürfen sie als aktive Referenzen in `reference` liegen.

**Face-Backend-Vertrag:** Jedes Backend muss Registry-ID, Adaptername, Modellhash, Provider, Vorverarbeitung, Metrik und Auswahlfingerprint bereitstellen.

**Score-Vertrag:** `family_score` ist eine Fließkommazahl im Bereich [0,0 bis 1,0] oder `None`.

## 4.6 Manual Keep (manual_keep, manual_keep_match)

- **Status:** Pflicht.
- **Zweck:** Ordnet extern (z. B. per WhatsApp) vorab ausgewählte, oft komprimierte/kleine Bilder ihrem Original im aktuellen Batch zu und erzwingt für dieses `keep`.

### Ablauf

1. Zweistufig: schneller auflösungsrobuster Vorfilter (Seitenverhältnis, Perceptual Hash).
2. Danach strenge normalisierte Endprüfung (Verifikationsscore auf EXIF-korrigierten, gleich skalierten Bildern).
3. Match nur bei Schwelle und ausreichendem Abstand zum Zweitbesten.
4. Ergebnis erzwingt `keep` mit Grund `manual_keep_match`.
5. Danach durchläuft das Bild normales Scoring; erst nach Zuordnung wird die Quelldatei nach `used` verschoben.

**Manual-Keep-Vertrag:** `manual_keep` ist ein boolescher Wert (`true` bei Match, `false` oder `null` sonst). `manual_keep_match` wird in der Run-Summary als Zähler geführt.

## 4.7 Metadaten (Rating, Tags, Beschreibung)

- **Status:** Pflicht.
- **Zweck:** Macht Bewertungen und Personentreffer in gängigen Fotoprogrammen sichtbar.

### Ablauf

1. Sternrating aus Score-Band bestimmen.
2. Namespaced Keywords einbetten (`workflow:ai_cull`, `decision:final`, `series:`, `family:match`, `person:<slug>`, `manual_keep:true`).
3. Per `exiftool` (shell=False) in Bild schreiben.
4. Nach dem Schreiben zurücklesen und abgleichen.

**Metadaten-Vertrag:** Metadaten müssen namespaced sein (Präfix `workflow:`). `failed_metadata` ist ein boolescher Wert. `exiftool_status` ist einer von `success`, `disabled`, `failed`, `sidecar`.

## 4.8 Kalibrierung und Gewichtungsassistent

- **Status:** Pflicht.
- **Zweck:** Lernt aus bestätigten menschlichen Endentscheidungen, ob die vorhandenen Score-Komponenten anders gewichtet werden sollten. Ersetzt nie die Komponenten selbst.

### Ablauf

1. Pro manuell freigegebenem Batch entsteht ein unveränderliches `review_decision_record.json`.
2. Daraus werden Kennzahlen (terminale Übereinstimmung, `reject_to_keep_rate` etc.) berechnet.
3. Optional wird ein Gewichtsvorschlag im Schattenmodus erzeugt.
4. Eine Aktivierung erfordert bewusste Nutzerfreigabe, erfüllte Gates und bleibt jederzeit rollbackfähig.

**Kalibrierungs-Vertrag:** `review_decision_record.json` muss `batch_id`, `timestamp`, `human_decision`, `predicted_decision`, `agreement`, `config_fingerprint`, `producer_version` enthalten.