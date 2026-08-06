"""Visible-only contract for V2.47.44 cross-domain binding."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24744_cross_domain_visible_contract_v1"
ROR_GROUPS = (('Sekolah Tinggi Maritim Yogyakarta', 'College of Nurses of Ontario', 'Institut Muslim Cendekia', 'Sudhir Heart Centre'), ('Unité des Virus Emergents', 'Roswell Park Comprehensive Cancer Center', 'The Arctic Institute Center for Circumpolar Security Studies', "Laboratoire d'Automatique, de Génie des Procédés et de Génie Pharmaceutique"))
OFFICIAL_CROSSREF_DOI_GROUPS = (('10.1038/171737a0', '10.1038/227680a0', '10.1038/35057062', '10.1038/nature14539'), ('10.1038/nature16961', '10.1038/s41586-018-0337-2', '10.1038/s41586-021-03819-2', '10.1126/science.1058040'))
ORDINARY_DUAL_SOURCE_DOI_GROUPS = (('10.1126/science.169.3946.635', '10.1126/science.286.5439.509', '10.1109/5.771073', '10.1109/CVPR.2016.90'), ('10.1145/1327452.1327492', '10.1145/2939672.2939785', '10.1016/j.cell.2011.02.013', '10.1073/pnas.0506580102'))


def _ror_question(group: tuple[str, ...]) -> str:
    rows = "\n".join(f"{index}. {value}" for index, value in enumerate(group, 1))
    return (
        "Use public registry records to complete one Markdown table.\n"
        "<ENTITIES>\n" + rows + "\n</ENTITIES>\n"
        "The column names are: Organization, ROR ID, Country code. "
        "Use the 9-character ROR suffix and ISO 3166-1 alpha-2 code. "
        "Use Unknown when an exact structured record is unavailable."
    )


def _doi_question(group: tuple[str, ...], *, ordinary: bool) -> str:
    rows = "\n".join(f"{index}. {value}" for index, value in enumerate(group, 1))
    evidence = (
        "Require the same value from the Crossref and OpenAlex structured records."
        if ordinary
        else "Use the exact-address Crossref registry record."
    )
    return (
        "Use public structured records to complete one Markdown table.\n"
        "<DOIS>\n" + rows + "\n</DOIS>\n"
        "The column names are: DOI, Title, Year. " + evidence + " "
        "Use Unknown when the required structured support is unavailable."
    )


QUESTIONS = tuple(_ror_question(group) for group in ROR_GROUPS) + tuple(
    _doi_question(group, ordinary=False) for group in OFFICIAL_CROSSREF_DOI_GROUPS
) + tuple(
    _doi_question(group, ordinary=True) for group in ORDINARY_DUAL_SOURCE_DOI_GROUPS
)


def task_vector() -> list[dict[str, str]]:
    return [
        {
            "opaque_id": "task_" + hashlib.sha256(
                f"v24744:{position}:{question}".encode("utf-8")
            ).hexdigest()[:24],
            "question": question,
        }
        for position, question in enumerate(QUESTIONS, 1)
    ]


def copy_task_vector() -> list[dict[str, str]]:
    return copy.deepcopy(task_vector())


__all__ = [
    "OFFICIAL_CROSSREF_DOI_GROUPS",
    "ORDINARY_DUAL_SOURCE_DOI_GROUPS",
    "POLICY_ID",
    "QUESTIONS",
    "ROR_GROUPS",
    "copy_task_vector",
    "task_vector",
]
