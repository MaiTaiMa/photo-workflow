"""Tests fuer Ausgabe-Bloecke: Face-Statusblock (P5) und INIT/Abschluss (P6)."""


def test_face_block_emoji_und_pro_person() -> None:
    from app.faces.face_proposal_status import build_face_proposal_status_block

    block = build_face_proposal_status_block({
        "batch_id": "2026-08-01",
        "status": "proposals_created",
        "people_with_new_proposals": ["alice", "bob"],
        "new_per_person": {"alice": 2, "bob": 1},
        "pending_per_person": {"alice": 7, "bob": 3},
    })
    assert "🙂 FACE-VORSCHLÄGE" in block
    assert "Neu pro Person:" in block
    assert "alice: 2" in block
    assert "Review offen:" in block
    assert "bob: 3" in block


def test_face_block_ohne_pro_person_kompatibel() -> None:
    from app.faces.face_proposal_status import build_face_proposal_status_block

    block = build_face_proposal_status_block({
        "batch_id": "2026-08-01",
        "status": "proposals_created",
        "people_with_new_proposals": ["alice"],
    })
    assert "Neu pro Person:" not in block
    assert "Review offen:" not in block


def test_registration_zaehlt_new_per_person() -> None:
    from app.faces.face_proposal_reporting import build_registration_status

    status = build_registration_status(
        batch_id="b1",
        registration_result={"registered": [
            {"person_slug": "alice"},
            {"person_slug": "alice"},
            {"person_slug": "bob"},
        ], "skipped_count": 0},
    )
    assert status["new_per_person"] == {"alice": 2, "bob": 1}
    assert status["pending_per_person"] == {}


def test_registration_pending_per_person_durchgereicht() -> None:
    from app.faces.face_proposal_reporting import build_registration_status

    status = build_registration_status(
        batch_id="b1",
        registration_result={"registered": [{"person_slug": "alice"}],
                             "skipped_count": 0},
        pending_per_person={"alice": 7},
    )
    assert status["pending_per_person"] == {"alice": 7}


def test_init_banner_zeigt_temp_final(capsys) -> None:
    from app.photo_workflow import print_start_banner

    cfg = {"paths": {"base_dir": "b", "temp_sd": "s", "temp_images": "i",
                     "temp_done": "d", "temp_final": "f"}}
    print_start_banner(cfg, "pipeline")
    out = capsys.readouterr().out
    assert "TEMP_FINAL" in out


def test_abschlussbericht_sagt_moved(capsys) -> None:
    from app.photo_workflow import print_scheduler_summary

    payload = {
        "status": "success",
        "command": "pipeline",
        "counts": {"found_temp_sd": 0, "found_temp_done": 0, "processed": 0,
                   "moved_merged": 0, "finalized": 0, "skipped": 0,
                   "errors": 0},
        "paths": {"log_file": "l", "error_log": "e"},
        "learning": {},
        "started_at": "x",
        "finished_at": "y",
    }
    print_scheduler_summary({}, payload)
    out = capsys.readouterr().out
    assert "Moved:" in out
    assert "Moved/Final" not in out


def test_pending_per_person_zaehlt_new_faces(tmp_path) -> None:
    from app.photo_workflow import _pending_per_person

    faces = tmp_path / "faces"
    (faces / "Lilly" / "new_faces").mkdir(parents=True)
    (faces / "Lilly" / "new_faces" / "a.jpg").write_text("x")
    (faces / "Finn" / "new_faces").mkdir(parents=True)
    (faces / "Finn" / "new_faces" / "b.jpg").write_text("x")
    (faces / "Finn" / "new_faces" / "c.jpg").write_text("x")
    (faces / "Chris").mkdir(parents=True)
    cfg = {"family_recognition": {"reference_dir": str(faces)}}
    assert _pending_per_person(cfg) == {"Lilly": 1, "Finn": 2}
    assert _pending_per_person({}) == {}


def test_abschlussbericht_zeigt_pending_faces(capsys) -> None:
    """F7: pending_review > 0 muss im Abschlussbericht als Hinweis erscheinen."""
    from app.photo_workflow import print_scheduler_summary

    payload = {
        "status": "success",
        "command": "pipeline",
        "counts": {"found_temp_sd": 0, "found_temp_done": 0, "processed": 0,
                   "moved_merged": 0, "finalized": 0, "skipped": 0,
                   "errors": 0},
        "paths": {"log_file": "l", "error_log": "e"},
        "learning": {},
        "started_at": "x",
        "finished_at": "y",
        "face_proposal_status": {"pending_review": 3},
    }
    print_scheduler_summary({}, payload)
    out = capsys.readouterr().out
    assert "HINWEISE:" in out
    assert "Face-Vorschläge: 3 pending" in out
    assert "Ausstehend" in out


