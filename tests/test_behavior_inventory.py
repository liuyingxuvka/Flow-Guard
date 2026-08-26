import unittest

from flowguard import (
    BCL_BEHAVIOR_DISPOSITION_BLOCKED,
    BCL_BEHAVIOR_DISPOSITION_DELEGATED,
    BCL_BEHAVIOR_DISPOSITION_SCOPED,
    BCL_BEHAVIOR_DISPOSITION_MODELED,
    BehaviorCommitment,
    BehaviorCommitmentLedger,
    BehaviorInventory,
    BehaviorInventoryItem,
    behavior_commitment_ledger_fingerprint,
    behavior_commitment_ledger_from_mapping,
    review_behavior_commitment_ledger,
    review_independent_behavior_inventory,
)
from flowguard.behavior_commitment import BCL_LIFECYCLE_LANES


def lifecycle_envelope():
    return {
        lane: {
            "status": "required_and_covered",
            "test_refs": [f"test:{lane}"],
            "oracle_id": f"oracle:{lane}",
        }
        for lane in BCL_LIFECYCLE_LANES
    }


def inventory_item(**overrides):
    values = {
        "behavior_id": "behavior:submit",
        "source_kind": "api",
        "source_ref": "docs/api.md#submit",
        "source_fingerprint": "sha256:source-submit",
        "public_surface": "POST /submit",
        "intent": "accept a submit request",
        "intent_source_refs": ("spec:submit",),
        "intent_disposition": "accepted_current",
        "function_id": "function:submit",
        "route_id": "route:submit",
        "obligation_ids": ("obligation:submit",),
        "required_check_ids": ("check:submit",),
        "test_refs": ("tests/test_submit.py::test_valid",),
        "evidence_subject_ids": ("subject:submit",),
        "oracle_ids": ("oracle:submit",),
        "failure_case_ids": ("failure:submit-invalid",),
        "recovery_case_ids": ("recovery:submit-retry",),
        "current_intent_fingerprint": "sha256:intent-submit",
        "lifecycle_envelope": lifecycle_envelope(),
        "success": "request is accepted and queued",
        "errors": ("invalid request is rejected", "permission failure is visible"),
        "recovery": ("correct the request and retry", "grant permission and retry"),
        "owner": "owner:submit",
        "disposition": BCL_BEHAVIOR_DISPOSITION_MODELED,
        "commitment_id": "commitment:submit",
        "model_owner_id": "model:submit",
    }
    values.update(overrides)
    return BehaviorInventoryItem(**values)


def inventory(**overrides):
    values = {
        "inventory_id": "inventory:public-behavior",
        "project_boundary": "public API behavior",
        "current_revision": "discovery-rev-1",
        "discovery_owner": "api-surface-discovery",
        "discovery_fingerprint": "sha256:discovery-rev-1",
        "discovery_evidence_ids": ("evidence:api-discovery-rev-1",),
        "expected_behavior_ids": ("behavior:submit",),
        "items": (inventory_item(),),
        "claim_boundary": "discovered public API behavior only",
    }
    values.update(overrides)
    return BehaviorInventory(**values)


