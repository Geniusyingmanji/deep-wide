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

from deepwide_agent import v25322_twice_disjoint_worldbank_population as target  # noqa: E402


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
OLD_ENTITIES = ALL_CODES[:144]
CONSUMED_TARGETS = tuple(f"ZZ.OLD.{index}@2022" for index in range(48))
CONSUMED_RESPONSES = tuple(
    hashlib.sha256(f"consumed-response-{index}".encode()).hexdigest()
    for index in range(84)
)
TARGETS = tuple(
    target.TargetSpec(
        label=f"New metric {index}",
        indicator=f"ZZ.TWICE.{index}",
        year="2022",
        urls=target.target_urls(f"ZZ.TWICE.{index}"),
    )
    for index in range(24)
)


def blob(
    spec: target.TargetSpec,
    page: int,
    *,
    common_new: int = 121,
) -> bytes:
    codes = ALL_CODES[:200] if page == 1 else ALL_CODES[200:]
    allowed = set(ALL_CODES[144 : 144 + common_new])
    return json.dumps(
        [
            {"page": page, "pages": 2, "per_page": 200, "total": 265},
            [
                {
                    "countryiso3code": code,
                    "indicator": {"id": spec.indicator},
                    "date": "2022",
                    "value": None
                    if code not in allowed
                    else f"{spec.indicator}-{page}-{position}",
                }
                for position, code in enumerate(codes)
            ],
        ],
        separators=(",", ":"),
    ).encode()


def candidates(common_new: int = 121) -> dict:
    return {
        spec: (blob(spec, 1, common_new=common_new), blob(spec, 2, common_new=common_new))
        for spec in TARGETS
    }


def catalog() -> bytes:
    records = [
        {
            "id": item[:-5],
            "name": f"Old metric {index}",
            "source": {"id": "2"},
        }
        for index, item in enumerate(CONSUMED_TARGETS)
    ]
    records.extend(
        {
            "id": f"ZZ.CATALOG.{index}",
            "name": f"Catalog metric {index}",
            "source": {"id": "2"},
        }
        for index in range(80)
    )
    return json.dumps(
        [
            {"page": 1, "pages": 1, "per_page": 50000, "total": len(records)},
            records,
        ],
        separators=(",", ":"),
    ).encode()


class V25322TwiceDisjointWorldBankPopulationTests(unittest.TestCase):
    def _select(self, common_new: int = 121) -> dict:
        return target.select_and_render_population(
            candidates(common_new),
            consumed_target_keys=CONSUMED_TARGETS,
            consumed_entity_codes=OLD_ENTITIES,
            consumed_response_sha256=CONSUMED_RESPONSES,
        )

    def test_catalog_excludes_exact48_consumed_targets(self) -> None:
        selected, receipt = target.parse_catalog(
            catalog(),
            historical_target_keys=("ZZ.HISTORY.1@2022",),
            consumed_target_keys=CONSUMED_TARGETS,
        )
        self.assertEqual(len(selected), 24)
        self.assertEqual(receipt["consumed_target_count"], 48)
        self.assertTrue(
            set(item.key.casefold() for item in selected).isdisjoint(
                item.casefold() for item in CONSUMED_TARGETS
            )
        )

    def test_selector_prefers108_and_binds_48_144_84_manifest(self) -> None:
        value = self._select()
        self.assertEqual(len(value["target_keys"]), 4)
        self.assertEqual(len(value["entities"]), 108)
        self.assertEqual(value["rows_per_task"], 9)
        self.assertEqual(len(value["tasks"]), 12)
        self.assertEqual(len(value["pages"]), 8)
        receipt = value["disjointness_receipt"]
        self.assertEqual(receipt["consumed_target_count"], 48)
        self.assertEqual(receipt["consumed_entity_count"], 144)
        self.assertEqual(receipt["consumed_response_hash_count"], 84)
        self.assertTrue(receipt["candidate_response_hashes_unique"])

    def test_selector_falls_to96_and_below96_is_nogo(self) -> None:
        value = self._select(100)
        self.assertEqual(len(value["entities"]), 96)
        self.assertEqual(value["rows_per_task"], 8)
        with self.assertRaisesRegex(RuntimeError, "no viable twice-disjoint"):
            self._select(95)

    def test_manifest_cardinality_drift_fails_closed(self) -> None:
        for kind in ("target", "entity", "response"):
            kwargs = {
                "consumed_target_keys": CONSUMED_TARGETS,
                "consumed_entity_codes": OLD_ENTITIES,
                "consumed_response_sha256": CONSUMED_RESPONSES,
            }
            if kind == "target":
                kwargs["consumed_target_keys"] = CONSUMED_TARGETS[:-1]
            elif kind == "entity":
                kwargs["consumed_entity_codes"] = OLD_ENTITIES[:-1]
            else:
                kwargs["consumed_response_sha256"] = CONSUMED_RESPONSES[:-1]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.select_and_render_population(candidates(), **kwargs)

    def test_consumed_response_body_fails_closed(self) -> None:
        source = candidates()
        first = TARGETS[0]
        digest = hashlib.sha256(source[first][0]).hexdigest()
        consumed = (digest, *CONSUMED_RESPONSES[1:])
        with self.assertRaisesRegex(ValueError, "consumed target response"):
            target.select_and_render_population(
                source,
                consumed_target_keys=CONSUMED_TARGETS,
                consumed_entity_codes=OLD_ENTITIES,
                consumed_response_sha256=consumed,
            )

    def test_selection_is_deterministic_under_candidate_order(self) -> None:
        source = candidates()
        first = target.select_and_render_population(
            source,
            consumed_target_keys=CONSUMED_TARGETS,
            consumed_entity_codes=OLD_ENTITIES,
            consumed_response_sha256=CONSUMED_RESPONSES,
        )
        second = target.select_and_render_population(
            dict(reversed(list(source.items()))),
            consumed_target_keys=CONSUMED_TARGETS,
            consumed_entity_codes=OLD_ENTITIES,
            consumed_response_sha256=CONSUMED_RESPONSES,
        )
        self.assertEqual(first, second)

    def test_source_is_pure_label_blind_and_credit_zero(self) -> None:
        path = ROOT / "src/deepwide_agent/v25322_twice_disjoint_worldbank_population.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "requests",
            "socket",
            "subprocess",
            "urllib.request",
        ):
            self.assertNotIn(forbidden, imports)
        for forbidden in (
            '.get("category")',
            '.get("question_type")',
            '.get("split")',
            '.get("gold")',
            '.get("score")',
            "run_official_eval_local",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn(
            '"entropy_or_information_gain_assigns_signed_credit": False', source
        )


if __name__ == "__main__":
    unittest.main()
