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

from deepwide_agent import v24719_worldbank_transport_reliability as target  # noqa: E402


def code(index: int) -> str:
    return "".join(
        chr(ord("A") + value)
        for value in (index // (26 * 26), (index // 26) % 26, index % 26)
    )


def records() -> dict[str, Decimal | None]:
    return {
        code(index): (None if index % 17 == 0 else Decimal(f"{index}.50"))
        for index in range(205)
    }


def aggregate_bytes(target_spec: target.TransportTarget) -> bytes:
    rows = [
        {
            "indicator": {"id": target_spec.indicator, "value": "Synthetic"},
            "country": {"id": value, "value": f"Country {index}"},
            "countryiso3code": value,
            "date": target_spec.year,
            "value": (None if number is None else float(number)),
            "unit": "",
            "obs_status": "",
            "decimal": 1,
        }
        for index, (value, number) in enumerate(records().items())
    ]
    rows.append(
        {
            "indicator": {"id": target_spec.indicator, "value": "Synthetic"},
            "country": {"id": "", "value": "Aggregate"},
            "countryiso3code": "",
            "date": target_spec.year,
            "value": 1,
            "unit": "",
            "obs_status": "",
            "decimal": 1,
        }
    )
    return json.dumps(
        [
            {
                "page": 1,
                "pages": 1,
                "per_page": 400,
                "total": len(rows),
                "sourceid": "2",
                "lastupdated": "2026-01-01",
            },
            rows,
        ],
        separators=(",", ":"),
    ).encode()


def bulk_bytes(target_spec: target.TransportTarget) -> bytes:
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
            target_spec.year,
            "",
        ]
    )
    for index, (value, number) in enumerate(records().items()):
        writer.writerow(
            [
                f"Country {index}",
                value,
                "Synthetic",
                target_spec.indicator,
                "" if number is None else format(number, "f"),
                "",
            ]
        )
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            f"API_{target_spec.indicator}_DS2_en_csv_v2_1.csv",
            output.getvalue().encode(),
        )
    return raw.getvalue()


class V24719WorldBankTransportReliabilityTests(unittest.TestCase):
    def test_endpoint_vector_is_exact_and_credential_free(self) -> None:
        urls = {
            target.endpoint_url(spec, representation)
            for spec in target.TARGETS
            for representation in target.REPRESENTATIONS
        }
        self.assertEqual(len(urls), 12)
        self.assertTrue(all(url.startswith("https://api.worldbank.org/") for url in urls))
        self.assertTrue(all("@" not in url for url in urls))

    def test_bulk_and_json_vectors_are_semantically_equal(self) -> None:
        spec = target.TARGETS[0]
        bulk_raw = bulk_bytes(spec)
        json_raw = aggregate_bytes(spec)
        bulk_meta = target.parse_response(
            bulk_raw, target=spec, representation="bulk_zip"
        )
        json_meta = target.parse_response(
            json_raw, target=spec, representation="aggregate_json"
        )
        self.assertEqual(bulk_meta["semantic_sha256"], json_meta["semantic_sha256"])
        target.validate_parsed(bulk_meta)
        target.validate_parsed(json_meta)
        left, _ = target.parse_records(bulk_raw, target=spec, representation="bulk_zip")
        right, _ = target.parse_records(
            json_raw, target=spec, representation="aggregate_json"
        )
        comparison = target.compare_record_vectors(left, right)
        self.assertEqual(comparison["common_value_mismatch_count"], 0)
        self.assertEqual(comparison["symmetric_difference_count"], 0)
        self.assertFalse(comparison["content_persisted"])

    def test_truncated_or_wrong_target_json_fails_closed(self) -> None:
        spec = target.TARGETS[1]
        with self.assertRaises(ValueError):
            target.parse_response(
                aggregate_bytes(spec)[:100],
                target=spec,
                representation="aggregate_json",
            )
        payload = json.loads(aggregate_bytes(spec))
        payload[1][0]["indicator"]["id"] = "WRONG.ID"
        with self.assertRaises(ValueError):
            target.parse_response(
                json.dumps(payload).encode(),
                target=spec,
                representation="aggregate_json",
            )

    def test_too_few_records_and_tampered_receipt_fail_closed(self) -> None:
        spec = target.TARGETS[2]
        payload = json.loads(aggregate_bytes(spec))
        payload[1] = payload[1][:100]
        payload[0]["total"] = 100
        with self.assertRaises(ValueError):
            target.parse_response(
                json.dumps(payload).encode(),
                target=spec,
                representation="aggregate_json",
            )
        valid = target.parse_response(
            aggregate_bytes(spec), target=spec, representation="aggregate_json"
        )
        valid["response_content_persisted"] = True
        with self.assertRaises(ValueError):
            target.validate_parsed(valid)

    def test_aggregate_metadata_and_duplicate_iso_fail_closed(self) -> None:
        spec = target.TARGETS[3]
        payload = json.loads(aggregate_bytes(spec))
        payload[0]["pages"] = 2
        with self.assertRaises(ValueError):
            target.parse_response(
                json.dumps(payload).encode(),
                target=spec,
                representation="aggregate_json",
            )
        payload = json.loads(aggregate_bytes(spec))
        duplicate = dict(payload[1][0])
        payload[1].append(duplicate)
        payload[0]["total"] += 1
        with self.assertRaises(ValueError):
            target.parse_response(
                json.dumps(payload).encode(),
                target=spec,
                representation="aggregate_json",
            )

    def test_runtime_source_has_no_effect_capability(self) -> None:
        source = (ROOT / "src/deepwide_agent/v24719_worldbank_transport_reliability.py").read_text()
        for forbidden in (
            "urllib.request",
            "requests",
            "subprocess",
            "socket",
            "ground_truth",
            "question_type",
            "instance_id",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
