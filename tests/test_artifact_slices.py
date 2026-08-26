import json

import pytest

from flowguard.artifact_slices import ArtifactSliceError, read_artifact_slice
from scripts.read_flowguard_artifact_slice import main


def test_artifact_slice_is_bounded_and_deterministic(tmp_path):
    artifact = tmp_path / "report.json"
    artifact.write_text(
        json.dumps({"surfaces": [{"surface_id": f"surface:{i}"} for i in range(5)]}),
        encoding="utf-8",
    )
    first = read_artifact_slice(artifact, field="surfaces", offset=1, limit=2)
    second = read_artifact_slice(artifact, field="surfaces", offset=1, limit=2)
    assert first == second
    assert first["total_count"] == 5
    assert first["returned_count"] == 2
    assert first["omitted_before"] == 1
    assert first["omitted_after"] == 2
    assert [row["surface_id"] for row in first["rows"]] == ["surface:1", "surface:2"]
    assert first["claim_boundary"].startswith("Read-only bounded")


def test_artifact_slice_rejects_non_array_and_oversized_requests(tmp_path):
    artifact = tmp_path / "report.json"
    artifact.write_text(json.dumps({"status": "passed"}), encoding="utf-8")
    with pytest.raises(ArtifactSliceError):
        read_artifact_slice(artifact, field="status")
    with pytest.raises(ArtifactSliceError):
        read_artifact_slice(artifact, field="status", limit=501)


def test_artifact_slice_cli_is_small_and_points_to_full_artifact(tmp_path, capsys):
    artifact = tmp_path / "report.json"
    artifact.write_text(json.dumps({"items": list(range(10))}), encoding="utf-8")
    assert main(["--artifact", str(artifact), "--field", "items", "--offset", "8", "--limit", "5"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["artifact_ref"] == str(artifact.resolve())
    assert result["rows"] == [8, 9]
    assert result["omitted_after"] == 0
