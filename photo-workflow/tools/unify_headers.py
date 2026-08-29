# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tools/unify_headers.py
# PURPOSE:     Vereinheitlicht Python-Header in app/, tests/ und tools/
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.11.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   2026-08-29: Warnung bei Skript-Ausfuehrung hinzugefuegt
#   2026-08-29: Docstrings am Stueck entfernen
#   2026-08-29: ALLE Header-Bloecke entfernen
# =============================================================================
"""
Vereinheitlicht Python-Datei-Header gemaess IMPLEMENTATION_RULES.md.

ACHTUNG: Dieses Skript modifiziert 136 Python-Dateien.
Vor dem Ausfuehren:
  1. git reset --hard HEAD
  2. git clean -fd
  3. python3 tools/unify_headers.py
  4. Stichproben pruefen (z.B. app/auto_phase1_gate.py, app/embedding_cache.py)
  5. Bei Bedarf manuelle Korrekturen
"""

import os
import re
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("/home/matzethias/Programme/photo-workflow/photo-workflow")
TARGET_DIRS = ["app", "tests", "tools"]
MAX_HEADER_LINES = 40

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

def extract_changes(first_block: str) -> str:
    """Extrahiert einzigartige Changes aus dem gesamten Header-Block."""
    end_match = re.search(r'\n\s*(?:import|from|class|def)\s', first_block)
    header_text = first_block[:end_match.start()] if end_match else first_block
    
    all_changes = []
    seen = set()
    
    for line in header_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        clean = re.sub(r'^[\s\-\*•#]+', '', line).strip()
        
        if not re.match(r'\d{4}-\d{2}-\d{2}', clean):
            continue
        
        if len(clean) <= 10:
            continue
        
        dedup_key = clean
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        all_changes.append(clean)
    
    if all_changes:
        return '\n#   '.join(all_changes[:3])
    
    return 'Initial version'

def extract_existing_header(content: str) -> dict:
    """Extrahiert Informationen aus existierenden Headern."""
    info = {
        'purpose': 'Photo Workflow Module',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'version': '1.0.0',
        'requires': 'Python 3.11+',
        'changes': 'Initial version'
    }
    
    lines = content.split('\n')[:MAX_HEADER_LINES]
    first_block = '\n'.join(lines)
    
    # Purpose
    for pattern in [r'Zweck:\s*(.+?)(?:\n|$)', r'PURPOSE:\s*(.+?)(?:\n|$)']:
        match = re.search(pattern, first_block, re.IGNORECASE)
        if match:
            info['purpose'] = match.group(1).strip()
            break
    
    # Date
    for pattern in [r'Erstellt:\s*(\d{4}-\d{2}-\d{2})', r'DATE:\s*(\d{4}-\d{2}-\d{2})']:
        match = re.search(pattern, first_block, re.IGNORECASE)
        if match:
            info['date'] = match.group(1)
            break
    
    # Version
    match = re.search(r'Version:\s*(\S+)', first_block, re.IGNORECASE)
    if match:
        info['version'] = match.group(1).strip().rstrip(')').rstrip('(').strip()
    
    # Requires
    match = re.search(r'Requires:\s*(.+?)(?:\n|$)', first_block, re.IGNORECASE)
    if match:
        req = match.group(1).strip()
        info['requires'] = req if 'python' in req.lower() else f'Python 3.11+, {req}'
    
    # Changes
    info['changes'] = extract_changes(first_block)
    
    return info

def remove_all_headers(content: str) -> str:
    """Entfernt ALLE Header-Bloecke (=== und Docstring-Style)."""
    lines = content.split('\n')
    result_lines = []
    in_header = False
    in_docstring = False
    header_removed = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Header-Start erkennen (=== oder """ am Anfang)
        if not header_removed and i < MAX_HEADER_LINES:
            if stripped.startswith('# ====='):
                in_header = True
                header_removed = True
                continue
            elif stripped.startswith('"""'):
                in_docstring = True
                header_removed = True
                continue
        
        # Im ===-Header
        if in_header:
            if stripped.startswith('# ====='):
                in_header = False
                continue
            continue
        
        # Im Docstring-Header
        if in_docstring:
            if stripped == '"""' or (stripped.startswith('"""') and len(stripped) > 3):
                in_docstring = False
                continue
            continue
        
        # Zusaetzliche Header-Bloecke entfernen
        if i < MAX_HEADER_LINES * 2 and not in_header and not in_docstring:
            if (stripped.startswith('# PROJECT:') or stripped.startswith('# FILE:') or
                stripped.startswith('# PURPOSE:') or stripped.startswith('# AUTHOR:') or
                stripped.startswith('# DATE:') or stripped.startswith('# VERSION:') or
                stripped.startswith('# REQUIRES:') or stripped.startswith('# CHANGES:')):
                in_header = True
                continue
        
        result_lines.append(line)
    
    result = '\n'.join(result_lines)
    while result.startswith('\n'):
        result = result[1:]
    
    return result.strip()

def unify_header(filepath: Path, root: Path) -> bool:
    """Vereinheitlicht den Header einer einzelnen Datei."""
    try:
        rel_path = filepath.relative_to(root)
        content = filepath.read_text(encoding='utf-8')
        
        info = extract_existing_header(content)
        info['filepath'] = str(rel_path)
        
        content_without_header = remove_all_headers(content)
        new_header = HEADER_TEMPLATE.format(**info)
        new_content = new_header + '\n\n' + content_without_header
        
        filepath.write_text(new_content, encoding='utf-8')
        return True
        
    except Exception as e:
        print(f"  x Fehler bei {filepath.name}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Hauptfunktion."""
    print("\n" + "="*80)
    print("⚠️  ACHTUNG: Dieses Skript modifiziert 136 Python-Dateien!")
    print("="*80)
    print("\nVor dem Ausfuehren sicherstellen:")
    print("  1. git reset --hard HEAD")
    print("  2. git clean -fd")
    print("  3. Nach Ausfuehrung Stichproben pruefen")
    print("  4. Bei Bedarf manuelle Korrekturen (z.B. auto_phase1_gate.py)")
    print("\n" + "="*80)
    input("\nDruecke ENTER zum Fortfahren oder STRG+C zum Abbrechen...")
    print("="*80 + "\n")
    
    print("=== Python-Header Vereinheitlichung ===\n")
    
    total_files = 0
    updated_files = 0
    failed_files = 0
    
    for target_dir in TARGET_DIRS:
        dir_path = ROOT_DIR / target_dir
        if not dir_path.exists():
            print(f"⚠ Verzeichnis {target_dir} nicht gefunden")
            continue
        
        print(f"\n📁 {target_dir}/")
        py_files = list(dir_path.rglob("*.py"))
        
        for py_file in py_files:
            if py_file.name in ["__init__.py", "unify_headers.py"]:
                continue
            
            total_files += 1
            print(f"  → {py_file.relative_to(ROOT_DIR)}")
            
            if unify_header(py_file, ROOT_DIR):
                updated_files += 1
            else:
                failed_files += 1
    
    print(f"\n{'='*80}")
    print(f"=== Zusammenfassung ===")
    print(f"  Gesamt: {total_files} Dateien")
    print(f"  Aktualisiert: {updated_files} Dateien")
    print(f"  Fehler: {failed_files} Dateien")
    print(f"{'='*80}")
    print(f"\n✅ Fertig! Bitte pruefe Stichproben:")
    print(f"   head -20 app/auto_phase1_gate.py")
    print(f"   head -20 app/embedding_cache.py")
    print(f"   head -15 app/manual_keep.py")
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()