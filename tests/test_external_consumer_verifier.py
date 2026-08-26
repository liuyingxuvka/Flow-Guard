from flowguard._hashing import sha256_bytes
from pathlib import Path
import subprocess

from scripts.verify_external_consumer import (
    _package_path_findings,
    _scenario_review_passed,
    _write_current_proof,
)


def test_consumer_venv_under_repository_is_not_mistaken_for_source_import(tmp_path):
    source_root = tmp_path / "repo"
    venv_root = source_root / ".flowguard" / "work" / "consumer" / "venv"
    installed = venv_root / "Lib" / "site-packages" / "flowguard" / "__init__.py"

    assert _package_path_findings(
        str(installed), source_root=source_root, venv_root=venv_root
    ) == []


def test_consumer_source_import_and_outside_venv_are_distinct_findings(tmp_path):
    source_root = tmp_path / "repo"
    venv_root = source_root / ".flowguard" / "work" / "consumer" / "venv"

    assert _package_path_findings(
        str(source_root / "flowguard" / "__init__.py"),
        source_root=source_root,
        venv_root=venv_root,
    ) == [
        "external_consumer_imported_repository_source",
        "external_consumer_package_path_outside_venv",
    ]
    assert _package_path_findings(
        str(Path(tmp_path) / "other" / "flowguard" / "__init__.py"),
        source_root=source_root,
        venv_root=venv_root,
    ) == ["external_consumer_package_path_outside_venv"]


def test_external_consumer_requires_a_real_scenario_review_terminal_summary():
    passed = subprocess.CompletedProcess(
        ["flowguard", "scenario-review"],
        0,
        stdout="status: OK\n",
        stderr="",
    )
    failed_without_summary = subprocess.CompletedProcess(
        ["flowguard", "scenario-review"],
        0,
        stdout="usage: flowguard\n",
        stderr="",
    )
    failed_exit = subprocess.CompletedProcess(
        ["flowguard", "scenario-review"],
        1,
        stdout="status: OK\n",
        stderr="ModuleNotFoundError: examples\n",
    )

    assert _scenario_review_passed(passed)
    assert not _scenario_review_passed(failed_without_summary)
    assert not _scenario_review_passed(failed_exit)


def test_write_current_proof_hashes_written_bytes_exactly(tmp_path):
    output_path = tmp_path / "external-consumer.json"
    result = _write_current_proof(
        {
            "status": "passed",
            "wheel": "dist/flowguard.whl",
            "installation_exit_code": 0,
            "schema_entrypoint_exit_code": 0,
            "help_entrypoint_exit_code": 0,
            "scenario_entrypoint_exit_code": 0,
            "public_api_exit_code": 0,
            "template_entrypoint_exit_code": 0,
            "public_api": {"schema_version": "1.0"},
            "findings": [],
            "claim_boundary": "fixture",
        },
        output_path=output_path,
        wheel_sha256="sha256:" + "a" * 64,
    )

    terminal_path = output_path.with_suffix(".terminal.json")
    input_path = output_path.with_suffix(".inputs.json")
    receipt_path = output_path.with_suffix(".receipt.json")

    assert result["input_manifest_fingerprint"] == sha256_bytes(input_path.read_bytes())
    assert result["result_fingerprint"] == sha256_bytes(terminal_path.read_bytes())
    assert result["receipt_fingerprint"] == sha256_bytes(receipt_path.read_bytes())
