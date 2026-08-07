"""Visible-only contract for the V2.47.79 staged-fallback mechanism gate."""

from __future__ import annotations

import copy
import hashlib


POLICY_ID = "v24779_staged_fallback_external_contract_v1"
ENTITY_GROUPS = (('Sekolah Tinggi Teologi Moriah',
  'Sekolah Tinggi Teologi Cipanas',
  'Universitas Billfath',
  'Universitas Qomaruddin'),
 ("Politeknik 'Aisyiyah Sumatera Barat",
  'Sekolah Tinggi Agama Islam Tanbihul Ghofilin Banjarnegara',
  'Sekolah Tinggi Ilmu Kesehatan Brebes',
  'Sekolah Tinggi Teologi Galilea Indonesia'),
 ('Tanri Abeng University',
  'Sekolah Tinggi Ilmu Kesehatan Tri Mandiri Sakti Bengkulu',
  'Sekolah Tinggi Ilmu Administrasi Adabiah',
  'Sekolah Tinggi Manajemen Informatika dan Komputer Syaikh Zainuddin Nahdlatul Wathan Anjani'),
 ('Institut Binamadani Indonesia',
  'Politeknik Ilmu Pelayaran Makassar',
  'Universitas Al-Qolam Malang',
  'Sekolah Tinggi Teologi Bandung'),
 ('Raiganj Surendranath Mahavidyalaya',
  'IMS Ghaziabad',
  'Vikrant University',
  'Government Doon Medical College'),
 ('University of Burdwan',
  'Bharathidasan University',
  'Dibrugarh University',
  'Gandhi Institute for Technological Advancement'),
 ('Meghnad Saha Institute of Technology',
  'Chandernagore College',
  'Kusum Devi Sunderlal Dugar Jain Dental College & Hospital',
  'Christ Church College, Kanpur'),
 ('Nalla Malla Reddy Engineering College',
  'Asian School of Business',
  'Tamil Nadu Dr. M.G.R. Medical University',
  'Government Siddha Medical College & Hospital Palayamkottai'))
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Teologi Moriah\n'
 '2. Sekolah Tinggi Teologi Cipanas\n'
 '3. Universitas Billfath\n'
 '4. Universitas Qomaruddin\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 "1. Politeknik 'Aisyiyah Sumatera Barat\n"
 '2. Sekolah Tinggi Agama Islam Tanbihul Ghofilin Banjarnegara\n'
 '3. Sekolah Tinggi Ilmu Kesehatan Brebes\n'
 '4. Sekolah Tinggi Teologi Galilea Indonesia\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Tanri Abeng University\n'
 '2. Sekolah Tinggi Ilmu Kesehatan Tri Mandiri Sakti Bengkulu\n'
 '3. Sekolah Tinggi Ilmu Administrasi Adabiah\n'
 '4. Sekolah Tinggi Manajemen Informatika dan Komputer Syaikh Zainuddin Nahdlatul Wathan Anjani\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Institut Binamadani Indonesia\n'
 '2. Politeknik Ilmu Pelayaran Makassar\n'
 '3. Universitas Al-Qolam Malang\n'
 '4. Sekolah Tinggi Teologi Bandung\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Raiganj Surendranath Mahavidyalaya\n'
 '2. IMS Ghaziabad\n'
 '3. Vikrant University\n'
 '4. Government Doon Medical College\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. University of Burdwan\n'
 '2. Bharathidasan University\n'
 '3. Dibrugarh University\n'
 '4. Gandhi Institute for Technological Advancement\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Meghnad Saha Institute of Technology\n'
 '2. Chandernagore College\n'
 '3. Kusum Devi Sunderlal Dugar Jain Dental College & Hospital\n'
 '4. Christ Church College, Kanpur\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Nalla Malla Reddy Engineering College\n'
 '2. Asian School of Business\n'
 '3. Tamil Nadu Dr. M.G.R. Medical University\n'
 '4. Government Siddha Medical College & Hospital Palayamkottai\n'
 '</ENTITIES>\n'
 'The column names are: Organization, Founded, Country. Use a four-digit founding year and the '
 'English country name. Use Unknown unless an exact value is supported by two independent public '
 'sources. Return one table only.')


def task_vector() -> list[dict[str, str]]:
    return [
        {
            "opaque_id": "task_" + hashlib.sha256(
                f"v24779:{position}:{question}".encode("utf-8")
            ).hexdigest()[:24],
            "question": question,
        }
        for position, question in enumerate(QUESTIONS, 1)
    ]


def copy_task_vector() -> list[dict[str, str]]:
    return copy.deepcopy(task_vector())


__all__ = ["ENTITY_GROUPS", "POLICY_ID", "QUESTIONS", "copy_task_vector", "task_vector"]
