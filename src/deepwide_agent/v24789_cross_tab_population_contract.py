"""Visible-only task contract for the V2.47.89 cross-tab population."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24789_cross_tab_external_contract_v1"
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Teologi Ekumene Jakarta\n'
 '2. Universitas Teknologi Akba Makassar\n'
 '3. Sekolah Tinggi Teologi Tabernakel Indonesia\n'
 '4. Heartfulness Institute\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Politeknik ATK Yogyakarta\n'
 '2. Institut Agama Islam Miftahul Ulum Tanjungpinang\n'
 '3. Sekolah Tinggi Ilmu Kesehatan RS Husada\n'
 '4. Politeknik Surabaya\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Kementerian Pariwisata\n'
 '2. Politeknik ATI Padang\n'
 '3. Poltekkes Kemenkes Bengkulu\n'
 "4. Centre d'Énergétique et de Thermique de Lyon\n"
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Halton Region Health Department\n'
 '2. Ingenierie des Materiaux polymeres\n'
 '3. Centre de Recherche en Neurosciences de Lyon\n'
 '4. Urumu Dhanalakshmi College\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sciences, Normes, Démocratie\n'
 '2. University of Gour Banga\n'
 '3. Laboratoire de Sciences Actuarielle et Financière\n'
 '4. Sciences, Société, Historicité, Éducation et Pratiques\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. AISTROSIGHT: La pharmacologie des neurones et des astrocytes à l’aide des sciences du '
 'numérique\n'
 "2. Institut des langues et cultures d'Europe, Amérique, Afrique, Asie et Australie\n"
 '3. Aditya Institute of Technology and Management\n'
 '4. Hiralal Mazumdar Memorial College for Women\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Infections Virales et Pathologie Comparée\n'
 '2. Shree Dhanvantary Pharmacy College\n'
 '3. Apex University, Jaipur\n'
 "4. Institut National de Recherche pour l'Agriculture, l'Alimentation et l'Environnement\n"
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Maulana Abul Kalam Azad University of Technology, West Bengal\n'
 '2. Kendrapara Autonomous College\n'
 '3. Dr Baba Saheb Ambedkar Hospital\n'
 '4. Four Arrows Regional Health Authority\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.')


def task_vector() -> list[dict[str, str]]:
    return [
        {
            "opaque_id": "task_" + hashlib.sha256(
                f"v24789:{position}:{question}".encode("utf-8")
            ).hexdigest()[:24],
            "question": question,
        }
        for position, question in enumerate(QUESTIONS, 1)
    ]


def copy_task_vector() -> list[dict[str, str]]:
    return copy.deepcopy(task_vector())


__all__ = ["POLICY_ID", "QUESTIONS", "copy_task_vector", "task_vector"]
