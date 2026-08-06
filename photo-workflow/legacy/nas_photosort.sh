#!/bin/bash
set -euo pipefail
shopt -s nullglob

# =====================================
# EN: Synology Photo Ingest + DONE Workflow
# DE: Synology Foto-Ingest + DONE-Workflow
# EN: Version v4.2 – Safe counters, ERR trap, static DEST move/merge, no mail
# DE: Version v4.2 – Sichere Zähler, ERR-Trap, statisches DEST Move/Merge, ohne E-Mail
# =====================================

BASE_DIR="/volume1/TEMP"
SRC="$BASE_DIR/TEMP_SD"
DEST="$BASE_DIR/TEMP_IMAGES"
DONE="$BASE_DIR/TEMP_DONE"

LOGFILE="$BASE_DIR/process.log"
ERRORLOG="$BASE_DIR/error.log"
LOCKFILE="$BASE_DIR/.script.lock"

WAIT_TIME=60

# EN: Script metadata shown at startup and written to log
# DE: Skript-Metadaten, die beim Start angezeigt und ins Log geschrieben werden
SCRIPT_NAME="Synology Photo Ingest + DONE Workflow"
SCRIPT_VERSION="v4.2"
SCRIPT_DESCRIPTION="Processes top-level photo folders from TEMP_SD, renames and packages JPG/ARW files, moves or merges completed folders to TEMP_IMAGES, and post-processes TEMP_DONE including ARW cleanup and ARW ZIP creation."

COUNT_PROCESSED=0
COUNT_MOVED=0
COUNT_SKIPPED=0
COUNT_ERRORS=0
COUNT_FOUND_SRC=0
COUNT_FOUND_DONE=0

# EN: Stores the final processed folder path from process_folder()
# DE: Speichert den final verarbeiteten Ordnerpfad aus process_folder()
LAST_PROCESSED_DIR=""

exec > >(tee -a "$LOGFILE") 2> >(tee -a "$ERRORLOG" >&2)

# =====================================
# EN: LOCKFILE / ERROR TRAPS
# DE: SPERRDATEI / FEHLER-TRAPS
# =====================================
if [[ -f "$LOCKFILE" ]]; then
    echo "[LOCK] EN: Script already running / DE: Skript läuft bereits"
    exit 1
fi
touch "$LOCKFILE"

trap 'echo "[ERROR TRAP] EN: Line $LINENO: $BASH_COMMAND / DE: Zeile $LINENO: $BASH_COMMAND"' ERR
trap 'rc=$?; [[ $rc -ne 0 ]] && echo "[FATAL] EN: Script aborted with exit code $rc / DE: Skript mit Exit-Code $rc abgebrochen"; rm -f "$LOCKFILE"' EXIT

echo "===== START: $(date) ====="
echo "SCRIPT   : $SCRIPT_NAME"
echo "VERSION  : $SCRIPT_VERSION"
echo "PURPOSE  : $SCRIPT_DESCRIPTION"
echo "BASE_DIR : $BASE_DIR"
echo "SRC      : $SRC"
echo "DEST     : $DEST"
echo "DONE     : $DONE"
echo "========================================"

# EN: Remove leftover temp ZIP files from previous runs
# DE: Temporäre ZIP-Dateien von früheren Läufen entfernen
find "$BASE_DIR" -type f -name "*.tmp" -delete

# =====================================
# EN: LOGGING
# DE: LOGGING
# =====================================
log() { echo "$(date '+%F %T') - $1"; }

# =====================================
# EN: HELPERS
# DE: HILFSFUNKTIONEN
# =====================================
is_stable() {
    local s1 s2
    s1=$(find "$1" -type f -exec stat -c "%n %s" {} + 2>/dev/null | sort)
    sleep "$WAIT_TIME"
    s2=$(find "$1" -type f -exec stat -c "%n %s" {} + 2>/dev/null | sort)
    [[ "$s1" == "$s2" ]]
}

