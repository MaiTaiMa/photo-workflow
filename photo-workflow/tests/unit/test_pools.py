# =============================================================================
# PROJECT:     photo-workflow
# FILE:        tests/unit/test_pools.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from app.faces.crop_contract import CropContractError, save_new_face_crop
from app.faces.pool_rebuild import PoolRebuildError, RuntimeReferenceCache, rebuild_pool
from app.pool_limits import PoolLimits


def test_pool_rebuild_ranks_active_images_without_embeddings(tmp_path: Path):
    payload = rebuild_pool(tmp_path / "faces" / "alice", pool_type="face", slug="alice",
        images=[{"path": "a.jpg", "status": "active", "pool_utility_score": .5},
                {"path": "b.jpg", "status": "active", "pool_utility_score": .9}],
        limits={"max_active": 3, "max_new": 2}, model_fingerprint="m1",
        preprocessing_fingerprint="p1")
    assert payload["images"][0]["path"] == "b.jpg"
    assert "embedding" not in json.dumps(payload)
    assert payload["images"][0]["pool_rank"] == 1


def test_pool_rebuild_enforces_max_active(tmp_path: Path):
    with pytest.raises(PoolRebuildError):
        rebuild_pool(tmp_path / "pool", pool_type="face", slug="x",
            images=[{"path": "a.jpg", "status": "active"},
                    {"path": "b.jpg", "status": "active"}],
            limits={"max_active": 1}, model_fingerprint="m", preprocessing_fingerprint="p")


def test_crop_is_written_only_to_new_faces(tmp_path: Path):
    source = tmp_path / "photo.jpg"
    Image.new("RGB", (20, 20), "white").save(source)
    target = save_new_face_crop(source, tmp_path / "faces", slug="alice",
                                filename="candidate.jpg",
                                box={"left": 1, "top": 1, "right": 10, "bottom": 10})
    assert target.parts[-2:] == ("new_faces", "candidate.jpg")
    with pytest.raises(CropContractError):
        save_new_face_crop(source, tmp_path / "faces", slug="alice",
                           filename="../bad.jpg", box={"left": 1, "top": 1, "right": 10, "bottom": 10})





def test_workflow_face_proposals_default_is_disabled_in_config():
    import yaml
    from pathlib import Path

    config = yaml.safe_load(
        Path("config/config.yaml").read_text(encoding="utf-8")
    )
    assert config["face_proposals"]["enabled"] is True


def test_workflow_face_proposal_pipeline_is_config_gated():
    from pathlib import Path

    source = Path("app/photo_workflow.py").read_text(encoding="utf-8")
    assert 'face_proposal_cfg.get("enabled", False)' in source
    assert "build_face_proposal_batch" in source
    assert "register_face_proposals" in source


def test_workflow_face_proposal_hook_is_non_persistent_status_only():
    from pathlib import Path

    source = Path("app/photo_workflow.py").read_text(encoding="utf-8")
    assert "FACE_PROPOSALS_HOOK" in source
    assert "format_registration_status_block" in source
    assert '"registered": []' in source


