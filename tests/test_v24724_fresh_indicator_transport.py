from __future__ import annotations

import csv
import io
import json
import sys
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24724_fresh_indicator_transport as target  # noqa: E402


def code(index: int) -> str:
    return "".join(
        chr(ord("A") + value)
        for value in (index // 676, (index // 26) % 26, index % 26)
    )


def values(count: int) -> dict[str, Decimal | None]:
    return {
        code(index): (None if index % 19 == 0 else Decimal(f"{index}.25"))
        for index in range(count)
    }


def bulk_bytes(spec: target.FreshTarget) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Data Source", "World Development Indicators", ""])
    writer.writerow([])
    writer.writerow(["Last Updated Date", "2026-01-01", ""])
    writer.writerow([])
    writer.writerow(
        [
            "Country Name",
            "Country Code",
            "Indicator Name",
            "Indicator Code",
            spec.year,
            "",
        ]
    )
    for index, (iso3, number) in enumerate(values(265).items()):
        writer.writerow(
            [
                f"Country {index}",
                iso3,
                "Synthetic",
                spec.indicator,
                "" if number is None else format(number, "f"),
                "",
            ]
        )
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            f"API_{spec.indicator}_DS2_en_csv_v2_1.csv", output.getvalue().encode()
        )
    return raw.getvalue()


def aggregate_bytes(spec: target.FreshTarget, *, corrupt: bool = False) -> bytes:
    rows = []
    for index, (iso3, number) in enumerate(values(260).items()):
        if corrupt and index == 1:
            number = Decimal("999")
        rows.append(
            {
                "indicator": {"id": spec.indicator, "value": "Synthetic"},
                "country": {"id": iso3, "value": f"Country {index}"},
                "countryiso3code": iso3,
                "date": spec.year,
                "value": None if number is None else float(number),
            }
        )
    rows.append(
        {
            "indicator": {"id": spec.indicator},
            "countryiso3code": "",
            "date": spec.year,
            "value": 1,
        }
    )
    return json.dumps(
        [
            {
                "page": 1,
                "pages": 1,
                "per_page": 400,
                "total": len(rows),
                "lastupdated": "2026-01-01",
            },
            rows,
        ],
        separators=(",", ":"),
    ).encode()


class V24724FreshIndicatorTransportTests(unittest.TestCase):
    def test_targets_match_sealed_fresh_design(self) -> None:
        self.assertEqual(
            [target.target_key(item) for item in target.TARGETS],
            ["IT.NET.USER.ZS@2022", "SP.DYN.LE00.IN@2022"],
        )
        self.assertEqual(target.PRIMARY_REPRESENTATION, "bulk_zip")

    def test_primary_and_comparator_keep_domain_difference_separate(self) -> None:
        spec = target.TARGETS[0]
        primary, _ = target.parse_records(
            bulk_bytes(spec), target=spec, representation="bulk_zip"
        )
        comparator, _ = target.parse_records(
            aggregate_bytes(spec), target=spec, representation="aggregate_json"
        )
        comparison = target.compare_domains(primary, comparator)
        self.assertEqual(comparison["primary_record_count"], 265)
        self.assertEqual(comparison["comparator_record_count"], 260)
        self.assertEqual(comparison["common_domain_count"], 260)
        self.assertEqual(comparison["primary_only_domain_count"], 5)
        self.assertEqual(comparison["comparator_only_domain_count"], 0)
        self.assertEqual(comparison["common_value_mismatch_count"], 0)

    def test_common_value_corruption_is_not_hidden_by_domain_difference(self) -> None:
        spec = target.TARGETS[1]
        primary, _ = target.parse_records(
            bulk_bytes(spec), target=spec, representation="bulk_zip"
        )
        comparator, _ = target.parse_records(
            aggregate_bytes(spec, corrupt=True),
            target=spec,
            representation="aggregate_json",
        )
        self.assertEqual(
            target.compare_domains(primary, comparator)["common_value_mismatch_count"],
            1,
        )

    def test_truncated_and_duplicate_json_fail_closed(self) -> None:
        spec = target.TARGETS[0]
        with self.assertRaises(ValueError):
            target.parse_response(
                aggregate_bytes(spec)[:50],
                target=spec,
                representation="aggregate_json",
            )
        payload = json.loads(aggregate_bytes(spec))
        payload[1].append(dict(payload[1][0]))
        payload[0]["total"] += 1
        with self.assertRaises(ValueError):
            target.parse_response(
                json.dumps(payload).encode(),
                target=spec,
                representation="aggregate_json",
            )


if __name__ == "__main__":
    unittest.main()
