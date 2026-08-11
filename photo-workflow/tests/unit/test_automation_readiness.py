from app.automation_readiness import READINESS_POLICY, build_readiness_report


def _report(**overrides):
    report = {
        "evaluated_predictions": 0,
        "matching_predictions": 0,
        "predicted_keep": 0,
        "confirmed_keep": 0,
        "predicted_reject": 0,
        "confirmed_reject": 0,
        "excluded_review_predictions": 0,
        "unreviewed_predictions": 0,
    }
    report.update(overrides)
    return report


def test_readiness_uses_prediction_weighted_metrics() -> None:
    report = build_readiness_report(
        [
            _report(
                evaluated_predictions=100,
                matching_predictions=90,
                predicted_keep=50,
                confirmed_keep=45,
                predicted_reject=50,
                confirmed_reject=45,
            ),
            _report(
                evaluated_predictions=10,
                matching_predictions=10,
                predicted_keep=5,
                confirmed_keep=5,
                predicted_reject=5,
                confirmed_reject=5,
            ),
        ]
    )

    assert report["overall_agreement"] == 100 / 110
    assert report["keep_precision"] == 50 / 55
    assert report["reject_precision"] == 50 / 55
    assert report["status"] == "not_ready"


def test_readiness_is_not_evaluable_without_evaluated_predictions() -> None:
    report = build_readiness_report([_report(excluded_review_predictions=3)])

    assert report["status"] == "not_evaluable"
    assert report["overall_agreement"] is None
    assert report["readiness_reasons"] == ["no evaluated predictions are available"]


def test_readiness_is_ready_when_all_policy_thresholds_are_met() -> None:
    count = READINESS_POLICY["minimum_evaluated_predictions"]
    report = build_readiness_report(
        [
            _report(
                evaluated_predictions=count // 3,
                matching_predictions=count // 3,
                predicted_keep=count // 6,
                confirmed_keep=count // 6,
                predicted_reject=count // 6,
                confirmed_reject=count // 6,
            ),
            _report(
                evaluated_predictions=count // 3,
                matching_predictions=count // 3,
                predicted_keep=count // 6,
                confirmed_keep=count // 6,
                predicted_reject=count // 6,
                confirmed_reject=count // 6,
            ),
            _report(
                evaluated_predictions=count - (2 * (count // 3)),
                matching_predictions=count - (2 * (count // 3)),
                predicted_keep=count // 6,
                confirmed_keep=count // 6,
                predicted_reject=count - (5 * (count // 6)),
                confirmed_reject=count - (5 * (count // 6)),
            ),
        ]
    )

    assert report["status"] == "ready"
    assert report["evaluable_batch_count"] == 3
    assert report["evaluated_predictions"] == count
