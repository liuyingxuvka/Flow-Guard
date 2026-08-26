from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO

from scripts import check_flowguard_skill_suite as suite


def test_affected_terminal_projection_keeps_affected_scope() -> None:
    payload = {
        "scope": "affected",
        "status": "pass",
        "ok": True,
        "passed_members": 1,
        "total_members": 1,
        "members": [],
        "blockers": [],
        "skipped_checks": [],
        "claim_boundary": "affected only",
    }
    output = StringIO()
    with redirect_stdout(output):
        suite._print_light(payload, as_json=True)
    terminal = json.loads(output.getvalue())
    assert terminal["scope"] == "affected"
    assert terminal["claim_boundary"] == "affected only"


def test_light_terminal_projection_keeps_light_scope() -> None:
    payload = {
        "scope": "light",
        "status": "pass",
        "ok": True,
        "passed_members": 1,
        "total_members": 1,
        "members": [],
        "blockers": [],
        "skipped_checks": [],
        "claim_boundary": "light only",
    }
    output = StringIO()
    with redirect_stdout(output):
        suite._print_light(payload, as_json=True)
    terminal = json.loads(output.getvalue())
    assert terminal["scope"] == "light"
