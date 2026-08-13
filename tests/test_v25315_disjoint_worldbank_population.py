from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25315_disjoint_worldbank_population as target  # noqa: E402


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
CONSUMED_TARGETS = tuple(f"ZZ.OLD.{index}@2022" for index in range(24))
CONSUMED_RESPONSES = tuple(
    hashlib.sha256(f"consumed-response-{index}".encode()).hexdigest()
    for index in range(48)
)
TARGETS = tuple(
    target.TargetSpec(
        label=f"Fresh metric {index}",
        indicator=f"ZZ.NEW.{index}",
        year="2022",
        urls=target.target_urls(f"ZZ.NEW.{index}"),
    )
    for index in range(24)
)


def blob(
    spec: target.TargetSpec,
    page: int,
    *,
    codes: tuple[str, ...] = ALL_CODES,
    null_codes: frozenset[str] = frozenset(),
    salt: str = "",
) -> bytes:
    subset = codes[:200] if page == 1 else codes[200:]
    return json.dumps(
        [
            {"page": page, "pages": 2, "per_page": 200, "total": len(codes)},
            [
                {
                    "countryiso3code": code,
                    "indicator": {"id": spec.indicator},
                    "date": spec.year,
                    "value": None
                    if code in null_codes
                    else f"{spec.indicator}-{salt}-{page}-{position}",
                }
                for position, code in enumerate(subset)
            ],
        ],
        separators=(",", ":"),
    ).encode()


def candidates(*, common_new: int = 121) -> dict:
    new_codes = set(ALL_CODES[144 : 144 + common_new])
    output = {}
    for index, spec in enumerate(TARGETS):
        null_codes = frozenset(set(ALL_CODES[144:]) - new_codes)
        output[spec] = (
            blob(spec, 1, null_codes=null_codes, salt=str(index)),
            blob(spec, 2, null_codes=null_codes, salt=str(index)),
        )
    return output


def catalog() -> bytes:
    records = []
    for index in range(80):
        indicator = (
            CONSUMED_TARGETS[index][:-5]
            if index < len(CONSUMED_TARGETS)
            else f"ZZ.CAT.{index}"
        )
        records.append(
            {
                "id": indicator,
                "name": f"Catalog metric {index}",
                "source": {"id": "2"},
            }
        )
    return json.dumps(
        [
            {"page": 1, "pages": 1, "per_page": 50000, "total": len(records)},
            records,
        ],
        separators=(",", ":"),
    ).encode()


class V25315DisjointWorldBankPopulationTests(unittest.TestCase):
    def test_catalog_excludes_all_24_consumed_targets_before_ranking(self) -> None:
        selected, receipt = target.parse_catalog(
            catalog(),
            historical_target_keys=("ZZ.HISTORY.1@2022",),
            consumed_target_keys=CONSUMED_TARGETS,
        )
        self.assertEqual(len(selected), 24)
        self.assertEqual(receipt["consumed_target_count"], 24)
        self.assertTrue(
            set(item.key.casefold() for item in selected).isdisjoint(
                item.casefold() for item in CONSUMED_TARGETS
            )
        )

    def test_selector_prefers_108_new_entities_and_keeps_12_tasks(self) -> None:
        value = target.select_and_render_population(
            candidates(common_new=121),
            consumed_target_keys=CONSUMED_TARGETS,
            consumed_entity_codes=OLD_ENTITIES,
            consumed_response_sha256=CONSUMED_RESPONSES,
        )
        self.assertEqual(len(value["target_keys"]), 4)
        self.assertEqual(len(value["entities"]), 108)
        self.assertEqual(value["rows_per_task"], 9)
        self.assertEqual(len(value["tasks"]), 12)
        self.assertEqual(len(value["pages"]), 8)
        self.assertTrue(set(value["entities"]).isdisjoint(OLD_ENTITIES))
        self.assertEqual(
            value["disjointness_receipt"]["selected_entity_overlap_count"], 0
        )
        self.assertTrue(
            value["disjointness_receipt"]["candidate_response_hashes_unique"]
        )

    def test_selector_deterministically_falls_to_exactly_96_not_lower(self) -> None:
        source = candidates(common_new=100)
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
        self.assertEqual(len(first["entities"]), 96)
        self.assertEqual(first["rows_per_task"], 8)
        self.assertEqual(len(first["tasks"]), 12)

    def test_below_96_new_common_entities_is_strict_no_go(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "no viable disjoint"):
            target.select_and_render_population(
                candidates(common_new=95),
                consumed_target_keys=CONSUMED_TARGETS,
                consumed_entity_codes=OLD_ENTITIES,
                consumed_response_sha256=CONSUMED_RESPONSES,
            )

    def test_consumed_target_entity_or_duplicate_response_fails_closed(self) -> None:
        source = candidates()
        reused_target = copy.copy(TARGETS[0])
        object.__setattr__(reused_target, "indicator", "ZZ.OLD.0")
        object.__setattr__(reused_target, "urls", target.target_urls("ZZ.OLD.0"))
        changed = dict(source)
        bodies = changed.pop(TARGETS[0])
        changed[reused_target] = bodies
        with self.assertRaisesRegex(ValueError, "consumed target"):
            target.select_and_render_population(
                changed,
                consumed_target_keys=CONSUMED_TARGETS,
                consumed_entity_codes=OLD_ENTITIES,
                consumed_response_sha256=CONSUMED_RESPONSES,
            )
        duplicate = dict(source)
        first = TARGETS[0]
        second = TARGETS[1]
        duplicate[second] = duplicate[first]
        with self.assertRaisesRegex(ValueError, "response bytes reused"):
            target.select_and_render_population(
                duplicate,
                consumed_target_keys=CONSUMED_TARGETS,
                consumed_entity_codes=OLD_ENTITIES,
                consumed_response_sha256=CONSUMED_RESPONSES,
            )
        reused_response = dict(source)
        first_blob = reused_response[TARGETS[0]][0]
        consumed = (
            hashlib.sha256(first_blob).hexdigest(),
            *CONSUMED_RESPONSES[1:],
        )
        with self.assertRaisesRegex(ValueError, "consumed target response"):
            target.select_and_render_population(
                reused_response,
                consumed_target_keys=CONSUMED_TARGETS,
                consumed_entity_codes=OLD_ENTITIES,
                consumed_response_sha256=consumed,
            )
        with self.assertRaisesRegex(ValueError, "exact 144"):
            target.select_and_render_population(
                source,
                consumed_target_keys=CONSUMED_TARGETS,
                consumed_entity_codes=OLD_ENTITIES[:-1],
                consumed_response_sha256=CONSUMED_RESPONSES,
            )

    def test_source_is_pure_label_blind_and_has_no_evaluator_or_credit(self) -> None:
        path = ROOT / "src/deepwide_agent/v25315_disjoint_worldbank_population.py"
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
