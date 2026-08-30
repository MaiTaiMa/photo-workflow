# TODO v1.3 - Geplante Verbesserungen

## 1. Bibliotheks-Warnungen beheben

### face_recognition_models: pkg_resources → importlib.resources
- **Problem:** `face_recognition_models==0.3.0` verwendet deprecated `pkg_resources`
- **Warnung:** `UserWarning: pkg_resources is deprecated as an API`
- **Lösung:** Eigenes Fork mit `importlib.resources` erstellen oder auf Community-Patch warten
- **GitHub:** https://github.com/ageitgey/face_recognition_models/issues
- **Workaround v1.2:** Warning unterdrückt in `app/photo_workflow.py` (Zeile ~50)

### OpenCV 5.x: setPreferableTarget Graph-Engine
- **Problem:** Neue DNN Graph-Engine unterstützt Targets nicht, fällt auf Classic zurück
- **Warnung:** `[ WARN:0@...] global net_impl_backend.cpp:345 setPreferableTarget Targets are not supported by the new graph engine for now`
- **Status:** Harmlos, CPU-Fallback ist beabsichtigt
- **Lösung v1.3:** OpenCV-Docs prüfen, ob es eine offizielle API für Target-Selection in 5.x gibt

## 2. move_to_temp_final entkoppeln

### Aktueller Zustand (v1.2)
- `move_to_temp_final: true` greift NUR bei `mode: full_auto` + erfolgreichem `automatic_handoff`
- Manuell nach `03_TEMP_DONE` verschobene Batches werden übersprungen (kein Handoff-Token)
- **Problem:** User-Erwartung: Move sollte bei JEDEM erfolgreichen Cleanup greifen

### Geplanter Zustand (v1.3)
- `move_to_temp_final: true` greift für ALLE Batches mit erfolgreichem Cleanup
- Unabhängig vom Automationsmodus (`shadow`, `assisted`, `auto_phase2`, `full_auto`)
- Handoff-Prüfung bleibt für automatischen Start erhalten, blockiert aber nicht mehr den Move

### Änderungen erforderlich
1. `app/photo_workflow.py`:
   - Zeile ~2288: `if move_enabled:` statt `if move_enabled and mode == 'full_auto':`
   - Zeile ~2233-2245: Handoff-Prüfung als Log-only, nicht als Skip-Kriterium
2. `docs/AUTOMATION_AND_FINALIZATION_CONTRACT_v1-2.md`:
   - Tabelle "Automationsmodi für Phase 2" aktualisieren
   - Move-Logik neu dokumentieren
3. Tests:
   - Unit-Test: `test_move_to_temp_final_independent_of_mode`
   - Integration-Test: Manueller Batch mit `mode: shadow` + `move_to_temp_final: true`

## 3. Handoff-Gate für manuelle Batches

### Problem
- Bei `mode: auto_phase2/full_auto` werden manuell verschobene Batches übersprungen
- User-Erwartung: Cleanup + Move soll trotzdem laufen

### Lösung v1.3
- Handoff-Token nur für AUTOMATISCHEN Start prüfen
- Manuelle Batches: Log-Eintrag "kein Handoff, aber Cleanup trotzdem"
- Kein Skip mehr bei fehlendem Token

## Abnahmekriterien v1.3
- [x] Move-Logik entkoppelt (v1.2-Release)
- [x] Handoff-Prüfung als Log-only (v1.2-Release)
- [x] Warning-Filter hinzugefügt (v1.2-Release)

## Offen für v1.3
- [ ] Alle Warnungen behoben oder dokumentiert
- [ ] Move-Logik entkoppelt, Tests grün
- [ ] Contract-Dokument aktualisiert
- [ ] Manueller Workflow + automatischer Workflow beide getestet
