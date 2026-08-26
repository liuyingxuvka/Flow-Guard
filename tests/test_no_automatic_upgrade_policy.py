import json
from pathlib import Path
import flowguard.artifact_upgrade as artifact_upgrade

from flowguard.artifact_upgrade import (
    ARTIFACT_UPGRADE_POLICY,
    ARTIFACT_UPGRADE_STATUS_BLOCKED,
    review_artifact_upgrades,
)


def _legacy_ledger() -> dict:
    evidence = {
        "model_obligation_ids": [],
        "code_contract_ids": [],
        "test_evidence_ids": [],
        "proof_artifact_ids": [],
        "risk_gate_ids": [],
        "coverage_case_ids": [],
        "coverage_shard_ids": [],
        "coverage_receipt_ids": [],
        "evidence_state": "missing",
        "test_mesh_state": "shard_current",
        "current": False,
        "metadata": {},
    }
    path_authority = {
        "path_sensitive": False,
        "business_intent": "",
        "ppa_report_id": "",
        "ppa_decision": "",
        "ppa_confidence": "",
        "ppa_ok": None,
        "primary_path_ids": [],
        "fallback_candidate_ids": [],
        "ppa_coverage_receipt_ids": [],
        "ppa_coverage_shard_ids": [],
        "ppa_risk_gate_ids": [],
        "scoped_out_reason": "",
        "evidence_refs": [],
        "metadata": {},
    }

    def row(commitment_id: str) -> dict:
        return {
            "commitment_id": commitment_id,
            "label": commitment_id,
            "commitment_kind": "public_api",
            "actor": "external client",
            "trigger": "",
            "expected_result": "",
            "failure_boundary": "",
            "source_surface_ids": [],
            "source_refs": [],
            "primary_owner_model_id": "model:current",
            "supporting_model_ids": [],
            "child_model_ids": [],
            "dependency_commitment_ids": [],
            "excluded_behavior_ids": [],
            "replacement_state": "active",
            "model_sync_state": "owner_model_current",
            "miss_origin_state": "no_miss",
            "path_authority": path_authority,
            "evidence": evidence,
            "in_scope": True,
            "scoped_out_reason": "",
            "owner": "",
            "validation_boundary": "",
            "rationale": "",
            "metadata": {
                "migration_behavior_plane": "product_runtime",
                "migration_actor_kind": "external_system",
            },
        }

    return {
        "ledger_id": "ledger:legacy",
        "project_boundary": "legacy",
        "current_revision": "old",
        "commitments": [row("commitment:legacy")],
        "source_surfaces": [],
        "expected_commitment_ids": ["commitment:legacy"],
        "claim_scope": "routine",
        "change_mode": "bootstrap_ledger",
        "require_current_evidence": False,
        "require_risk_gates_for_broad_claim": True,
        "owner": "",
        "validation_boundary": "",
        "rationale": "",
        "metadata": {},
    }


def test_no_legacy_mapping_candidate_or_upgrade_status_is_exposed():
    assert not hasattr(artifact_upgrade, "upgrade_behavior_commitment_ledger_mapping")
    assert not hasattr(artifact_upgrade, "BehaviorLedgerMigrationResult")
    assert not hasattr(artifact_upgrade, "ARTIFACT_UPGRADE_STATUS_UPGRADED")


def test_scan_never_rewrites_legacy_ledger_or_obsolete_alias(tmp_path: Path):
    ledger = tmp_path / ".flowguard" / "behavior_commitment_ledger" / "ledger.json"
    alias = tmp_path / "scripts" / "old.py"
    ledger.parent.mkdir(parents=True)
    alias.parent.mkdir(parents=True)
    ledger.write_text(json.dumps(_legacy_ledger()), encoding="utf-8")
    alias.write_text("PlanIntakeSurface = object\n", encoding="utf-8")
    before = (ledger.read_bytes(), alias.read_bytes())

    report = review_artifact_upgrades(tmp_path)

    assert not report.ok
    assert all(item.status == ARTIFACT_UPGRADE_STATUS_BLOCKED for item in report.items)
    assert all(item.metadata.get("policy") == ARTIFACT_UPGRADE_POLICY for item in report.items)
    assert (ledger.read_bytes(), alias.read_bytes()) == before
    assert all(not item.changed for item in report.items)
