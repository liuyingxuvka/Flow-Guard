import json
from pathlib import Path

import pytest

from scripts.discover_behavior_inventory import (
    BehaviorDiscoveryError,
    load_discovery_manifest,
    main as discover_main,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "flowguard_behavior_inventory_manifest.json"


def test_native_manifest_materializes_current_complete_independent_denominator():
    result = load_discovery_manifest(MANIFEST, root=ROOT)

    assert result["status"] == "passed"
    assert result["review"]["ok"] is True
    assert result["review"]["findings"] == []
    assert result["inventory"]["expected_behavior_ids"] == [
        "flowguard.dna_completion.review",
        "flowguard.runtime_test_evidence.reconcile",
        "flowguard.behavior_inventory.reconcile",
        "flowguard.external_consumer.verify",
        "flowguard.public.api",
        "flowguard.public.cli",
        "flowguard.public.template",
        "flowguard.public.ui",
        "flowguard.public.provider_platform",
        "flowguard.public.release",
    ]
    assert result["evidence_fingerprint"].startswith("sha256:")


def test_native_manifest_rejects_bcl_or_test_sources(tmp_path):
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["behaviors"][0]["source_path"] = ".flowguard/behavior/inventory/ledger.json"
    payload["behaviors"][0]["source_ref"] = (
        ".flowguard/behavior/inventory/ledger.json#commitment"
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BehaviorDiscoveryError, match="may not use tests|canonical BCL"):
        load_discovery_manifest(manifest, root=ROOT)


def test_native_manifest_rejects_unlisted_explicit_behavior(tmp_path):
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["expected_behavior_ids"][0] = "flowguard.unlisted.behavior"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BehaviorDiscoveryError, match="must equal"):
        load_discovery_manifest(manifest, root=ROOT)


def test_native_manifest_cli_serializes_invalid_item_as_blocked(tmp_path):
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["behaviors"][0]["disposition"] = "delegated"
    manifest = tmp_path / "manifest.json"
    output = tmp_path / "evidence.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    assert discover_main(
        ["--root", str(ROOT), "--manifest", str(manifest), "--output", str(output)]
    ) == 1
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["status"] == "blocked"
    assert result["findings"][0]["code"] == "behavior_discovery_manifest_invalid"


def test_native_manifest_missing_current_intent_fields_is_blocked(tmp_path):
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["behaviors"][0].pop("current_intent_fingerprint")
    payload["behaviors"][0].pop("lifecycle_envelope")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    result = load_discovery_manifest(manifest, root=ROOT)
    assert result["status"] == "blocked"
    codes = {finding["code"] for finding in result["review"]["findings"]}
    assert "behavior_inventory_current_intent_identity_missing" in codes
    assert "behavior_inventory_lifecycle_envelope_incomplete" in codes
