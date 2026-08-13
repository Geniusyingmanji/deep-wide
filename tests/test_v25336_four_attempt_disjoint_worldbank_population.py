from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25336_four_attempt_disjoint_worldbank_population as target  # noqa: E402


def code3(value: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(
        (
            alphabet[(value // (36 * 36)) % 36],
            alphabet[(value // 36) % 36],
            alphabet[value % 36],
        )
    )


ALL_CODES = tuple(code3(index) for index in range(265))
CONSUMED_TARGETS = tuple(f"ZZ.OLD.{index}@2022" for index in range(96))
CONSUMED_ENTITIES = ALL_CODES[:144]
CONSUMED_RESPONSES = tuple(
    hashlib.sha256(f"old-{index}".encode()).hexdigest() for index in range(169)
)


def catalog() -> bytes:
    records = [
        {"id": f"ZZ.OLD.{index}", "name": f"Old {index}", "source": {"id": "2"}}
        for index in range(96)
    ]
    records.extend(
        {"id": f"ZZ.NEW.{index}", "name": f"New {index}", "source": {"id": "2"}}
        for index in range(80)
    )
    return json.dumps(
        [{"page": 1, "pages": 1, "per_page": 50000, "total": len(records)}, records],
        separators=(",", ":"),
    ).encode()


def page(indicator: str, page_number: int, available: set[str]) -> bytes:
    codes = ALL_CODES[:200] if page_number == 1 else ALL_CODES[200:]
    return json.dumps(
        [
            {"page": page_number, "pages": 2, "per_page": 200, "total": 265},
            [
                {
                    "countryiso3code": code,
                    "indicator": {"id": indicator},
                    "date": "2022",
                    "value": f"{indicator}-{code}" if code in available else None,
                }
                for code in codes
            ],
        ],
        separators=(",", ":"),
    ).encode()


class V25336FourAttemptDisjointWorldBankPopulationTests(unittest.TestCase):
    def specs(self):
        return target.parse_catalog(
            catalog(), historical_target_keys=(), consumed_target_keys=CONSUMED_TARGETS
        )[0]

    def candidates(self, available: set[str] | None = None):
        available = available or set(ALL_CODES[144:])
        return {
            spec: (page(spec.indicator, 1, available), page(spec.indicator, 2, available))
            for spec in self.specs()
        }

    def test_catalog_excludes_exact96_consumed_targets(self) -> None:
        specs, stats = target.parse_catalog(
            catalog(), historical_target_keys=(), consumed_target_keys=CONSUMED_TARGETS
        )
        self.assertEqual(len(specs), 24)
        self.assertEqual(stats["consumed_target_count"], 96)
        self.assertFalse(
            set(item.key.casefold() for item in specs).intersection(
                item.casefold() for item in CONSUMED_TARGETS
            )
        )

    def test_selector_prefers108_and_binds_96_144_169(self) -> None:
        value = target.select_and_render_population(
            self.candidates(),
            consumed_target_keys=CONSUMED_TARGETS,
            consumed_entity_codes=CONSUMED_ENTITIES,
            consumed_response_sha256=CONSUMED_RESPONSES,
        )
        self.assertEqual(len(value["target_keys"]), 4)
        self.assertEqual(len(value["entities"]), 108)
        self.assertEqual(value["rows_per_task"], 9)
        self.assertEqual(len(value["tasks"]), 12)
        receipt = value["disjointness_receipt"]
        self.assertEqual(receipt["consumed_target_count"], 96)
        self.assertEqual(receipt["consumed_response_hash_count"], 169)

    def test_selector_falls_to96_and_below96_is_nogo(self) -> None:
        available96 = set(ALL_CODES[144:240])
        value = target.select_and_render_population(
            self.candidates(available96),
            consumed_target_keys=CONSUMED_TARGETS,
            consumed_entity_codes=CONSUMED_ENTITIES,
            consumed_response_sha256=CONSUMED_RESPONSES,
        )
        self.assertEqual(len(value["entities"]), 96)
        self.assertEqual(value["rows_per_task"], 8)
        with self.assertRaises(RuntimeError):
            target.select_and_render_population(
                self.candidates(set(ALL_CODES[144:239])),
                consumed_target_keys=CONSUMED_TARGETS,
                consumed_entity_codes=CONSUMED_ENTITIES,
                consumed_response_sha256=CONSUMED_RESPONSES,
            )

    def test_consumed_response_body_fails_closed(self) -> None:
        candidates = self.candidates()
        spec = next(iter(candidates))
        candidates[spec] = (b"old-0", candidates[spec][1])
        with self.assertRaises(ValueError):
            target.select_and_render_population(
                candidates,
                consumed_target_keys=CONSUMED_TARGETS,
                consumed_entity_codes=CONSUMED_ENTITIES,
                consumed_response_sha256=CONSUMED_RESPONSES,
            )

    def test_manifest_cardinality_drift_fails_closed(self) -> None:
        for targets, entities, responses in (
            (CONSUMED_TARGETS[:-1], CONSUMED_ENTITIES, CONSUMED_RESPONSES),
            (CONSUMED_TARGETS, CONSUMED_ENTITIES[:-1], CONSUMED_RESPONSES),
            (CONSUMED_TARGETS, CONSUMED_ENTITIES, CONSUMED_RESPONSES[:-1]),
        ):
            with self.assertRaises(ValueError):
                target.select_and_render_population(
                    self.candidates(),
                    consumed_target_keys=targets,
                    consumed_entity_codes=entities,
                    consumed_response_sha256=responses,
                )

    def test_selection_is_deterministic_under_candidate_order(self) -> None:
        candidates = self.candidates()
        reverse = dict(reversed(tuple(candidates.items())))
        first = target.select_and_render_population(
            candidates,
            consumed_target_keys=CONSUMED_TARGETS,
            consumed_entity_codes=CONSUMED_ENTITIES,
            consumed_response_sha256=CONSUMED_RESPONSES,
        )
        second = target.select_and_render_population(
            reverse,
            consumed_target_keys=CONSUMED_TARGETS,
            consumed_entity_codes=CONSUMED_ENTITIES,
            consumed_response_sha256=CONSUMED_RESPONSES,
        )
        self.assertEqual(first, second)

    def test_source_is_pure_label_blind_and_credit_zero(self) -> None:
        source = (ROOT / "src/deepwide_agent/v25336_four_attempt_disjoint_worldbank_population.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            node.names[0].name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import) and node.names
        }
        self.assertFalse(imports.intersection({"os", "pathlib", "requests", "subprocess", "socket"}))
        for forbidden in (
            '.get("category")', '.get("question_type")', '.get("split")',
            '.get("gold")', '.get("score")', "run_official_eval_local",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('"entropy_or_information_gain_assigns_signed_credit": False', source)


if __name__ == "__main__":
    unittest.main()
