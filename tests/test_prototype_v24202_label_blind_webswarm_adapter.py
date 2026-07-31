from __future__ import annotations

import unittest

from scripts.prototype_v24202_label_blind_webswarm_adapter import (
    DelegationLimits,
    EvidenceRecord,
    RootScope,
    build_planner_context,
    classify_web_topology,
    compile_label_blind_payload,
    infer_visible_mode,
    validate_child_envelope,
)


def payload(
    question: str,
    *,
    columns: list[str] | None = None,
    rows: list[str] | None = None,
    evidence: list[dict] | None = None,
    proposals: list[dict] | None = None,
) -> dict:
    visible_input = {
            "visible_question": question,
            "output_columns": columns or [],
            "visible_known_rows": rows or [],
    }
    evidence_values = evidence or []
    context = build_planner_context(
        RootScope.from_mapping(visible_input),
        [EvidenceRecord.from_mapping(item) for item in evidence_values],
    )
    proposal_values = proposals or [
        {"objective": question, "mode": None, "evidence_ids": []}
    ]
    proposal_values = [
        {
            **item,
            "planner_context_sha256": item.get(
                "planner_context_sha256", context.planner_context_sha256
            ),
        }
        for item in proposal_values
    ]
    return {
        "visible_input": visible_input,
        "current_trace": {"evidence": evidence_values},
        "proposals": proposal_values,
    }


def page(
    evidence_id: str,
    source_id: str,
    query_id: str,
    *,
    rows: list[str] | None = None,
    columns: list[str] | None = None,
    contradicted: bool = False,
) -> dict:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "query_id": query_id,
        "row_keys": rows or [],
        "column_keys": columns or [],
        "page_backed": True,
        "contradicted": contradicted,
    }


