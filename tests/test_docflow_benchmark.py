from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from benchmark import compare, validate_report


def report():
    sample = {"wall_seconds": 2.0, "parent_process_cpu_seconds": 1.0,
              "workload_sha256": "workload", "result_sha256": "result", "completed": 37, "failed": 3}
    return {"schema": 2, "conditions": {"runs": 3, "workload_sha256": "workload", "measurement_label": "same"},
            "samples": [deepcopy(sample) for _ in range(3)], "median_wall_seconds": 2.0, "median_parent_process_cpu_seconds": 1.0}


def pair(tmp_path, before, after):
    paths = [tmp_path / "before.json", tmp_path / "after.json"]
    for p, value in zip(paths, (before, after)):
        p.write_text(json.dumps(value))
    return SimpleNamespace(before=paths[0], after=paths[1])


def test_comparison_rejects_changed_outputs(tmp_path):
    before, after = report(), report()
    after["samples"][1]["result_sha256"] = "wrong"
    with pytest.raises(ValueError, match="Correctness"):
        compare(pair(tmp_path, before, after))


def test_comparison_rejects_incompatible_monitoring(tmp_path):
    before, after = report(), report()
    after["conditions"]["measurement_label"] = "different"
    with pytest.raises(ValueError, match="conditions differ"):
        compare(pair(tmp_path, before, after))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, 0])
def test_invalid_measurements(value):
    data = report()
    data["samples"][0]["wall_seconds"] = value
    with pytest.raises(ValueError):
        validate_report(data)


def test_forged_median_and_short_reports():
    data = report()
    data["median_wall_seconds"] = 0.01
    with pytest.raises(ValueError, match="median"):
        validate_report(data)
    data = report()
    data["samples"].pop()
    with pytest.raises(ValueError, match="trial count"):
        validate_report(data)


def test_local_comparison_cannot_award_efficiency_points(tmp_path):
    assert compare(pair(tmp_path, report(), report()))["efficiency_score_eligible"] is False
