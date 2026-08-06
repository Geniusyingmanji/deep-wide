"""Visible-only contract for V2.47.50 cross-domain binding."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24750_cross_domain_visible_contract_v1"
ROR_GROUPS = (('Politeknik TEDC Bandung', 'Akademi Kebidanan Surya Mandiri Bima', 'Salbari College', 'Charuchandra College'), ('Mediterranean Primate Research Center', 'Dynamique et Nanoenvironnement des Membranes Biologiques', 'Aligning Research to Impact Autism', 'Covenant House Toronto'))
OFFICIAL_CROSSREF_DOI_GROUPS = (('10.1038/nature12373', '10.1038/nature12443', '10.1038/s41586-020-2649-2', '10.1038/s41586-020-03113-5'), ('10.1038/s41586-022-04815-2', '10.1038/s41586-023-06004-9', '10.1126/science.1127647', '10.1126/science.1151810'))
ORDINARY_DUAL_SOURCE_DOI_GROUPS = (('10.1126/science.1201158', '10.1126/science.1260419', '10.1109/TPAMI.2008.50', '10.1109/CVPR.2015.7298594'), ('10.1145/1273442.1252032', '10.1145/1963405.1963494', '10.1016/j.cell.2012.03.034', '10.1073/pnas.0703993104'))


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
                f"v24750:{position}:{question}".encode("utf-8")
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
