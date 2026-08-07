"""Visible-only contract for the V2.47.60 zero-effect external gate."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24760_zero_effect_external_visible_contract_v1"
ENTITY_GROUPS = (('Institut Kesehatan Karsa Husada Garut',
  'Sekolah Tinggi Ilmu Hukum Muhammadiyah Takengon',
  'Sekolah Tinggi Ilmu Sosial dan Ilmu Politik Wira Bhakti Denpasar',
  'Biju Patnaik University of Technology'),
 ('Akademi Keperawatan Buntet Pesantren Cirebon',
  'Sekolah Tinggi Ilmu Tarbiyah Ahlussunnah Bukittinggi',
  'Sekolah Tinggi Ilmu Ekonomi Kertanegara Malang',
  'STAI Ali bin Abi Thalib Surabaya'),
 ('Institut Citra Internasional',
  'STIQ Miftahul Huda Rawalo Banyumas',
  'Akademi Pariwisata Dharma Nusantara Sakti',
  'Universitas PGRI Argopuro Jember'),
 ('Chhatrapati Shahu Ji Maharaj University',
  'Gujarat Technological University',
  'Scottish Church College',
  'UBC Centre for Health Services and Policy Research'),
 ('Government Dental College and Hospital Vijayawada',
  'Bodoland University',
  'D. Y. Patil Agriculture and Technical University',
  'D.A.V. College Chandigarh'),
 ('Deen Dayal Upadhyaya College',
  'Calcutta Institute of Technology',
  'Christ Academy Institute for Advanced Studies',
  'Université Grenoble Alpes'),
 ('Cooperative Institute for Research to Operations in Hydrology',
  'Université de Lyon',
  "L'Institut Agro",
  'Gilmour Academy'),
 ('Observatoire de Lyon',
  'La Rochelle Université',
  'Technische Universität Dresden',
  'Alliant University'))
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Institut Kesehatan Karsa Husada Garut\n'
 '2. Sekolah Tinggi Ilmu Hukum Muhammadiyah Takengon\n'
 '3. Sekolah Tinggi Ilmu Sosial dan Ilmu Politik Wira Bhakti Denpasar\n'
 '4. Biju Patnaik University of Technology\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Akademi Keperawatan Buntet Pesantren Cirebon\n'
 '2. Sekolah Tinggi Ilmu Tarbiyah Ahlussunnah Bukittinggi\n'
 '3. Sekolah Tinggi Ilmu Ekonomi Kertanegara Malang\n'
 '4. STAI Ali bin Abi Thalib Surabaya\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Institut Citra Internasional\n'
 '2. STIQ Miftahul Huda Rawalo Banyumas\n'
 '3. Akademi Pariwisata Dharma Nusantara Sakti\n'
 '4. Universitas PGRI Argopuro Jember\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Chhatrapati Shahu Ji Maharaj University\n'
 '2. Gujarat Technological University\n'
 '3. Scottish Church College\n'
 '4. UBC Centre for Health Services and Policy Research\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Government Dental College and Hospital Vijayawada\n'
 '2. Bodoland University\n'
 '3. D. Y. Patil Agriculture and Technical University\n'
 '4. D.A.V. College Chandigarh\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Deen Dayal Upadhyaya College\n'
 '2. Calcutta Institute of Technology\n'
 '3. Christ Academy Institute for Advanced Studies\n'
 '4. Université Grenoble Alpes\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Cooperative Institute for Research to Operations in Hydrology\n'
 '2. Université de Lyon\n'
 "3. L'Institut Agro\n"
 '4. Gilmour Academy\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Observatoire de Lyon\n'
 '2. La Rochelle Université\n'
 '3. Technische Universität Dresden\n'
 '4. Alliant University\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.')


def task_vector() -> list[dict[str, str]]:
    return [
        {
            "opaque_id": "task_" + hashlib.sha256(
                f"v24760:{position}:{question}".encode("utf-8")
            ).hexdigest()[:24],
            "question": question,
        }
        for position, question in enumerate(QUESTIONS, 1)
    ]


def copy_task_vector() -> list[dict[str, str]]:
    return copy.deepcopy(task_vector())


__all__ = ["ENTITY_GROUPS", "POLICY_ID", "QUESTIONS", "copy_task_vector", "task_vector"]