def test_face_proposal_end_to_end_synthetic_batch(tmp_path: Path):
    from PIL import Image
    from app.faces.face_proposal_batch import build_face_proposal_batch
    from app.faces.face_proposal_registration import register_face_proposals
    from app.faces.face_proposal_reporting import format_registration_status_block

    source = tmp_path / "input" / "family_photo.png"
    source.parent.mkdir()
    Image.new("RGB", (640, 480), (120, 90, 60)).save(source)
    faces_root = tmp_path / "WORKFLOW_DATA" / "faces"
    batch_id = "synthetic-batch-a"

    batch = build_face_proposal_batch(
        [{
            "batch_id": batch_id,
            "source_id": f"{batch_id}:family_photo.jpg:face-0",
            "person_slug": "alice",
            "known_person": True,
            "ambiguous": False,
            "face_index": 0,
            "original_path": str(source),
            "bounding_box": {
                "left": 180,
                "top": 100,
                "right": 400,
                "bottom": 340,
            },
            "face_confidence": 0.95,
            "face_area_ratio": 0.8,
            "sharpness_score": 0.9,
            "exposure_score": 0.9,
            "framing_score": 0.9,
            "diversity_score": 0.8,
            "robustness_score": 0.8,
        }],
        batch_id=batch_id,
        output_root=faces_root,
        min_quality_score=0.7,
    )
    registration = register_face_proposals(
        batch["candidates"],
        pool_root=faces_root,
        limits={"max_new": 20, "max_new_per_batch": 5},
    )
    block = format_registration_status_block(
        batch_id=batch_id,
        registration_result=registration,
        known_matches=batch["counters"]["known_matches"],
        skipped_unknown=batch["counters"]["skipped_unknown"],
        skipped_ambiguous=batch["counters"]["skipped_ambiguous"],
        skipped_quality=batch["counters"]["skipped_quality"],
        remaining_batch_slots=4,
        remaining_global_slots=19,
    )

    crop = faces_root / "alice" / "new_faces" / (
        "synthetic-batch-a__synthetic-batch-a:family_photo__face-000.jpg"
    )
    selection = faces_root / "alice" / "selection.json"
    assert registration["registered_count"] == 1, registration
    assert crop.is_file()
    with Image.open(crop) as image:
        assert image.size == (256, 256)
        assert image.mode == "RGB"
        assert image.format == "JPEG"
    assert selection.is_file()
    assert not (faces_root / "alice" / "reference").exists()
    assert "FACE-VORSCHLÄGE" in block
    assert "Status:             proposals_created" in block
    assert "Personen:           -" in block
    assert "human_review_required_move_new_faces_to_reference" in block


def test_face_proposal_registration_status_lists_people():
    from app.faces.face_proposal_reporting import format_registration_status_block

    block = format_registration_status_block(
        batch_id="batch-a",
        registration_result={
            "registered": [{"person_slug": "alice"}, {"person_slug": "bob"}],
            "registered_count": 2,
            "skipped_count": 0,
        },
        known_matches=3,
        remaining_batch_slots=3,
        remaining_global_slots=18,
    )
    assert "FACE-VORSCHLÄGE" in block
    assert "Personen:           alice, bob" in block
    assert "Status:             proposals_created" in block
    assert "human_review_required" in block


def test_face_proposal_registration_writes_selection_only_for_new_faces(tmp_path: Path):
    from PIL import Image
    from app.faces.face_proposal_registration import register_face_proposals

    pool_root = tmp_path / "faces"
    crop = pool_root / "alice" / "new_faces" / "crop.jpg"
    crop.parent.mkdir(parents=True)
    Image.new("RGB", (256, 256), (10, 20, 30)).save(crop)

    result = register_face_proposals([{
        "source_id": "batch-a:photo.jpg:face-0",
        "batch_id": "batch-a",
        "person_slug": "alice",
        "crop_path": str(crop),
        "original_path": "/tmp/photo.jpg",
        "quality_score": 0.9,
        "candidate_utility_score": 0.8,
        "bounding_box": {"left": 1, "top": 2, "right": 10, "bottom": 12},
        "face_confidence": 0.95,
    }], pool_root=pool_root, limits={"max_new": 20, "max_new_per_batch": 5})

    assert result["registered_count"] == 1, {"result": result, "pool_root": str(pool_root), "crop": str(crop)}
    assert result["activation_required"] is True
    assert (pool_root / "alice" / "selection.json").is_file()
    assert not (pool_root / "alice" / "reference").exists()


def test_face_proposal_registration_skips_crop_outside_new_faces(tmp_path: Path):
    from PIL import Image
    from app.faces.face_proposal_registration import register_face_proposals

    pool_root = tmp_path / "faces"
    crop = pool_root / "alice" / "reference" / "crop.jpg"
    crop.parent.mkdir(parents=True)
    Image.new("RGB", (256, 256), (10, 20, 30)).save(crop)

    result = register_face_proposals([{
        "source_id": "batch-a:photo.jpg:face-0",
        "batch_id": "batch-a",
        "person_slug": "alice",
        "crop_path": str(crop),
        "original_path": "/tmp/photo.jpg",
        "quality_score": 0.9,
        "candidate_utility_score": 0.8,
        "bounding_box": {"left": 1, "top": 2, "right": 10, "bottom": 12},
        "face_confidence": 0.95,
    }], pool_root=pool_root, limits={"max_new": 20, "max_new_per_batch": 5})

    assert result["registered_count"] == 0
    assert result["skipped_count"] == 1


