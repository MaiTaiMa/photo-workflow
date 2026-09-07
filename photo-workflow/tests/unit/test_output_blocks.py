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
