from __future__ import annotations

import csv
import io
import json
import sys
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24735_dual_namespace_reachability as target  # noqa: E402
from deepwide_agent import v24724_fresh_indicator_transport as wb  # noqa: E402
from deepwide_agent.v24648_unknown_target_structured_runtime import exact_lookup_url  # noqa: E402
from deepwide_agent.v24733_dual_namespace_contract import task_vector  # noqa: E402


def ror_response(entity: str, suffix: str, country: str, *, duplicate: bool = False) -> bytes:
    item = {
        "id": f"https://ror.org/{suffix}",
        "status": "active",
        "names": [{"value": entity, "types": ["ror_display"]}],
        "locations": [{"geonames_details": {"country_code": country}}],
    }
    items = [item, {**item, "id": "https://ror.org/099999999"}] if duplicate else [item]
    return json.dumps(
        {"number_of_results": len(items), "items": items}, separators=(",", ":")
    ).encode()


def bulk(target_spec: wb.FreshTarget, values: dict[str, str]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Data Source", "World Development Indicators", ""])
    writer.writerow([])
    writer.writerow(["Last Updated Date", "2026-08-01", ""])
    writer.writerow([])
    writer.writerow(["Country Name", "Country Code", "Indicator Name", "Indicator Code", target_spec.year, ""])
    codes = list(values)
    for index in range(265 - len(codes)):
        code = f"{chr(65 + index // 676)}{chr(65 + (index // 26) % 26)}{chr(65 + index % 26)}"
        if code in values:
            continue
        codes.append(code)
    if len(codes) < 265:
        index = 265
        while len(codes) < 265:
            code = f"{chr(65 + index // 676)}{chr(65 + (index // 26) % 26)}{chr(65 + index % 26)}"
            if code not in values:
                codes.append(code)
            index += 1
    for index, code in enumerate(codes):
        writer.writerow([f"Country {index}", code, "Synthetic", target_spec.indicator, values.get(code, str(index + 1)), ""])
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"API_{target_spec.indicator}_DS2_en_csv_v2_1.csv", output.getvalue().encode())
    return raw.getvalue()


class V24735DualNamespaceReachabilityTests(unittest.TestCase):
    def test_request_vectors_derive_only_from_visible_question(self) -> None:
        ror_task, wb_task = task_vector()[0], task_vector()[12]
        self.assertEqual(len(target.request_urls(ror_task)), 4)
        self.assertTrue(all(url.startswith("https://api.ror.org/v2/organizations?") for url in target.request_urls(ror_task)))
        self.assertEqual(len(target.request_urls(wb_task)), 2)
        self.assertTrue(all("downloadformat=csv" in url for url in target.request_urls(wb_task)))

    def test_ror_exact_identity_and_country_change_candidate(self) -> None:
        task = task_vector()[0]
        entities = target.ror_entities(task["question"])
        responses = {
            exact_lookup_url(entity): ror_response(entity, f"0{index:08d}", "US")
            for index, entity in enumerate(entities, 1)
        }
        result = target.run_task(task, responses)
        self.assertTrue(result["receipt"]["prediction_changed"])
        self.assertEqual(result["receipt"]["primary_identity_bound_target_count"], 4)
        self.assertEqual(result["receipt"]["changed_cell_count"], 8)

    def test_ror_ambiguous_or_wrong_identity_abstains(self) -> None:
        task = task_vector()[0]
        entities = target.ror_entities(task["question"])
        responses = {
            exact_lookup_url(entity): ror_response(
                "Wrong Entity" if index == 0 else entity,
                f"0{index + 1:08d}",
                "US",
                duplicate=index == 1,
            )
            for index, entity in enumerate(entities)
        }
        result = target.run_task(task, responses)
        self.assertEqual(result["receipt"]["primary_identity_bound_target_count"], 2)
        self.assertEqual(result["receipt"]["changed_cell_count"], 4)

    def test_worldbank_complete_bulk_bundle_changes_all_visible_cells(self) -> None:
        task = task_vector()[12]
        codes = [country[1] for country in __import__("deepwide_agent.v24733_dual_namespace_contract", fromlist=["WORLD_BANK_COUNTRY_GROUPS"]).WORLD_BANK_COUNTRY_GROUPS[0]]
        responses = {
            wb.endpoint_url(spec, wb.PRIMARY_REPRESENTATION): bulk(
                spec, {code: f"{index + 1}.25" for index, code in enumerate(codes)}
            )
            for spec in wb.TARGETS
        }
        result = target.run_task(task, responses)
        self.assertTrue(result["receipt"]["bulk_bundle_complete"])
        self.assertEqual(result["receipt"]["primary_identity_bound_target_count"], 4)
        self.assertEqual(result["receipt"]["changed_cell_count"], 8)

    def test_worldbank_invalid_bundle_does_not_admit_its_values(self) -> None:
        task = task_vector()[12]
        urls = target.request_urls(task)
        responses = {
            urls[0]: bulk(wb.TARGETS[0], {}),
            urls[1]: b"truncated",
        }
        result = target.run_task(task, responses)
        self.assertFalse(result["receipt"]["bulk_bundle_complete"])
        self.assertEqual(result["receipt"]["schema_valid_response_count"], 1)
        self.assertEqual(result["receipt"]["primary_identity_bound_target_count"], 0)
        self.assertEqual(result["receipt"]["changed_cell_count"], 0)

    def test_result_tamper_and_extra_response_fail_closed(self) -> None:
        task = task_vector()[0]
        entities = target.ror_entities(task["question"])
        responses = {
            exact_lookup_url(entity): ror_response(entity, f"0{index:08d}", "US")
            for index, entity in enumerate(entities, 1)
        }
        with self.assertRaises(ValueError):
            target.run_task(task, {**responses, "https://example.org/": b"x"})
        result = target.run_task(task, responses)
        result["receipt"]["changed_cell_count"] = 0
        with self.assertRaises(ValueError):
            target.validate_result(result)


if __name__ == "__main__":
    unittest.main()