def test_face_proposal_batch_creates_only_known_quality_crops(tmp_path: Path):
    from PIL import Image
    from app.faces.face_proposal_batch import build_face_proposal_batch

    source = tmp_path / "photo.png"
    Image.new("RGB", (400, 300), (120, 80, 40)).save(source)
    result = build_face_proposal_batch([
        {
            "batch_id": "batch-a",
            "source_id": "photo.jpg:face-0",
            "person_slug": "alice",
            "known_person": True,
            "original_path": str(source),
            "bounding_box": {"left": 100, "top": 60, "right": 250, "bottom": 230},
            "face_confidence": 0.95,
            "face_area_ratio": 0.8,
            "sharpness_score": 0.9,
            "exposure_score": 0.9,
            "framing_score": 0.9,
            "diversity_score": 0.8,
            "robustness_score": 0.8,
        },
        {"batch_id": "batch-a", "source_id": "unknown:face-0", "known_person": False},
    ], batch_id="batch-a", output_root=tmp_path / "faces")

    assert result["counters"]["created_new"] == 1
    assert result["counters"]["skipped_unknown"] == 1
    assert result["counters"]["people_with_new_proposals"] == ["alice"]
    assert result["candidates"][0]["status"] == "new"
    assert result["candidates"][0]["path"].startswith("new_faces/")
    assert (tmp_path / "faces" / "alice" / "new_faces").is_dir()
    assert not (tmp_path / "faces" / "alice" / "reference").exists()


def test_face_proposal_batch_skips_low_quality_candidate(tmp_path: Path):
    from PIL import Image
    from app.faces.face_proposal_batch import build_face_proposal_batch

    source = tmp_path / "photo.png"
    Image.new("RGB", (100, 100), (1, 2, 3)).save(source)
    result = build_face_proposal_batch([{
        "batch_id": "batch-a",
        "source_id": "photo.jpg:face-0",
        "person_slug": "alice",
        "known_person": True,
        "original_path": str(source),
        "bounding_box": {"left": 10, "top": 10, "right": 40, "bottom": 40},
        "face_confidence": 0.4,
        "face_area_ratio": 0.2,
        "sharpness_score": 0.2,
        "exposure_score": 0.2,
        "framing_score": 0.2,
    }], batch_id="batch-a", output_root=tmp_path / "faces")
    assert result["counters"]["created_new"] == 0
    assert result["counters"]["skipped_quality"] == 1


def test_face_proposal_quality_score_uses_transparent_weights():
    from app.faces.face_proposal_scoring import calculate_quality_score

    score = calculate_quality_score(
        face_confidence=1.0,
        face_area_ratio=1.0,
        sharpness_score=1.0,
        exposure_score=1.0,
        framing_score=1.0,
    )
    assert score == 1.0

    lower = calculate_quality_score(
        face_confidence=0.5,
        face_area_ratio=0.5,
        sharpness_score=0.5,
        exposure_score=0.5,
        framing_score=0.5,
    )
    assert lower == 0.5


def test_face_proposal_utility_score_rewards_diversity():
    from app.faces.face_proposal_scoring import calculate_candidate_utility_score

    high = calculate_candidate_utility_score(
        quality_score=0.9,
        diversity_score=1.0,
        robustness_score=0.8,
        confidence_score=0.95,
    )
    low_diversity = calculate_candidate_utility_score(
        quality_score=0.9,
        diversity_score=0.0,
        robustness_score=0.8,
        confidence_score=0.95,
    )
    assert high > low_diversity


def test_face_proposal_scores_reject_out_of_range_values():
    import pytest
    from app.faces.face_proposal_scoring import (
        FaceProposalScoringError,
        calculate_quality_score,
    )

    with pytest.raises(FaceProposalScoringError):
        calculate_quality_score(
            face_confidence=1.1,
            face_area_ratio=0.5,
            sharpness_score=0.5,
            exposure_score=0.5,
            framing_score=0.5,
        )


def test_face_crop_generator_creates_256_square_rgb_jpeg(tmp_path: Path):
    from PIL import Image
    from app.faces.face_crop_generator import create_square_face_crop

    source = tmp_path / "source.png"
    target = tmp_path / "faces" / "alice" / "new_faces" / "crop.jpg"
    Image.new("RGB", (640, 480), (120, 80, 40)).save(source)

    result = create_square_face_crop(
        source,
        {"left": 200, "top": 120, "right": 360, "bottom": 300},
        target,
    )

    assert result == target
    with Image.open(target) as image:
        assert image.size == (256, 256)
        assert image.mode == "RGB"
        assert image.format == "JPEG"


