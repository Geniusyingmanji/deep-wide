"""Visible-only contract for the V2.47.74 fair-recovery external gate."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24774_visible_entity_fair_external_contract_v1"
ENTITY_GROUPS = (('Institut Kesehatan Payung Negeri Pekanbaru',
  'Sekolah Tinggi Ilmu Ekonomi Bhakti Pembangunan',
  'Indonesian Institute for Corporate Learning and Studies',
  'Sekolah Tinggi Teologi Sola Gratia Indonesia'),
 ('Universitas Dharma Andalas',
  'Sekolah Tinggi Diakones HKBP',
  'Sekolah Tinggi Agama Islam Ki Ageng Pekalongan',
  'Institut Ahmad Dahlan Probolinggo'),
 ('Sekolah Tinggi Ilmu Ekonomi Makassar Bongaya',
  'Politeknik ATI Makassar',
  'Sekolah Tinggi Filsafat Driyarkara',
  'Rajendra University, Balangir'),
 ('Akademi Keperawatan Kesdam I/Bukit Barisan Padang',
  'Universitas Islam Nusantara Al-Azhaar Lubuklinggau',
  'Sekolah Tinggi Penerbangan Aviasi',
  'Sekolah Tinggi Keguruan dan Ilmu Pendidikan Melawi'),
 ('Sekolah Tinggi Analis Bakti Asih',
  "St. Stephen's College",
  'Gurudas College',
  'Kishkinda University'),
 ('Gurucharan University',
  'Amrutvahini Polytechnic Sangamner',
  'Utkal University',
  'Dinabandhu Andrews College'),
 ('Vidyasagar University',
  'Hemwati Nandan Bahuguna Uttarakhand Medical Education University',
  'Jagadguru Kripalu University',
  'Midnapore City College'),
 ('Gauhati University',
  'Kammavari Sangham Institute of Technology',
  'Jawaharlal Nehru Technological University, Hyderabad',
  'Shri Madhwa Vadiraja Institute of Technology and Management'))
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Institut Kesehatan Payung Negeri Pekanbaru\n'
 '2. Sekolah Tinggi Ilmu Ekonomi Bhakti Pembangunan\n'
 '3. Indonesian Institute for Corporate Learning and Studies\n'
 '4. Sekolah Tinggi Teologi Sola Gratia Indonesia\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Universitas Dharma Andalas\n'
 '2. Sekolah Tinggi Diakones HKBP\n'
 '3. Sekolah Tinggi Agama Islam Ki Ageng Pekalongan\n'
 '4. Institut Ahmad Dahlan Probolinggo\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Ilmu Ekonomi Makassar Bongaya\n'
 '2. Politeknik ATI Makassar\n'
 '3. Sekolah Tinggi Filsafat Driyarkara\n'
 '4. Rajendra University, Balangir\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Akademi Keperawatan Kesdam I/Bukit Barisan Padang\n'
 '2. Universitas Islam Nusantara Al-Azhaar Lubuklinggau\n'
 '3. Sekolah Tinggi Penerbangan Aviasi\n'
 '4. Sekolah Tinggi Keguruan dan Ilmu Pendidikan Melawi\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Analis Bakti Asih\n'
 "2. St. Stephen's College\n"
 '3. Gurudas College\n'
 '4. Kishkinda University\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Gurucharan University\n'
 '2. Amrutvahini Polytechnic Sangamner\n'
 '3. Utkal University\n'
 '4. Dinabandhu Andrews College\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Vidyasagar University\n'
 '2. Hemwati Nandan Bahuguna Uttarakhand Medical Education University\n'
 '3. Jagadguru Kripalu University\n'
 '4. Midnapore City College\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Gauhati University\n'
 '2. Kammavari Sangham Institute of Technology\n'
 '3. Jawaharlal Nehru Technological University, Hyderabad\n'
 '4. Shri Madhwa Vadiraja Institute of Technology and Management\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.')


def task_vector() -> list[dict[str, str]]:
    return [
        {
            "opaque_id": "task_" + hashlib.sha256(
                f"v24774:{position}:{question}".encode("utf-8")
            ).hexdigest()[:24],
            "question": question,
        }
        for position, question in enumerate(QUESTIONS, 1)
    ]


def copy_task_vector() -> list[dict[str, str]]:
    return copy.deepcopy(task_vector())


__all__ = ["ENTITY_GROUPS", "POLICY_ID", "QUESTIONS", "copy_task_vector", "task_vector"]
