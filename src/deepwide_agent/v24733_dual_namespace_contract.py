"""Visible-only contract for the V2.47.33 dual-namespace gate."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .v24639_ror_objective_runtime import extract_visible_entities
import re


POLICY_ID = "v24733_dual_namespace_visible_contract_v1"
TASK_COUNT = 24
TASKS_PER_CLUSTER = 12
ROR_ENTITY_GROUPS = (('Institut Syariah Negeri Junjungan Bengkalis',
  'Berhampur University',
  'Graduate Institute of International and Development Studies',
  'Gibbeum General Hospital'),
 ('Alzheimer Society of Canada',
  'Society of Vascular and Interventional Neurology',
  'Helmholtz Association of German Research Centres',
  'Universidad Dr. Andrés Bello'),
 ('Sekolah Tinggi Teologi Baptis Kalvari Jakarta',
  'Calgary Foothills Primary Care Network',
  'Faridpur Medical College',
  'Fundação Universitária Mário Martins'),
 ('Sekolah Tinggi Ilmu Kesehatan Pemkab Purworejo',
  'Alliance for South Asian Aids Prevention',
  'German Breast Group',
  'Suleyman Demirel University Research and Education Hospital'),
 ('Akademi Kesehatan John Paul II Pekanbaru',
  'Bristol Eye Hospital',
  'Institut National Polytechnique Félix Houphouët-Boigny',
  'Kolehiyo ng Pantukan'),
 ('Nilgiri College of Arts and Science',
  'Continental Florida University',
  'National Park Service',
  'Department of Water Resources and Irrigation'),
 ('Kaziranga English Academy',
  'Institute of Biological and Medical Imaging',
  'Instituto Tecnológico Superior de Teziutlán',
  'Tecnológico del Valle del Guadiana'),
 ('Parala Maharaja Engineering College',
  'Konstantinion Research Center of Molecular Medicine and Biotechnology',
  'WageIndicator Foundation',
  'Universidad La Salle Victoria'),
 ("Fédération de Recherche sur l'Energie Solaire",
  'Coalition for Aligning Science',
  'Centro Universitario Sagrada Familia',
  'Fundación Omar Dengo'),
 ('Laboratoire AstroParticule et Cosmologie',
  'The Laurier Institution',
  'Nürnberg Institut für Marktentscheidungen e.V.',
  'Shandong Meteorological Bureau'),
 ("Laboratoire d'Ecologie des Hydrosystèmes Naturels et Anthropisés",
  'China Academy of Information and Communications Technology',
  'Abraham Adesanya Polytechnic',
  'Ashiya Municipal Hospital'),
 ("Laboratoire d'Informatique en Images et Systèmes d'Information",
  'Hashimoto Foundation',
  'Faculdade Princesa do Oeste',
  'Islamic Azad University Gonbad Kavoos Branch'))
WORLD_BANK_COUNTRY_GROUPS = ((('Kenya', 'KEN'),
  ('Macao SAR, China', 'MAC'),
  ('Iran, Islamic Rep.', 'IRN'),
  ('Luxembourg', 'LUX')),
 (('Honduras', 'HND'), ('Comoros', 'COM'), ('Naoero', 'NRU'), ('Jordan', 'JOR')),
 (('Belgium', 'BEL'), ('St. Lucia', 'LCA'), ('Gabon', 'GAB'), ('Palau', 'PLW')),
 (('Afghanistan', 'AFG'), ('Bulgaria', 'BGR'), ('Costa Rica', 'CRI'), ('Benin', 'BEN')),
 (('Hong Kong SAR, China', 'HKG'), ('Djibouti', 'DJI'), ('Albania', 'ALB'), ('Jamaica', 'JAM')),
 (('Mauritius', 'MUS'), ('Micronesia, Fed. Sts.', 'FSM'), ('Lebanon', 'LBN'), ('Belarus', 'BLR')),
 (('Cuba', 'CUB'), ('Sierra Leone', 'SLE'), ('New Zealand', 'NZL'), ('Malta', 'MLT')),
 (('Hungary', 'HUN'),
  ('Bolivia', 'BOL'),
  ('Equatorial Guinea', 'GNQ'),
  ('Brunei Darussalam', 'BRN')),
 (('Bahrain', 'BHR'), ('Poland', 'POL'), ('Bahamas, The', 'BHS'), ("Cote d'Ivoire", 'CIV')),
 (('Fiji', 'FJI'), ('Egypt, Arab Rep.', 'EGY'), ('Georgia', 'GEO'), ('Ecuador', 'ECU')),
 (('Zambia', 'ZMB'), ('Mongolia', 'MNG'), ('Ukraine', 'UKR'), ('Dominican Republic', 'DOM')),
 (('Madagascar', 'MDG'), ('Lao PDR', 'LAO'), ('Armenia', 'ARM'), ('Dominica', 'DMA')))
WORLD_BANK_TARGETS = ({'label': 'Individuals using the Internet (% of population)',
  'indicator': 'IT.NET.USER.ZS',
  'year': '2022'},
 {'label': 'Life expectancy at birth, total (years)',
  'indicator': 'SP.DYN.LE00.IN',
  'year': '2022'})
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Institut Syariah Negeri Junjungan Bengkalis\n'
 '2. Berhampur University\n'
 '3. Graduate Institute of International and Development Studies\n'
 '4. Gibbeum General Hospital\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Alzheimer Society of Canada\n'
 '2. Society of Vascular and Interventional Neurology\n'
 '3. Helmholtz Association of German Research Centres\n'
 '4. Universidad Dr. Andrés Bello\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Teologi Baptis Kalvari Jakarta\n'
 '2. Calgary Foothills Primary Care Network\n'
 '3. Faridpur Medical College\n'
 '4. Fundação Universitária Mário Martins\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Ilmu Kesehatan Pemkab Purworejo\n'
 '2. Alliance for South Asian Aids Prevention\n'
 '3. German Breast Group\n'
 '4. Suleyman Demirel University Research and Education Hospital\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Akademi Kesehatan John Paul II Pekanbaru\n'
 '2. Bristol Eye Hospital\n'
 '3. Institut National Polytechnique Félix Houphouët-Boigny\n'
 '4. Kolehiyo ng Pantukan\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Nilgiri College of Arts and Science\n'
 '2. Continental Florida University\n'
 '3. National Park Service\n'
 '4. Department of Water Resources and Irrigation\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Kaziranga English Academy\n'
 '2. Institute of Biological and Medical Imaging\n'
 '3. Instituto Tecnológico Superior de Teziutlán\n'
 '4. Tecnológico del Valle del Guadiana\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Parala Maharaja Engineering College\n'
 '2. Konstantinion Research Center of Molecular Medicine and Biotechnology\n'
 '3. WageIndicator Foundation\n'
 '4. Universidad La Salle Victoria\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 "1. Fédération de Recherche sur l'Energie Solaire\n"
 '2. Coalition for Aligning Science\n'
 '3. Centro Universitario Sagrada Familia\n'
 '4. Fundación Omar Dengo\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Laboratoire AstroParticule et Cosmologie\n'
 '2. The Laurier Institution\n'
 '3. Nürnberg Institut für Marktentscheidungen e.V.\n'
 '4. Shandong Meteorological Bureau\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 "1. Laboratoire d'Ecologie des Hydrosystèmes Naturels et Anthropisés\n"
 '2. China Academy of Information and Communications Technology\n'
 '3. Abraham Adesanya Polytechnic\n'
 '4. Ashiya Municipal Hospital\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 "1. Laboratoire d'Informatique en Images et Systèmes d'Information\n"
 '2. Hashimoto Foundation\n'
 '3. Faculdade Princesa do Oeste\n'
 '4. Islamic Azad University Gonbad Kavoos Branch\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Kenya [KEN]\n'
 '2. Macao SAR, China [MAC]\n'
 '3. Iran, Islamic Rep. [IRN]\n'
 '4. Luxembourg [LUX]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Honduras [HND]\n'
 '2. Comoros [COM]\n'
 '3. Naoero [NRU]\n'
 '4. Jordan [JOR]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Belgium [BEL]\n'
 '2. St. Lucia [LCA]\n'
 '3. Gabon [GAB]\n'
 '4. Palau [PLW]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Afghanistan [AFG]\n'
 '2. Bulgaria [BGR]\n'
 '3. Costa Rica [CRI]\n'
 '4. Benin [BEN]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Hong Kong SAR, China [HKG]\n'
 '2. Djibouti [DJI]\n'
 '3. Albania [ALB]\n'
 '4. Jamaica [JAM]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Mauritius [MUS]\n'
 '2. Micronesia, Fed. Sts. [FSM]\n'
 '3. Lebanon [LBN]\n'
 '4. Belarus [BLR]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Cuba [CUB]\n'
 '2. Sierra Leone [SLE]\n'
 '3. New Zealand [NZL]\n'
 '4. Malta [MLT]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Hungary [HUN]\n'
 '2. Bolivia [BOL]\n'
 '3. Equatorial Guinea [GNQ]\n'
 '4. Brunei Darussalam [BRN]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Bahrain [BHR]\n'
 '2. Poland [POL]\n'
 '3. Bahamas, The [BHS]\n'
 "4. Cote d'Ivoire [CIV]\n"
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Fiji [FJI]\n'
 '2. Egypt, Arab Rep. [EGY]\n'
 '3. Georgia [GEO]\n'
 '4. Ecuador [ECU]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Zambia [ZMB]\n'
 '2. Mongolia [MNG]\n'
 '3. Ukraine [UKR]\n'
 '4. Dominican Republic [DOM]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Madagascar [MDG]\n'
 '2. Lao PDR [LAO]\n'
 '3. Armenia [ARM]\n'
 '4. Dominica [DMA]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | Individuals using the Internet (% of population) [IT.NET.USER.ZS] @2022 | Life '
 'expectancy at birth, total (years) [SP.DYN.LE00.IN] @2022\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.')


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()



_WORLD_BANK_QUESTION = re.compile(
    r"Use public web sources to return one Markdown table about these countries:\n"
    r"<COUNTRIES>\n(?P<countries>.*?)\n</COUNTRIES>\n"
    r"Please output one Markdown table with the columns, in this exact order:\n"
    r"(?P<columns>[^\n]+)\n"
    r"Use the World Bank API values\. Preserve the decimal representation returned by "
    r"the official API\. Use Unknown when unavailable\. Return one table only\.",
    flags=re.DOTALL,
)
_WORLD_BANK_COUNTRY = re.compile(
    r"(?P<ordinal>[1-4])\. (?P<name>[^\[\]|\r\n]+) \[(?P<iso3>[A-Z]{3})\]"
)
_WORLD_BANK_TARGET = re.compile(
    r"(?P<label>[^|\[\]\r\n]{1,120})\s*"
    r"\[(?P<indicator>[A-Z][A-Z0-9.]{4,40})\]\s*@(?P<year>20[0-3][0-9])"
)


def parse_worldbank_visible_contract(question: str) -> dict[str, object]:
    match = _WORLD_BANK_QUESTION.fullmatch(str(question or "").strip())
    if match is None:
        raise ValueError("V2.47.33 visible World Bank syntax drifted")
    countries = []
    for expected, line in enumerate(match.group("countries").splitlines(), 1):
        parsed = _WORLD_BANK_COUNTRY.fullmatch(line)
        if parsed is None or int(parsed.group("ordinal")) != expected:
            raise ValueError("V2.47.33 visible country vector drifted")
        countries.append({"name": parsed.group("name").strip(), "iso3": parsed.group("iso3")})
    if (
        len(countries) != 4
        or len({item["name"].casefold() for item in countries}) != 4
        or len({item["iso3"] for item in countries}) != 4
    ):
        raise ValueError("V2.47.33 visible country identity drifted")
    columns = [value.strip() for value in match.group("columns").split("|")]
    if len(columns) != 3 or columns[0] != "Country":
        raise ValueError("V2.47.33 visible column vector drifted")
    targets = []
    for column in columns[1:]:
        parsed = _WORLD_BANK_TARGET.fullmatch(column)
        if parsed is None:
            raise ValueError("V2.47.33 visible target address drifted")
        targets.append(
            {
                "label": parsed.group("label").strip(),
                "indicator": parsed.group("indicator"),
                "year": parsed.group("year"),
            }
        )
    if targets != list(WORLD_BANK_TARGETS):
        raise ValueError("V2.47.33 visible target vector drifted")
    return {"countries": countries, "columns": columns, "targets": targets}


def visible_namespace(question: str) -> str:
    if not isinstance(question, str):
        raise ValueError("V2.47.33 question drifted")
    if "<ENTITIES>" in question and "The column names are: Organization, ROR ID, Country code." in question:
        entities = extract_visible_entities(question)
        if len(entities) == 4:
            return "ror"
    if "<COUNTRIES>" in question and "World Bank API values" in question:
        contract = parse_worldbank_visible_contract(question)
        if len(contract["countries"]) == 4 and contract["targets"] == list(WORLD_BANK_TARGETS):
            return "worldbank"
    raise ValueError("V2.47.33 visible namespace is unsupported")


def visible_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= TASK_COUNT:
        raise ValueError("V2.47.33 task ordinal drifted")
    value = {
        "opaque_id": f"task_{0x247330 + ordinal:024x}",
        "question": QUESTIONS[ordinal - 1],
    }
    namespace = visible_namespace(value["question"])
    expected = "ror" if ordinal <= TASKS_PER_CLUSTER else "worldbank"
    if namespace != expected:
        raise ValueError("V2.47.33 namespace/order drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, TASK_COUNT + 1)]


__all__ = [
    "POLICY_ID", "QUESTIONS", "ROR_ENTITY_GROUPS", "TASK_COUNT",
    "TASKS_PER_CLUSTER", "WORLD_BANK_COUNTRY_GROUPS", "WORLD_BANK_TARGETS",
    "payload_sha256", "task_vector", "visible_namespace", "visible_task",
]