def test_face_crop_generator_rejects_out_of_bounds_box(tmp_path: Path):
    import pytest
    from PIL import Image
    from app.faces.face_crop_generator import FaceCropError, create_square_face_crop

    source = tmp_path / "source.png"
    Image.new("RGB", (100, 100), (1, 2, 3)).save(source)
    with pytest.raises(FaceCropError):
        create_square_face_crop(
            source,
            {"left": 0, "top": 0, "right": 101, "bottom": 50},
            tmp_path / "new_faces" / "crop.jpg",
        )


def test_face_crop_generator_handles_image_edge_with_padding(tmp_path: Path):
    from PIL import Image
    from app.faces.face_crop_generator import create_square_face_crop

    source = tmp_path / "source.png"
    target = tmp_path / "new_faces" / "crop.jpg"
    Image.new("RGB", (120, 120), (255, 0, 0)).save(source)
    create_square_face_crop(
        source,
        {"left": 0, "top": 0, "right": 30, "bottom": 30},
        target,
    )
    with Image.open(target) as image:
        assert image.size == (256, 256)
        assert image.mode == "RGB"


def test_face_proposal_status_block_lists_people_with_new_proposals():
    from app.faces.face_proposal_status import build_face_proposal_status_block

    block = build_face_proposal_status_block({
        "batch_id": "batch-a",
        "status": "proposals_created",
        "people_with_new_proposals": ["bob", "alice", "alice"],
    })
    assert "Personen:           alice, bob" in block


def test_face_proposal_status_block_is_visually_separated():
    from app.faces.face_proposal_status import build_face_proposal_status_block

    block = build_face_proposal_status_block({
        "batch_id": "batch-a",
        "status": "proposals_created",
        "known_matches": 4,
        "eligible_candidates": 2,
        "created_new": 2,
        "pending_review": 2,
        "skipped_unknown": 0,
        "skipped_ambiguous": 1,
        "skipped_quality": 1,
        "skipped_limits": 0,
        "remaining_batch_slots": 3,
        "remaining_global_slots": 18,
        "action": "human_review_required",
        "people_with_new_proposals": ["alice"],
    })

    assert "FACE-VORSCHLÄGE" in block
    assert block.count("=") >= 72
    assert "Batch:              batch-a" in block
    assert "Aktion erforderlich: human_review_required" in block


def test_face_proposal_status_block_rejects_invalid_counts():
    import pytest
    from app.faces.face_proposal_status import (
        FaceProposalStatusError,
        build_face_proposal_status_block,
    )

    with pytest.raises(FaceProposalStatusError):
        build_face_proposal_status_block({
            "batch_id": "batch-a",
            "status": "no_candidates",
            "created_new": -1,
        })


def test_review_keep_can_become_face_candidate():
    review = {
        "batch_id": "batch-a",
        "image_id": "photo.jpg",
        "human_decision": "keep",
    }
    family = {
        "detected_people": ["alice"],
        "regions": [
            {
                "name": "alice",
                "left": 1,
                "top": 2,
                "right": 10,
                "bottom": 12,
                "distance": 0.12,
            }
        ],
    }

    assert review["human_decision"] == "keep"
    assert len(family["detected_people"]) == 1
    assert family["regions"][0]["name"] == "alice"
    assert "embedding" not in family


def test_face_proposal_pipeline_requires_complete_candidate_contract(tmp_path: Path):
    from app.faces.face_proposal_pipeline import (
        FaceProposalPipelineError,
        persist_selected_face_proposals,
    )

    root = tmp_path / "faces" / "alice"
    crop = root / "new_faces" / "candidate.jpg"
    crop.parent.mkdir(parents=True)
    crop.write_bytes(b"test")

    incomplete = {
        "source_id": "photo.jpg::face-0",
        "batch_id": "batch-a",
        "crop_path": crop,
        "original_path": "incoming/photo.jpg",
        "quality_score": 0.9,
        "candidate_utility_score": 0.8,
        "bounding_box": {"left": 1, "top": 2, "right": 10, "bottom": 12},
    }

    with pytest.raises((FaceProposalPipelineError, KeyError)):
        persist_selected_face_proposals(
            [incomplete],
            pool_root=str(root),
            slug="alice",
            limits={"max_new": 20, "max_new_per_batch": 5},
        )

    assert not (root / "selection.json").exists()


