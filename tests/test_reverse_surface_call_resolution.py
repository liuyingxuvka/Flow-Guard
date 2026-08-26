from __future__ import annotations

import json
import copy

from flowguard.behavior_surface_audit import (
    audit_implementation_behavior_surface,
    discover_implementation_behavior_surfaces,
    discover_implementation_surface_shard,
    merge_implementation_surface_shards,
    plan_implementation_surface_shards,
)


def test_unqualified_call_prefers_the_only_same_source_definition(tmp_path):
    (tmp_path / "caller.py").write_text(
        "def shared(value):\n"
        "    return value\n\n"
        "def caller(value):\n"
        "    return shared(value)\n",
        encoding="utf-8",
    )
    # These definitions share a leaf name with the caller-local helper.  They
    # must not make the local call ambiguous: source-only resolution can bind
    # it to the one definition in caller.py without importing either module.
    (tmp_path / "left.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "right.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)

    assert discovery["findings"] == []
    caller = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function" and row["symbol"].endswith("caller")
    )
    caller_edges = [
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == caller["surface_id"]
        and edge["callee_name"] == "shared"
    ]
    assert len(caller_edges) == 1
    assert caller_edges[0]["resolution"] == "resolved"
    target = next(
        row
        for row in discovery["surfaces"]
        if row["surface_id"] == caller_edges[0]["resolved_surface_ids"][0]
    )
    assert target["source_path"] == "caller.py"


def test_multiple_same_source_definitions_form_an_exact_dispatch_set(tmp_path):
    (tmp_path / "app.py").write_text(
        "def shared(value):\n"
        "    return value\n\n"
        "def shared(value):\n"
        "    return value + 1\n\n"
        "class Box:\n"
        "    def shared(self, value):\n"
        "        return value\n\n"
        "def caller(value):\n"
        "    return shared(value)\n",
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)

    assert discovery["status"] == "passed"
    assert discovery["findings"] == []
    caller = next(
        row for row in discovery["surfaces"]
        if row["surface_kind"] == "function" and row["symbol"].endswith("caller")
    )
    edge = next(
        edge for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == caller["surface_id"]
        and edge["callee_name"] == "shared"
    )
    assert edge["resolution"] == "resolved_static_dispatch"
    assert len(edge["resolved_surface_ids"]) == 2
    assert edge["dispatch_kind"] == "source_candidate_set"


def test_enclosing_surfaces_do_not_inherit_nested_definition_calls(tmp_path):
    (tmp_path / "app.py").write_text(
        "def helper(value):\n"
        "    return value\n\n"
        "def outer(value):\n"
        "    def nested(inner):\n"
        "        return helper(inner)\n"
        "    return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    rows = {row["surface_id"]: row for row in discovery["surfaces"]}
    helper_edges = [
        edge
        for edge in discovery["call_graph"]
        if edge["callee_name"] == "helper"
    ]

    assert len(helper_edges) == 1
    assert rows[helper_edges[0]["caller_surface_id"]]["symbol"].endswith("nested")


def test_relative_import_alias_resolves_only_to_the_imported_local_symbol(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )
    (package / "app.py").write_text(
        "from .helpers import shared\n\n"
        "def caller(value):\n"
        "    return shared(value)\n",
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)

    assert discovery["findings"] == []
    caller = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function" and row["symbol"].endswith("app.caller")
    )
    edge = next(
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == caller["surface_id"]
        and edge["callee_name"] == "shared"
    )
    assert edge["resolution"] == "resolved"
    target = next(
        row
        for row in discovery["surfaces"]
        if row["surface_id"] == edge["resolved_surface_ids"][0]
    )
    assert target["source_path"] == "pkg/helpers.py"


