from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24221_cgdp_baseline import (  # noqa: E402
    PRODUCTION_PACKAGE_AUTHORIZED,
    build_predicate_ledger,
    build_trace_step,
    decide_cgdp_baseline,
    object_sha256,
    validate_decision_receipt,
    validate_predicate_ledger,
    validate_trace,
)


ROOT_SCOPE = "0" * 64
TASK_REF = "1" * 64


def digest(character: str) -> str:
    return character * 64


def predicate(
    reference: str,
    action: str,
    *,
    priority: int,
    status: str = "unresolved",
    required: bool = True,
    support: tuple[str, ...] = (),
    contradiction: tuple[str, ...] = (),
) -> dict[str, object]:
    return {
        "predicate_ref_sha256": reference,
        "required": required,
        "priority": priority,
        "status": status,
        "action_class_sha256": action,
        "support_evidence_class_sha256s": sorted(support),
        "contradiction_evidence_class_sha256s": sorted(contradiction),
    }


def evidence(
    evidence_class: str,
    source_class: str,
    *,
    page_backed: bool = True,
    contradicted: bool = False,
) -> dict[str, object]:
    return {
        "evidence_class_sha256": evidence_class,
        "source_class_sha256": source_class,
        "page_backed": page_backed,
        "contradicted": contradicted,
    }


