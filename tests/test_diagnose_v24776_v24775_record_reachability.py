from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24776_v24775_record_reachability as target  # noqa: E402


ENTITIES = ("Alpha Institute", "Beta College", "Gamma School", "Delta Academy")


class V24776RecordReachabilityDiagnosisTests(unittest.TestCase):
    def candidates(self, text: str, *, entity: str = ENTITIES[0], column: str = "Founded") -> set[str]:
        return target.extract_target_candidates(
            text, entities=ENTITIES, entity=entity, column=column
        )

    def test_bounded_multilingual_founding_records_are_reachable(self) -> None:
        cases = (
            ("Alpha Institute\nEstablished: | 2017", "2017"),
            ("Alpha Institute\nTanggal Berdiri | : | 24 November 2014", "2014"),
            ("Alpha Institute\nTahun Didirikan: 1985", "1985"),
            ("Alpha Institute berdiri sejak 2023.", "2023"),
            ("Alpha Institute didirikan pada tahun 2010.", "2010"),
            ("Alpha Institute was established in 2009.", "2009"),
        )
        for text, year in cases:
            with self.subTest(text=text):
                self.assertEqual(self.candidates(text), {year})

    def test_inauguration_and_nearby_unbound_year_are_not_founding(self) -> None:
        self.assertEqual(
            self.candidates("Alpha Institute was inaugurated in 2026."), set()
        )
        self.assertEqual(
            self.candidates(
                "Alpha Institute\nThis prose interrupts the exact record.\nFounded: 1998"
            ),
            set(),
        )

    def test_country_requires_exact_label_and_closed_value(self) -> None:
        self.assertEqual(
            self.candidates("Alpha Institute\nCountry: India", column="Country"),
            {"India"},
        )
        for text in (
            "Alpha Institute\nCountry rank: India",
            "Alpha Institute\nNational: India",
            "Alpha Institute is a college in India.",
            "Alpha Institute\nCountry: 17th in India",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.candidates(text, column="Country"), set())

    def test_exact_markdown_table_is_supported_without_cross_entity_binding(self) -> None:
        table = """| Organization | Founded | Country |
| --- | --- | --- |
| Alpha Institute | 2017 | India |
| Beta College | 1999 | Canada |"""
        self.assertEqual(self.candidates(table), {"2017"})
        self.assertEqual(self.candidates(table, column="Country"), {"India"})
        self.assertEqual(
            self.candidates(table, entity="Beta College", column="Founded"),
            {"1999"},
        )
        self.assertEqual(
            self.candidates(
                "Alpha Institute and Beta College were founded in 2017."
            ),
            set(),
        )

    def test_cell_state_partition_and_status_are_fail_closed(self) -> None:
        fields = {"a": "Founded", "b": "Founded", "c": "Country", "d": "Country"}
        observations = {
            "b": {"v1": {"one.example"}},
            "c": {"v2": {"one.example", "two.example"}},
            "d": {"v3": {"one.example"}, "v4": {"two.example"}},
        }
        aggregate, by_field, safe = target.classify_record_cells(observations, fields)
        self.assertEqual(
            aggregate,
            {
                "unreachable_cell_count": 1,
                "one_source_same_value_cell_count": 1,
                "two_source_same_value_cell_count": 1,
                "conflicting_cell_count": 1,
            },
        )
        self.assertEqual(safe, {("c", "v2")})
        self.assertEqual(sum(by_field["Founded"].values()), 2)
        self.assertEqual(sum(by_field["Country"].values()), 2)
        self.assertEqual(
            target.choose_status(
                safe_pair_count=0,
                safe_pairs_with_two_projection_sources=0,
                safe_pairs_with_support=0,
                final_changed_cell_count=0,
            ),
            target.STATUS_ACQUISITION,
        )
        self.assertEqual(
            target.choose_status(
                safe_pair_count=1,
                safe_pairs_with_two_projection_sources=0,
                safe_pairs_with_support=0,
                final_changed_cell_count=0,
            ),
            target.STATUS_PROJECTION,
        )

    def test_resealed_authorization_or_claim_tamper_is_rejected(self) -> None:
        value = {
            "artifact_version": 1,
            "role": target.ROLE,
            "protocol_id": target.contract.PROTOCOL_ID,
            "created_at_unix": 0,
            "status": target.STATUS_ACQUISITION,
            "parents": {},
            "source_manifest": {
                str(path): target.contract.sha256(ROOT / path)
                for path in target.SOURCE_FILES
            },
            "frozen_forward": {"forward_health_go": True, "mechanism_go": False},
            "acquisition_funnel": {
                "entity_slot_count": 1,
                "requested_aligned_source_coverage_histogram": {"0": 1, "1": 0, "2+": 0},
                "usable_exact_identity_source_coverage_histogram": {"0": 1, "1": 0, "2+": 0},
            },
            "unknown_surface": {"unknown_cell_count": 1},
            "strict_exact_record_reachability": {
                "unreachable_cell_count": 1,
                "one_source_same_value_cell_count": 0,
                "two_source_same_value_cell_count": 0,
                "conflicting_cell_count": 0,
                "safe_two_source_same_value_pair_count": 0,
                "record_target_value_pair_count": 0,
                "record_source_observation_count": 0,
            },
            "projection_and_support_binding": {
                "record_pairs_with_any_legacy_projection": 0,
                "record_pairs_missing_legacy_projection": 0,
                "record_source_links_preserved_by_legacy_projection": 0,
                "record_source_links_lost_before_legacy_projection": 0,
            },
            "diagnosis": {
                "parser_only_can_reach_the_unchanged_two_source_gate_on_frozen_pages": False
            },
            "source_policy": {},
            "claim_scope": {
                "mechanism_bottleneck_diagnosed": True,
                "deepwidebench_quality_measured": False,
                "benchmark_improvement_measured": False,
                "entropy_or_credit_assignment_validated": False,
                "sota_supported": False,
            },
            "authorization": {
                "append_only_query_source_fetch_design": True,
                "append_only_structured_record_projector_design": False,
                "append_only_support_binding_design": False,
                "append_only_integration_design": False,
                "same_population_forward_retry_resume_or_rerun": False,
                "fresh_external_activation_or_launch": False,
                "private_truth_or_quality_surface_open": False,
                "evaluator": False,
                "paired_dev64": False,
                "exact220": False,
                "leaderboard_or_sota": False,
            },
        }
        value["diagnosis_payload_sha256"] = target.contract.payload_sha256(value)
        target.validate_diagnosis(value)
        for path, field in (("authorization", "exact220"), ("claim_scope", "sota_supported")):
            changed = copy.deepcopy(value)
            changed[path][field] = True
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                {key: item for key, item in changed.items() if key != "diagnosis_payload_sha256"}
            )
            with self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_public_surface_and_create_only_publication(self) -> None:
        safe = {"role": "aggregate", "count": 1}
        target._assert_public_surface(safe, private_literals=("Private Entity",))
        for unsafe in (
            {"url": "https://example.org/private"},
            {"entity": "Private Entity"},
        ):
            with self.assertRaises(ValueError):
                target._assert_public_surface(
                    unsafe, private_literals=("Private Entity",)
                )
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "diagnosis.json"
            target.publish_new(path, safe)
            with self.assertRaises(FileExistsError):
                target.publish_new(path, safe)

    def test_source_has_no_privileged_metadata_or_external_effect_import(self) -> None:
        path = Path(target.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        privileged = {
            "answer_key",
            "benchmark_question_type",
            "category",
            "gold",
            "ground_truth",
            "mapping",
            "question_type",
            "reward",
            "score",
            "split",
            "task_category",
        }
        accesses = []
        for node in ast.walk(tree):
            key = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                key = node.args[0].value
            if isinstance(key, str) and key.casefold() in privileged:
                accesses.append((node.lineno, key))
        self.assertEqual(accesses, [])
        serialized = json.dumps(
            {"output": str(target.OUTPUT), "source": path.name}, ensure_ascii=False
        )
        self.assertNotIn("evaluation/", serialized)


if __name__ == "__main__":
    unittest.main()