def test_function_local_import_does_not_bind_a_different_function(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text(
        "def local_only(value):\n"
        "    from pkg.helpers import shared\n"
        "    return shared(value)\n\n"
        "def caller(value):\n"
        "    return shared(value)\n",
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    caller = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function" and row["symbol"].endswith("caller")
    )
    caller_edges = [
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == caller["surface_id"]
        and edge["callee_name"] == "shared"
    ]

    assert len(caller_edges) == 1
    assert caller_edges[0]["resolution"] == "resolved_static_dispatch"
    assert len(caller_edges[0]["resolved_surface_ids"]) == 2


def test_function_local_exact_import_resolves_only_inside_its_lexical_scope(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text(
        "def local_only(value):\n"
        "    from pkg.helpers import shared\n"
        "    return shared(value)\n\n"
        "def caller(value):\n"
        "    return shared(value)\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    local_only = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function"
        and row["symbol"].endswith("local_only")
    )
    caller = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function"
        and row["symbol"].endswith("caller")
    )
    local_edge = next(
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == local_only["surface_id"]
        and edge["callee_name"] == "shared"
    )
    caller_edge = next(
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == caller["surface_id"]
        and edge["callee_name"] == "shared"
    )

    target = next(
        row
        for row in discovery["surfaces"]
        if row["surface_id"] == local_edge["resolved_surface_ids"][0]
    )
    assert local_edge["resolution"] == "resolved"
    assert target["symbol"].endswith("pkg.helpers.shared")
    assert caller_edge["resolution"] == "resolved_static_dispatch"
    assert len(caller_edge["resolved_surface_ids"]) == 2
    assert caller_edge["resolved_surface_ids"] == sorted(caller_edge["resolved_surface_ids"])


def test_unimported_cross_file_name_is_never_resolved_by_a_single_leaf_candidate(
    tmp_path,
):
    (tmp_path / "app.py").write_text(
        "def caller(value):\n    return shared(value)\n",
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    caller = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function" and row["symbol"].endswith("caller")
    )
    edge = next(
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == caller["surface_id"]
    )

    assert edge["resolution"] == "resolved_external_contract"
    assert edge["resolved_surface_ids"] == []
    assert edge["external_contract_id"].startswith("contract:external_unbound_call:")


def test_unimported_qualified_module_member_is_never_resolved_by_suffix(
    tmp_path,
):
    (tmp_path / "app.py").write_text(
        "def caller(value):\n    return other.shared(value)\n",
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    edge = next(
        edge
        for edge in discovery["call_graph"]
        if edge["callee_name"] == "other.shared"
    )

    assert edge["resolution"] == "resolved_external_contract"
    assert edge["resolved_surface_ids"] == []
    assert edge["external_contract_id"].startswith("contract:external_unbound_call:")


def test_plain_dotted_import_resolves_the_longest_exact_module_prefix(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "helpers.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "app.py").write_text(
        "import pkg.helpers\n\n"
        "def caller(value):\n"
        "    return pkg.helpers.shared(value)\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    edge = next(
        edge
        for edge in discovery["call_graph"]
        if edge["callee_name"] == "pkg.helpers.shared"
    )
    target = next(
        row
        for row in discovery["surfaces"]
        if row["surface_id"] == edge["resolved_surface_ids"][0]
    )

    assert edge["resolution"] == "resolved"
    assert target["symbol"] == "pkg.helpers.shared"


def test_same_name_class_method_does_not_ambiguous_module_global_call(tmp_path):
    (tmp_path / "app.py").write_text(
        "def shared(value):\n"
        "    return value\n\n"
        "class Box:\n"
        "    def shared(self, value):\n"
        "        return value\n\n"
        "def caller(value):\n"
        "    return shared(value)\n",
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    caller = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function" and row["symbol"].endswith("caller")
    )
    edge = next(
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == caller["surface_id"]
        and edge["callee_name"] == "shared"
    )
    target = next(
        row
        for row in discovery["surfaces"]
        if row["surface_id"] == edge["resolved_surface_ids"][0]
    )

    assert edge["resolution"] == "resolved"
    assert target["symbol"] == "app.shared"


def test_lexical_self_recursion_wins_over_same_name_method(tmp_path):
    (tmp_path / "app.py").write_text(
        "def loop(value):\n"
        "    if value:\n"
        "        return loop(value - 1)\n"
        "    return value\n\n"
        "class Box:\n"
        "    def loop(self, value):\n"
        "        return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    loop = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function" and row["symbol"] == "app.loop"
    )
    edge = next(
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == loop["surface_id"]
    )

    assert edge["resolution"] == "resolved"
    assert edge["resolved_surface_ids"] == [loop["surface_id"]]
    assert not any(
        row["surface_kind"] == "unreachable_or_unbound"
        and row["observed"].get("original_surface_id") == loop["surface_id"]
        for row in discovery["surfaces"]
    )


def test_method_self_recursion_is_not_reported_as_unbound(tmp_path):
    (tmp_path / "app.py").write_text(
        "class Node:\n"
        "    def visit(self, value):\n"
        "        if value:\n"
        "            return self.visit(value - 1)\n"
        "        return value\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    visit = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function" and row["symbol"] == "app.Node.visit"
    )
    edge = next(
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == visit["surface_id"]
    )

    assert edge["resolution"] == "resolved"
    assert edge["resolved_surface_ids"] == [visit["surface_id"]]
    assert not any(
        row["surface_kind"] == "unreachable_or_unbound"
        and row["observed"].get("original_surface_id") == visit["surface_id"]
        for row in discovery["surfaces"]
    )


def test_dynamic_receiver_and_callback_close_to_stable_boundary_targets(tmp_path):
    (tmp_path / "app.py").write_text(
        "def callback(value):\n"
        "    return value\n\n"
        "def invoke(callback, receiver, value):\n"
        "    first = callback(value)\n"
        "    second = receiver.run(value)\n"
        "    third = getattr(receiver, 'run')(value)\n"
        "    fourth = {'run': callback}[value](value)\n"
        "    return first, second, third, fourth\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    invoke = next(
        row
        for row in discovery["surfaces"]
        if row["surface_kind"] == "function" and row["symbol"] == "app.invoke"
    )
    edges = [
        edge
        for edge in discovery["call_graph"]
        if edge["caller_surface_id"] == invoke["surface_id"]
    ]
    by_name = {edge["callee_name"]: edge for edge in edges}

    assert by_name["callback"]["resolution"] == "resolved_external_contract"
    assert by_name["callback"]["resolved_surface_ids"] == []
    assert by_name["callback"]["boundary_kind"] == "dynamic_callback"
    assert by_name["receiver.run"]["resolution"] == "resolved_external_contract"
    assert by_name["receiver.run"]["resolved_surface_ids"] == []
    assert by_name["receiver.run"]["boundary_kind"] == "dynamic_receiver"
    assert by_name["callback"]["external_contract_id"] != by_name["receiver.run"]["external_contract_id"]
    expression_edges = [
        edge for edge in edges if edge["callee_name"] == "<dynamic>"
    ]
    # The source-only call facts intentionally deduplicate identical dynamic
    # call-name shapes; the edge still closes the complete observed shape to a
    # deterministic current boundary identity.
    assert len(expression_edges) == 1
    assert all(edge["resolution"] == "resolved_external_contract" for edge in expression_edges)
    assert all(edge["boundary_kind"] == "dynamic_expression" for edge in expression_edges)
    assert expression_edges[0]["external_contract_id"].startswith(
        "contract:dynamic_expression:"
    )
    assert discovery["findings"] == []

    plan = plan_implementation_surface_shards(tmp_path, max_rows=100)
    shards = [
        discover_implementation_surface_shard(tmp_path, plan, row["shard_id"])
        for row in plan["shards"]
    ]
    merged = merge_implementation_surface_shards(tmp_path, plan, shards)
    assert merged["status"] == "passed"
    assert merged["findings"] == []
    assert merged["call_graph"] == discovery["call_graph"]
    assert all(
        edge["resolution"]
        in {
            "resolved",
            "resolved_static_dispatch",
            "resolved_external_contract",
        }
        for edge in merged["call_graph"]
    )
    assert not any(
        "ambiguous" in str(edge.get("resolution", ""))
        or "unknown" in str(edge.get("resolution", ""))
        for edge in merged["call_graph"]
    )


def test_external_contract_registry_is_exactly_conserved_for_dynamic_edges(tmp_path):
    (tmp_path / "app.py").write_text(
        "def invoke(callback, receiver, value):\n"
        "    return callback(value), receiver.run(value)\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    edges = [
        edge
        for edge in discovery["call_graph"]
        if edge["resolution"] == "resolved_external_contract"
    ]
    registry_by_id = {
        row["contract_id"]: row for row in discovery["external_contracts"]
    }

    assert edges
    assert len(registry_by_id) == len(discovery["external_contracts"])
    assert {edge["external_contract_id"] for edge in edges} == set(registry_by_id)
    for edge in edges:
        contract = registry_by_id[edge["external_contract_id"]]
        assert contract["boundary_kind"] == edge["boundary_kind"]
        assert contract["callee_name"] == edge["callee_name"]
        assert contract["caller_surface_id"] == edge["caller_surface_id"]
        assert edge["resolved_surface_ids"] == []
        assert edge["target_kind"] == "external_contract"
        assert edge["target_identity"] == edge["external_contract_id"]
        assert edge["target_status"] == "current_resolved"
        assert edge["target_proof"] == "external_contract_registry"
        assert contract["target_kind"] == "external_contract"
        assert contract["target_identity"] == contract["contract_id"]
        assert contract["target_status"] == "current_resolved"
        assert contract["target_proof"] == "external_contract_registry"

    plan = plan_implementation_surface_shards(tmp_path, max_rows=10)
    shards = [
        discover_implementation_surface_shard(tmp_path, plan, row["shard_id"])
        for row in plan["shards"]
    ]
    merged = merge_implementation_surface_shards(tmp_path, plan, shards)
    assert merged["status"] == "passed"
    assert merged["external_contracts"] == discovery["external_contracts"]
    assert merged["call_graph"] == discovery["call_graph"]


def test_external_contract_target_cannot_be_downgraded_to_typed_observation(
    tmp_path,
):
    (tmp_path / "app.py").write_text(
        "def invoke(callback, value):\n"
        "    return callback(value)\n",
        encoding="utf-8",
    )

    discovery = discover_implementation_behavior_surfaces(tmp_path)
    mutated = copy.deepcopy(discovery)
    edge = next(
        edge
        for edge in mutated["call_graph"]
        if edge["resolution"] == "resolved_external_contract"
    )
    edge["target_status"] = "typed_current_observation"

    audit = audit_implementation_behavior_surface(
        tmp_path,
        None,
        discovery=mutated,
    )

    assert audit["status"] == "blocked"
    assert any(
        finding["code"]
        == "implementation_surface_discovery_call_graph_external_target_invalid"
        for finding in audit["discovery_observation_findings"]
    )


def test_same_source_and_sha_produces_identical_discovery_bytes(tmp_path):
    (tmp_path / "app.py").write_text(
        "def shared(value):\n"
        "    return value\n\n"
        "def caller(value):\n"
        "    return shared(value)\n",
        encoding="utf-8",
    )

    first = discover_implementation_behavior_surfaces(tmp_path)
    second = discover_implementation_behavior_surfaces(tmp_path)
    first_bytes = json.dumps(first, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    second_bytes = json.dumps(second, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )

    assert first["discovery_fingerprint"] == second["discovery_fingerprint"]
    assert first_bytes == second_bytes


def test_merged_shards_conserve_class_body_call_graph_edges(tmp_path):
    (tmp_path / "app.py").write_text(
        "class Box:\n"
        "    value = helper()\n"
        "    def helper(self):\n"
        "        return 1\n\n"
        "def helper():\n"
        "    return 2\n",
        encoding="utf-8",
    )

    full = discover_implementation_behavior_surfaces(tmp_path)
    plan = plan_implementation_surface_shards(tmp_path, max_rows=100)
    shards = [
        discover_implementation_surface_shard(tmp_path, plan, row["shard_id"])
        for row in plan["shards"]
    ]
    merged = merge_implementation_surface_shards(tmp_path, plan, shards)

    def edge_shape(discovery):
        return sorted(
            (
                edge["caller_surface_id"],
                edge["callee_name"],
                edge["resolution"],
                tuple(edge["resolved_surface_ids"]),
            )
            for edge in discovery["call_graph"]
        )

    assert edge_shape(full) == edge_shape(merged)


def test_merged_shards_conserve_module_body_call_graph_edges(tmp_path):
    """Top-level module calls must survive shard merge as graph observations."""

    (tmp_path / "app.py").write_text(
        "value = helper()\n\n"
        "def helper():\n"
        "    return 2\n",
        encoding="utf-8",
    )

    full = discover_implementation_behavior_surfaces(tmp_path)
    plan = plan_implementation_surface_shards(tmp_path, max_rows=100)
    shards = [
        discover_implementation_surface_shard(tmp_path, plan, row["shard_id"])
        for row in plan["shards"]
    ]
    merged = merge_implementation_surface_shards(tmp_path, plan, shards)

    def edge_shape(discovery):
        return sorted(
            (
                edge["caller_surface_id"],
                edge["callee_name"],
                edge["resolution"],
                tuple(edge["resolved_surface_ids"]),
            )
            for edge in discovery["call_graph"]
        )

    assert edge_shape(full) == edge_shape(merged)
    assert any(
        row["surface_kind"] == "module"
        and row["surface_id"] == edge["caller_surface_id"]
        for edge in merged["call_graph"]
        for row in merged["surfaces"]
    )


def test_merged_shards_conserve_collision_safe_duplicate_unbound_rows_and_sites(
    tmp_path,
):
    """A repeated nested symbol must retain each child row and call-site anchor."""

    (tmp_path / "app.py").write_text(
        "class GraphEdge:\n"
        "    pass\n\n"
        "def outer(flag):\n"
        "    if flag:\n"
        "        def transition(value):\n"
        "            return GraphEdge(value)\n"
        "    else:\n"
        "        def transition(value):\n"
        "            return GraphEdge(value)\n"
        "    return 1\n",
        encoding="utf-8",
    )

    full = discover_implementation_behavior_surfaces(tmp_path)
    plan = plan_implementation_surface_shards(tmp_path, max_rows=100)
    shards = [
        discover_implementation_surface_shard(tmp_path, plan, row["shard_id"])
        for row in plan["shards"]
    ]
    merged = merge_implementation_surface_shards(tmp_path, plan, shards)

    assert full["status"] == "passed"
    assert merged["status"] == "passed"
    assert full["findings"] == []
    assert merged["findings"] == []
    assert full["surfaces"] == merged["surfaces"]

    def edge_shape(discovery):
        return sorted(
            (
                edge["caller_surface_id"],
                edge["caller_source_ref"],
                edge["callee_name"],
                edge["resolution"],
                tuple(edge["resolved_surface_ids"]),
            )
            for edge in discovery["call_graph"]
        )

    assert edge_shape(full) == edge_shape(merged)
    unbound_rows = [
        row
        for row in merged["surfaces"]
        if row["surface_kind"] == "unreachable_or_unbound"
    ]
    assert len(unbound_rows) == 3
    assert len({row["observed"]["original_surface_id"] for row in unbound_rows}) == 3


def test_merged_shards_close_dispatch_call_graph_without_unresolved_targets(
    tmp_path,
):
    """Finite source candidate sets close as exact dispatch edges."""

    (tmp_path / "caller.py").write_text(
        "def caller(value):\n    return shared(value)\n",
        encoding="utf-8",
    )
    (tmp_path / "left.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )
    (tmp_path / "right.py").write_text(
        "def shared(value):\n    return value\n",
        encoding="utf-8",
    )

    plan = plan_implementation_surface_shards(tmp_path, max_rows=10)
    shards = [
        discover_implementation_surface_shard(tmp_path, plan, row["shard_id"])
        for row in plan["shards"]
    ]
    merged = merge_implementation_surface_shards(tmp_path, plan, shards)

    assert merged["status"] == "passed"
    assert merged["call_graph"]
    assert not merged["findings"]
    edge = next(edge for edge in merged["call_graph"] if edge["callee_name"] == "shared")
    assert edge["resolution"] == "resolved_static_dispatch"
    assert len(edge["resolved_surface_ids"]) == 2