def test_face_proposal_pipeline_persists_selected_candidates(tmp_path: Path):
    from app.faces.face_proposal_pipeline import (
        persist_selected_face_proposals,
    )

    root = tmp_path / "faces" / "alice"
    crop = root / "new_faces" / "candidate.jpg"
    crop.parent.mkdir(parents=True)
    crop.write_bytes(b"test")

    candidate = {
        "source_id": "photo.jpg::face-0",
        "batch_id": "batch-a",
        "crop_path": crop,
        "original_path": "incoming/photo.jpg",
        "quality_score": 0.9,
        "candidate_utility_score": 0.8,
        "bounding_box": {"left": 1, "top": 2, "right": 10, "bottom": 12},
        "face_confidence": 0.95,
    }

    result = persist_selected_face_proposals(
        [candidate],
        pool_root=str(root),
        slug="alice",
        limits={"max_new": 20, "max_new_per_batch": 5},
    )

    assert len(result) == 1
    assert result[0]["status"] == "new"
    assert (root / "selection.json").is_file()


def test_face_proposal_pipeline_does_not_persist_rejected_candidates():
    from app.faces.face_proposal_pipeline import select_available_face_proposals

    candidates = [
        {
            "source_id": "unknown.jpg::face-0",
            "known_person": False,
            "human_decision": "keep",
            "quality_score": 0.99,
            "candidate_utility_score": 0.99,
        },
        {
            "source_id": "reject.jpg::face-0",
            "known_person": True,
            "human_decision": "reject",
            "quality_score": 0.99,
            "candidate_utility_score": 0.99,
        },
    ]

    result = select_available_face_proposals(
        candidates,
        [],
        batch_id="batch-a",
        limits={"max_new": 20, "max_new_per_batch": 5},
        min_quality_score=0.70,
    )

    assert result == []


def test_face_proposal_pipeline_applies_global_and_batch_slots():
    from app.faces.face_proposal_pipeline import (
        select_available_face_proposals,
    )

    candidates = [
        {
            "source_id": f"photo-{index}.jpg::face-0",
            "known_person": True,
            "human_decision": "keep",
            "quality_score": 0.9,
            "candidate_utility_score": 1.0 - index / 10,
        }
        for index in range(8)
    ]

    existing = [
        {"status": "new", "batch_id": "other-batch"}
        for _ in range(18)
    ]

    result = select_available_face_proposals(
        candidates,
        existing,
        batch_id="batch-a",
        limits={"max_new": 20, "max_new_per_batch": 5},
        min_quality_score=0.70,
    )

    assert len(result) == 2
    assert [item["source_id"] for item in result] == [
        "photo-0.jpg::face-0",
        "photo-1.jpg::face-0",
    ]


def test_face_candidate_selection_respects_available_pool_slots():
    from app.faces.face_proposal_selection import select_face_candidates

    candidates = [
        {
            "source_id": f"photo-{index}.jpg::face-0",
            "known_person": True,
            "human_decision": "keep",
            "quality_score": 0.9,
            "candidate_utility_score": 1.0 - index / 10,
        }
        for index in range(8)
    ]

    result = select_face_candidates(
        candidates,
        min_quality_score=0.70,
        max_count=min(3, 20 - 18),
    )

    assert len(result) == 2
    assert [item["source_id"] for item in result] == [
        "photo-0.jpg::face-0",
        "photo-1.jpg::face-0",
    ]


def test_face_proposal_selection_applies_both_limits():
    from app.faces.face_proposal_selection import select_face_candidates

    candidates = [
        {
            "source_id": f"photo-{index}.jpg::face-0",
            "known_person": True,
            "human_decision": "keep",
            "quality_score": 0.9,
            "candidate_utility_score": 1.0 - index / 10,
        }
        for index in range(6)
    ]

    result = select_face_candidates(
        candidates,
        min_quality_score=0.70,
        max_count=5,
    )

    assert len(result) == 5
    assert result[0]["source_id"] == "photo-0.jpg::face-0"
    assert result[-1]["source_id"] == "photo-4.jpg::face-0"


