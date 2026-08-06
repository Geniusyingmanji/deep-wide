from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24743_generic_record_binding as target  # noqa: E402


BASELINE = """```markdown
| Item | Identifier | Year |
| --- | --- | --- |
| Alpha | Unknown | Unknown |
| Beta | keep-me | Unknown |
```"""


def record(
    ordinal: int,
    *,
    identity: str = "Alpha",
    identifier: str = "A-1",
    year: str = "2025",
    host: str = "registry.example",
    authority: str = "official_exact_record",
) -> dict:
    return target.build_record(
        record_id=f"S{ordinal:04d}",
        source_host=host,
        source_url=f"https://{host}/records/{ordinal}",
        authority=authority,
        exact_address_and_primary_identity_bound=(
            authority == "official_exact_record"
        ),
        primary_identity=identity,
        fields=[
            {"label": "Identifier", "value": identifier},
            {"label": "Year", "value": year},
        ],
    )


class V24743GenericRecordBindingTests(unittest.TestCase):
    def test_official_exact_record_fills_unknown_cells(self) -> None:
        result = target.bind_records(BASELINE, [record(1)])
        self.assertIn("| Alpha | A-1 | 2025 |", result["candidate"])
        self.assertEqual(result["receipt"]["official_admitted_cell_count"], 2)
        self.assertEqual(result["receipt"]["changed_cell_count"], 2)

    def test_two_independent_ordinary_records_corroborate(self) -> None:
        records = [
            record(1, host="one.example", authority="ordinary_structured_page"),
            record(2, host="two.example", authority="ordinary_structured_page"),
        ]
        result = target.bind_records(BASELINE, records)
        self.assertEqual(result["receipt"]["corroborated_admitted_cell_count"], 2)
        self.assertIn("| Alpha | A-1 | 2025 |", result["candidate"])

    def test_one_ordinary_source_abstains(self) -> None:
        result = target.bind_records(
            BASELINE,
            [record(1, host="one.example", authority="ordinary_structured_page")],
        )
        self.assertEqual(result["candidate"], BASELINE)
        self.assertEqual(
            result["receipt"]["insufficient_corroboration_cell_count"], 2
        )

    def test_conflicting_values_abstain_even_with_official_record(self) -> None:
        records = [
            record(1, identifier="A-1", year="2025"),
            record(2, identifier="A-2", year="2024"),
        ]
        result = target.bind_records(BASELINE, records)
        self.assertEqual(result["candidate"], BASELINE)
        self.assertEqual(result["receipt"]["conflicting_cell_count"], 2)

    def test_nonunknown_cell_is_immutable(self) -> None:
        result = target.bind_records(
            BASELINE,
            [record(1, identity="Beta", identifier="overwrite", year="2020")],
        )
        self.assertIn("| Beta | keep-me | 2020 |", result["candidate"])
        self.assertNotIn("overwrite", result["candidate"])
        self.assertEqual(
            result["receipt"]["nonunknown_immutable_proposal_count"], 1
        )

    def test_exact_visible_identity_and_field_names_are_required(self) -> None:
        wrong_identity = record(1, identity="Alpha Institute")
        wrong_field = target.build_record(
            record_id="S0002",
            source_host="registry.example",
            source_url="https://registry.example/records/2",
            authority="official_exact_record",
            exact_address_and_primary_identity_bound=True,
            primary_identity="Alpha",
            fields=[{"label": "Unrequested field", "value": "x"}],
        )
        result = target.bind_records(BASELINE, [wrong_identity, wrong_field])
        self.assertEqual(result["candidate"], BASELINE)
        self.assertEqual(result["receipt"]["unmatched_record_count"], 1)
        self.assertEqual(result["receipt"]["unmatched_field_count"], 1)

    def test_case_or_punctuation_drift_does_not_bind(self) -> None:
        case_drift = record(1, identity="alpha")
        punctuation_drift = target.build_record(
            record_id="S0002",
            source_host="registry.example",
            source_url="https://registry.example/records/2",
            authority="official_exact_record",
            exact_address_and_primary_identity_bound=True,
            primary_identity="Alpha",
            fields=[{"label": "Year.", "value": "2025"}],
        )
        result = target.bind_records(BASELINE, [case_drift, punctuation_drift])
        self.assertEqual(result["candidate"], BASELINE)
        self.assertEqual(result["receipt"]["unmatched_record_count"], 1)
        self.assertEqual(result["receipt"]["unmatched_field_count"], 1)

    def test_ambiguous_baseline_identity_fails_closed(self) -> None:
        ambiguous = BASELINE.replace(
            "| Beta | keep-me | Unknown |", "| Alpha | keep-me | Unknown |"
        )
        with self.assertRaises(ValueError):
            target.bind_records(ambiguous, [record(1)])

    def test_record_schema_and_result_tamper_fail_closed(self) -> None:
        value = record(1)
        altered = copy.deepcopy(value)
        altered["fields"][0]["value"] = "A-2"
        with self.assertRaises(ValueError):
            target.validate_record(altered)
        result = target.bind_records(BASELINE, [value])
        result["receipt"]["changed_cell_count"] = 0
        with self.assertRaises(ValueError):
            target.validate_result(result, baseline=BASELINE)

        extra = target.bind_records(BASELINE, [value])
        extra["receipt"]["unexpected"] = False
        receipt_unsigned = dict(extra["receipt"])
        receipt_unsigned.pop("receipt_payload_sha256")
        extra["receipt"]["receipt_payload_sha256"] = target.payload_sha256(
            receipt_unsigned
        )
        result_unsigned = dict(extra)
        result_unsigned.pop("result_payload_sha256")
        extra["result_payload_sha256"] = target.payload_sha256(result_unsigned)
        with self.assertRaises(ValueError):
            target.validate_result(extra, baseline=BASELINE)

    def test_result_replay_validation_terminates_and_matches(self) -> None:
        records = [record(1)]
        result = target.bind_records(BASELINE, records)
        self.assertEqual(
            target.validate_result(result, baseline=BASELINE, records=records),
            result,
        )

    def test_builder_seals_canonical_identity_fields_and_source(self) -> None:
        value = target.build_record(
            record_id="S0001",
            source_host="REGISTRY.EXAMPLE.",
            source_url="https://REGISTRY.EXAMPLE/records/1",
            authority="official_exact_record",
            exact_address_and_primary_identity_bound=True,
            primary_identity="  Alpha  ",
            fields=[{"label": "  Year ", "value": " 2025  "}],
        )
        self.assertEqual(value["source_host"], "registry.example")
        self.assertEqual(value["source_url"], "https://registry.example/records/1")
        self.assertEqual(value["primary_identity"], "Alpha")
        self.assertEqual(value["fields"], [{"label": "Year", "value": "2025"}])
        self.assertEqual(target.validate_record(value), value)

        noncanonical = copy.deepcopy(value)
        noncanonical["primary_identity"] = "  Alpha  "
        unsigned = dict(noncanonical)
        unsigned.pop("record_payload_sha256")
        noncanonical["record_payload_sha256"] = target.payload_sha256(unsigned)
        with self.assertRaises(ValueError):
            target.validate_record(noncanonical)

    def test_unsafe_value_and_source_binding_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            record(1, identifier="bad|cell")
        with self.assertRaises(ValueError):
            target.build_record(
                record_id="S0001",
                source_host="localhost",
                source_url="https://localhost/record/1",
                authority="official_exact_record",
                exact_address_and_primary_identity_bound=True,
                primary_identity="Alpha",
                fields=[{"label": "Year", "value": "2025"}],
            )
        with self.assertRaises(ValueError):
            target.build_record(
                record_id="S0001",
                source_host="one.example",
                source_url="https://two.example/record/1",
                authority="official_exact_record",
                exact_address_and_primary_identity_bound=True,
                primary_identity="Alpha",
                fields=[{"label": "Year", "value": "2025"}],
            )


if __name__ == "__main__":
    unittest.main()