def trace(
    *rows: tuple[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    return [
        build_trace_step(
            step_index=index,
            action_class_sha256=action,
            evidence=observations,
        )
        for index, (action, observations) in enumerate(rows)
    ]


def decide(
    predicates: list[dict[str, object]],
    observations: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object]]:
    ledger = build_predicate_ledger(
        root_scope_sha256=ROOT_SCOPE,
        predicates=predicates,
    )
    receipt = decide_cgdp_baseline(
        predicate_ledger=ledger,
        trace=observations,
        opaque_task_ref_sha256=TASK_REF,
        decision_index=7,
    )
    return ledger, receipt


class V24221CGDPBaselineTests(unittest.TestCase):
    def test_all_supported_is_answer_ready_but_not_task_success(self) -> None:
        action = digest("a")
        evidence_class = digest("b")
        _, receipt = decide(
            [
                predicate(
                    digest("c"),
                    action,
                    priority=0,
                    status="supported",
                    support=(evidence_class,),
                )
            ],
            trace(
                (
                    action,
                    [evidence(evidence_class, digest("d"))],
                )
            ),
        )
        self.assertEqual(receipt["decision_kind"], "answer_ready")
        self.assertEqual(receipt["required_supported_count"], 1)
        self.assertIs(receipt["answer_ready_is_not_task_success"], True)
        self.assertIs(receipt["open_set_completeness_claimed"], False)

    def test_unresolved_selects_highest_priority_nonexhausted_action(self) -> None:
        action_low = digest("a")
        action_high = digest("b")
        _, receipt = decide(
            [
                predicate(digest("d"), action_low, priority=9),
                predicate(digest("c"), action_high, priority=1),
            ],
            [],
        )
        self.assertEqual(receipt["decision_kind"], "continue")
        self.assertEqual(receipt["selected_predicate_ref_sha256"], digest("c"))
        self.assertEqual(receipt["selected_action_class_sha256"], action_high)

    def test_contradicted_predicate_precedes_unresolved_predicate(self) -> None:
        contradicted_action = digest("a")
        unresolved_action = digest("b")
        contradiction = digest("e")
        _, receipt = decide(
            [
                predicate(digest("c"), unresolved_action, priority=0),
                predicate(
                    digest("d"),
                    contradicted_action,
                    priority=100,
                    status="contradicted",
                    contradiction=(contradiction,),
                ),
            ],
            trace(
                (
                    contradicted_action,
                    [
                        evidence(
                            contradiction,
                            digest("f"),
                            contradicted=True,
                        )
                    ],
                )
            ),
        )
        self.assertEqual(receipt["decision_kind"], "continue")
        self.assertEqual(receipt["selected_predicate_ref_sha256"], digest("d"))
        self.assertEqual(
            receipt["selected_action_class_sha256"], contradicted_action
        )

    def test_one_stagnant_repeat_continues_and_two_abstain(self) -> None:
        action = digest("a")
        predicates = [predicate(digest("b"), action, priority=0)]
        one_repeat = trace((action, []), (action, []))
        _, one_receipt = decide(predicates, one_repeat)
        self.assertEqual(one_receipt["pending_action_stagnant_repeats"][action], 1)
        self.assertEqual(one_receipt["decision_kind"], "continue")

        two_repeats = trace((action, []), (action, []), (action, []))
        _, two_receipt = decide(predicates, two_repeats)
        self.assertEqual(two_receipt["pending_action_stagnant_repeats"][action], 2)
        self.assertEqual(two_receipt["decision_kind"], "abstain_exhausted")
        self.assertIsNone(two_receipt["selected_predicate_ref_sha256"])
        self.assertIsNone(two_receipt["selected_action_class_sha256"])
        self.assertIn("without_success_claim", two_receipt["decision_reason"])

    def test_interleaved_actions_keep_independent_exhaustion_streaks(self) -> None:
        action_a = digest("a")
        action_b = digest("b")
        predicates = [
            predicate(digest("c"), action_a, priority=0),
            predicate(digest("d"), action_b, priority=1),
        ]
        observations = trace(
            (action_a, []),
            (action_b, []),
            (action_a, []),
            (action_b, []),
            (action_a, []),
            (action_b, []),
        )
        _, receipt = decide(predicates, observations)
        self.assertEqual(
            receipt["pending_action_stagnant_repeats"],
            {action_a: 2, action_b: 2},
        )
        self.assertEqual(receipt["decision_kind"], "abstain_exhausted")

    def test_new_usable_evidence_resets_action_exhaustion(self) -> None:
        action = digest("a")
        observations = trace(
            (action, []),
            (action, []),
            (action, [evidence(digest("c"), digest("d"))]),
        )
        _, receipt = decide(
            [predicate(digest("b"), action, priority=0)], observations
        )
        self.assertEqual(receipt["pending_action_stagnant_repeats"][action], 0)
        self.assertEqual(receipt["usable_page_evidence_class_count"], 1)
        self.assertEqual(receipt["decision_kind"], "continue")

    def test_new_source_class_resets_action_exhaustion(self) -> None:
        action = digest("a")
        evidence_class = digest("c")
        source_a = digest("d")
        source_b = digest("e")
        observations = trace(
            (action, [evidence(evidence_class, source_a)]),
            (action, [evidence(evidence_class, source_a)]),
            (action, [evidence(evidence_class, source_b)]),
        )
        _, receipt = decide(
            [predicate(digest("b"), action, priority=0)], observations
        )
        self.assertEqual(receipt["pending_action_stagnant_repeats"][action], 0)
        self.assertEqual(receipt["usable_page_evidence_class_count"], 1)
        self.assertEqual(receipt["source_class_count"], 2)

    def test_new_contradiction_signal_resets_but_is_not_positive_novelty(self) -> None:
        action = digest("a")
        observations = trace(
            (action, []),
            (action, []),
            (
                action,
                [
                    evidence(
                        digest("c"),
                        digest("d"),
                        contradicted=True,
                    )
                ],
            ),
        )
        _, receipt = decide(
            [predicate(digest("b"), action, priority=0)], observations
        )
        self.assertEqual(receipt["pending_action_stagnant_repeats"][action], 0)
        self.assertEqual(receipt["usable_page_evidence_class_count"], 0)
        self.assertEqual(receipt["source_class_count"], 0)
        self.assertEqual(receipt["contradiction_page_evidence_class_count"], 1)

    def test_nonpage_observation_is_not_usable_or_source_novelty(self) -> None:
        action = digest("a")
        observations = trace(
            (
                action,
                [
                    evidence(
                        digest("c"),
                        digest("d"),
                        page_backed=False,
                    )
                ],
            )
        )
        _, receipt = decide(
            [predicate(digest("b"), action, priority=0)], observations
        )
        self.assertEqual(receipt["usable_page_evidence_class_count"], 0)
        self.assertEqual(receipt["source_class_count"], 0)
        self.assertEqual(receipt["contradiction_page_evidence_class_count"], 0)
        self.assertEqual(receipt["nonpage_observation_count"], 1)

    def test_same_evidence_class_clean_and_contradicted_fails_closed(self) -> None:
        action = digest("a")
        evidence_class = digest("c")
        observations = trace(
            (action, [evidence(evidence_class, digest("d"))]),
            (
                action,
                [
                    evidence(
                        evidence_class,
                        digest("e"),
                        contradicted=True,
                    )
                ],
            ),
        )
        with self.assertRaisesRegex(ValueError, "both clean and contradicted"):
            decide([predicate(digest("b"), action, priority=0)], observations)

    def test_ledger_support_requires_clean_page_backed_trace_support(self) -> None:
        action = digest("a")
        support = digest("c")
        predicates = [
            predicate(
                digest("b"),
                action,
                priority=0,
                status="supported",
                support=(support,),
            )
        ]
        with self.assertRaisesRegex(ValueError, "clean trace page evidence"):
            decide(
                predicates,
                trace(
                    (
                        action,
                        [
                            evidence(
                                support,
                                digest("d"),
                                page_backed=False,
                            )
                        ],
                    )
                ),
            )

    def test_nested_forbidden_metadata_is_rejected(self) -> None:
        value = predicate(digest("b"), digest("a"), priority=0)
        value["priority"] = {"safe": [{"question_type": "hidden"}]}
        with self.assertRaisesRegex(ValueError, "privileged metadata rejected"):
            build_predicate_ledger(
                root_scope_sha256=ROOT_SCOPE,
                predicates=[value],
            )

    def test_nested_forbidden_metadata_is_rejected_in_trace_and_receipt(self) -> None:
        action = digest("a")
        unsafe_step = build_trace_step(
            step_index=0,
            action_class_sha256=action,
            evidence=[],
        )
        unsafe_step["evidence"] = [{"safe": {"evaluator_score": 1}}]
        with self.assertRaisesRegex(ValueError, "privileged metadata rejected"):
            validate_trace([unsafe_step])

        ledger, receipt = decide(
            [predicate(digest("b"), action, priority=0)],
            [],
        )
        unsafe_receipt = copy.deepcopy(receipt)
        unsafe_receipt["pending_action_stagnant_repeats"] = {
            "safe": {"ground_truth": "hidden"}
        }
        with self.assertRaisesRegex(ValueError, "privileged metadata rejected"):
            validate_decision_receipt(
                unsafe_receipt,
                predicate_ledger=ledger,
                trace=[],
                opaque_task_ref_sha256=TASK_REF,
                decision_index=7,
            )

    def test_tampered_and_resealed_artifacts_are_rejected(self) -> None:
        action = digest("a")
        evidence_class = digest("c")
        predicates = [
            predicate(
                digest("b"),
                action,
                priority=0,
                status="supported",
                support=(evidence_class,),
            )
        ]
        observations = trace(
            (action, [evidence(evidence_class, digest("d"))])
        )
        ledger, receipt = decide(predicates, observations)

        tampered_ledger = copy.deepcopy(ledger)
        tampered_ledger["role"] = "resealed_wrong_role"
        tampered_ledger.pop("ledger_sha256")
        tampered_ledger["ledger_sha256"] = object_sha256(tampered_ledger)
        with self.assertRaisesRegex(ValueError, "contract drifted"):
            validate_predicate_ledger(tampered_ledger)

        tampered_trace = copy.deepcopy(observations)
        tampered_trace[0]["role"] = "resealed_wrong_role"
        tampered_trace[0].pop("step_sha256")
        tampered_trace[0]["step_sha256"] = object_sha256(tampered_trace[0])
        with self.assertRaisesRegex(ValueError, "contract drifted"):
            validate_trace(tampered_trace)

        tampered_receipt = copy.deepcopy(receipt)
        tampered_receipt["decision_kind"] = "abstain_exhausted"
        tampered_receipt.pop("receipt_sha256")
        tampered_receipt["receipt_sha256"] = object_sha256(tampered_receipt)
        with self.assertRaisesRegex(ValueError, "contract drifted"):
            validate_decision_receipt(
                tampered_receipt,
                predicate_ledger=ledger,
                trace=observations,
                opaque_task_ref_sha256=TASK_REF,
                decision_index=7,
            )

    def test_canonical_schema_and_order_are_exact(self) -> None:
        action_a = digest("a")
        action_b = digest("b")
        ledger = build_predicate_ledger(
            root_scope_sha256=ROOT_SCOPE,
            predicates=[
                predicate(digest("d"), action_b, priority=2),
                predicate(digest("c"), action_a, priority=1),
            ],
        )
        self.assertEqual(
            [row["predicate_ref_sha256"] for row in ledger["predicates"]],
            [digest("c"), digest("d")],
        )
        self.assertEqual(
            list(ledger),
            [
                "artifact_version",
                "role",
                "policy_id",
                "root_scope_sha256",
                "construction_policy",
                "predicates",
                "question_text_or_raw_evidence_embedded",
                "benchmark_metadata_or_outcome_embedded",
                "ledger_sha256",
            ],
        )
        step = build_trace_step(
            step_index=0,
            action_class_sha256=action_a,
            evidence=[
                evidence(digest("f"), digest("9")),
                evidence(digest("e"), digest("8")),
            ],
        )
        self.assertEqual(
            [item["evidence_class_sha256"] for item in step["evidence"]],
            [digest("e"), digest("f")],
        )
        self.assertEqual(
            list(step),
            [
                "artifact_version",
                "role",
                "step_index",
                "action_class_sha256",
                "evidence",
                "step_sha256",
            ],
        )
        _, receipt = decide(
            [predicate(digest("c"), action_a, priority=0)],
            [],
        )
        self.assertEqual(
            list(receipt),
            [
                "artifact_version",
                "role",
                "policy_id",
                "label_blind",
                "baseline_only",
                "opaque_task_ref_sha256",
                "root_scope_sha256",
                "decision_index",
                "predicate_ledger_sha256",
                "trace_sha256",
                "required_predicate_count",
                "required_supported_count",
                "required_unresolved_count",
                "required_contradicted_count",
                "pending_action_count",
                "pending_action_stagnant_repeats",
                "minimum_stagnant_repeats",
                "usable_page_evidence_class_count",
                "source_class_count",
                "contradiction_page_evidence_class_count",
                "nonpage_observation_count",
                "decision_kind",
                "selected_predicate_ref_sha256",
                "selected_action_class_sha256",
                "decision_reason",
                "answer_ready_is_not_task_success",
                "open_set_completeness_claimed",
                "source_independence_claimed",
                "four_layer_risk_entropy_or_voc_used",
                "question_text_or_raw_evidence_read",
                "mapping_gold_category_question_type_evaluator_score_or_reward_read",
                "file_environment_network_model_search_fetch_or_process_accessed",
                "benchmark_forward_evaluator_credit_or_training_authorized",
                "receipt_sha256",
            ],
        )
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_predicate_ledger({**ledger, "extra": False})

    def test_source_independence_and_all_runtime_authorities_are_false(self) -> None:
        action = digest("a")
        _, receipt = decide(
            [predicate(digest("b"), action, priority=0)],
            [],
        )
        self.assertIs(PRODUCTION_PACKAGE_AUTHORIZED, False)
        for field in (
            "source_independence_claimed",
            "open_set_completeness_claimed",
            "four_layer_risk_entropy_or_voc_used",
            "question_text_or_raw_evidence_read",
            "mapping_gold_category_question_type_evaluator_score_or_reward_read",
            "file_environment_network_model_search_fetch_or_process_accessed",
            "benchmark_forward_evaluator_credit_or_training_authorized",
        ):
            self.assertIs(receipt[field], False, field)
        source = (ROOT / "src/deepwide_agent/v24221_cgdp_baseline.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("source-dependency hashes", source)

    def test_module_ast_has_no_io_network_process_or_dynamic_execution(self) -> None:
        path = ROOT / "src/deepwide_agent/v24221_cgdp_baseline.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        allowed_imports = {
            "__future__",
            "collections",
            "hashlib",
            "json",
            "re",
            "typing",
        }
        forbidden_calls = {
            "__import__",
            "breakpoint",
            "compile",
            "eval",
            "exec",
            "input",
            "open",
        }
        forbidden_roots = {
            "asyncio",
            "builtins",
            "http",
            "httpx",
            "importlib",
            "os",
            "pathlib",
            "requests",
            "shutil",
            "socket",
            "subprocess",
            "urllib",
        }
        imports: set[str] = set()
        calls: set[str] = set()
        attributes: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in forbidden_calls:
                    calls.add(node.func.id)
            elif isinstance(node, ast.Attribute):
                current: ast.expr = node
                while isinstance(current, ast.Attribute):
                    current = current.value
                if isinstance(current, ast.Name) and current.id in forbidden_roots:
                    attributes.add(current.id)
        self.assertEqual(imports - allowed_imports, set())
        self.assertEqual(calls, set())
        self.assertEqual(attributes, set())


if __name__ == "__main__":
    unittest.main()
