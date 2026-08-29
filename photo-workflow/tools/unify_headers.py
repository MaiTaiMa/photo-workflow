# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tools/unify_headers.py
# PURPOSE:     Vereinheitlicht Python-Header in app/, tests/ und tools/
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     2.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   2026-08-29: Grundlegend sicherer gemacht - entfernt NUR den einen
#               zusammenhaengenden Header-Block am Dateianfang und stoppt
#               danach sofort. Kein Scannen mehr weiter im Code (verhinderte
#               vorher versehentliches Loeschen von Klassenkoerpern/Docstrings).
#   2026-08-29: Dynamische Dateizahl/-namen statt hartcodierter Zahl.
#               Unterstuetzt --files zum gezielten Bearbeiten einzelner Dateien.
#   2026-08-29: Warnung bei Skript-Ausfuehrung hinzugefuegt
# =============================================================================
"""
Vereinheitlicht Python-Datei-Header gemaess IMPLEMENTATION_RULES.md.

Sicherheitsprinzip: Es wird IMMER nur genau EIN zusammenhaengender Header-
Block am Dateianfang gesucht und ersetzt. Sobald das Ende dieses einen
Blocks gefunden wurde, wird die Suche gestoppt - der restliche Dateiinhalt
bleibt garantiert unberuehrt.
"""

import argparse
import re
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("/home/matzethias/Programme/photo-workflow/photo-workflow")
TARGET_DIRS = ["app", "tests", "tools"]
SKIP_NAMES = {"__init__.py", "unify_headers.py"}
MAX_LEADING_BLANK_LINES = 3  # Toleranz fuer Leerzeilen/Encoding-Kommentare vor dem Header

HEADER_TEMPLATE = """# =============================================================================
# PROJECT:     photo-workflow
# FILE:        {filepath}
# PURPOSE:     {purpose}
# AUTHOR:      Matzethias
# DATE:        {date}
# VERSION:     {version}
# REQUIRES:    {requires}
# CHANGES:
#   {changes}
# =============================================================================
"""


def find_leading_header_block(lines: list[str]):
    """Findet GENAU EINEN zusammenhaengenden Header-Block am Dateianfang.

    Gibt (start_idx, end_idx_inclusive) zurueck, oder None wenn kein
    Header am Anfang gefunden wurde. Es wird NICHT weiter im Code gesucht,
    sobald der erste Block geschlossen wurde - das verhindert das
    versehentliche Entfernen von Klassen-/Funktions-Docstrings.
    """
    idx = 0
    n = len(lines)

    # Tolerante Anfangs-Leerzeilen ueberspringen (max. wenige Zeilen)
    skipped = 0
    while idx < n and lines[idx].strip() == "" and skipped < MAX_LEADING_BLANK_LINES:
        idx += 1
        skipped += 1

    if idx >= n:
        return None

    first = lines[idx].strip()

    # Fall 1: "# ====...=" Block (unser eigenes Zielformat)
    if first.startswith("# " + "=" * 10):
        for j in range(idx + 1, min(idx + 60, n)):
            if lines[j].strip().startswith("# " + "=" * 10):
                return (idx, j)
        return None  # Kein Ende gefunden -> nichts entfernen (sicherheitshalber)

    # Fall 2: Docstring-Block, der mit """ beginnt
    if first.startswith('"""'):
        rest_of_line = first[3:]
        # Einzeiliger Docstring: """ ... """ in derselben Zeile
        if rest_of_line.strip().endswith('"""') and rest_of_line.strip() != "":
            return (idx, idx)
        # Mehrzeiliger Docstring: Ende suchen (Zeile, die auf """ endet)
        for j in range(idx + 1, min(idx + 60, n)):
            if lines[j].strip() == '"""' or lines[j].rstrip().endswith('"""'):
                return (idx, j)
        return None  # Kein Ende gefunden -> nichts entfernen (sicherheitshalber)

    # Kein erkennbarer Header am Dateianfang
    return None


def extract_changes(header_text: str) -> str:
    """Extrahiert einzigartige Changes-Zeilen aus dem Header-Text."""
    all_changes = []
    seen = set()

    for line in header_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        clean = re.sub(r"^[\s\-\*\u2022#]+", "", line).strip()

        if not re.match(r"\d{4}-\d{2}-\d{2}", clean):
            continue
        if len(clean) <= 10:
            continue

        if clean in seen:
            continue
        seen.add(clean)
        all_changes.append(clean)

    if all_changes:
        return "\n#   ".join(all_changes[:3])

    return "Initial version"