class IndependentBehaviorInventoryTests(unittest.TestCase):
    def test_valid_inventory_preserves_independent_identity_and_round_trips_through_bcl(
        self,
    ):
        candidate = BehaviorCommitmentLedger(
            ledger_id="ledger:current",
            commitments=(BehaviorCommitment(commitment_id="commitment:submit"),),
            independent_behavior_inventory=inventory(),
        )

        report = review_independent_behavior_inventory(
            candidate.independent_behavior_inventory,
            ledger=candidate,
        )

        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(("behavior:submit",), report.actual_behavior_ids)
        self.assertNotEqual(
            report.inventory_fingerprint,
            behavior_commitment_ledger_fingerprint(candidate),
        )

        loaded = behavior_commitment_ledger_from_mapping(candidate.to_dict())
        self.assertEqual(
            report.inventory_fingerprint,
            loaded.independent_behavior_inventory.fingerprint,
        )
        self.assertEqual(
            "POST /submit",
            loaded.independent_behavior_inventory.items[0].public_surface,
        )

    def test_conservation_blocks_missing_unexpected_and_duplicate_ids(self):
        missing_and_unexpected = inventory(
            items=(inventory_item(behavior_id="behavior:other"),),
        )
        report = review_independent_behavior_inventory(missing_and_unexpected)
        codes = {finding.code for finding in report.findings}
        self.assertFalse(report.ok)
        self.assertEqual(("behavior:submit",), report.missing_behavior_ids)
        self.assertEqual(("behavior:other",), report.unexpected_behavior_ids)
        self.assertIn("behavior_inventory_expected_item_missing", codes)
        self.assertIn("behavior_inventory_unexpected_item", codes)

        duplicate_expected = review_independent_behavior_inventory(
            inventory(expected_behavior_ids=("behavior:submit", "behavior:submit"))
        )
        self.assertIn(
            "behavior_inventory_expected_duplicate_id",
            {finding.code for finding in duplicate_expected.findings},
        )

        duplicate_actual = review_independent_behavior_inventory(
            inventory(
                expected_behavior_ids=("behavior:submit",),
                items=(inventory_item(), inventory_item()),
            )
        )
        self.assertIn(
            "behavior_inventory_duplicate_id",
            {finding.code for finding in duplicate_actual.findings},
        )

    def test_each_disposition_requires_its_native_handoff_fields(self):
        delegated = review_independent_behavior_inventory(
            inventory(
                items=(
                    inventory_item(
                        disposition=BCL_BEHAVIOR_DISPOSITION_DELEGATED,
                        commitment_id="",
                        model_owner_id="",
                    ),
                ),
            )
        )
        self.assertIn(
            "behavior_inventory_delegated_owner_incomplete",
            {finding.code for finding in delegated.findings},
        )
        delegated_complete = review_independent_behavior_inventory(
            inventory(
                items=(
                    inventory_item(
                        disposition=BCL_BEHAVIOR_DISPOSITION_DELEGATED,
                        commitment_id="",
                        model_owner_id="",
                        delegated_owner_inventory_id="inventory:ui-owner",
                        delegation_relation_type="owns-ui-behavior",
                    ),
                ),
            )
        )
        self.assertTrue(delegated_complete.ok, delegated_complete.to_dict())

        scoped = review_independent_behavior_inventory(
            inventory(
                items=(
                    inventory_item(
                        disposition=BCL_BEHAVIOR_DISPOSITION_SCOPED,
                        commitment_id="",
                        model_owner_id="",
                    ),
                ),
            )
        )
        self.assertIn(
            "behavior_inventory_out_of_scope_disposition_incomplete",
            {finding.code for finding in scoped.findings},
        )
        scoped_complete = review_independent_behavior_inventory(
            inventory(
                items=(
                    inventory_item(
                        disposition=BCL_BEHAVIOR_DISPOSITION_SCOPED,
                        commitment_id="",
                        model_owner_id="",
                        scoped_out_reason="outside this bounded project surface",
                        validation_boundary="specialist owner validates the external contract",
                        rationale="the native owner remains accountable for this item",
                    ),
                ),
            )
        )
        self.assertTrue(scoped_complete.ok, scoped_complete.to_dict())

    def test_inventory_discovery_identity_cannot_reuse_bcl_identity(self):
        candidate = BehaviorCommitmentLedger(
            ledger_id="ledger:current",
            commitments=(BehaviorCommitment(commitment_id="commitment:submit"),),
        )
        report = review_independent_behavior_inventory(
            inventory(
                discovery_fingerprint=(
                    "sha256:" + behavior_commitment_ledger_fingerprint(candidate)
                )
            ),
            ledger=candidate,
        )
        self.assertIn(
            "behavior_inventory_discovery_not_independent",
            {finding.code for finding in report.findings},
        )

    def test_blocked_gap_is_a_first_class_failing_disposition(self):
        blocked = review_independent_behavior_inventory(
            inventory(
                items=(
                    inventory_item(
                        disposition=BCL_BEHAVIOR_DISPOSITION_BLOCKED,
                        commitment_id="",
                        model_owner_id="",
                    ),
                ),
            )
        )
        self.assertFalse(blocked.ok)
        self.assertIn(
            "behavior_inventory_blocked_gap_incomplete",
            {finding.code for finding in blocked.findings},
        )

        resolved = review_independent_behavior_inventory(
            inventory(
                items=(
                    inventory_item(
                        disposition=BCL_BEHAVIOR_DISPOSITION_BLOCKED,
                        commitment_id="",
                        model_owner_id="",
                        blocked_gap_reason="native owner has not yet supplied an implementation contract",
                        validation_boundary="public API behavior remains unclaimed until owner handoff",
                        rationale="preserve the discovered denominator without silently treating the gap as out of scope",
                    ),
                ),
            )
        )
        self.assertFalse(resolved.ok)
        self.assertIn(
            "behavior_inventory_blocked_gap",
            {finding.code for finding in resolved.findings},
        )

    def test_legacy_bcl_surface_dispositions_are_not_inventory_values(self):
        for legacy in ("delegated", "scoped"):
            with self.subTest(legacy=legacy):
                with self.assertRaises(ValueError):
                    inventory_item(disposition=legacy)

    def test_current_inventory_blocks_missing_semantic_links_and_lifecycle_lane(self):
        candidate = inventory(
            items=(
                inventory_item(
                    obligation_ids=(),
                    required_check_ids=(),
                    test_refs=(),
                    evidence_subject_ids=(),
                    oracle_ids=(),
                    failure_case_ids=(),
                    recovery_case_ids=(),
                    lifecycle_envelope={"happy_path": {"status": "required_and_covered"}},
                ),
            )
        )
        report = review_independent_behavior_inventory(candidate)
        codes = {finding.code for finding in report.findings}
        self.assertFalse(report.ok)
        self.assertIn("behavior_inventory_required_link_missing", codes)
        self.assertIn("behavior_inventory_lifecycle_envelope_incomplete", codes)

    def test_old_independent_inventory_schema_is_rejected_without_a_reader(self):
        candidate = inventory().to_dict()
        candidate["schema_version"] = "flowguard.independent-behavior-inventory.v1"
        with self.assertRaisesRegex(ValueError, "unsupported behavior inventory schema_version"):
            review_independent_behavior_inventory(candidate)

    def test_current_inventory_fingerprint_is_deterministic(self):
        first = inventory().fingerprint
        second = inventory(
            items=(inventory_item(),),
            metadata={"same": "value"},
        ).fingerprint
        self.assertNotEqual(first, second)
        self.assertEqual(first, inventory().fingerprint)

    def test_bcl_can_opt_in_to_blocking_when_denominator_is_absent(self):
        report = review_behavior_commitment_ledger(
            BehaviorCommitmentLedger(
                ledger_id="ledger:requires-inventory",
                require_complete_behavior_inventory=True,
            )
        )
        self.assertFalse(report.ok)
        self.assertIn(
            "independent_behavior_inventory_missing",
            {finding.code for finding in report.findings},
        )


if __name__ == "__main__":
    unittest.main()