folder_hash() {
    find "$1" -type f \( -iname "*.jpg" \) -exec stat -c "%n %s" {} + 2>/dev/null | sort | md5sum | awk '{print $1}'
}

safe_zip() {
    local zip_target="$1"
    shift
    local files=("$@")
    local tmpfile="${zip_target}.tmp"

    rm -f "$tmpfile"
    [[ ${#files[@]} -eq 0 ]] && return 0

    zip -j -q "$tmpfile" "${files[@]}" 2>/dev/null

    if [[ -f "$tmpfile" ]]; then
        mv "$tmpfile" "$zip_target"
        log "[ZIP OK] EN: ZIP created / DE: ZIP erstellt: $zip_target"
        return 0
    fi

    log "[ZIP FAIL] EN: ZIP creation failed / DE: ZIP-Erstellung fehlgeschlagen: $zip_target"
    COUNT_ERRORS=$((COUNT_ERRORS + 1))
    return 1
}

# EN: Original naming logic from the working script
# DE: Originale Namenslogik aus dem funktionierenden Skript
make_date_name() {
    local oldname="$1"

    if [[ "$oldname" =~ ^[0-9]{8}$ ]]; then
        local year="202${oldname:3:1}"
        local month="${oldname:4:2}"
        local day="${oldname:6:2}"
        echo "${year}-${month}-${day}"
    else
        echo "$oldname"
    fi
}

is_valid_raw_folder() {
    [[ "$1" =~ ^[0-9]{8}$ ]]
}

# EN: Accepts both YYYY-MM-DD and YYYY-MM-DD_SUFFIX
# DE: Akzeptiert sowohl YYYY-MM-DD als auch YYYY-MM-DD_SUFFIX
is_valid_done_folder() {
    [[ "$1" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}(_.*)?$ ]]
}

# EN: Generate fallback destination name if merge target already exists
# DE: Fallback-Zielnamen erzeugen, falls Merge-Ziel bereits existiert
resolve_merge_fallback_dir() {
    local target="$1"

    if [[ ! -e "${target}_MERGE" ]]; then
        echo "${target}_MERGE"
        return 0
    fi

    local i=2
    while [[ -e "${target}_MERGE_${i}" ]]; do
        ((i++))
    done
    echo "${target}_MERGE_${i}"
}

# =====================================
# EN: MERGE OR MOVE TO DESTINATION
# DE: INS ZIEL MERGEN ODER VERSCHIEBEN
# =====================================
merge_or_move_folder() {
    local src_dir="$1"
    local dest_dir="$2"

    [[ -d "$src_dir" ]] || {
        log "[SKIP MOVE] EN: Source folder missing / DE: Quellordner fehlt: $src_dir"
        return 0
    }

    if [[ ! -d "$dest_dir" ]]; then
        mv "$src_dir" "$dest_dir" || {
            log "[ERROR] EN: Move failed / DE: Verschieben fehlgeschlagen: $src_dir -> $dest_dir"
            COUNT_ERRORS=$((COUNT_ERRORS + 1))
            return 1
        }
        log "[MOVE] EN: Folder moved / DE: Ordner verschoben: $(basename "$dest_dir")"
        COUNT_MOVED=$((COUNT_MOVED + 1))
        return 0
    fi

    log "[MERGE TRY] EN: Destination exists, trying rsync merge / DE: Ziel existiert, rsync-Merge wird versucht: $(basename "$dest_dir")"

    if command -v rsync >/dev/null 2>&1; then
        if rsync -a "$src_dir"/ "$dest_dir"/; then
            rm -rf "$src_dir" || {
                log "[ERROR] EN: Source cleanup after merge failed / DE: Quellen-Bereinigung nach Merge fehlgeschlagen: $src_dir"
                COUNT_ERRORS=$((COUNT_ERRORS + 1))
                return 1
            }
            log "[MERGE OK] EN: rsync merge completed / DE: rsync-Merge abgeschlossen: $(basename "$dest_dir")"
            log "[MERGE POST] EN: Merge finished, continuing script / DE: Merge abgeschlossen, Skript läuft weiter"
            COUNT_MOVED=$((COUNT_MOVED + 1))
            return 0
        else
            log "[MERGE FAIL] EN: rsync merge failed, using fallback / DE: rsync-Merge fehlgeschlagen, nutze Fallback"
        fi
    else
        log "[MERGE SKIP] EN: rsync not available, using fallback / DE: rsync nicht verfügbar, nutze Fallback"
    fi

    local fallback_dir
    fallback_dir="$(resolve_merge_fallback_dir "$dest_dir")"

    mv "$src_dir" "$fallback_dir" || {
        log "[ERROR] EN: Fallback move failed / DE: Fallback-Verschiebung fehlgeschlagen: $src_dir -> $fallback_dir"
        COUNT_ERRORS=$((COUNT_ERRORS + 1))
        return 1
    }

    log "[MOVE ALT] EN: Folder moved to fallback name / DE: Ordner unter Fallback-Namen verschoben: $(basename "$fallback_dir")"
    COUNT_MOVED=$((COUNT_MOVED + 1))
    return 0
}

# =====================================
# EN: PROCESS SINGLE TEMP_SD FOLDER
# DE: EINZELNEN TEMP_SD-ORDNER VERARBEITEN
# =====================================
process_folder() {
    local dir="$1"
    local oldname newname workdir
    oldname="$(basename "$dir")"

    LAST_PROCESSED_DIR=""

    if is_valid_raw_folder "$oldname"; then
        newname="$(make_date_name "$oldname")"
        workdir="$SRC/$newname"

        if [[ "$oldname" != "$newname" ]]; then
            mv "$dir" "$workdir" || {
                log "[ERROR] EN: Rename failed / DE: Umbenennen fehlgeschlagen: $oldname -> $newname"
                COUNT_ERRORS=$((COUNT_ERRORS + 1))
                return 1
            }
            log "[RENAMED] $oldname → $newname"
        else
            workdir="$dir"
        fi
    elif is_valid_done_folder "$oldname"; then
        newname="$oldname"
        workdir="$dir"
        log "[CONTINUE] EN: Continue already renamed folder / DE: Bereits umbenannten Ordner fortsetzen: $newname"
    else
        log "[SKIP] EN: Invalid folder name / DE: Ungültiger Ordnername: $oldname"
        COUNT_SKIPPED=$((COUNT_SKIPPED + 1))
        return 2
    fi

    cd "$workdir" || return 1

    local arw
    arw=(*.ARW *.arw)
    if [[ ${#arw[@]} -gt 0 ]]; then
        mkdir -p ARW
        mv "${arw[@]}" ARW/ 2>/dev/null || true
        log "[ARW MOVED] EN: ARW files moved / DE: ARW-Dateien verschoben: ${#arw[@]}"
    else
        log "[NO ARW] EN: No ARW files found / DE: Keine ARW-Dateien gefunden in: $workdir"
    fi

    local jpg
    jpg=(*.JPG *.jpg)
    if [[ ${#jpg[@]} -gt 0 ]]; then
        mkdir -p SAVE
        local zipfile="SAVE/${newname}_ALL_JPG.zip"

        if [[ ! -f "$zipfile" ]] || [[ "$(find . -iname '*.jpg' -newer "$zipfile" | wc -l)" -gt 0 ]]; then
            safe_zip "$zipfile" "${jpg[@]}"
        else
            log "[SKIP JPG ZIP] EN: JPG ZIP up to date / DE: JPG-ZIP aktuell"
        fi
    else
        log "[NO JPG] EN: No JPG files found / DE: Keine JPG-Dateien gefunden in: $workdir"
    fi

    touch "$workdir/.DONE"
    log "[DONE] EN: Folder marked DONE / DE: Ordner als DONE markiert: $newname"

    cd "$BASE_DIR" || return 1
    COUNT_PROCESSED=$((COUNT_PROCESSED + 1))

    LAST_PROCESSED_DIR="$workdir"
    return 0
}

# =====================================
# EN: PROCESS SINGLE TEMP_DONE FOLDER
# DE: EINZELNEN TEMP_DONE-ORDNER VERARBEITEN
# =====================================
process_done_folder() {
    local dir="$1"
    local name
    name="$(basename "$dir")"

    local ARW_DIR="$dir/ARW"
    local SAVE_DIR="$dir/SAVE"
    local new_hash old_hash
    local z arw base jpg
    local arw_files
    local ARW_ZIP

    [[ -d "$ARW_DIR" ]] || {
        log "[SKIP DONE] EN: No ARW directory / DE: Kein ARW-Verzeichnis vorhanden: $name"
        return 0
    }

    mkdir -p "$SAVE_DIR"

    new_hash=$(folder_hash "$dir")

    if [[ -f "$dir/.PROCESSED" ]]; then
        old_hash=$(cat "$dir/.PROCESSED")
        if [[ "$new_hash" == "$old_hash" ]]; then
            log "[SKIP DONE] EN: Folder unchanged / DE: Ordner unverändert: $name"
            return 0
        else
            log "[REPROCESS] EN: Changes detected / DE: Änderungen erkannt: $name"
        fi
    else
        log "[PROCESS DONE] EN: Processing done folder / DE: Verarbeite DONE-Ordner: $name"
    fi

    for z in "$ARW_DIR"/*.zip; do
        [[ -f "$z" ]] && mv "$z" "$SAVE_DIR/"
    done

    for z in "$SAVE_DIR"/*.zip; do
        [[ -f "$z" ]] || continue
        [[ "$z" != *_ALL_JPG.zip && "$z" != *_SORT_ARW.zip ]] && mv "$z" "${z%.zip}_ALL_JPG.zip"
    done

    for arw in "$ARW_DIR"/*.ARW "$ARW_DIR"/*.arw; do
        [[ -f "$arw" ]] || continue
        base="$(basename "$arw")"
        base="${base%.*}"
        jpg="$dir/$base.JPG"

        if [[ ! -f "$jpg" && ! -f "$dir/$base.jpg" ]]; then
            rm -f "$arw"
            log "[DELETE ARW] EN: No matching JPG / DE: Kein passendes JPG, ARW gelöscht: $base"
        fi
    done

    arw_files=("$ARW_DIR"/*.ARW "$ARW_DIR"/*.arw)
    ARW_ZIP="$SAVE_DIR/${name}_SORT_ARW.zip"

    if [[ ${#arw_files[@]} -gt 0 ]]; then
        if safe_zip "$ARW_ZIP" "${arw_files[@]}"; then
            rm -rf "$ARW_DIR"
            log "[REMOVE ARW DIR] EN: ARW directory removed after ZIP / DE: ARW-Ordner nach ZIP-Erstellung entfernt: $name"
        fi
    else
        log "[INFO] EN: No ARW files / DE: Keine ARW-Dateien vorhanden: $name"
        rm -rf "$ARW_DIR"
        log "[REMOVE ARW DIR] EN: Empty ARW directory removed / DE: Leerer ARW-Ordner entfernt: $name"
    fi

    echo "$new_hash" > "$dir/.PROCESSED"
    log "[DONE MARKED] EN: Folder marked processed / DE: Ordner als verarbeitet markiert: $name"
}

# =====================================
# EN: PROCESS TEMP_DONE CONTAINER
# DE: TEMP_DONE-CONTAINER VERARBEITEN
# =====================================
process_container_done() {
    local dir="$1"
    local name
    name="$(basename "$dir")"
    log "[DONE CONTAINER] EN: Processing done container / DE: Verarbeite DONE-Container: $name"

    local sub subname
    for sub in "$dir"/*/; do
        [[ -d "$sub" ]] || continue
        sub="${sub%/}"
        subname="$(basename "$sub")"

        if is_valid_done_folder "$subname"; then
            process_done_folder "$sub"
        else
            log "[SKIP DONE SUB] EN: Unsupported TEMP_DONE subfolder / DE: Nicht unterstützter TEMP_DONE-Unterordner: $subname"
            COUNT_SKIPPED=$((COUNT_SKIPPED + 1))
        fi
    done
}

# =====================================
# EN: MAIN
# DE: HAUPTPROGRAMM
# =====================================
log "[PHASE 1] EN: Processing TEMP_SD / DE: Verarbeite TEMP_SD"

for dir in "$SRC"/*; do
    [[ -d "$dir" ]] || continue
    dir="${dir%/}"
    name="$(basename "$dir")"
    COUNT_FOUND_SRC=$((COUNT_FOUND_SRC + 1))

    if ! is_valid_raw_folder "$name" && ! is_valid_done_folder "$name"; then
        log "[SKIP TOP] EN: Unsupported top-level folder, not checked / DE: Nicht unterstützter Ordner auf oberster Ebene, nicht geprüft: $name"
        COUNT_SKIPPED=$((COUNT_SKIPPED + 1))
        continue
    fi

    if [[ ! -f "$dir/.DONE" ]] && ! is_stable "$dir"; then
        log "[WAIT] EN: Transfer still running, folder not checked yet / DE: Transfer läuft noch, Ordner noch nicht geprüft: $name"
        COUNT_SKIPPED=$((COUNT_SKIPPED + 1))
        continue
    fi

    if [[ -f "$dir/.DONE" ]]; then
        log "[DEBUG MOVE] EN: Moving already DONE folder / DE: Verschiebe bereits DONE-markierten Ordner: $dir"
        merge_or_move_folder "$dir" "$DEST/$name"
        continue
    fi

    LAST_PROCESSED_DIR=""
    if process_folder "$dir"; then
        if [[ -n "$LAST_PROCESSED_DIR" && -d "$LAST_PROCESSED_DIR" && -f "$LAST_PROCESSED_DIR/.DONE" ]]; then
            log "[DEBUG MOVE] EN: Using processed dir / DE: Verwende verarbeiteten Ordner: $LAST_PROCESSED_DIR"
            merge_or_move_folder "$LAST_PROCESSED_DIR" "$DEST/$(basename "$LAST_PROCESSED_DIR")"
        else
            log "[WAIT MOVE] EN: No movable DONE folder found / DE: Kein verschiebbarer DONE-Ordner gefunden: $name"
        fi
    else
        log "[ERROR] EN: process_folder failed / DE: process_folder fehlgeschlagen: $name"
        COUNT_ERRORS=$((COUNT_ERRORS + 1))
    fi
done

log "[PHASE 2] EN: Processing TEMP_DONE / DE: Verarbeite TEMP_DONE"

for dir in "$DONE"/*; do
    [[ -d "$dir" ]] || continue
    dir="${dir%/}"
    name="$(basename "$dir")"
    COUNT_FOUND_DONE=$((COUNT_FOUND_DONE + 1))

    if is_valid_done_folder "$name"; then
        process_done_folder "$dir"
    else
        process_container_done "$dir"
    fi
done

SUMMARY=$(cat <<EOF
EN: Photo ingest summary
DE: Foto-Ingest Zusammenfassung

EN: Found folders in TEMP_SD   / DE: Gefundene Ordner in TEMP_SD:   $COUNT_FOUND_SRC
EN: Found folders in TEMP_DONE / DE: Gefundene Ordner in TEMP_DONE: $COUNT_FOUND_DONE
EN: Processed folders          / DE: Verarbeitete Ordner:           $COUNT_PROCESSED
EN: Moved/Merged              / DE: Verschoben/Gemerged:           $COUNT_MOVED
EN: Skipped folders           / DE: Übersprungene Ordner:          $COUNT_SKIPPED
EN: Errors                    / DE: Fehler:                        $COUNT_ERRORS

EN: Log file                  / DE: Logdatei:                      $LOGFILE
EN: Error log                 / DE: Fehlerlog:                     $ERRORLOG
EOF
)

echo "$SUMMARY"
echo "===== END: $(date) ====="