def test_face_candidate_selection_module_filters_and_prioritizes():
    from app.faces.face_proposal_selection import select_face_candidates

    candidates = [
        {
            "source_id": "low.jpg::face-0",
            "known_person": True,
            "human_decision": "keep",
            "quality_score": 0.69,
            "candidate_utility_score": 0.99,
        },
        {
            "source_id": "best.jpg::face-0",
            "known_person": True,
            "human_decision": "keep",
            "quality_score": 0.95,
            "candidate_utility_score": 0.90,
        },
        {
            "source_id": "reject.jpg::face-0",
            "known_person": True,
            "human_decision": "reject",
            "quality_score": 0.99,
            "candidate_utility_score": 1.00,
        },
        {
            "source_id": "unknown.jpg::face-0",
            "known_person": False,
            "human_decision": "keep",
            "quality_score": 0.99,
            "candidate_utility_score": 0.99,
        },
    ]

    result = select_face_candidates(
        candidates,
        min_quality_score=0.70,
        max_count=1,
    )

    assert [item["source_id"] for item in result] == [
        "best.jpg::face-0"
    ]


def test_face_candidate_filtering_and_prioritization_contract():
    candidates = [
        {
            "source_id": "low.jpg::face-0",
            "batch_id": "batch-a",
            "quality_score": 0.69,
            "candidate_utility_score": 0.99,
        },
        {
            "source_id": "best.jpg::face-0",
            "batch_id": "batch-a",
            "quality_score": 0.95,
            "candidate_utility_score": 0.90,
        },
        {
            "source_id": "second.jpg::face-0",
            "batch_id": "batch-a",
            "quality_score": 0.90,
            "candidate_utility_score": 0.80,
        },
    ]

    allowed = [
        candidate
        for candidate in candidates
        if candidate["quality_score"] >= 0.70
    ]
    prioritized = sorted(
        allowed,
        key=lambda candidate: -candidate["candidate_utility_score"],
    )

    assert [item["source_id"] for item in prioritized[:1]] == [
        "best.jpg::face-0"
    ]
    assert all(item["quality_score"] >= 0.70 for item in prioritized[:1])


def test_face_proposal_writer_rejects_unsafe_crop_path(tmp_path: Path):
    from app.faces.proposal_contract import FaceProposalError, add_face_proposal

    root = tmp_path / "faces" / "alice"
    crop = tmp_path / "outside.jpg"
    crop.write_bytes(b"test")

    with pytest.raises(FaceProposalError, match="inside the face pool"):
        add_face_proposal(
            pool_root=root,
            slug="alice",
            source_id="photo.jpg::face-0",
            batch_id="batch-a",
            crop_path=crop,
            original_path="incoming/photo.jpg",
            quality_score=0.9,
            candidate_utility_score=0.8,
            bounding_box={"left": 1, "top": 2, "right": 10, "bottom": 12},
            face_confidence=0.95,
            limits={"max_new": 20, "max_new_per_batch": 5},
        )


def test_face_proposal_writer_rejects_unsafe_identifiers(tmp_path: Path):
    from app.faces.proposal_contract import FaceProposalError, add_face_proposal

    root = tmp_path / "faces" / "alice"
    crop = root / "new_faces" / "candidate.jpg"
    crop.parent.mkdir(parents=True)
    crop.write_bytes(b"test")

    common = {
        "pool_root": root,
        "source_id": "photo.jpg::face-0",
        "batch_id": "batch-a",
        "crop_path": crop,
        "original_path": "incoming/photo.jpg",
        "quality_score": 0.9,
        "candidate_utility_score": 0.8,
        "bounding_box": {"left": 1, "top": 2, "right": 10, "bottom": 12},
        "face_confidence": 0.95,
        "limits": {"max_new": 20, "max_new_per_batch": 5},
    }

    unsafe_slug = dict(common)
    unsafe_slug["slug"] = "../alice"
    with pytest.raises(FaceProposalError, match="slug"):
        add_face_proposal(**unsafe_slug)

    unsafe_batch = dict(common)
    unsafe_batch["slug"] = "alice"
    unsafe_batch["batch_id"] = "../batch-a"
    with pytest.raises(FaceProposalError, match="batch_id"):
        add_face_proposal(**unsafe_batch)


