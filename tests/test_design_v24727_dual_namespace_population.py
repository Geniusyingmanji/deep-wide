from __future__ import annotations

import copy
import hashlib
import io
import json
import sys
import unittest
import zipfile
from collections import Counter
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24727_dual_namespace_population as target  # noqa: E402


def canonical(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def ror_record(index: int, *, label: str | None = None, country: str = "US"):
    record_id = f"0{index:08d}"
    value = {
        "id": f"https://ror.org/{record_id}",
        "status": "active",
        "names": [
            {
                "value": label or f"Fresh Institute {index}",
                "types": ["ror_display"],
            }
        ],
        "locations": [{"geonames_details": {"country_code": country}}],
    }
    raw = json.dumps(value, separators=(",", ":")).encode()
    blob = hashlib.sha1(
        f"blob {len(raw)}\0".encode() + raw,
        usedforsecurity=False,
    ).hexdigest()
    return f"{record_id}.json", blob, raw, value


class V24727DualNamespacePopulationTests(unittest.TestCase):
    def test_ror_selection_is_disjoint_deterministic_and_country_capped(self) -> None:
        records = [
            ror_record(index, country=("US", "GB", "DE", "FR")[index % 4])
            for index in range(1, 17)
        ]
        history = {canonical("Fresh Institute 1")}
        selected, metrics = target.select_ror_records(
            records,
            historical_canonical=history,
            canonical=canonical,
            selected_count=8,
            country_cap=2,
        )
        selected_again, _ = target.select_ror_records(
            list(reversed(records)),
            historical_canonical=history,
            canonical=canonical,
            selected_count=8,
            country_cap=2,
        )
        self.assertEqual(selected, selected_again)
        self.assertNotIn("Fresh Institute 1", {item["label"] for item in selected})
        self.assertLessEqual(max(Counter(item["country"] for item in selected).values()), 2)
        self.assertEqual(metrics["selected_country_max"], 2)

    def test_worldbank_selection_is_disjoint_complete_and_group_diverse(self) -> None:
        countries = {
            f"A{chr(65 + index // 26)}{chr(65 + index % 26)}": {
                "name": f"Country {index}",
                "region_id": f"R{index % 4}",
                "region_name": f"Region {index % 4}",
            }
            for index in range(20)
        }
        snapshots = [
            {code: Decimal(index + offset) for index, code in enumerate(countries)}
            for offset in (1, 101)
        ]
        excluded = {next(iter(countries))}
        selected, metrics = target.select_worldbank_records(
            countries,
            snapshots,
            excluded=excluded,
            selected_count=8,
            region_cap=2,
        )
        self.assertEqual(len(selected), 8)
        self.assertTrue(excluded.isdisjoint(item["iso3"] for item in selected))
        self.assertEqual(metrics["minimum_distinct_regions_per_task"], 4)
        self.assertLessEqual(metrics["selected_region_max"], 2)

    def test_ror_archive_rejects_tree_or_blob_tamper(self) -> None:
        path, blob, raw, value = ror_record(1)
        tree = {
            "truncated": False,
            "tree": [
                {"path": path, "type": "blob", "sha": blob}
                for _ in range(3482)
            ],
        }
        tree["tree"] = [
            {"path": f"{index:09d}.json", "type": "blob", "sha": blob}
            for index in range(3482)
        ]
        tree["tree"][0]["sha"] = "0" * 40
        tree_raw = json.dumps(tree, separators=(",", ":")).encode()
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as archive:
            for item in tree["tree"]:
                archive.writestr(
                    f"root/{target.ROR_VERSION}/{item['path']}", raw
                )
        with patch.object(
            target,
            "ROR_TREE_SHA256",
            hashlib.sha256(tree_raw).hexdigest(),
        ):
            with self.assertRaises(RuntimeError):
                target.parse_ror_archive(tree_raw, archive_bytes.getvalue())

    def test_public_design_resealed_tamper_fails_closed(self) -> None:
        with patch.object(target, "sha256", return_value="a" * 64):
            private_ror, private_wb, public = target.build_artifacts(
                ror_records=[
                    {
                        "label": f"R {index}",
                        "record_id": f"0{index:08d}",
                        "country": "US",
                        "record_bytes_sha256": "b" * 64,
                    }
                    for index in range(target.ROR_SELECTED_COUNT)
                ],
                ror_metrics={"candidate_count": 100},
                wb_records=[
                    {
                        "name": f"C {index}",
                        "iso3": f"A{chr(65 + index // 26)}{chr(65 + index % 26)}",
                        "values": ["1", "2"],
                    }
                    for index in range(target.WB_SELECTED_COUNT)
                ],
                wb_metrics={"candidate_count": 100},
                ror_tree_response_sha256="c" * 64,
                ror_archive_response_sha256="d" * 64,
                wb_catalog_response_sha256="e" * 64,
                wb_snapshot_metadata=[],
                now=0,
                git_head="f" * 40,
            )
            self.assertFalse(private_ror["forward_import_or_runtime_read_authorized"])
            self.assertFalse(private_wb["forward_import_or_runtime_read_authorized"])
            public["clusters"]["ror"]["private_population_file_sha256"] = "1" * 64
            public["clusters"]["worldbank"]["private_population_file_sha256"] = "2" * 64
            public["design_payload_sha256"] = target.payload_sha256(public)
            target.validate_public(public)
            tampered = copy.deepcopy(public)
            tampered["authorization"]["forward_launch"] = True
            tampered.pop("design_payload_sha256")
            tampered["design_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_public(tampered)

    def test_source_policy_and_authorization_are_fail_closed(self) -> None:
        self.assertEqual(
            [f"{item['indicator']}@{item['year']}" for item in target.WB_TARGETS],
            ["IT.NET.USER.ZS@2022", "SP.DYN.LE00.IN@2022"],
        )
        self.assertEqual(target.ROR_COMMIT, "aab1443afefefa8460e69ab01bccceff0a8544d4")
        self.assertEqual(target.ROR_SELECTED_COUNT, 48)
        self.assertEqual(target.WB_SELECTED_COUNT, 48)


if __name__ == "__main__":
    unittest.main()
