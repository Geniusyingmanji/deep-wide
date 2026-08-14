from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25471_qualified_source_label_candidate as target  # noqa: E402
from scripts import run_v25469_row_key_source_external as runner  # noqa: E402


COLUMNS = ("Domain", "Type", "TLD Manager")
BASE = (
    "```markdown\n"
    "| Domain | Type | TLD Manager |\n"
    "| --- | --- | --- |\n"
    "| .af | Unknown | Old Manager |\n"
    "```"
)


def page(content: str, *, url: str = "https://www.iana.org/domains/root/db/af.html", title: str = ".af record") -> dict[str, str]:
    return {"url": url, "title": title, "content": content}


class V25471QualifiedSourceLabelCandidateTests(unittest.TestCase):
    def test_one_qualifier_source_label_maps_to_visible_field(self) -> None:
        value = target.build_application(
            BASE,
            columns=COLUMNS,
            pages=[page("TLD Type | country-code")],
        )
        self.assertIn("| .af | country-code | Old Manager |", value["candidate_prediction"])
        candidate = value["private_candidate_registry"]["candidates"][0]
        self.assertEqual(candidate["source_field"], "TLD Type")
        self.assertEqual(candidate["field"], "Type")
        self.assertEqual(candidate["source_kind"], "qualified_source_label_pipe_record")

    def test_parent_exact_label_candidates_are_preserved(self) -> None:
        value = target.build_application(
            BASE,
            columns=COLUMNS,
            pages=[page("Type: country-code")],
        )
        self.assertIn("| .af | country-code | Old Manager |", value["candidate_prediction"])
        self.assertNotEqual(
            value["private_candidate_registry"]["candidates"][0]["source_kind"],
            "qualified_source_label_pipe_record",
        )

    def test_exactly_one_qualifier_and_complete_suffix_are_required(self) -> None:
        for label in (
            "Official TLD Type",
            "TLD Domain Type",
            "TLD Typed",
            "Manager TLD",
        ):
            with self.subTest(label=label):
                value = target.build_application(
                    BASE, columns=COLUMNS, pages=[page(f"{label} | country-code")]
                )
                self.assertEqual(value["candidate_prediction"], BASE)

    def test_unbound_unknown_duplicate_or_conflicting_coordinates_fail_closed(self) -> None:
        fixtures = {
            "unbound": [page("TLD Type | country-code", url="https://www.iana.org/domains/root/db/bh.html", title=".bh record")],
            "unknown": [page("TLD Type | Unknown")],
            "duplicate": [page("TLD Type | country-code\nTLD Type | country-code")],
            "conflict": [page("TLD Type | country-code\nTLD Type | generic")],
        }
        for name, pages in fixtures.items():
            with self.subTest(name=name):
                value = target.build_application(BASE, columns=COLUMNS, pages=pages)
                self.assertEqual(value["candidate_prediction"], BASE)

    def test_replay_and_resealed_alias_tamper_fail_closed(self) -> None:
        pages = [page("TLD Type | country-code")]
        value = target.build_application(BASE, columns=COLUMNS, pages=pages)
        self.assertEqual(
            target.validate_application(value, base_prediction=BASE, columns=COLUMNS, pages=pages),
            value,
        )
        changed = copy.deepcopy(value)
        item = changed["private_candidate_registry"]["candidates"][0]
        item["source_field"] = "Official Type"
        item.pop("candidate_payload_sha256")
        item["candidate_payload_sha256"] = target.payload_sha256(item)
        changed["private_candidate_registry"].pop("artifact_payload_sha256")
        changed["private_candidate_registry"]["artifact_payload_sha256"] = target.payload_sha256(changed["private_candidate_registry"])
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_application(changed)

    def test_frozen_v25469_pages_have_outcome_blind_counterfactual_reach(self) -> None:
        rows = [
            runner.validate_task_row(json.loads(line))
            for line in (ROOT / "outputs/v25469_row_key_source_external_v1_20260814/frozen_task_results.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        task_count = candidate_count = 0
        for row in rows:
            decoded = runner._decode_completed(row["runtime_result"], row["content_free_stage_receipt"])
            result = decoded["result"]
            value = target.build_application(
                result["predictions"][runner.runtime.BASE_ARM],
                columns=result["private_source_columns"],
                pages=result["private_same_forward_pages"],
            )
            count = value["content_free_receipt"]["applied_coordinate_count"]
            task_count += int(count > 0)
            candidate_count += count
        self.assertEqual(task_count, 4)
        self.assertEqual(candidate_count, 4)

    def test_pure_module_has_no_privileged_or_external_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {
            "category", "question_type", "task_category", "split", "ground_truth",
            "gold", "answer_key", "score", "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value in forbidden_fields:
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".") for forbidden in ("os", "pathlib", "subprocess", "socket", "requests", "httpx") for name in imports))
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search_many", source)
        self.assertNotIn("fetch_urls", source)


if __name__ == "__main__":
    unittest.main()
