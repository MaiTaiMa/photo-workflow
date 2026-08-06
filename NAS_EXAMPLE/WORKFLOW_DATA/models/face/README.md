<!-- Projekt: Synology Photo Workflow; Pfad: NAS_EXAMPLE/TEMP/WORKFLOW_DATA/models/face/README.md; Rolle: Face-Backend-Modelle -->
# face

Dieser Ordner hält die Modelle und Artefakte der optionalen Familien- und Gesichtserkennung. Hier liegen die Dateien, die das ausgewählte Face-Backend für Erkennung oder Vergleich benötigt, sofern die Funktion aktiviert und technisch abgenommen wurde. Der Ordner ist eng an das konfigurierte Backend, die Laufzeitprofile und die Diagnoselogik gebunden. Er darf nicht für allgemeine Bilddaten, Referenzlisten oder persönliche Favoriten verwendet werden. Wenn es sich um manuell bestätigte Persönlichkeits- oder Geschmackssamples handelt, gehört der Inhalt nach `models/taste` oder in die Samples-/Referenzstruktur, nicht hierher.

## Abgrenzung

Dieser Ordner ist nicht für Archivdateien oder Review-Bilder gedacht. Laufzeitdaten gehören in `runtime`, Referenzen in `samples` und Eingänge in `TEMP_SD`. Hier dürfen nur Artefakte liegen, die direkt von der Face-Funktion genutzt werden.

## Enthaltene Modelldateien (Beispiel)

| Datei | Aufgabe |
|---|---|
| `face_detection_yunet.onnx` | Gesichtsdetektion via OpenCV YuNet (FaceDetectorYN) |
| `face_recognition_sface.onnx` | Gesichtsvergleich via OpenCV SFace (FaceRecognizerSF) |

Nur die oben genannten Originaldateien der offiziellen OpenCV-Sammlung ablegen. Keine int8-Varianten ohne eigenen Vergleichstest verwenden.