class LabelBlindWebSwarmAdapterPrototypeTests(unittest.TestCase):
    def test_visible_mode_fallback_covers_four_modes(self) -> None:
        atom = RootScope.build(visible_question="Give the official launch date for Alpha")
        deep = RootScope.build(
            visible_question="Identify the person who was born after 1980 and verify the employer"
        )
        collect = RootScope.build(
            visible_question="List all members in the visible scope as a complete list"
        )
        wide = RootScope.build(
            visible_question="Fill a table for the supplied organizations",
            output_columns=["Name", "Year", "Value"],
            visible_known_rows=["Alpha", "Beta"],
        )
        self.assertEqual(infer_visible_mode(atom, atom.visible_question)[0], "atom")
        self.assertEqual(infer_visible_mode(deep, deep.visible_question)[0], "deep")
        self.assertEqual(
            infer_visible_mode(collect, collect.visible_question)[0], "entity_collect"
        )
        self.assertEqual(infer_visible_mode(wide, wide.visible_question)[0], "wide")

    def test_hidden_anchor_precedes_downstream_table(self) -> None:
        scope = RootScope.build(
            visible_question=(
                "Identify the unknown company that satisfies three constraints, then list all "
                "of its products in a table"
            ),
            output_columns=["Product", "Year", "Value"],
        )
        self.assertEqual(infer_visible_mode(scope, "Resolve the unknown company")[0], "deep")

    def test_topology_is_observed_only_and_does_not_claim_unseen_mass(self) -> None:
        scope = RootScope.build(
            visible_question="Fill the requested table",
            output_columns=["Name", "Year"],
            visible_known_rows=["A", "B"],
        )
        centralized = classify_web_topology(
            scope,
            [
                EvidenceRecord.from_mapping(
                    page(
                        "E0001",
                        "S1",
                        "Q1",
                        rows=["A", "B"],
                        columns=["Name", "Year"],
                    )
                )
            ],
        )
        self.assertEqual(centralized.topology, "centralized")
        self.assertTrue(centralized.observed_coverage_only)
        self.assertFalse(centralized.unseen_mass_estimated)

        distributed = classify_web_topology(
            scope,
            [
                EvidenceRecord.from_mapping(
                    page("E0001", "S1", "Q1", rows=["A"], columns=["Name"])
                ),
                EvidenceRecord.from_mapping(
                    page("E0002", "S2", "Q2", rows=["B"], columns=["Year"])
                ),
            ],
        )
        self.assertEqual(distributed.topology, "distributed")

    def test_contract_preserves_root_scope_and_active_provenance(self) -> None:
        value = compile_label_blind_payload(
            payload(
                "List every visible-scope item, excluding archived entries",
                columns=["Name", "Year"],
                evidence=[page("E0001", "S1", "Q1", columns=["Name"])],
                proposals=[
                    {
                        "objective": "Enumerate current items without changing exclusions",
                        "mode": "entity_collect",
                        "evidence_ids": ["E0001"],
                    }
                ],
            ),
            depth=0,
        )
        contract = value.contracts[0]
        self.assertEqual(contract.root_scope_sha256, value.root_scope_sha256)
        self.assertEqual(contract.inherited_evidence_ids, ("E0001",))
        self.assertIn("excluding archived entries", contract.child_prompt)
        self.assertIn("E0001", contract.child_prompt)
        self.assertTrue(contract.may_delegate)
        self.assertGreater(contract.max_children, 0)

    def test_exact_contract_duplicates_are_removed_but_distinct_objectives_survive(self) -> None:
        proposal = {
            "objective": "Collect the two requested attributes",
            "mode": "wide",
            "evidence_ids": ["E0001"],
        }
        value = compile_label_blind_payload(
            payload(
                "Build a table",
                columns=["Name", "Year"],
                evidence=[page("E0001", "S1", "Q1")],
                proposals=[
                    proposal,
                    dict(proposal),
                    {
                        **proposal,
                        "objective": "Verify the two requested attributes",
                    },
                ],
            ),
            depth=0,
        )
        self.assertEqual(len(value.contracts), 2)
        self.assertEqual(value.exact_contract_duplicates_removed, 1)
        self.assertEqual(value.unique_evidence_set_count, 1)
        self.assertEqual(
            value.contracts[0].evidence_set_key,
            value.contracts[1].evidence_set_key,
        )
        self.assertNotEqual(
            value.contracts[0].contract_equivalence_key,
            value.contracts[1].contract_equivalence_key,
        )

    def test_frozen_ablation_policies_do_not_read_task_labels(self) -> None:
        base = payload(
            "List all visible members and verify each one",
            columns=["Name", "Year", "Value"],
        )
        all_wide = compile_label_blind_payload(base, depth=0, policy="all_to_wide")
        all_deep = compile_label_blind_payload(base, depth=0, policy="all_to_deep")
        no_recursive = compile_label_blind_payload(base, depth=0, policy="no_recursive")
        self.assertEqual(all_wide.contracts[0].mode, "wide")
        self.assertEqual(all_deep.contracts[0].mode, "deep")
        self.assertFalse(no_recursive.contracts[0].may_delegate)
        self.assertEqual(no_recursive.contracts[0].max_children, 0)

    def test_model_proposed_mode_is_accepted_only_through_strict_schema(self) -> None:
        value = compile_label_blind_payload(
            payload(
                "Find the requested fact",
                proposals=[
                    {"objective": "Use two independent paths", "mode": "deep", "evidence_ids": []}
                ],
            ),
            depth=0,
        )
        self.assertEqual(value.contracts[0].mode, "deep")
        self.assertTrue(value.contracts[0].model_mode_accepted)

    def test_stale_or_cross_task_planner_context_is_rejected(self) -> None:
        value = payload("Find the requested fact")
        value["proposals"][0]["planner_context_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not match"):
            compile_label_blind_payload(value, depth=0)

    def test_benchmark_and_label_metadata_are_rejected_recursively(self) -> None:
        for key in (
            "benchmark",
            "subset",
            "category",
            "question_type",
            "ground_truth",
            "gold",
            "evaluator",
            "score",
            "prediction",
            "task_id",
        ):
            value = payload("Find the requested fact")
            value["current_trace"]["evidence"] = [{key: "forbidden"}]
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "privileged metadata"):
                    compile_label_blind_payload(value, depth=0)

    def test_privileged_camel_case_and_nested_keys_are_rejected(self) -> None:
        for key in ("questionType", "benchmarkQuestionType", "groundTruth", "answerKey"):
            value = payload("Find the requested fact")
            value["proposals"][0]["nested"] = {key: "forbidden"}
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "privileged metadata"):
                    compile_label_blind_payload(value, depth=0)

    def test_label_words_in_visible_question_values_remain_allowed(self) -> None:
        value = compile_label_blind_payload(
            payload(
                "List each product category and its official score; do not use a benchmark label"
            ),
            depth=0,
        )
        self.assertEqual(len(value.contracts), 1)

    def test_unknown_nonprivileged_fields_also_fail_closed(self) -> None:
        value = payload("Find the requested fact")
        value["visible_input"]["routing_hint"] = "wide"
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            compile_label_blind_payload(value, depth=0)

    def test_inactive_or_search_answer_only_evidence_is_rejected(self) -> None:
        value = payload(
            "Build a table",
            evidence=[
                {
                    **page("E0001", "S1", "Q1"),
                    "page_backed": False,
                }
            ],
            proposals=[
                {"objective": "Fill rows", "mode": "wide", "evidence_ids": ["E0001"]}
            ],
        )
        with self.assertRaisesRegex(ValueError, "inactive page evidence"):
            compile_label_blind_payload(value, depth=0)

    def test_contradicted_page_cannot_drive_topology_or_child_provenance(self) -> None:
        value = payload(
            "Build a table",
            columns=["Name", "Year"],
            rows=["A", "B"],
            evidence=[
                page(
                    "E0001",
                    "S1",
                    "Q1",
                    rows=["A", "B"],
                    columns=["Name", "Year"],
                    contradicted=True,
                )
            ],
            proposals=[
                {"objective": "Fill rows", "mode": "wide", "evidence_ids": ["E0001"]}
            ],
        )
        with self.assertRaisesRegex(ValueError, "inactive page evidence"):
            compile_label_blind_payload(value, depth=0)

        scope = RootScope.from_mapping(value["visible_input"])
        topology = classify_web_topology(
            scope,
            [EvidenceRecord.from_mapping(value["current_trace"]["evidence"][0])],
        )
        self.assertEqual(topology.topology, "unprobed")
        self.assertEqual(topology.contradicted_page_count, 1)

    def test_depth_and_child_caps_are_enforced(self) -> None:
        value = compile_label_blind_payload(
            payload(
                "Build a table for every supplied item",
                columns=["Name", "Year", "Value"],
                rows=["A", "B"],
            ),
            depth=2,
            limits=DelegationLimits(max_depth=2, max_batch_children=2, max_children_per_node=4),
        )
        self.assertFalse(value.contracts[0].may_delegate)
        self.assertEqual(value.contracts[0].max_children, 0)
        with self.assertRaisesRegex(ValueError, "depth exceeds"):
            compile_label_blind_payload(
                payload("Find a fact"),
                depth=3,
                limits=DelegationLimits(max_depth=2),
            )

    def test_batch_cap_and_duplicate_active_evidence_fail_closed(self) -> None:
        over_cap = payload(
            "Find the requested facts",
            proposals=[
                {"objective": f"Find fact {index}", "mode": "atom", "evidence_ids": []}
                for index in range(3)
            ],
        )
        with self.assertRaisesRegex(ValueError, "batch exceeds"):
            compile_label_blind_payload(
                over_cap,
                depth=0,
                limits=DelegationLimits(max_batch_children=2),
            )

        duplicate = payload(
            "Find the requested fact",
            evidence=[
                page("E0001", "S1", "Q1"),
                page("E0001", "S2", "Q2"),
            ],
        )
        with self.assertRaisesRegex(ValueError, "globally unique"):
            compile_label_blind_payload(duplicate, depth=0)

    def test_child_return_requires_scope_objective_provenance_and_cap(self) -> None:
        batch = compile_label_blind_payload(
            payload(
                "Build a table for the supplied rows",
                columns=["Name", "Year", "Value"],
                rows=["A", "B"],
                evidence=[page("E0001", "S1", "Q1")],
                proposals=[
                    {"objective": "Fill the visible rows", "mode": "wide", "evidence_ids": ["E0001"]}
                ],
            ),
            depth=0,
        )
        contract = batch.contracts[0]
        valid = validate_child_envelope(
            contract,
            {
                "root_scope_sha256": contract.root_scope_sha256,
                "objective_sha256": contract.objective_sha256,
                "evidence_ids": ["E0001", "E0002"],
                "generated_child_count": contract.max_children,
                "status": "completed",
            },
            active_evidence_ids=["E0001", "E0002"],
        )
        self.assertTrue(valid.valid)

        tampered = validate_child_envelope(
            contract,
            {
                "root_scope_sha256": "0" * 64,
                "objective_sha256": contract.objective_sha256,
                "evidence_ids": ["E9999"],
                "generated_child_count": contract.max_children + 1,
                "status": "completed",
            },
            active_evidence_ids=["E0001"],
        )
        self.assertFalse(tampered.valid)
        self.assertEqual(
            set(tampered.errors),
            {
                "root_scope_anchor_mismatch",
                "inactive_evidence_returned",
                "generated_child_cap_exceeded",
            },
        )

    def test_audit_is_content_free_and_grants_no_credit_or_launch(self) -> None:
        batch = compile_label_blind_payload(payload("Find the requested fact"), depth=0)
        audit = batch.audit()
        for field in (
            "benchmark_subset_category_question_type_or_label_read",
            "mapping_gold_answer_key_evaluator_score_prediction_or_reward_read",
            "credential_or_environment_value_read",
            "network_model_search_fetch_subprocess_or_benchmark_called",
            "answer_evidence_membership_row_cell_predicate_or_task_credit_granted",
            "benchmark_forward_or_full220_launch_allowed",
        ):
            self.assertFalse(audit[field], field)
        self.assertNotIn("Find the requested fact", repr(audit))


if __name__ == "__main__":
    unittest.main()