def test_face_proposal_writer_rejects_invalid_selection(tmp_path: Path):
    from app.faces.proposal_contract import FaceProposalError, add_face_proposal

    root = tmp_path / "faces" / "alice"
    crop = root / "new_faces" / "candidate.jpg"
    crop.parent.mkdir(parents=True)
    crop.write_bytes(b"test")

    invalid_selection = {
        "schema_version": 1,
        "pool_type": "face",
        "slug": "alice",
        "images": [
            {
                "status": "new",
                "batch_id": "batch-a",
                "path": "../outside.jpg",
                "embedding": [0.1, 0.2],
            }
        ],
    }
    (root / "selection.json").write_text(
        json.dumps(invalid_selection),
        encoding="utf-8",
    )

    with pytest.raises(FaceProposalError):
        add_face_proposal(
            pool_root=root,
            slug="alice",
            source_id="photo.jpg::face-0",
            batch_id="batch-b",
            crop_path=crop,
            original_path="incoming/photo.jpg",
            quality_score=0.9,
            candidate_utility_score=0.8,
            bounding_box={"left": 1, "top": 2, "right": 10, "bottom": 12},
            face_confidence=0.95,
            limits={"max_new": 20, "max_new_per_batch": 5},
        )


def test_face_proposal_writer_enforces_global_max_new(tmp_path: Path):
    from app.faces.proposal_contract import FaceProposalError, add_face_proposal

    root = tmp_path / "faces" / "alice"
    crop_dir = root / "new_faces"
    crop_dir.mkdir(parents=True)

    limits = {"max_new": 2, "max_new_per_batch": 2}
    common = {
        "pool_root": root,
        "slug": "alice",
        "original_path": "incoming/photo.jpg",
        "quality_score": 0.9,
        "candidate_utility_score": 0.8,
        "bounding_box": {"left": 1, "top": 2, "right": 10, "bottom": 12},
        "face_confidence": 0.95,
        "limits": limits,
    }

    for index, batch_id in enumerate(("batch-a", "batch-b")):
        crop = crop_dir / f"candidate-{index}.jpg"
        crop.write_bytes(b"test")
        add_face_proposal(
            **common,
            source_id=f"photo-{index}.jpg::face-0",
            batch_id=batch_id,
            crop_path=crop,
        )

    crop = crop_dir / "candidate-2.jpg"
    crop.write_bytes(b"test")

    with pytest.raises(FaceProposalError, match="max_new reached"):
        add_face_proposal(
            **common,
            source_id="photo-2.jpg::face-0",
            batch_id="batch-c",
            crop_path=crop,
        )

    import json
    selection = json.loads((root / "selection.json").read_text(encoding="utf-8"))
    assert len(selection["images"]) == 2


def test_face_proposal_writer_keeps_batch_limits_isolated(tmp_path: Path):
    from app.faces.proposal_contract import FaceProposalError, add_face_proposal

    root = tmp_path / "faces" / "alice"
    crop_dir = root / "new_faces"
    crop_dir.mkdir(parents=True)

    common = {
        "pool_root": root,
        "slug": "alice",
        "original_path": "incoming/photo.jpg",
        "quality_score": 0.9,
        "candidate_utility_score": 0.8,
        "bounding_box": {"left": 1, "top": 2, "right": 10, "bottom": 12},
        "face_confidence": 0.95,
        "limits": {"max_new": 4, "max_new_per_batch": 1},
    }

    first_crop = crop_dir / "batch-a.jpg"
    first_crop.write_bytes(b"test")
    add_face_proposal(
        **common,
        source_id="a.jpg::face-0",
        batch_id="batch-a",
        crop_path=first_crop,
    )

    second_crop = crop_dir / "batch-b.jpg"
    second_crop.write_bytes(b"test")
    add_face_proposal(
        **common,
        source_id="b.jpg::face-0",
        batch_id="batch-b",
        crop_path=second_crop,
    )

    third_crop = crop_dir / "batch-a-second.jpg"
    third_crop.write_bytes(b"test")

    with pytest.raises(FaceProposalError, match="max_new_per_batch"):
        add_face_proposal(
            **common,
            source_id="a2.jpg::face-0",
            batch_id="batch-a",
            crop_path=third_crop,
        )


