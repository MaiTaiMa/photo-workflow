# Changelog

## Unreleased — AP00–AP04

- Baseline branch für Konfigurationsprüfung, Pfadsicherheit, Batch-ID und State Store begonnen.
- Konfigurationsfingerprint mit kanonischer JSON-Darstellung ergänzt.
- Kanonische Root-Prüfung sowie Symlink- und optionaler Mount-Prüfung ergänzt.
- Stabile `batch_id` aus Ordnernamen und gekürztem SHA256-Fingerprint ergänzt.
- Atomare, pro-Batch gespeicherte und hash-verknüpfte Zustandsdateien ergänzt.
- Die bestehende CLI ist noch nicht an diese Basisschicht angebunden; das erfolgt in den Folge-APs.
