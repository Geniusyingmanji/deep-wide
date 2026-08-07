from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24743_generic_record_binding import _table_matrix, _render_table  # noqa: E402
from deepwide_agent.v24816_label_blind_consensus import (  # noqa: E402
    build_consensus,
    symmetric_medoid_fallback,
    validate_consensus,
)


QUESTION = "Please output a Markdown table with the following columns: Entity, A, B. Return one table only."


def table(rows):
    return _render_table(["Entity", "A", "B"], rows)


class V24816ConsensusTests(unittest.TestCase):
    def test_majority_rows_and_cells(self):
        sources = [
            table([["Alpha", "1", "x"], ["Beta", "2", "Unknown"]]),
            table([["Alpha", "1", "y"], ["Beta", "2", "z"]]),
            table([["Alpha", "3", "x"], ["Gamma", "9", "q"]]),
        ]
        value = build_consensus(QUESTION, sources)
        _columns, rows = _table_matrix(value["prediction"])
        self.assertEqual(rows, [["Alpha", "1", "x"], ["Beta", "2", "z"]])
        self.assertEqual(value["receipt"]["single_source_rows_excluded"], 1)
        self.assertGreaterEqual(value["receipt"]["majority_supported_cells"], 3)

    def test_all_conflicting_known_uses_deterministic_medoid(self):
        sources = [
            table([["Alpha", "1", "x"]]),
            table([["Alpha", "2", "x"]]),
            table([["Alpha", "3", "x"]]),
        ]
        value = build_consensus(QUESTION, sources)
        _columns, rows = _table_matrix(value["prediction"])
        self.assertEqual(rows[0][1], "1")
        self.assertEqual(value["receipt"]["unresolved_known_conflict_cells"], 1)

    def test_medoid_singleton_row_is_preserved_but_nonmedoid_singleton_is_not(self):
        sources = [
            table([["Alpha", "1", "x"], ["MedoidOnly", "m", "n"]]),
            table([["Alpha", "1", "y"]]),
            table([["Alpha", "2", "x"], ["OtherOnly", "q", "r"]]),
        ]
        value = build_consensus(QUESTION, sources)
        _columns, rows = _table_matrix(value["prediction"])
        identities = {row[0] for row in rows}
        self.assertIn("MedoidOnly", identities)
        self.assertNotIn("OtherOnly", identities)
        self.assertEqual(value["receipt"]["medoid_only_rows_preserved"], 1)

    def test_header_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "header"):
            build_consensus(
                QUESTION,
                [table([["Alpha", "1", "x"]]), _render_table(["Entity", "A", "C"], [["Alpha", "1", "x"]]), table([["Alpha", "1", "x"]])],
            )

    def test_tamper_and_privileged_argument_surface_absent(self):
        sources = [table([["Alpha", "1", "x"]])] * 3
        value = build_consensus(QUESTION, sources)
        changed = copy.deepcopy(value)
        changed["receipt"]["majority_supported_cells"] += 1
        changed["receipt"].pop("receipt_sha256")
        changed["receipt"]["receipt_sha256"] = payload_sha256(changed["receipt"])
        changed.pop("result_sha256")
        changed["result_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            validate_consensus(changed, question=QUESTION, predictions=sources)

    def test_prediction_is_invariant_to_source_permutation(self):
        sources = [
            table([["Alpha", "1", "x"], ["Beta", "2", "Unknown"]]),
            table([["Alpha", "1", "y"], ["Beta", "2", "z"]]),
            table([["Alpha", "3", "x"], ["Gamma", "9", "q"]]),
        ]
        expected = build_consensus(QUESTION, sources)["prediction"]
        self.assertEqual(
            build_consensus(QUESTION, [sources[2], sources[0], sources[1]])[
                "prediction"
            ],
            expected,
        )

    def test_header_fallback_is_source_order_invariant(self):
        sources = [
            table([["Alpha", "1", "x"]]),
            _render_table(["Entity", "A", "C"], [["Alpha", "1", "x"]]),
            table([["Alpha", "2", "x"]]),
        ]
        expected = symmetric_medoid_fallback(QUESTION, sources)["prediction"]
        self.assertEqual(
            symmetric_medoid_fallback(
                QUESTION, [sources[1], sources[2], sources[0]]
            )["prediction"],
            expected,
        )


if __name__ == "__main__": unittest.main()
