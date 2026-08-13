from __future__ import annotations

import copy
import inspect
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25420_list_atomic_changed_safe_runtime as target  # noqa: E402


COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")


def table(authors: str, *, title="Title", stream="IETF") -> str:
    return (
        "```markdown\n"
        "| RFC | Title | Authors | Status | Stream | Published |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        f"| RFC 9400 | {title} | {authors} | Informational | {stream} | May 2023 |\n"
        "```"
    )


class V25420ListAtomicChangedSafeRuntimeTests(unittest.TestCase):
    def test_cardinality_decrease_rolls_back_only_authors_cell(self) -> None:
        base = table("A. Smith; B. Jones; C. Brown")
        candidate = table(
            "A. Smith Example Corp B. Jones Other Corp C. Brown Third Corp",
            title="Corrected Title",
        )
        value = target.apply_list_atomic_guard(base, candidate, COLUMNS)
        self.assertEqual(value["rejected_list_cardinality_decrease_count"], 1)
        self.assertEqual(value["retained_candidate_coordinate_count"], 1)
        self.assertIn("A. Smith; B. Jones; C. Brown", value["prediction"])
        self.assertIn("Corrected Title", value["prediction"])

    def test_equal_or_larger_authors_cardinality_is_retained(self) -> None:
        base = table("A. Smith; B. Jones")
        candidate = table("A. Smith; B. Jones; C. Brown")
        value = target.apply_list_atomic_guard(base, candidate, COLUMNS)
        self.assertEqual(value["rejected_list_cardinality_decrease_count"], 0)
        self.assertEqual(value["prediction"], candidate)

    def test_non_list_column_edit_is_always_retained(self) -> None:
        base = table("A. Smith; B. Jones", stream="IETF")
        candidate = table("A. Smith; B. Jones", stream="Internet Engineering Task Force")
        value = target.apply_list_atomic_guard(base, candidate, COLUMNS)
        self.assertEqual(value["list_semantic_changed_coordinate_count"], 0)
        self.assertEqual(value["prediction"], candidate)

    def test_guard_rejects_shape_or_identity_drift(self) -> None:
        base = table("A. Smith; B. Jones")
        with self.assertRaises(ValueError):
            target.apply_list_atomic_guard(
                base, table("A. Smith").replace("RFC 9400", "RFC 9401"), COLUMNS
            )

    def test_receipt_is_content_free_and_tamper_fails(self) -> None:
        value = target.apply_list_atomic_guard(
            table("A. Smith; B. Jones"), table("A. Smith B. Jones"), COLUMNS
        )
        receipt = target._receipt(value)
        self.assertEqual(target.validate_receipt(receipt), receipt)
        text = repr(receipt)
        self.assertNotIn("A. Smith", text)
        changed = copy.deepcopy(receipt)
        changed["rejected_list_cardinality_decrease_count"] = 0
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_receipt(changed)

    def test_runtime_calls_parent_once_and_has_no_extra_provider_surface(self) -> None:
        source = inspect.getsource(target.run_task)
        self.assertEqual(source.count("parent.run_task("), 1)
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search(", source)
        self.assertNotIn("requests", source)

    def test_diagnostic_replay_blocks_known_author_list_collapse(self) -> None:
        base = table("K. De Schepper; B. Briscoe, Ed.; G. White")
        candidate = table("K. De Schepper B. Briscoe, Ed. G. White")
        value = target.apply_list_atomic_guard(base, candidate, COLUMNS)
        self.assertEqual(value["prediction"], base)
        self.assertEqual(value["rejected_list_cardinality_decrease_count"], 1)

    def test_list_semantics_are_fixed_visible_column_names(self) -> None:
        self.assertIn("authors", target.LIST_COLUMN_KEYS)
        self.assertNotIn("status", target.LIST_COLUMN_KEYS)
        self.assertNotIn("stream", target.LIST_COLUMN_KEYS)

    def test_result_recomputes_guard_from_private_parent(self) -> None:
        base = table("A. Smith; B. Jones")
        candidate = table("A. Smith Example B. Jones Other")
        raw_parent = {
            "predictions": {
                target.parent.CONTROL_ARM: base,
                target.parent.CANDIDATE_ARM: candidate,
            }
        }
        parent_result = {
            "opaque_id": "a" * 24,
            "prediction_kind": "model_generated",
            "private_parent_result": raw_parent,
            "result_payload_sha256": "b" * 64,
            "cost": {"model": {}, "search": {}, "system_total_tokens": 0},
        }
        with mock.patch.object(
            target.parent, "validate_result", side_effect=lambda value: value
        ), mock.patch.object(
            target.parent.parent, "validate_result", side_effect=lambda value: value
        ):
            value = target._wrap_result(parent_result)
            self.assertEqual(target.validate_result(value), value)
            self.assertTrue(value["list_atomic_guard_receipt"]["guard_changed_candidate"])
            changed = copy.deepcopy(value)
            changed["prediction"] = candidate
            changed["prediction_sha256"] = target.hashlib.sha256(
                candidate.encode()
            ).hexdigest()
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.assertRaises(ValueError):
                target.validate_result(changed)


if __name__ == "__main__":
    unittest.main()
