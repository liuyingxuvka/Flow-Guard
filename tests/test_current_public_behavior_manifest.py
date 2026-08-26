import json
import copy
from pathlib import Path

from scripts.discover_behavior_inventory import load_discovery_manifest
from flowguard.behavior_surface_audit import (
    PUBLIC_BEHAVIOR_SURFACE_CLASSES,
    build_public_behavior_surface_gap_report,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "flowguard_behavior_inventory_manifest.json"


def test_current_manifest_is_an_explicit_complete_public_behavior_denominator():
    evidence = load_discovery_manifest(MANIFEST, root=ROOT)
    assert evidence["status"] == "passed"
    inventory = evidence["inventory"]
    scope = inventory["metadata"]["coverage_scope"]
    assert scope["status"] == "complete_current"
    assert set(scope["surface_classes"]) == set(PUBLIC_BEHAVIOR_SURFACE_CLASSES)
    assert scope["candidate_intent_count"] == 23
    assert scope["candidate_model_obligation_count"] == 25
    assert set(scope["intent_decision_vocabulary"]) == {
        "retain_current",
        "supersede",
        "merge_into",
        "retire",
        "reject",
        "unresolved",
    }
    assert {
        "cli",
        "authority",
        "fault",
        "recovery",
        "file_format",
        "install",
        "upgrade",
        "manifest",
        "provider",
        "platform",
        "template",
        "ui",
        "release",
        "public_declaration",
        "scope",
    }.issubset(set(scope["behavior_domains"]))

    rows = inventory["items"]
    assert len(rows) >= len(PUBLIC_BEHAVIOR_SURFACE_CLASSES)
    assert {row["metadata"]["surface_class"] for row in rows} == set(
        PUBLIC_BEHAVIOR_SURFACE_CLASSES
    )
    assert all(row["intent_disposition"] != "unresolved" for row in rows)
    assert all(row["disposition"] != "blocked_gap" for row in rows)


def test_current_public_behavior_audit_licenses_complete_manifest():
    evidence = load_discovery_manifest(MANIFEST, root=ROOT)
    report = build_public_behavior_surface_gap_report(
        root=ROOT,
        manifest_evidence=evidence,
        manifest_path=MANIFEST,
        authority_status="passed",
    )
    assert report["status"] == "passed"
    assert report["complete_public_surface_claim_licensed"] is True
    assert report["denominator_expansion"] == "explicit_manifest"
    assert report["generated_behavior_ids"] == []
    assert {row["behavior_id"] for row in report["materialized_behavior_rows"]} == set(
        inventory["behavior_id"] for inventory in evidence["inventory"]["items"]
    )
    assert report["unresolved_surface_classes"] == []
    assert report["findings"] == []
    assert all(
        "Keep the current explicit manifest" in item["action"]
        or "Keep the current model-authority" in item["action"]
        for item in report["next_actions"]
    )


def test_complete_scope_cannot_hide_an_unrepresented_public_surface_class():
    evidence = load_discovery_manifest(MANIFEST, root=ROOT)
    incomplete = copy.deepcopy(evidence)
    incomplete["inventory"]["metadata"]["coverage_scope"]["surface_classes"] = [
        value
        for value in incomplete["inventory"]["metadata"]["coverage_scope"][
            "surface_classes"
        ]
        if value != "cli_command"
    ]
    report = build_public_behavior_surface_gap_report(
        root=ROOT,
        manifest_evidence=incomplete,
        manifest_path=MANIFEST,
        authority_status="passed",
    )
    assert report["status"] == "blocked"
    assert "cli_command" in report["unresolved_surface_classes"]
    assert any(
        finding["code"] == "behavior_discovery_cli_command_not_manifested"
        for finding in report["findings"]
    )