def extract_header_info(header_text: str) -> dict:
    """Extrahiert Metadaten NUR aus dem identifizierten Header-Block."""
    info = {
        "purpose": "Photo Workflow Module",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "version": "1.0.0",
        "requires": "Python 3.11+",
        "changes": "Initial version",
    }

    for pattern in [r"Zweck:\s*(.+?)(?:\n|$)", r"PURPOSE:\s*(.+?)(?:\n|$)"]:
        match = re.search(pattern, header_text, re.IGNORECASE)
        if match:
            info["purpose"] = match.group(1).strip()
            break

    for pattern in [r"Erstellt:\s*(\d{4}-\d{2}-\d{2})", r"DATE:\s*(\d{4}-\d{2}-\d{2})"]:
        match = re.search(pattern, header_text, re.IGNORECASE)
        if match:
            info["date"] = match.group(1)
            break

    match = re.search(r"Version:\s*(\S+)", header_text, re.IGNORECASE)
    if match:
        info["version"] = match.group(1).strip().rstrip(")").rstrip("(").strip()

    match = re.search(r"Requires:\s*(.+?)(?:\n|$)", header_text, re.IGNORECASE)
    if match:
        req = match.group(1).strip()
        info["requires"] = req if "python" in req.lower() else f"Python 3.11+, {req}"

    info["changes"] = extract_changes(header_text)

    return info


def unify_header(filepath: Path, root: Path) -> tuple[bool, str]:
    """Vereinheitlicht den Header einer einzelnen Datei.

    Returns (changed: bool, message: str)
    """
    try:
        rel_path = filepath.relative_to(root)
        original = filepath.read_text(encoding="utf-8")
        lines = original.split("\n")

        block = find_leading_header_block(lines)

        if block is None:
            header_text = ""
            remaining_lines = lines
        else:
            start, end = block
            header_text = "\n".join(lines[start : end + 1])
            remaining_lines = lines[:start] + lines[end + 1 :]

        info = extract_header_info(header_text)
        info["filepath"] = str(rel_path)

        remaining = "\n".join(remaining_lines)
        while remaining.startswith("\n"):
            remaining = remaining[1:]
        remaining = remaining.strip()

        new_header = HEADER_TEMPLATE.format(**info)
        new_content = new_header + "\n\n" + remaining + "\n"

        if new_content.strip() == original.strip():
            return False, "unveraendert"

        filepath.write_text(new_content, encoding="utf-8")
        return True, "aktualisiert"

    except Exception as e:
        return False, f"FEHLER: {e}"


def collect_target_files(explicit_files):
    """Ermittelt die tatsaechliche Liste der zu bearbeitenden Dateien."""
    if explicit_files:
        return [ROOT_DIR / f for f in explicit_files]

    files = []
    for target_dir in TARGET_DIRS:
        dir_path = ROOT_DIR / target_dir
        if not dir_path.exists():
            continue
        for py_file in sorted(dir_path.rglob("*.py")):
            if py_file.name in SKIP_NAMES:
                continue
            files.append(py_file)
    return files


def main():
    parser = argparse.ArgumentParser(description="Vereinheitlicht Python-Header.")
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="Nur diese Dateien bearbeiten (Pfade relativ zum Projekt-Root).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Bestaetigung ueberspringen (ohne Nachfrage ausfuehren).",
    )
    args = parser.parse_args()

    target_files = collect_target_files(args.files)

    print("\n" + "=" * 80)
    print(f"Dieses Skript bearbeitet {len(target_files)} Datei(en):")
    print("=" * 80)
    for f in target_files:
        print(f"  - {f.relative_to(ROOT_DIR)}")
    print("=" * 80)

    if not args.yes:
        input("\nDruecke ENTER zum Fortfahren oder STRG+C zum Abbrechen...")

    print("\n=== Python-Header Vereinheitlichung ===\n")

    updated, unchanged, failed = [], [], []

    for f in target_files:
        changed, message = unify_header(f, ROOT_DIR)
        rel = f.relative_to(ROOT_DIR)
        if message.startswith("FEHLER"):
            print(f"  x {rel}: {message}")
            failed.append(str(rel))
        elif changed:
            print(f"  -> {rel}")
            updated.append(str(rel))
        else:
            unchanged.append(str(rel))

    print(f"\n{'='*80}")
    print("=== Zusammenfassung ===")
    print(f"  Bearbeitet gesamt:  {len(target_files)}")
    print(f"  Aktualisiert:       {len(updated)}")
    print(f"  Unveraendert:       {len(unchanged)}")
    print(f"  Fehler:             {len(failed)}")
    if failed:
        print("\n  Fehlerhafte Dateien:")
        for f in failed:
            print(f"    - {f}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()