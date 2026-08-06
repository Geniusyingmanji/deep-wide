from __future__ import annotations

import copy
import csv
import io
import sys
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24709_sparse_worldbank_adapter as adapter  # noqa: E402


def code_for(index: int) -> str:
    return "".join(
        chr(ord("A") + value)
        for value in (index // (26 * 26), (index // 26) % 26, index % 26)
    )


COUNTRIES = [(f"Example Nation {index + 1}", code_for(index)) for index in range(53)]


def question() -> str:
    return (
        "According to the statistics of the World Bank, return surface area using "
        "2022 statistics rounded to an integer, population density using 2022 "
        "statistics rounded to an integer, total population in thousand using 2023 "
        "statistics rounded to an integer, and merchandise trade using 2023 "
        "statistics rounded to one decimal place.\n\n"
        "Please output one Markdown table. The column names in the table are: "
        + ", ".join(adapter.EXPECTED_COLUMNS)
        + "."
    )


def control_prediction(value: str | tuple[str, str, str, str] = "Unknown") -> str:
    values = (value,) * 4 if isinstance(value, str) else value
    rows = [
        [name, f"Capital {index + 1}", *values]
        for index, (name, _code) in enumerate(COUNTRIES)
    ]
    return (
        "```markdown\n| "
        + " | ".join(adapter.EXPECTED_COLUMNS)
        + " |\n| "
        + " | ".join("---" for _ in adapter.EXPECTED_COLUMNS)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def bulk_archive(
    spec: adapter.TargetSpec,
    *,
    missing_code: str | None = None,
    rename_code: str | None = None,
    rename_value: str = "Different Nation",
    traversal: bool = False,
    swapped_names: bool = False,
) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Data Source", "World Development Indicators", ""])
    writer.writerow([])
    writer.writerow(["Last Updated Date", "2026-07-13", ""])
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
    values = {
        "AG.SRF.TOTL.K2": "1234.5",
        "EN.POP.DNST": "67.5",
        "SP.POP.TOTL": "2345678",
        "TG.VAL.TOTL.GD.ZS": "45.25",
    }
    for name, code in COUNTRIES:
        if swapped_names and code == COUNTRIES[0][1]:
            name = COUNTRIES[1][0]
        elif swapped_names and code == COUNTRIES[1][1]:
            name = COUNTRIES[0][0]
        writer.writerow(
            [
                rename_value if code == rename_code else name,
                code,
                "Synthetic official indicator",
                spec.indicator,
                "" if code == missing_code else values[spec.indicator],
                "",
            ]
        )
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as archive:
        member = f"API_{spec.indicator}_DS2_en_csv_v2_1.csv"
        archive.writestr("../" + member if traversal else member, output.getvalue())
    return raw.getvalue()


def bundle(**kwargs):
    return {spec.url: bulk_archive(spec, **kwargs) for spec in adapter.TARGETS}


class V24709SparseWorldBankAdapterTests(unittest.TestCase):
    def test_visible_contract_requires_exact_authority_schema_and_rounding(self) -> None:
        self.assertTrue(adapter.visible_contract_eligible(question()))
        self.assertFalse(
            adapter.visible_contract_eligible(
                question().replace("According to the statistics of the World Bank", "From public websites")
            )
        )
        self.assertFalse(
            adapter.visible_contract_eligible(
                question().replace("rounded to one decimal place", "without rounding")
            )
        )

    def test_nontrigger_is_byte_exact_and_does_not_fetch(self) -> None:
        called = False

        def forbidden(_urls):
            nonlocal called
            called = True
            raise AssertionError("nontrigger must not fetch")

        control = control_prediction()
        result = adapter.run_sparse_adapter(
            {"opaque_id": "task_" + "0" * 24, "question": "Return one table."},
            control,
            forbidden,
        )
        self.assertFalse(called)
        self.assertFalse(result["applied"])
        self.assertEqual(result["failure_reason"], "not_eligible")
        self.assertEqual(result["prediction"], control)

    def test_complete_four_bulk_bundle_changes_212_cells(self) -> None:
        observed = []

        def fetch(urls):
            observed.append(urls)
            return bundle()

        control = control_prediction()
        result = adapter.run_sparse_adapter(
            {"opaque_id": "task_" + "1" * 24, "question": question()},
            control,
            fetch,
        )
        self.assertTrue(result["applied"])
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0], tuple(spec.url for spec in adapter.TARGETS))
        self.assertEqual(result["bulk_download_count"], 4)
        self.assertEqual(result["identity_binding_count"], 53)
        self.assertEqual(result["target_value_count"], 212)
        self.assertEqual(result["changed_cell_count"], 212)
        self.assertIn("| Example Nation 1 | Capital 1 | 1235 | 68 | 2346 | 45.3 |", result["prediction"])
        self.assertNotEqual(result["prediction_sha256"], result["control_prediction_sha256"])

    def test_one_missing_target_fails_closed_without_partial_table(self) -> None:
        data = bundle()
        spec = adapter.TARGETS[-1]
        data[spec.url] = bulk_archive(spec, missing_code=COUNTRIES[-1][1])
        control = control_prediction()
        result = adapter.run_sparse_adapter(
            {"opaque_id": "task_" + "2" * 24, "question": question()},
            control,
            lambda _urls: data,
        )
        self.assertFalse(result["applied"])
        self.assertEqual(result["failure_reason"], "target_value_incomplete")
        self.assertEqual(result["prediction"], control)
        self.assertEqual(result["changed_cell_count"], 0)

    def test_numeric_format_only_differences_do_not_create_treatment(self) -> None:
        control = control_prediction(("1,235", "68", "2,346", "45.3"))
        result = adapter.run_sparse_adapter(
            {"opaque_id": "task_" + "6" * 24, "question": question()},
            control,
            lambda _urls: bundle(),
        )
        self.assertFalse(result["applied"])
        self.assertEqual(result["failure_reason"], "candidate_identity")
        self.assertEqual(result["prediction"], control)
        self.assertEqual(result["target_value_count"], 212)

    def test_cross_dataset_same_code_name_disagreement_fails_closed(self) -> None:
        data = bundle()
        spec = adapter.TARGETS[1]
        data[spec.url] = bulk_archive(
            spec,
            rename_code=COUNTRIES[0][1],
            rename_value="Example Nation One",
        )
        control = control_prediction()
        result = adapter.run_sparse_adapter(
            {"opaque_id": "task_" + "7" * 24, "question": question()},
            control,
            lambda _urls: data,
        )
        self.assertFalse(result["applied"])
        self.assertEqual(result["failure_reason"], "identity_binding_incomplete")
        self.assertEqual(result["prediction"], control)

    def test_cross_dataset_visible_name_to_different_code_fails_closed(self) -> None:
        data = bundle()
        spec = adapter.TARGETS[2]
        data[spec.url] = bulk_archive(spec, swapped_names=True)
        control = control_prediction()
        result = adapter.run_sparse_adapter(
            {"opaque_id": "task_" + "8" * 24, "question": question()},
            control,
            lambda _urls: data,
        )
        self.assertFalse(result["applied"])
        self.assertEqual(result["failure_reason"], "identity_binding_incomplete")
        self.assertEqual(result["prediction"], control)

    def test_cross_dataset_country_name_disagreement_fails_closed(self) -> None:
        data = bundle()
        spec = adapter.TARGETS[1]
        data[spec.url] = bulk_archive(spec, rename_code=COUNTRIES[0][1])
        control = control_prediction()
        result = adapter.run_sparse_adapter(
            {"opaque_id": "task_" + "3" * 24, "question": question()},
            control,
            lambda _urls: data,
        )
        self.assertFalse(result["applied"])
        self.assertEqual(result["failure_reason"], "identity_binding_incomplete")
        self.assertEqual(result["prediction"], control)

    def test_unicode_and_legal_suffix_country_matching_is_conservative(self) -> None:
        records = {
            "CIV": adapter.OfficialRow("Cote d'Ivoire", "CIV", None),
            "STP": adapter.OfficialRow("Sao Tome and Principe", "STP", None),
            "SOM": adapter.OfficialRow("Somalia, Fed. Rep.", "SOM", None),
            "COD": adapter.OfficialRow("Congo, Dem. Rep.", "COD", None),
            "COG": adapter.OfficialRow("Congo, Rep.", "COG", None),
        }
        self.assertEqual(adapter._candidate_codes("Côte d'Ivoire", records), ["CIV"])
        self.assertEqual(adapter._candidate_codes("São Tomé and Príncipe", records), ["STP"])
        self.assertEqual(adapter._candidate_codes("Somalia", records), ["SOM"])
        self.assertEqual(
            adapter._candidate_codes("Democratic Republic of the Congo", records),
            ["COD"],
        )
        self.assertEqual(adapter._candidate_codes("Republic of the Congo", records), ["COG"])
        self.assertEqual(adapter._candidate_codes("Congo", records), ["COD", "COG"])

    def test_unsafe_zip_member_and_wrong_bundle_fail_closed(self) -> None:
        spec = adapter.TARGETS[0]
        with self.assertRaisesRegex(ValueError, "unsafe ZIP"):
            adapter.parse_bulk_archive(bulk_archive(spec, traversal=True), spec)
        control = control_prediction()
        result = adapter.run_sparse_adapter(
            {"opaque_id": "task_" + "4" * 24, "question": question()},
            control,
            lambda _urls: {},
        )
        self.assertFalse(result["applied"])
        self.assertEqual(result["failure_reason"], "bulk_bundle_invalid")
        self.assertEqual(result["prediction"], control)

    def test_result_tamper_fails_closed(self) -> None:
        value = adapter.run_sparse_adapter(
            {"opaque_id": "task_" + "5" * 24, "question": "Return one table."},
            control_prediction(),
            lambda _urls: {},
        )
        tampered = copy.deepcopy(value)
        tampered["entropy_credit_assigned"] = True
        tampered.pop("result_payload_sha256")
        tampered["result_payload_sha256"] = adapter.payload_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "result drifted"):
            adapter.validate_result(tampered)


if __name__ == "__main__":
    unittest.main()
