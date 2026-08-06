from __future__ import annotations

import csv
import copy
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

from deepwide_agent import v24740_dual_representation_resilience as target  # noqa: E402


def code(index: int) -> str:
    return "".join(
        chr(ord("A") + value)
        for value in (index // 676, (index // 26) % 26, index % 26)
    )


def values(count: int, *, corrupt_index: int | None = None) -> dict[str, Decimal | None]:
    output = {
        code(index): (None if index % 19 == 0 else Decimal(f"{index}.25"))
        for index in range(count)
    }
    if corrupt_index is not None:
        output[code(corrupt_index)] = Decimal("999")
    return output


def bulk_bytes(spec: target.FreshTarget) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Data Source", "World Development Indicators", ""])
    writer.writerow([])
    writer.writerow(["Last Updated Date", "2026-01-01", ""])
    writer.writerow([])
    writer.writerow(
        ["Country Name", "Country Code", "Indicator Name", "Indicator Code", spec.year, ""]
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


def aggregate_bytes(
    spec: target.FreshTarget, *, corrupt_index: int | None = None
) -> bytes:
    rows = []
    for index, (iso3, number) in enumerate(
        values(260, corrupt_index=corrupt_index).items()
    ):
        rows.append(
            {
                "indicator": {"id": spec.indicator, "value": "Synthetic"},
                "country": {"id": iso3, "value": f"Country {index}"},
                "countryiso3code": iso3,
                "date": spec.year,
                "value": None if number is None else float(number),
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


def response_pair(
    spec: target.FreshTarget,
    *,
    preferred: bytes | None = None,
    fallback: bytes | None = None,
) -> dict[str, bytes]:
    return {
        target.endpoint_url(spec, target.PREFERRED_REPRESENTATION): (
            bulk_bytes(spec) if preferred is None else preferred
        ),
        target.endpoint_url(spec, target.FALLBACK_REPRESENTATION): (
            aggregate_bytes(spec) if fallback is None else fallback
        ),
    }


class V24740DualRepresentationResilienceTests(unittest.TestCase):
    def test_targets_match_frozen_fresh_population(self) -> None:
        self.assertEqual(
            [target.target_key(item) for item in target.TARGETS],
            ["EG.ELC.ACCS.ZS@2022", "SH.H2O.BASW.ZS@2022"],
        )
        self.assertEqual(target.REPRESENTATIONS, ("bulk_zip", "aggregate_json"))

    def test_both_valid_agree_and_preferred_is_selected(self) -> None:
        resolved = target.reconcile_target(target.TARGETS[0], response_pair(target.TARGETS[0]))
        receipt = resolved["receipt"]
        self.assertTrue(receipt["target_admitted"])
        self.assertEqual(receipt["schema_valid_representation_count"], 2)
        self.assertEqual(receipt["selected_representation"], "bulk_zip")
        self.assertTrue(receipt["dual_valid_common_value_agreement"])
        self.assertEqual(receipt["comparison"]["common_value_mismatch_count"], 0)

    def test_each_single_valid_representation_admits_without_retry(self) -> None:
        spec = target.TARGETS[0]
        preferred_only = target.reconcile_target(
            spec, response_pair(spec, fallback=b"")
        )["receipt"]
        fallback_only = target.reconcile_target(
            spec, response_pair(spec, preferred=b"")
        )["receipt"]
        self.assertTrue(preferred_only["target_admitted"])
        self.assertEqual(preferred_only["selected_representation"], "bulk_zip")
        self.assertTrue(fallback_only["target_admitted"])
        self.assertEqual(fallback_only["selected_representation"], "aggregate_json")

    def test_dual_valid_value_disagreement_abstains(self) -> None:
        spec = target.TARGETS[0]
        resolved = target.reconcile_target(
            spec,
            response_pair(spec, fallback=aggregate_bytes(spec, corrupt_index=1)),
        )
        self.assertFalse(resolved["receipt"]["target_admitted"])
        self.assertTrue(resolved["receipt"]["dual_valid_consistency_failed"])
        self.assertEqual(resolved["records"], {})

    def test_one_target_total_failure_is_isolated_from_other_target(self) -> None:
        first, second = target.TARGETS
        responses = {
            **response_pair(first, preferred=b"", fallback=b""),
            **response_pair(second),
        }
        resolved = target.reconcile_bundle(responses)
        self.assertEqual(resolved["receipt"]["admitted_target_count"], 1)
        self.assertEqual(resolved["receipt"]["abstained_target_count"], 1)
        self.assertNotIn(target.target_key(first), resolved["records_by_target"])
        self.assertIn(target.target_key(second), resolved["records_by_target"])

    def test_extra_or_missing_response_address_fails_closed(self) -> None:
        spec = target.TARGETS[0]
        responses = response_pair(spec)
        responses["https://example.invalid"] = b"x"
        with self.assertRaises(ValueError):
            target.reconcile_target(spec, responses)

    def test_resealed_receipt_consistency_tamper_fails_closed(self) -> None:
        receipt = target.reconcile_target(
            target.TARGETS[0], response_pair(target.TARGETS[0])
        )["receipt"]
        for path, replacement in (
            (("schema_valid_representation_count",), 1),
            (("selected_representation",), "aggregate_json"),
            (("comparison", "common_domain_count"), 0),
        ):
            tampered = copy.deepcopy(receipt)
            if len(path) == 1:
                tampered[path[0]] = replacement
            else:
                tampered[path[0]][path[1]] = replacement
            tampered.pop("receipt_payload_sha256")
            tampered["receipt_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(ValueError):
                target.validate_receipt(tampered)

    def test_resealed_bundle_count_tamper_fails_closed(self) -> None:
        responses = {
            url: raw
            for spec in target.TARGETS
            for url, raw in response_pair(spec).items()
        }
        resolved = target.reconcile_bundle(responses)
        tampered = copy.deepcopy(resolved["receipt"])
        tampered["admitted_target_count"] = 1
        tampered["abstained_target_count"] = 1
        tampered.pop("receipt_payload_sha256")
        tampered["receipt_payload_sha256"] = target.payload_sha256(tampered)
        with self.assertRaises(ValueError):
            target.validate_bundle_receipt(
                tampered, target_receipts=resolved["target_receipts"]
            )


if __name__ == "__main__":
    unittest.main()
