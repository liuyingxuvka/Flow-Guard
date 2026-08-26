import json

import pytest

from scripts.classify_behavior_surface_candidates import main


def test_discovery_artifact_must_be_json_object(tmp_path):
    discovery = tmp_path / "discovery.json"
    output = tmp_path / "report.json"
    discovery.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(ValueError, match="must contain an object"):
        main(
            [
                "--discovery",
                str(discovery),
                "--output",
                str(output),
            ]
        )


def test_plan_artifact_must_be_json_object(tmp_path):
    discovery = tmp_path / "discovery.json"
    plan = tmp_path / "plan.json"
    output = tmp_path / "report.json"
    discovery.write_text(json.dumps({}), encoding="utf-8")
    plan.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(ValueError, match="must contain an object"):
        main(
            [
                "--discovery",
                str(discovery),
                "--plan",
                str(plan),
                "--output",
                str(output),
            ]
        )
