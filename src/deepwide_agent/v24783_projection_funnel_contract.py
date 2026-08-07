"""Visible-only task contract for the V2.47.83 projection-funnel population."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24783_projection_funnel_external_contract_v1"
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Universitas Islam Al Azhar Gresik\n'
 "2. Gokhale Memorial Girls' College\n"
 '3. Sekolah Tinggi Ilmu Ekonomi Tri Bhakti\n'
 "4. Sekolah Tinggi Ilmu Kesehatan Al-Ma'arif Baturaja\n"
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Ekonomi Islam Kanjeng Sepuh Gresik Jawa Timur\n'
 '2. Akademi Inovasi Indonesia\n'
 '3. Institut Teknologi Sains Bandung\n'
 '4. Sekolah Tinggi Pariwisata AMPTA Yogyakarta\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Laboratoire de Géologie de Lyon : Terre, Planètes et Environnement\n'
 '2. Laboratoire de Biomécanique Appliquée\n'
 '3. Institute of Pesticide Formulation Technology\n'
 '4. Laboratoire de Microbiologie, Adaptation et Pathogénie\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. CEA Paris-Saclay\n'
 '2. Laboratoire de recherche en cardiovasculaire, métabolisme, diabétologie et nutrition\n'
 '3. Fédération des Sciences Chimiques de Marseille\n'
 '4. Institut Lumière Matière\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Cadham Provincial Laboratory\n'
 '2. Fakir Chand College\n'
 '3. Hooghly Mohsin College\n'
 '4. Government of India\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. NOAA Meteorological Development Laboratory\n'
 '2. Chhatrapati Shivaji Maharaj University\n'
 '3. Rashtrasant Tukadoji Maharaj Nagpur University\n'
 '4. International Council for Education Research and Training\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Canadian Integrated Ocean Observing System\n'
 '2. Carrier Sekani Family Services\n'
 '3. Canadian Centre on Substance Use and Addiction\n'
 '4. Canadian Integrated Ocean Observing System, Atlantic Region\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. RÉZO\n'
 '2. Canadian Association of Midwives\n'
 '3. NOAA National Centers for Environmental Prediction\n'
 '4. Ecology Action Center\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.')


def task_vector() -> list[dict[str, str]]:
    return [
        {
            "opaque_id": "task_" + hashlib.sha256(
                f"v24783:{position}:{question}".encode("utf-8")
            ).hexdigest()[:24],
            "question": question,
        }
        for position, question in enumerate(QUESTIONS, 1)
    ]


def copy_task_vector() -> list[dict[str, str]]:
    return copy.deepcopy(task_vector())


__all__ = ["POLICY_ID", "QUESTIONS", "copy_task_vector", "task_vector"]
