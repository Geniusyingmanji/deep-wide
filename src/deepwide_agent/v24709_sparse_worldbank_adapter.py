"""Visible-only sparse World Bank adapter for an exploratory full-220 probe.

The module has no filesystem, process, network, benchmark-label, answer, or
scoring capability.  It accepts one visible task, one already-frozen control
prediction, and caller-supplied bytes from four public World Bank bulk CSV
downloads.  A candidate is emitted only when all 53 visible identities bind
uniquely and all 212 requested target values validate; otherwise the control
prediction is returned byte-for-byte.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
import zipfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from .v24257_score_first_runtime import extract_valid_markdown_table
from .v24675_expanded_visible_schema import extract_expanded_visible_columns
from .v24705_visible_authority_scope_repair import (
    validate_signature,
    visible_authority_signature,
)


POLICY_ID = "v24709_sparse_worldbank_bulk_adapter_v1"
ROLE = "v24709_sparse_worldbank_adapter_result"
WORLD_BANK_BULK_TEMPLATE = (
    "https://api.worldbank.org/v2/en/indicator/{indicator}?downloadformat=csv"
)
EXPECTED_COLUMNS = (
    "Country",
    "Capital City",
    "Surface Area (km²)",
    "Population Density (people/km² of land area)",
    "Total Population (thousands)",
    "Merchandise Trade (% of GDP)",
)
EXPECTED_ROW_COUNT = 53
EXPECTED_TARGET_VALUE_COUNT = 212
MAX_ARCHIVE_BYTES = 2_000_000
MAX_MEMBER_BYTES = 4_000_000
MAX_ARCHIVE_MEMBER_COUNT = 8

_YEAR = re.compile(r"(?:19|20)\d{2}")
_ISO3 = re.compile(r"[A-Z]{3}")
_UPDATE_DATE = re.compile(r"20\d{2}-\d{2}-\d{2}")
_MAIN_MEMBER = re.compile(r"API_(?P<indicator>[A-Z0-9.]+)_DS2_en_csv_v\d+_\d+\.csv")
_CONTRACT_PATTERNS = (
    re.compile(r"surface\s+area.{0,180}?2022.{0,180}?rounded\s+to\s+an?\s+integer", re.I | re.S),
    re.compile(r"population\s+density.{0,180}?2022.{0,180}?rounded\s+to\s+an?\s+integer", re.I | re.S),
    re.compile(r"total\s+population.{0,180}?thousand.{0,180}?2023.{0,180}?rounded\s+to\s+an?\s+integer", re.I | re.S),
    re.compile(r"merchandise\s+trade.{0,180}?2023.{0,180}?rounded\s+to\s+one\s+decimal", re.I | re.S),
)
_TOKEN = re.compile(r"[a-z0-9]+")
_CONTROL_NUMBER = re.compile(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
_TOKEN_EQUIVALENTS = {
    "democratic": "dem",
    "federal": "fed",
    "federated": "fed",
    "republic": "rep",
}
_IGNORED_COUNTRY_TOKENS = frozenset({"of", "the"})
_LEGAL_FORM_TOKENS = frozenset({"arab", "dem", "fed", "rep"})
_FAILURE_REASONS = frozenset(
    {
        "not_eligible",
        "control_table_invalid",
        "bulk_fetch_failed",
        "bulk_bundle_invalid",
        "identity_binding_incomplete",
        "target_value_incomplete",
        "candidate_identity",
    }
)


@dataclass(frozen=True)
class TargetSpec:
    indicator: str
    year: str
    transform: str
    column_index: int

    @property
    def url(self) -> str:
        return WORLD_BANK_BULK_TEMPLATE.format(indicator=self.indicator)


TARGETS = (
    TargetSpec("AG.SRF.TOTL.K2", "2022", "integer_half_up", 2),
    TargetSpec("EN.POP.DNST", "2022", "integer_half_up", 3),
    TargetSpec("SP.POP.TOTL", "2023", "thousands_integer_half_up", 4),
    TargetSpec("TG.VAL.TOTL.GD.ZS", "2023", "one_decimal_half_up", 5),
)


@dataclass(frozen=True)
class OfficialRow:
    country_name: str
    iso3: str
    value: Decimal | None


def payload_sha256(value: Any) -> str:
    import json

    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def visible_contract_eligible(question: str) -> bool:
    visible = str(question or "")
    signature = validate_signature(visible_authority_signature(visible))
    return bool(
        signature["adapter_route_eligible"]
        and signature["unique_namespace"] == "world_bank"
        and tuple(extract_expanded_visible_columns(visible)) == EXPECTED_COLUMNS
        and all(pattern.search(visible) is not None for pattern in _CONTRACT_PATTERNS)
    )


def _matrix(table: str) -> list[list[str]] | None:
    canonical, _reason = extract_valid_markdown_table(table, EXPECTED_COLUMNS)
    if canonical is None:
        return None
    lines = [
        line.strip()
        for line in canonical.splitlines()
        if line.strip().startswith("|")
    ]
    if len(lines) < 2:
        return None
    header = [cell.strip() for cell in lines[0][1:-1].split("|")]
    rows = [
        [cell.strip() for cell in line[1:-1].split("|")]
        for line in lines[2:]
    ]
    if (
        tuple(header) != EXPECTED_COLUMNS
        or len(rows) != EXPECTED_ROW_COUNT
        or any(len(row) != len(EXPECTED_COLUMNS) for row in rows)
        or any(not row[0] or not row[1] for row in rows)
        or len({_country_tokens(row[0]) for row in rows}) != EXPECTED_ROW_COUNT
    ):
        return None
    return rows


def _country_tokens(value: object) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", str(value or "").casefold())
    ascii_text = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    output = []
    for token in _TOKEN.findall(ascii_text):
        canonical = _TOKEN_EQUIVALENTS.get(token, token)
        if canonical not in _IGNORED_COUNTRY_TOKENS:
            output.append(canonical)
    return tuple(sorted(output))


def _country_core(tokens: Sequence[str]) -> tuple[str, ...]:
    return tuple(token for token in tokens if token not in _LEGAL_FORM_TOKENS)


def _strip_trailing_empty(row: list[str]) -> list[str]:
    return row[:-1] if row and row[-1] == "" else row


def parse_bulk_archive(raw: bytes, spec: TargetSpec) -> dict[str, OfficialRow]:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_ARCHIVE_BYTES:
        raise ValueError("V2.47.09 bulk archive size drifted")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except (OSError, zipfile.BadZipFile) as exc:
        raise ValueError("V2.47.09 invalid ZIP") from exc
    with archive:
        infos = archive.infolist()
        if (
            not 1 <= len(infos) <= MAX_ARCHIVE_MEMBER_COUNT
            or any(
                info.is_dir()
                or info.flag_bits & 0x1
                or info.file_size > MAX_MEMBER_BYTES
                or "/" in info.filename
                or "\\" in info.filename
                for info in infos
            )
        ):
            raise ValueError("V2.47.09 unsafe ZIP member surface")
        candidates = []
        for info in infos:
            match = _MAIN_MEMBER.fullmatch(info.filename)
            if match is not None and match.group("indicator") == spec.indicator:
                candidates.append(info)
        if len(candidates) != 1:
            raise ValueError("V2.47.09 main CSV member drifted")
        try:
            text = archive.read(candidates[0]).decode("utf-8-sig")
        except (KeyError, RuntimeError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
            raise ValueError("V2.47.09 unreadable main CSV") from exc

    try:
        raw_rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        raise ValueError("V2.47.09 malformed main CSV") from exc
    if (
        len(raw_rows) < 6
        or _strip_trailing_empty(raw_rows[0])
        != ["Data Source", "World Development Indicators"]
        or raw_rows[1] != []
        or len(_strip_trailing_empty(raw_rows[2])) != 2
        or _strip_trailing_empty(raw_rows[2])[0] != "Last Updated Date"
        or _UPDATE_DATE.fullmatch(_strip_trailing_empty(raw_rows[2])[1]) is None
        or raw_rows[3] != []
    ):
        raise ValueError("V2.47.09 dataset preamble drifted")
    header = _strip_trailing_empty(raw_rows[4])
    if (
        header[:4]
        != ["Country Name", "Country Code", "Indicator Name", "Indicator Code"]
        or len(header) < 5
        or any(_YEAR.fullmatch(value) is None for value in header[4:])
        or len(set(header)) != len(header)
        or header[4:] != sorted(header[4:])
        or spec.year not in header
    ):
        raise ValueError("V2.47.09 dataset header drifted")
    year_index = header.index(spec.year)
    records: dict[str, OfficialRow] = {}
    for raw_row in raw_rows[5:]:
        if raw_row == []:
            continue
        row = _strip_trailing_empty(raw_row)
        if len(row) != len(header):
            raise ValueError("V2.47.09 dataset row width drifted")
        country_name, code, indicator_name, indicator = row[:4]
        if not country_name or not indicator_name or indicator != spec.indicator:
            raise ValueError("V2.47.09 dataset identity drifted")
        if _ISO3.fullmatch(code) is None:
            continue
        if code in records:
            raise ValueError("V2.47.09 duplicate ISO3")
        lexeme = row[year_index].strip()
        value: Decimal | None = None
        if lexeme:
            try:
                value = Decimal(lexeme)
            except InvalidOperation as exc:
                raise ValueError("V2.47.09 invalid decimal") from exc
            if not value.is_finite():
                raise ValueError("V2.47.09 non-finite decimal")
        records[code] = OfficialRow(country_name, code, value)
    if not records:
        raise ValueError("V2.47.09 empty official dataset")
    return records


def _candidate_codes(
    visible_name: str, records: Mapping[str, OfficialRow]
) -> list[str]:
    visible = _country_tokens(visible_name)
    if not visible or not _country_core(visible):
        return []
    exact = sorted(
        code for code, record in records.items() if _country_tokens(record.country_name) == visible
    )
    if exact:
        return exact
    core = _country_core(visible)
    return sorted(
        code
        for code, record in records.items()
        if _country_core(_country_tokens(record.country_name)) == core
    )


def bind_visible_countries(
    visible_rows: Sequence[Sequence[str]],
    datasets: Mapping[str, Mapping[str, OfficialRow]],
) -> list[str]:
    if set(datasets) != {spec.indicator for spec in TARGETS}:
        raise ValueError("V2.47.09 dataset vector drifted")
    bound: list[str] = []
    used: set[str] = set()
    for row in visible_rows:
        per_dataset: list[str] = []
        for spec in TARGETS:
            candidates = _candidate_codes(str(row[0]), datasets[spec.indicator])
            if len(candidates) != 1:
                raise ValueError("V2.47.09 country identity is not unique")
            per_dataset.append(candidates[0])
        if len(set(per_dataset)) != 1:
            raise ValueError("V2.47.09 cross-dataset country code drifted")
        code = per_dataset[0]
        official_names = {
            _country_tokens(datasets[spec.indicator][code].country_name)
            for spec in TARGETS
        }
        if len(official_names) != 1 or code in used:
            raise ValueError("V2.47.09 cross-dataset country binding drifted")
        used.add(code)
        bound.append(code)
    if len(bound) != EXPECTED_ROW_COUNT:
        raise ValueError("V2.47.09 country binding incomplete")
    return bound


def _format_value(value: Decimal, transform: str) -> str:
    if transform == "integer_half_up":
        return format(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP), "f")
    if transform == "thousands_integer_half_up":
        return format(
            (value / Decimal("1000")).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            ),
            "f",
        )
    if transform == "one_decimal_half_up":
        return format(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), ".1f")
    raise ValueError("V2.47.09 unknown value transform")


def _numeric_value(value: object) -> Decimal | None:
    text = str(value or "").strip()
    if _CONTROL_NUMBER.fullmatch(text) is None:
        return None
    try:
        parsed = Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _render(rows: Sequence[Sequence[str]]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(EXPECTED_COLUMNS)
        + " |\n| "
        + " | ".join("---" for _ in EXPECTED_COLUMNS)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def _result(
    control_prediction: str,
    prediction: str,
    *,
    route_eligible: bool,
    applied: bool,
    reason: str | None,
    bulk_download_count: int,
    identity_binding_count: int,
    target_value_count: int,
    changed_cell_count: int,
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode("utf-8")).hexdigest(),
        "control_prediction_sha256": hashlib.sha256(
            control_prediction.encode("utf-8")
        ).hexdigest(),
        "route_eligible": route_eligible,
        "applied": applied,
        "failure_reason": reason,
        "bulk_download_count": bulk_download_count,
        "identity_binding_count": identity_binding_count,
        "target_value_count": target_value_count,
        "changed_cell_count": changed_cell_count,
        "visible_row_count": EXPECTED_ROW_COUNT if route_eligible else 0,
        "country_and_capital_cells_preserved": applied,
        "whole_task_fail_closed": not applied,
        "entropy_credit_assigned": False,
        "runtime_input_keys": ["opaque_id", "question"],
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def run_sparse_adapter(
    task: Mapping[str, Any],
    control_prediction: str,
    fetch_bulk_bundle: Callable[[tuple[str, ...]], Mapping[str, bytes]],
) -> dict[str, Any]:
    if (
        set(task) != {"opaque_id", "question"}
        or not isinstance(task.get("opaque_id"), str)
        or not isinstance(task.get("question"), str)
        or not isinstance(control_prediction, str)
        or not control_prediction.strip()
    ):
        raise ValueError("V2.47.09 visible runtime boundary drifted")
    eligible = visible_contract_eligible(task["question"])
    if not eligible:
        return _result(
            control_prediction,
            control_prediction,
            route_eligible=False,
            applied=False,
            reason="not_eligible",
            bulk_download_count=0,
            identity_binding_count=0,
            target_value_count=0,
            changed_cell_count=0,
        )
    rows = _matrix(control_prediction)
    if rows is None:
        return _result(
            control_prediction,
            control_prediction,
            route_eligible=True,
            applied=False,
            reason="control_table_invalid",
            bulk_download_count=0,
            identity_binding_count=0,
            target_value_count=0,
            changed_cell_count=0,
        )
    urls = tuple(spec.url for spec in TARGETS)
    try:
        bundle = fetch_bulk_bundle(urls)
    except Exception:
        return _result(
            control_prediction,
            control_prediction,
            route_eligible=True,
            applied=False,
            reason="bulk_fetch_failed",
            bulk_download_count=0,
            identity_binding_count=0,
            target_value_count=0,
            changed_cell_count=0,
        )
    try:
        if not isinstance(bundle, Mapping) or set(bundle) != set(urls):
            raise ValueError("V2.47.09 bulk bundle key drifted")
        datasets = {
            spec.indicator: parse_bulk_archive(bundle[spec.url], spec)
            for spec in TARGETS
        }
    except (KeyError, TypeError, ValueError):
        return _result(
            control_prediction,
            control_prediction,
            route_eligible=True,
            applied=False,
            reason="bulk_bundle_invalid",
            bulk_download_count=len(bundle) if isinstance(bundle, Mapping) else 0,
            identity_binding_count=0,
            target_value_count=0,
            changed_cell_count=0,
        )
    try:
        iso3_vector = bind_visible_countries(rows, datasets)
    except ValueError:
        return _result(
            control_prediction,
            control_prediction,
            route_eligible=True,
            applied=False,
            reason="identity_binding_incomplete",
            bulk_download_count=len(bundle),
            identity_binding_count=0,
            target_value_count=0,
            changed_cell_count=0,
        )
    candidate = [list(row) for row in rows]
    target_count = 0
    for row_index, iso3 in enumerate(iso3_vector):
        for spec in TARGETS:
            record = datasets[spec.indicator].get(iso3)
            if record is None or record.value is None:
                return _result(
                    control_prediction,
                    control_prediction,
                    route_eligible=True,
                    applied=False,
                    reason="target_value_incomplete",
                    bulk_download_count=len(bundle),
                    identity_binding_count=len(iso3_vector),
                    target_value_count=target_count,
                    changed_cell_count=0,
                )
            rendered = _format_value(record.value, spec.transform)
            previous = candidate[row_index][spec.column_index]
            if _numeric_value(previous) != Decimal(rendered):
                candidate[row_index][spec.column_index] = rendered
            target_count += 1
    prediction = _render(candidate)
    changed = sum(
        candidate[row_index][column_index] != rows[row_index][column_index]
        for row_index in range(EXPECTED_ROW_COUNT)
        for column_index in range(2, len(EXPECTED_COLUMNS))
    )
    if target_count != EXPECTED_TARGET_VALUE_COUNT or changed == 0:
        return _result(
            control_prediction,
            control_prediction,
            route_eligible=True,
            applied=False,
            reason=(
                "target_value_incomplete"
                if target_count != EXPECTED_TARGET_VALUE_COUNT
                else "candidate_identity"
            ),
            bulk_download_count=len(bundle),
            identity_binding_count=len(iso3_vector),
            target_value_count=target_count,
            changed_cell_count=0,
        )
    return _result(
        control_prediction,
        prediction,
        route_eligible=True,
        applied=True,
        reason=None,
        bulk_download_count=len(bundle),
        identity_binding_count=len(iso3_vector),
        target_value_count=target_count,
        changed_cell_count=changed,
    )


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    integer_fields = (
        "bulk_download_count",
        "identity_binding_count",
        "target_value_count",
        "changed_cell_count",
        "visible_row_count",
    )
    applied = value.get("applied")
    prediction = value.get("prediction")
    if (
        set(value)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "prediction",
            "prediction_sha256",
            "control_prediction_sha256",
            "route_eligible",
            "applied",
            "failure_reason",
            "bulk_download_count",
            "identity_binding_count",
            "target_value_count",
            "changed_cell_count",
            "visible_row_count",
            "country_and_capital_cells_preserved",
            "whole_task_fail_closed",
            "entropy_credit_assigned",
            "runtime_input_keys",
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
            "result_payload_sha256",
        }
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(prediction, str)
        or hashlib.sha256(prediction.encode("utf-8")).hexdigest()
        != value.get("prediction_sha256")
        or not isinstance(value.get("control_prediction_sha256"), str)
        or len(value["control_prediction_sha256"]) != 64
        or not isinstance(value.get("route_eligible"), bool)
        or not isinstance(applied, bool)
        or value.get("failure_reason") not in (_FAILURE_REASONS | {None})
        or (value.get("failure_reason") is None) is not applied
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in integer_fields
        )
        or value.get("country_and_capital_cells_preserved") is not applied
        or value.get("whole_task_fail_closed") is not (not applied)
        or value.get("entropy_credit_assigned") is not False
        or value.get("runtime_input_keys") != ["opaque_id", "question"]
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.09 result drifted")
    if applied:
        if (
            value.get("route_eligible") is not True
            or value.get("bulk_download_count") != len(TARGETS)
            or value.get("identity_binding_count") != EXPECTED_ROW_COUNT
            or value.get("target_value_count") != EXPECTED_TARGET_VALUE_COUNT
            or value.get("changed_cell_count") not in range(
                1, EXPECTED_TARGET_VALUE_COUNT + 1
            )
            or value.get("visible_row_count") != EXPECTED_ROW_COUNT
            or value.get("prediction_sha256")
            == value.get("control_prediction_sha256")
        ):
            raise ValueError("V2.47.09 applied result drifted")
    elif (
        value.get("changed_cell_count") != 0
        or value.get("prediction_sha256") != value.get("control_prediction_sha256")
        or (value.get("route_eligible") is False and value.get("visible_row_count") != 0)
    ):
        raise ValueError("V2.47.09 fail-closed result drifted")
    return dict(value)


__all__ = [
    "EXPECTED_COLUMNS",
    "EXPECTED_ROW_COUNT",
    "EXPECTED_TARGET_VALUE_COUNT",
    "POLICY_ID",
    "ROLE",
    "TARGETS",
    "TargetSpec",
    "bind_visible_countries",
    "parse_bulk_archive",
    "run_sparse_adapter",
    "validate_result",
    "visible_contract_eligible",
]
