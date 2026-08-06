from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24744_cross_domain_contract as contract  # noqa: E402
from deepwide_agent import v24745_cross_domain_adapters as target  # noqa: E402


def raw(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode()


def ror_response(entity: str, suffix: str = "0abcdef12", country: str = "CA") -> bytes:
    return raw(
        {
            "number_of_results": 1,
            "items": [
                {
                    "id": f"https://ror.org/{suffix}",
                    "status": "active",
                    "names": [{"value": entity, "types": ["ror_display"]}],
                    "locations": [
                        {"geonames_details": {"country_code": country}}
                    ],
                }
            ],
        }
    )


def crossref_response(doi: str, title: str = "A Shared Title", year: int = 2020) -> bytes:
    return raw(
        {
            "status": "ok",
            "message-type": "work",
            "message-version": "1.0.0",
            "message": {
                "DOI": doi,
                "title": [title],
                "published": {"date-parts": [[year, 1, 1]]},
            },
        }
    )


def openalex_response(doi: str, title: str = "A Shared Title", year: int = 2020) -> bytes:
    return raw(
        {
            "id": "https://openalex.org/W123",
            "doi": f"https://doi.org/{doi}",
            "title": title,
            "publication_year": year,
        }
    )


class V24745CrossDomainAdapterTests(unittest.TestCase):
    def test_ror_official_exact_records_bind(self) -> None:
        task = contract.task_vector()[0]
        visible = target.visible_contract(task)
        responses = {
            target.ror_url(entity): ror_response(entity, suffix=f"0abcde{index:03d}")
            for index, entity in enumerate(visible["identities"], 1)
        }
        result = target.run_task(task, responses)
        self.assertEqual(result["receipt"]["fully_admitted_row_count"], 4)
        self.assertEqual(
            result["receipt"]["binding_receipt"]["official_admitted_cell_count"],
            8,
        )
        self.assertEqual(target.validate_result(result, task=task, responses=responses), result)

    def test_crossref_official_exact_records_bind(self) -> None:
        task = contract.task_vector()[2]
        visible = target.visible_contract(task)
        responses = {
            target.crossref_url(doi): crossref_response(doi) for doi in visible["identities"]
        }
        result = target.run_task(task, responses)
        self.assertEqual(result["receipt"]["fully_admitted_row_count"], 4)
        self.assertEqual(
            result["receipt"]["binding_receipt"]["official_admitted_cell_count"],
            8,
        )

    def test_independent_crossref_openalex_records_corroborate(self) -> None:
        task = contract.task_vector()[4]
        visible = target.visible_contract(task)
        responses = {}
        for doi in visible["identities"]:
            responses[target.crossref_url(doi)] = crossref_response(doi)
            responses[target.openalex_url(doi)] = openalex_response(doi)
        result = target.run_task(task, responses)
        self.assertEqual(result["receipt"]["fully_admitted_row_count"], 4)
        self.assertEqual(
            result["receipt"]["binding_receipt"]["corroborated_admitted_cell_count"],
            8,
        )

    def test_cross_source_value_conflict_abstains_per_cell(self) -> None:
        task = contract.task_vector()[4]
        visible = target.visible_contract(task)
        responses = {}
        for doi in visible["identities"]:
            responses[target.crossref_url(doi)] = crossref_response(doi)
            responses[target.openalex_url(doi)] = openalex_response(
                doi, title="Conflicting Title"
            )
        result = target.run_task(task, responses)
        binding = result["receipt"]["binding_receipt"]
        self.assertEqual(binding["conflicting_cell_count"], 4)
        self.assertEqual(binding["corroborated_admitted_cell_count"], 4)
        self.assertEqual(result["receipt"]["fully_admitted_row_count"], 0)
        self.assertIn("| Unknown | 2020 |", result["candidate"])

    def test_identity_mismatch_and_missing_response_abstain_or_fail_closed(self) -> None:
        task = contract.task_vector()[2]
        visible = target.visible_contract(task)
        responses = {
            target.crossref_url(doi): crossref_response("10.9999/not-the-target")
            for doi in visible["identities"]
        }
        result = target.run_task(task, responses)
        self.assertEqual(result["candidate"], result["baseline"])
        self.assertEqual(result["receipt"]["validated_record_count"], 0)
        incomplete = dict(responses)
        incomplete.pop(next(iter(incomplete)))
        with self.assertRaises(ValueError):
            target.run_task(task, incomplete)

    def test_task_or_seal_tamper_fails_closed(self) -> None:
        task = contract.task_vector()[2]
        responses = {
            target.crossref_url(doi): crossref_response(doi)
            for doi in target.visible_contract(task)["identities"]
        }
        result = target.run_task(task, responses)
        altered = copy.deepcopy(result)
        altered["receipt"]["fully_admitted_row_count"] = 0
        with self.assertRaises(ValueError):
            target.validate_result(altered)
        resealed = copy.deepcopy(result)
        resealed["receipt"]["fully_admitted_row_count"] = 0
        receipt_unsigned = dict(resealed["receipt"])
        receipt_unsigned.pop("receipt_payload_sha256")
        resealed["receipt"]["receipt_payload_sha256"] = target.payload_sha256(
            receipt_unsigned
        )
        result_unsigned = dict(resealed)
        result_unsigned.pop("result_payload_sha256")
        resealed["result_payload_sha256"] = target.payload_sha256(result_unsigned)
        with self.assertRaises(ValueError):
            target.validate_result(resealed, task=task, responses=responses)
        with self.assertRaises(ValueError):
            target.visible_contract({**task, "question_type": "doi"})


if __name__ == "__main__":
    unittest.main()