def test_abschlussbericht_ohne_pending_faces(capsys) -> None:
    """F7: Ohne pending_review bleibt der Bericht im gruenen Zustand."""
    from app.photo_workflow import print_scheduler_summary

    payload = {
        "status": "success",
        "command": "pipeline",
        "counts": {"found_temp_sd": 0, "found_temp_done": 0, "processed": 0,
                   "moved_merged": 0, "finalized": 0, "skipped": 0,
                   "errors": 0},
        "paths": {"log_file": "l", "error_log": "e"},
        "learning": {},
        "started_at": "x",
        "finished_at": "y",
        "face_proposal_status": {"pending_review": 0},
    }
    print_scheduler_summary({}, payload)
    out = capsys.readouterr().out
    assert "Keine ausstehenden Aktionen" in out
    assert "- Face-Vorschl" not in out


def test_face_block_zeigt_skipped_limits_und_waisen() -> None:
    """F8: Block zeigt durchgereichte Limits und verwaiste Dateien."""
    from app.faces.face_proposal_status import build_face_proposal_status_block

    block = build_face_proposal_status_block({
        "batch_id": "b1",
        "status": "proposals_created",
        "people_with_new_proposals": ["alice"],
        "skipped_limits": 13,
        "orphaned_per_person": {"alice": 3},
    })
    assert "skipped_limits:" in block
    assert "13" in block
    assert "Verwaiste Dateien:" in block
    assert "alice: 3" in block


def test_registration_f8_overrides_und_defaults() -> None:
    """F8: skipped_limits/pending_review Override, Fallback, Waisen-Default."""
    from app.faces.face_proposal_reporting import build_registration_status

    fallback = build_registration_status(
        batch_id="b1",
        registration_result={"registered": [{"person_slug": "alice"}],
                             "skipped_count": 4},
    )
    assert fallback["skipped_limits"] == 4
    assert fallback["pending_review"] == 1
    assert fallback["orphaned_per_person"] == {}

    override = build_registration_status(
        batch_id="b1",
        registration_result={"registered": [{"person_slug": "alice"}],
                             "skipped_count": 4},
        skipped_limits=9,
        pending_review=15,
        orphaned_per_person={"alice": 2},
    )
    assert override["skipped_limits"] == 9
    assert override["pending_review"] == 15
    assert override["created_new"] == 1
    assert override["orphaned_per_person"] == {"alice": 2}


def test_orphaned_face_crops_erkennt_dateien_ohne_eintrag(tmp_path) -> None:
    """F8: Waise = Datei ohne irgendeinen selection.json-Eintrag."""
    from app.photo_workflow import _orphaned_face_crops_per_person

    faces = tmp_path / "faces"
    nf = faces / "Lilly" / "new_faces"
    nf.mkdir(parents=True)
    for name in ("a.jpg", "b.jpg", "c.jpg"):
        (nf / name).write_text("x")
    (faces / "Lilly" / "selection.json").write_text(
        '{"images": [{"path": "new_faces/a.jpg", "status": "new"},'
        ' {"path": "new_faces/b.jpg", "status": "active"}]}',
        encoding="utf-8",
    )
    (faces / "Chris").mkdir()
    assert _orphaned_face_crops_per_person(faces) == {"Lilly": 1}
    assert _orphaned_face_crops_per_person(tmp_path / "fehlt") == {}


def test_face_proposal_summary_status_live_fallback(tmp_path, monkeypatch) -> None:
    """F9: pending_review kommt zur Not live aus dem Pool."""
    import app.photo_workflow as pw

    person = tmp_path / "WORKFLOW_DATA" / "faces" / "Lilly"
    person.mkdir(parents=True)
    (person / "selection.json").write_text(
        '{"images": [{"path": "new_faces/a.jpg", "status": "new"},'
        ' {"path": "new_faces/b.jpg", "status": "new"},'
        ' {"path": "new_faces/c.jpg", "status": "active"}]}',
        encoding="utf-8")
    cfg = {"paths": {"base_dir": str(tmp_path)}}

    monkeypatch.setattr(pw, "LAST_FACE_PROPOSAL_STATUS", {})
    assert pw._face_proposal_summary_status(cfg)["pending_review"] == 2

    monkeypatch.setattr(pw, "LAST_FACE_PROPOSAL_STATUS",
                        {"registered_count": 5, "pending_review": 0})
    status = pw._face_proposal_summary_status(cfg)
    assert status["pending_review"] == 2
    assert status["registered_count"] == 5
