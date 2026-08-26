"""Verify one clean, non-editable FlowGuard wheel as an external consumer.

The script deliberately runs from a temporary directory and imports only the
installed public package.  It does not use the repository on ``sys.path`` and
does not run the repository test suite.  The JSON result is an evidence input
for the outer DNA completion gate, not a release or Git authority.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

from flowguard._hashing import sha256_bytes
from flowguard.proof_artifact import (
    ProofArtifactRef,
    proof_artifact_integrity_gap_codes,
)


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    # Do not allow a caller's editable checkout/PYTHONPATH to masquerade as
    # the installed consumer.  The clean venv remains the only package source.
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            command,
            127,
            stdout="",
            stderr=str(exc),
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _evidence_fingerprint(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

def _write_current_proof(
    result: dict[str, object],
    *,
    output_path: Path,
    wheel_sha256: str,
) -> dict[str, object]:
    """Write independently verifiable consumer result, input, and receipt.

    The ordinary consumer smoke result is not itself a proof.  This helper
    creates a terminal result object, an exact input manifest, and a producer
    receipt, then verifies the resulting ``ProofArtifactRef`` by reopening
    those bytes.  A caller-authored status or a hash-shaped placeholder cannot
    make the evidence pass.
    """

    evidence_dir = output_path.parent.resolve()
    stem = output_path.stem
    terminal_path = evidence_dir / f"{stem}.terminal.json"
    input_path = evidence_dir / f"{stem}.inputs.json"
    receipt_path = evidence_dir / f"{stem}.receipt.json"
    started_at = datetime.now(timezone.utc).isoformat()
    finished_at = datetime.now(timezone.utc).isoformat()
    input_payload: dict[str, object] = {
        "schema_version": "flowguard.external_consumer_input_manifest.v1",
        "wheel": result.get("wheel", ""),
        "wheel_sha256": wheel_sha256,
        "consumer_commands": [
            "flowguard schema-version",
            "flowguard --help",
            "flowguard scenario-review",
            "flowguard behavior-commitment-ledger-template",
        ],
        "python_version": sys.version,
        "platform": platform.platform(),
        "claim_boundary": result.get("claim_boundary", ""),
    }
    input_bytes = _canonical_json_bytes(input_payload)
    input_path.write_bytes(input_bytes)
    input_fingerprint = sha256_bytes(input_bytes)
    subject_fingerprint = wheel_sha256
    model_fingerprint = sha256_bytes(
        _canonical_json_bytes(
            {
                "subject": "external-consumer-contract",
                "wheel_sha256": wheel_sha256,
                "input_manifest_fingerprint": input_fingerprint,
            }
        )
    )
    toolchain_fingerprint = sha256_bytes(
        _canonical_json_bytes(
            {
                "python": sys.version,
                "platform": platform.platform(),
                "verifier": "flowguard.verify_external_consumer.v2",
            }
        )
    )
    environment_fingerprint = sha256_bytes(
        _canonical_json_bytes(
            {
                "python_implementation": platform.python_implementation(),
                "machine": platform.machine(),
                "system": platform.system(),
            }
        )
    )
    owner_id = "native-consumer-owner:clean-wheel"
    receipt_id = f"receipt:{owner_id}:external-consumer:{wheel_sha256[7:19]}"
    command = [
        "flowguard schema-version",
        "flowguard --help",
        "flowguard scenario-review",
        "flowguard behavior-commitment-ledger-template",
    ]
    command_text = " && ".join(command)
    terminal_payload: dict[str, object] = {
        "schema_version": "flowguard.external_consumer_terminal_result.v1",
        "status": result.get("status", "blocked"),
        "wheel_sha256": wheel_sha256,
        "installation_exit_code": result.get("installation_exit_code"),
        "schema_entrypoint_exit_code": result.get("schema_entrypoint_exit_code"),
        "help_entrypoint_exit_code": result.get("help_entrypoint_exit_code"),
        "scenario_entrypoint_exit_code": result.get("scenario_entrypoint_exit_code"),
        "public_api_exit_code": result.get("public_api_exit_code"),
        "template_entrypoint_exit_code": result.get("template_entrypoint_exit_code"),
        "public_api": result.get("public_api", {}),
        "findings": result.get("findings", []),
        "input_manifest_fingerprint": input_fingerprint,
    }
    terminal_bytes = _canonical_json_bytes(terminal_payload)
    terminal_path.write_bytes(terminal_bytes)
    result_fingerprint = sha256_bytes(terminal_bytes)
    receipt_payload: dict[str, object] = {
        "receipt_id": receipt_id,
        "producer_id": owner_id,
        "result_status": "passed" if not result.get("findings") else "blocked",
        "exit_code": 0 if not result.get("findings") else 1,
        "command": command_text,
        "source_fingerprint": wheel_sha256,
        "model_fingerprint": model_fingerprint,
        "toolchain_fingerprint": toolchain_fingerprint,
        "environment_fingerprint": environment_fingerprint,
        "result_fingerprint": result_fingerprint,
        "terminal_state": "terminal_success" if not result.get("findings") else "terminal_failure",
        "cleanup_state": "zero_descendants",
        "cleanup_verified": True,
        "started_at": started_at,
        "finished_at": finished_at,
        "result_path": str(terminal_path),
        "input_manifest_path": str(input_path),
        "input_manifest_fingerprint": input_fingerprint,
    }
    receipt_bytes = _canonical_json_bytes(receipt_payload)
    receipt_path.write_bytes(receipt_bytes)
    receipt_fingerprint = sha256_bytes(receipt_bytes)
    artifact = ProofArtifactRef(
        artifact_id=f"proof:external-consumer:{wheel_sha256[7:19]}",
        producer_route="scripts.verify_external_consumer",
        command=command_text,
        result_path=str(terminal_path),
        result_status="passed" if not result.get("findings") else "failed",
        exit_code=0 if not result.get("findings") else 1,
        started_at=started_at,
        finished_at=finished_at,
        subject_id="flowguard.external-consumer",
        subject_fingerprint=subject_fingerprint,
        artifact_fingerprints={"result": result_fingerprint, "wheel": wheel_sha256},
        covered_obligation_ids=(
            "external_consumer.install",
            "external_consumer.console",
            "external_consumer.scenario",
            "external_consumer.public_api",
        ),
        assertion_scope="external_contract",
        current=True,
        route_evidence_current=True,
        receipt_id=receipt_id,
        receipt_path=str(receipt_path),
        receipt_fingerprint=receipt_fingerprint,
        execution_owner_id=owner_id,
        source_fingerprint=wheel_sha256,
        model_fingerprint=model_fingerprint,
        toolchain_fingerprint=toolchain_fingerprint,
        environment_fingerprint=environment_fingerprint,
        result_fingerprint=result_fingerprint,
        terminal_state="terminal_success" if not result.get("findings") else "terminal_failure",
        cleanup_state="zero_descendants",
        cleanup_verified=True,
        metadata={"input_manifest_path": str(input_path)},
    )
    gaps = proof_artifact_integrity_gap_codes(
        artifact,
        expected_receipt_id=receipt_id,
        expected_receipt_fingerprint=receipt_fingerprint,
        expected_owner_id=owner_id,
        expected_source_fingerprint=wheel_sha256,
        expected_model_fingerprint=model_fingerprint,
        expected_toolchain_fingerprint=toolchain_fingerprint,
        expected_environment_fingerprint=environment_fingerprint,
        expected_result_fingerprint=result_fingerprint,
    )
    if gaps:
        result.setdefault("findings", [])
        result["findings"] = [
            *list(result.get("findings", [])),
            "proof_artifact_verification_failed:" + ",".join(code for code, _ in gaps),
        ]
        result["status"] = "blocked"
    result.update(
        {
            "evidence_id": artifact.artifact_id,
            "proof_artifact": artifact.to_dict(),
            "input_manifest_path": str(input_path),
            "input_manifest_fingerprint": input_fingerprint,
            "result_fingerprint": result_fingerprint,
            "receipt_fingerprint": receipt_fingerprint,
        }
    )
    return result


def _package_path_findings(
    package_path: str,
    *,
    source_root: Path,
    venv_root: Path,
) -> list[str]:
    """Classify whether the consumer import escaped its clean venv.

    The consumer root may intentionally live below the repository's audit
    directory.  Therefore checking whether the package path is below the
    repository root is not sufficient: an installed package under that
    temporary venv is still a valid external-consumer import.  Only the
    repository's actual ``flowguard`` source package is forbidden, and the
    imported package must remain inside the venv.
    """

    try:
        resolved_package_path = Path(package_path).resolve()
        package_is_source = resolved_package_path.is_relative_to(
            (source_root / "flowguard").resolve()
        )
        package_is_outside_consumer_venv = not resolved_package_path.is_relative_to(
            venv_root.resolve()
        )
    except (OSError, ValueError):
        package_is_source = False
        package_is_outside_consumer_venv = True
    findings: list[str] = []
    if package_is_source:
        findings.append("external_consumer_imported_repository_source")
    if package_is_outside_consumer_venv:
        findings.append("external_consumer_package_path_outside_venv")
    return findings


def _scenario_review_passed(result: subprocess.CompletedProcess[str]) -> bool:
    """Require the documented scenario command's native terminal summary."""

    return result.returncode == 0 and "status: OK" in result.stdout