def test_add_face_proposal_writes_selection_and_enforces_limits(tmp_path: Path):
    from app.faces.proposal_contract import FaceProposalError, add_face_proposal

    root = tmp_path / "faces" / "alice"
    crop = root / "new_faces" / "candidate.jpg"
    crop.parent.mkdir(parents=True)
    crop.write_bytes(b"test")

    kwargs = {
        "pool_root": root,
        "slug": "alice",
        "source_id": "photo.jpg::face-0",
        "batch_id": "batch-a",
        "crop_path": crop,
        "original_path": "incoming/photo.jpg",
        "quality_score": 0.9,
        "candidate_utility_score": 0.8,
        "bounding_box": {"left": 1, "top": 2, "right": 10, "bottom": 12},
        "face_confidence": 0.95,
        "limits": {"max_new": 2, "max_new_per_batch": 1},
    }

    first = add_face_proposal(**kwargs)
    assert first["status"] == "new"
    assert first["batch_id"] == "batch-a"

    selection = json.loads((root / "selection.json").read_text(encoding="utf-8"))
    assert len(selection["images"]) == 1
    assert selection["images"][0]["path"] == "new_faces/candidate.jpg"
    assert "embedding" not in json.dumps(selection)
    assert "image_bytes" not in json.dumps(selection)

    second_kwargs = dict(kwargs)
    second_kwargs["source_id"] = "other.jpg::face-0"
    second_kwargs["crop_path"] = root / "new_faces" / "other.jpg"

    with pytest.raises(FaceProposalError, match="max_new_per_batch"):
        add_face_proposal(**second_kwargs)


def test_face_proposal_selection_contract_has_batch_and_source_fields():
    proposal = {
        "source_id": "photo.jpg::face-0",
        "batch_id": "2026-09-03-example",
        "path": "faces/alice/new_faces/photo__face.jpg",
        "status": "new",
        "quality_score": 0.91,
        "candidate_utility_score": 0.84,
        "bounding_box": {"left": 1, "top": 2, "right": 10, "bottom": 12},
        "face_confidence": 0.97,
        "original_path": "incoming/photo.jpg",
    }

    required = {
        "source_id",
        "batch_id",
        "path",
        "status",
        "quality_score",
        "candidate_utility_score",
        "bounding_box",
        "face_confidence",
        "original_path",
    }

    assert required <= proposal.keys()
    assert proposal["status"] == "new"
    assert "embedding" not in proposal
    assert "image_bytes" not in proposal


def test_face_pool_limits_are_resolved_from_reference_pools_common():
    cfg = {
        "reference_pools": {
            "common": {
                "max_new": 20,
                "max_new_per_batch": 5,
            },
            "faces": {
                "enabled": True,
                "root_dir": "faces",
            },
        }
    }

    common = cfg["reference_pools"]["common"]
    face_cfg = cfg["reference_pools"]["faces"]
    limits = {
        "max_new": int(common["max_new"]),
        "max_new_per_batch": int(common["max_new_per_batch"]),
    }

    assert face_cfg["enabled"] is True
    assert limits == {"max_new": 20, "max_new_per_batch": 5}


def test_pool_limits_blocks_new_candidates_at_max_new():
    limits = PoolLimits({
        "max_active": 10,
        "min_active": 0,
        "target_active": 5,
        "max_new": 5,
        "max_new_per_batch": 5,
    })

    assert limits.can_add_new(new_count=0, count=5) is True
    assert limits.can_add_new(new_count=5, count=1) is False
    assert limits.get_batch_limit(new_count=0) == 5
    assert limits.get_batch_limit(new_count=5) == 0


def test_crop_limit_blocks_sixth_candidate(tmp_path: Path):
    source = tmp_path / "photo.jpg"
    Image.new("RGB", (20, 20), "white").save(source)
    root = tmp_path / "faces"
    box = {"left": 1, "top": 1, "right": 10, "bottom": 10}

    for index in range(5):
        save_new_face_crop(
            source,
            root,
            slug="alice",
            filename=f"candidate-{index}.jpg",
            box=box,
            max_new_per_batch=5,
        )

    with pytest.raises(CropContractError, match="max_new_per_batch"):
        save_new_face_crop(
            source,
            root,
            slug="alice",
            filename="candidate-5.jpg",
            box=box,
            max_new_per_batch=5,
        )

    assert len(list((root / "alice" / "new_faces").glob("*.jpg"))) == 5


def test_runtime_cache_rebuilds_after_fingerprint_change():
    cache = RuntimeReferenceCache()
    calls = []
    assert cache.get_or_rebuild("a", lambda: calls.append(1) or {"x": 1})["x"] == 1
    cache.get_or_rebuild("a", lambda: calls.append(1) or {"x": 2})
    cache.get_or_rebuild("b", lambda: calls.append(1) or {"x": 3})
    assert len(calls) == 2