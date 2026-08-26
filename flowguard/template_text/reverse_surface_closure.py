"""Public target scaffold for reverse implementation-surface authoring."""

from __future__ import annotations

REVERSE_SURFACE_CLOSURE_MODEL_TEMPLATE = '''"""FlowGuard Risk Purpose Header

Created with FlowGuard: https://github.com/liuyingxuvka/FlowGuard
Purpose: Author the exact implementation-to-model and model-to-implementation reverse closure.
Guards against: unmapped surfaces, orphan obligations, one-way joins, unmodeled UI actions, and unresolved dynamic completion.
Use before editing: Update this reverse authoring scaffold when implementation discovery or model obligations change.
Run: python .flowguard/verification/owners/reverse_surface_closure/run_checks.py
"""

from __future__ import annotations

from flowguard.reverse_surface_authoring import REVERSE_SURFACE_AUTHORING_CONTEXT_SCHEMA


REQUIRED_AUTHOR_FIELDS = (
    "implementation_denominator",
    "component_groups",
    "model_obligation_denominator",
    "implementation_to_model_join",
    "model_to_implementation_join",
    "owner_test_receipt_authority_join",
    "ui_like_action_join",
    "finite_dynamic_dispatch_or_external_boundary",
)


def authoring_contract() -> dict[str, object]:
    return {
        "schema_version": REVERSE_SURFACE_AUTHORING_CONTEXT_SCHEMA,
        "required_fields": list(REQUIRED_AUTHOR_FIELDS),
        "disposition": "authoring_required",
        "discovery_observations": "typed unresolved observations may block graduation",
        "completion_zeroes": [
            "blocked_gap", "unmapped", "orphan", "one_way",
            "unmodeled_ui_like_action", "dynamic", "ambiguous", "unknown",
        ],
    }


def run_checks() -> tuple[bool, bool]:
    contract = authoring_contract()
    good = all(field in contract["required_fields"] for field in REQUIRED_AUTHOR_FIELDS)
    broken = len(contract["required_fields"]) < len(REQUIRED_AUTHOR_FIELDS)
    return good, broken
'''

REVERSE_SURFACE_CLOSURE_RUN_CHECKS_TEMPLATE = '''"""Run reverse-surface authoring scaffold checks."""

from model import run_checks


def main() -> int:
    good, broken = run_checks()
    print("reverse-surface authoring contract: " + ("PASS" if good else "BLOCKED"))
    print("reverse-surface incomplete fixture: " + ("BLOCKED" if not broken else "UNEXPECTED_PASS"))
    return 0 if good and not broken else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

REVERSE_SURFACE_CLOSURE_NOTES_TEMPLATE = """# FlowGuard Reverse Surface Closure Notes

Use the existing discovery, shard, merge, authoring-context, semantic-map,
owner-authority, and audit APIs.  This scaffold does not invent intent from
names.  The target author must provide an independent implementation
denominator, exact component groups, target-owned model-obligation denominator,
both join directions, owner/test/receipt/authority joins, UI-like action joins,
and either a finite dynamic dispatch map or a deterministic external boundary.

Discovery may show typed unresolved observations.  Graduation/current
authority cannot: blocked_gap, unmapped, orphan, one-way, unmodeled UI-like,
dynamic, ambiguous, and unknown completion findings must all be zero.
"""

__all__ = [
    "REVERSE_SURFACE_CLOSURE_MODEL_TEMPLATE",
    "REVERSE_SURFACE_CLOSURE_RUN_CHECKS_TEMPLATE",
    "REVERSE_SURFACE_CLOSURE_NOTES_TEMPLATE",
]