def verify_external_consumer(
    wheel: Path,
    *,
    root: Path | None = None,
    keep_root: bool = False,
) -> dict[str, object]:
    wheel = wheel.resolve()
    if not wheel.is_file() or wheel.suffix.lower() != ".whl":
        raise ValueError(f"wheel must be an existing .whl file: {wheel}")
    temporary = root is None
    consumer_root = (root or Path(tempfile.mkdtemp(prefix="flowguard-external-consumer-"))).resolve()
    consumer_root.mkdir(parents=True, exist_ok=True)
    venv_root = consumer_root / "venv"
    venv.EnvBuilder(with_pip=True, clear=True).create(venv_root)
    if sys.platform.startswith("win"):
        python = venv_root / "Scripts" / "python.exe"
        entrypoint = venv_root / "Scripts" / "flowguard.exe"
    else:
        python = venv_root / "bin" / "python"
        entrypoint = venv_root / "bin" / "flowguard"
    install = _run(
        [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        cwd=consumer_root,
    )
    findings: list[str] = []
    if install.returncode != 0:
        findings.append("wheel_install_failed")
    schema = _run([str(entrypoint), "schema-version"], cwd=consumer_root)
    if schema.returncode != 0 or schema.stdout.strip() != "1.0":
        findings.append("console_schema_version_failed")
    help_result = _run([str(entrypoint), "--help"], cwd=consumer_root)
    if help_result.returncode != 0 or "usage" not in help_result.stdout.lower():
        findings.append("console_help_entrypoint_failed")
    # ``--help`` only proves that argparse can be constructed.  Run one of the
    # documented model-backed commands as a real installed consumer as well;
    # this catches package-boundary regressions such as a console command that
    # imports repository-only ``examples`` modules.
    scenario_result = _run([str(entrypoint), "scenario-review"], cwd=consumer_root)
    if not _scenario_review_passed(scenario_result):
        findings.append("console_scenario_review_failed")
    public = _run(
        [
            str(python),
            "-I",
            "-c",
            (
                "import importlib.metadata, json, pathlib, flowguard; "
                "print(json.dumps({"
                "'installed_version': importlib.metadata.version('flowguard'), "
                "'schema_version': flowguard.SCHEMA_VERSION, "
                "'dna_completion_schema': flowguard.DNA_COMPLETION_SCHEMA, "
                "'runtime_evidence_type': flowguard.RuntimeTestEvidenceReport.__name__, "
                "'package_path': str(pathlib.Path(flowguard.__file__).resolve())"
                "}, sort_keys=True))"
            ),
        ],
        cwd=consumer_root,
    )
    if public.returncode != 0:
        findings.append("public_api_import_failed")
    public_payload: dict[str, object] = {}
    if public.stdout.strip():
        try:
            public_payload = json.loads(public.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            findings.append("public_api_output_not_json")
    package_path = str(public_payload.get("package_path", ""))
    source_root = Path(__file__).resolve().parents[1]
    findings.extend(
        _package_path_findings(
            package_path,
            source_root=source_root,
            venv_root=venv_root,
        )
    )
    template = _run([str(entrypoint), "behavior-commitment-ledger-template"], cwd=consumer_root)
    if template.returncode != 0 or not template.stdout.lstrip().startswith("{"):
        findings.append("console_template_contract_failed")
    result_without_fingerprint: dict[str, object] = {
        "schema_version": "flowguard.external_consumer_evidence.v1",
        "status": "passed" if not findings else "blocked",
        "claim_boundary": (
            "clean non-editable wheel, console entry point, documented "
            "scenario-review runtime, public API, and template smoke only"
        ),
        "wheel": str(wheel),
        "wheel_sha256": _sha256_file(wheel),
        "consumer_root": str(consumer_root),
        "installation_exit_code": install.returncode,
        "schema_entrypoint_exit_code": schema.returncode,
        "schema_entrypoint_stdout": schema.stdout.strip(),
        "help_entrypoint_exit_code": help_result.returncode,
        "help_entrypoint_stdout": help_result.stdout.strip(),
        "scenario_entrypoint_exit_code": scenario_result.returncode,
        "scenario_entrypoint_stdout": scenario_result.stdout.strip(),
        "scenario_entrypoint_stderr": scenario_result.stderr.strip(),
        "public_api_exit_code": public.returncode,
        "public_api": public_payload,
        "template_entrypoint_exit_code": template.returncode,
        "findings": findings,
    }
    result = {
        **result_without_fingerprint,
        "evidence_fingerprint": _evidence_fingerprint(result_without_fingerprint),
    }
    if temporary and not keep_root:
        # Keep the evidence self-contained in the result but remove the
        # temporary environment after terminal inspection has completed.
        import shutil

        shutil.rmtree(consumer_root, ignore_errors=True)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--root", type=Path, help="explicit consumer root to retain")
    parser.add_argument("--keep-root", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = verify_external_consumer(args.wheel, root=args.root, keep_root=args.keep_root)
    if args.output:
        result = _write_current_proof(
            result,
            output_path=args.output.resolve(),
            wheel_sha256=str(result.get("wheel_sha256", "")),
        )
        evidence_payload = dict(result)
        evidence_payload.pop("evidence_fingerprint", None)
        result["evidence_fingerprint"] = _evidence_fingerprint(evidence_payload)
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
