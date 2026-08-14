"""Pure visible-output constraint contract for production synthesis.

V2.55.40 established broad transfer reach for explicit temporal, numeric
scale, and rank/order requirements, while the current V2.54.06 production
closure has no mechanical contract for any of them.  This module ports only
small, conservative, visible-only recognizers into the current runtime line.
It deliberately does *not* import the legacy monolithic runtime.

The contract is trusted data copied from the visible question and exact
requested columns.  It can be appended to an already-paid synthesis prompt;
it never edits a prediction, invents a value, fetches a page, or assigns
credit.  Ambiguous ranges, formats, scales, rank domains, and sort directives
fail closed.  ``observe_prediction`` is diagnostic only: it checks structural
adherence without judging factual correctness.

This module is pure and has no file, environment, process, network, model,
search, fetch, evaluator, benchmark-label, mapping, gold, score, reward,
credential, or historical-result capability.  Entropy/information gain is
shadow-only and assigns no signed credit.  This build grants no launch.
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

from . import v24257_score_first_runtime as score
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25541_visible_output_constraint_contract_v1"
ROLE = "v25541_private_visible_output_constraint_contract"
OBSERVATION_ROLE = "v25541_content_free_constraint_observation"
MAXIMUM_COLUMNS = 20
MAXIMUM_COLUMN_CHARACTERS = 80
MAXIMUM_YEAR_SPAN = 200
MAXIMUM_TOP_K = 100
MAXIMUM_SUFFIX_CHARACTERS = 6_000
FAMILY_ORDER = (
    "temporal_year_range",
    "date_format",
    "numeric_scale",
    "rank_slots",
    "explicit_order",
)
DATE_STYLES = frozenset(
    {
        "iso_dash",
        "iso_slash",
        "iso_dot",
        "chinese_ymd",
        "chinese_ymd_unpadded",
        "english_long",
        "english_short",
    }
)
NUMERIC_SCALES = frozenset({"thousand", "million", "billion", "trillion"})
ORDER_DIRECTIONS = frozenset({"ascending", "descending"})

_YEAR_RANGE_PATTERNS = (
    re.compile(
        r"(?<!\d)(?:from\s+)?((?:19|20)\d{2})\s*年?\s*"
        r"(?:-|－|–|—|~|～|至|到|to|through|thru)\s*"
        r"((?:19|20)\d{2})\s*年?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbetween\s+((?:19|20)\d{2})\s+and\s+"
        r"((?:19|20)\d{2})\b",
        re.IGNORECASE,
    ),
)
_TOP_K_PATTERNS = (
    re.compile(
        r"(?:排名\s*)?(?:前|头)\s*"
        r"(\d{1,3}|[一二两三四五六七八九十百千]+)\s*"
        r"(?:名|位|个|强)?",
        re.IGNORECASE,
    ),
    re.compile(r"\btop\s*[-–—]?\s*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"\b(?:first|best)\s+(\d{1,3})\b", re.IGNORECASE),
)
_TIE_CUE = re.compile(
    r"(?:并列|同名次|tie(?:d|s)?|including\s+ties)", re.IGNORECASE
)
_UNKNOWN = re.compile(
    r"^(?:unknown|n/?a|not\s+available|unavailable|none|null|-|—|未知|不详|暂无)$",
    re.IGNORECASE,
)
_FULL_NUMBER = re.compile(
    r"^[\s$€£¥￥]*[-+]?\d[\d,]*(?:\.\d+)?\s*%?[\s]*$"
)
_CE_YEAR = r"(?:[1-9]\d{0,3})"
_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_SCALE_PATTERNS = {
    "thousand": re.compile(
        r"\bthousands?\b|千(?:元|美元|欧元|人民币)?", re.IGNORECASE
    ),
    "million": re.compile(
        r"\bmillions?\b|百万(?:元|美元|欧元|人民币)?", re.IGNORECASE
    ),
    "billion": re.compile(
        r"\bbillions?\b|十亿(?:元|美元|欧元|人民币)?", re.IGNORECASE
    ),
    "trillion": re.compile(
        r"\btrillions?\b|万亿(?:元|美元|欧元|人民币)?", re.IGNORECASE
    ),
}
_NUMERIC_COLUMN = re.compile(
    r"(?i)(?:\b(?:amount|value|total|count|number|population|gdp|revenue|income|"
    r"expense|expenditure|budget|debt|price|cost|capacity|power|torque|"
    r"rate|ratio|share|percent|percentage|score)\b|数量|数值|总计|总额|人口|"
    r"收入|支出|预算|债务|价格|成本|容量|功率|扭矩|比率|比例|百分比|分数)"
)


def _text(value: object) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", str(value or ""))
        .replace("\x00", " ")
        .split()
    )


def _key(value: object) -> str:
    return "".join(
        character.casefold()
        for character in unicodedata.normalize("NFKC", str(value or ""))
        if character.isalnum() or "\u3400" <= character <= "\u9fff"
    )


def _safe_columns(columns: Sequence[str]) -> tuple[str, ...]:
    if isinstance(columns, (str, bytes)) or not 1 <= len(columns) <= MAXIMUM_COLUMNS:
        raise ValueError("V2.55.41 visible column vector drifted")
    output: list[str] = []
    keys: list[str] = []
    for raw in columns:
        if not isinstance(raw, str) or any(character in raw for character in "|\x00\r\n"):
            raise ValueError("V2.55.41 visible column is unsafe")
        value = _text(raw)
        key = _key(value)
        if not value or len(value) > MAXIMUM_COLUMN_CHARACTERS or not key:
            raise ValueError("V2.55.41 visible column is invalid")
        output.append(value)
        keys.append(key)
    if len(set(keys)) != len(keys):
        raise ValueError("V2.55.41 visible columns are ambiguous")
    return tuple(output)


def _is_year_column(column: object) -> bool:
    value = _text(column).casefold()
    return bool(re.search(r"(?:^|\b)(?:year|years)(?:\b|$)|年份|年度|年代", value))


def _is_date_column(column: object) -> bool:
    value = _text(column).casefold()
    key = _key(value)
    if "date" in key or key.endswith("日期") or _is_year_column(column):
        return True
    return bool(
        key.endswith("时间")
        and re.search(
            r"(?:出生|诞生|逝世|死亡|去世|成立|创立|创建|开始|起始|结束|"
            r"终止|就任|就职|卸任|任职|发行|发布|上映|播出|发生|转会|签约|"
            r"加入|离开)",
            key,
        )
    )


def _is_rank_column(column: object) -> bool:
    return bool(
        re.search(
            r"(?:排名|名次|位次|序位|排行|rank(?:ing)?|position|place)",
            _text(column),
            re.IGNORECASE,
        )
    )


def _small_chinese_integer(value: str) -> int | None:
    text = value.strip().replace("两", "二").replace("〇", "零")
    if not text or not re.fullmatch(r"[零一二三四五六七八九十百千]+", text):
        return None
    digits = {
        "零": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    if all(character in digits for character in text):
        number = int("".join(str(digits[character]) for character in text))
        return number if number > 0 else None
    total = current = 0
    for character in text:
        if character in digits:
            current = digits[character]
        else:
            total += (current or 1) * {"十": 10, "百": 100, "千": 1000}[character]
            current = 0
    total += current
    return total if total > 0 else None


def _year_range(question: str, columns: Sequence[str]) -> dict[str, Any] | None:
    matches: set[tuple[int, int]] = set()
    for pattern in _YEAR_RANGE_PATTERNS:
        for match in pattern.finditer(question):
            start, end = int(match.group(1)), int(match.group(2))
            if start <= end and end - start <= MAXIMUM_YEAR_SPAN:
                matches.add((start, end))
    if len(matches) != 1:
        return None
    start, end = next(iter(matches))
    targets = [column for column in columns if _is_date_column(column)]
    return {
        "inclusive_start_year": start,
        "inclusive_end_year": end,
        "target_columns": targets,
        "row_scope_applies_even_without_year_column": not targets,
    }


def _date_style(question: str, columns: Sequence[str]) -> dict[str, Any] | None:
    targets = [column for column in columns if _is_date_column(column)]
    if not targets:
        return None
    normalized = (
        question.replace("–", "-")
        .replace("—", "-")
        .replace("／", "/")
        .replace("．", ".")
    )
    styles: set[str] = set()
    if re.search(r"\bISO(?:\s*-?\s*8601)?\b", normalized, re.IGNORECASE):
        styles.add("iso_dash")
    for match in re.finditer(
        r"\bY{2,4}\s*([-/.])\s*M{1,4}\s*\1\s*D{1,2}\b",
        normalized,
        re.IGNORECASE,
    ):
        styles.add({"-": "iso_dash", "/": "iso_slash", ".": "iso_dot"}[match.group(1)])
    for match in re.finditer(
        r"[YX]{2,4}\s*年\s*([MX]{1,2})\s*月\s*([DX]{1,2})\s*日",
        normalized,
        re.IGNORECASE,
    ):
        styles.add(
            "chinese_ymd_unpadded"
            if len(match.group(1)) == 1 and len(match.group(2)) == 1
            else "chinese_ymd"
        )
    if re.search(r"\bMMMM\s+D{1,2}\s*,\s*Y{2,4}\b", normalized, re.IGNORECASE):
        styles.add("english_long")
    if re.search(
        r"\b(?:MMM|Mon(?:th)?)\s+D{1,2}\s*,\s*Y{2,4}\b",
        normalized,
        re.IGNORECASE,
    ):
        styles.add("english_short")
    if len(styles) != 1:
        return None
    return {"style": next(iter(styles)), "target_columns": targets}


def _scale_matches(value: str) -> set[str]:
    return {
        scale for scale, pattern in _SCALE_PATTERNS.items() if pattern.search(value)
    }


def _scale_is_explicit(question: str, scale: str) -> bool:
    pattern = _SCALE_PATTERNS[scale]
    for match in pattern.finditer(question):
        start = max(0, match.start() - 60)
        end = min(len(question), match.end() + 60)
        window = question[start:end]
        if re.search(
            r"(?i)(?:\b(?:in|unit|units|express(?:ed)?|denominat(?:ed|ion))\b|"
            r"单位|为单位|以.+计|按.+计|换算|折合)",
            window,
        ):
            return True
    return False


def _numeric_scale(question: str, columns: Sequence[str]) -> dict[str, Any] | None:
    column_matches = {
        scale
        for column in columns
        for scale in _scale_matches(column)
    }
    all_matches = _scale_matches(" ".join([question, *columns]))
    if len(all_matches) != 1:
        return None
    scale = next(iter(all_matches))
    if scale not in column_matches and not _scale_is_explicit(question, scale):
        return None
    targets = [
        column
        for column in columns
        if scale in _scale_matches(column) or _NUMERIC_COLUMN.search(column)
    ]
    return {
        "scale": scale,
        "target_columns": targets,
        "all_numeric_non_key_cells_when_targets_empty": not targets,
    }


def _top_k(question: str, columns: Sequence[str]) -> dict[str, Any] | None:
    if _TIE_CUE.search(question):
        return None
    values: set[int] = set()
    for pattern in _TOP_K_PATTERNS:
        for match in pattern.finditer(question):
            raw = match.group(1)
            value = int(raw) if raw.isdigit() else _small_chinese_integer(raw)
            if value is not None and 1 <= value <= MAXIMUM_TOP_K:
                values.add(value)
    rank_columns = [column for column in columns if _is_rank_column(column)]
    if len(values) != 1 or len(rank_columns) != 1:
        return None
    count = next(iter(values))
    return {
        "count": count,
        "rank_column": rank_columns[0],
        "required_rank_values": [str(value) for value in range(1, count + 1)],
        "rank_order": "ascending",
    }


def _direction(raw: str) -> str:
    folded = raw.casefold()
    if re.search(r"descending|decreasing|reverse|降序|高到低|大到小|晚到早", folded):
        return "descending"
    return "ascending"


def _explicit_order(
    question: str,
    columns: Sequence[str],
    rank_slots: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    candidates: set[tuple[str, str]] = set()
    for column in columns:
        escaped = re.escape(column)
        patterns = (
            re.compile(
                rf"(?i)(?:sort(?:ed)?|order(?:ed)?|rank(?:ed)?)\s+by\s+"
                rf"{escaped}.{{0,24}}(ascending|descending|increasing|decreasing|"
                rf"chronological|reverse\s+chronological)"
            ),
            re.compile(
                rf"(?i){escaped}.{{0,20}}(ascending|descending|increasing|"
                rf"decreasing|chronological|reverse\s+chronological)\s*(?:order)?"
            ),
            re.compile(rf"(?:按|依)\s*{escaped}\s*(升序|降序)(?:排列|排序)?"),
            re.compile(rf"{escaped}\s*(升序|降序)(?:排列|排序)?"),
            re.compile(rf"{escaped}.{{0,16}}(从高到低|从低到高|从大到小|从小到大|从早到晚|从晚到早)"),
        )
        for pattern in patterns:
            for match in pattern.finditer(question):
                candidates.add((column, _direction(match.group(1))))
    if len(candidates) != 1:
        return None
    column, direction = next(iter(candidates))
    if (
        rank_slots is not None
        and column == rank_slots["rank_column"]
        and direction == "ascending"
    ):
        return None
    value_kind = (
        "date"
        if _is_date_column(column)
        else "rank"
        if _is_rank_column(column)
        else "numeric_or_lexical"
    )
    return {"target_column": column, "direction": direction, "value_kind": value_kind}


def build_contract(question: str, columns: Sequence[str]) -> dict[str, Any]:
    """Build one sealed, deterministic contract from visible text only."""

    visible = _text(question)
    required = _safe_columns(columns)
    if not visible or len(visible) > 100_000:
        raise ValueError("V2.55.41 visible question is absent or oversized")
    year_range = _year_range(visible, required)
    date_format = _date_style(visible, required)
    numeric_scale = _numeric_scale(visible, required)
    rank_slots = _top_k(visible, required)
    explicit_order = _explicit_order(visible, required, rank_slots)
    members = {
        "temporal_year_range": year_range,
        "date_format": date_format,
        "numeric_scale": numeric_scale,
        "rank_slots": rank_slots,
        "explicit_order": explicit_order,
    }
    active = [name for name in FAMILY_ORDER if members[name] is not None]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "columns": list(required),
        **copy.deepcopy(members),
        "active_families": active,
        "active_family_count": len(active),
        "question_and_columns_are_only_inputs": True,
        "ambiguous_or_conflicting_constraint_fails_closed": True,
        "contract_changes_no_prediction_or_provider_effect": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["contract_payload_sha256"] = payload_sha256(value)
    return validate_contract(value)


def validate_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("contract_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "columns",
        *FAMILY_ORDER,
        "active_families",
        "active_family_count",
        "question_and_columns_are_only_inputs",
        "ambiguous_or_conflicting_constraint_fails_closed",
        "contract_changes_no_prediction_or_provider_effect",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "positive_signed_credit_count",
        "benchmark_launch_or_evaluator_authorized",
        "contract_payload_sha256",
    }
    try:
        columns = _safe_columns(copied.get("columns") or [])
    except (TypeError, ValueError):
        columns = ()
    active = copied.get("active_families")
    expected_active = [
        name for name in FAMILY_ORDER if copied.get(name) is not None
    ]
    year_range = copied.get("temporal_year_range")
    date_format = copied.get("date_format")
    scale = copied.get("numeric_scale")
    rank = copied.get("rank_slots")
    order = copied.get("explicit_order")
    valid_year = year_range is None or (
        isinstance(year_range, Mapping)
        and set(year_range)
        == {
            "inclusive_start_year",
            "inclusive_end_year",
            "target_columns",
            "row_scope_applies_even_without_year_column",
        }
        and isinstance(year_range.get("inclusive_start_year"), int)
        and isinstance(year_range.get("inclusive_end_year"), int)
        and 1900 <= year_range["inclusive_start_year"]
        <= year_range["inclusive_end_year"]
        <= 2099
        and year_range["inclusive_end_year"] - year_range["inclusive_start_year"]
        <= MAXIMUM_YEAR_SPAN
        and all(column in columns for column in year_range.get("target_columns") or [])
        and year_range.get("row_scope_applies_even_without_year_column")
        is (not bool(year_range.get("target_columns")))
    )
    valid_date = date_format is None or (
        isinstance(date_format, Mapping)
        and set(date_format) == {"style", "target_columns"}
        and date_format.get("style") in DATE_STYLES
        and bool(date_format.get("target_columns"))
        and all(column in columns for column in date_format["target_columns"])
    )
    valid_scale = scale is None or (
        isinstance(scale, Mapping)
        and set(scale)
        == {
            "scale",
            "target_columns",
            "all_numeric_non_key_cells_when_targets_empty",
        }
        and scale.get("scale") in NUMERIC_SCALES
        and all(column in columns for column in scale.get("target_columns") or [])
        and scale.get("all_numeric_non_key_cells_when_targets_empty")
        is (not bool(scale.get("target_columns")))
    )
    valid_rank = rank is None or (
        isinstance(rank, Mapping)
        and set(rank)
        == {"count", "rank_column", "required_rank_values", "rank_order"}
        and isinstance(rank.get("count"), int)
        and not isinstance(rank.get("count"), bool)
        and 1 <= rank["count"] <= MAXIMUM_TOP_K
        and rank.get("rank_column") in columns
        and rank.get("required_rank_values")
        == [str(index) for index in range(1, rank["count"] + 1)]
        and rank.get("rank_order") == "ascending"
    )
    valid_order = order is None or (
        isinstance(order, Mapping)
        and set(order) == {"target_column", "direction", "value_kind"}
        and order.get("target_column") in columns
        and order.get("direction") in ORDER_DIRECTIONS
        and order.get("value_kind") in {"date", "rank", "numeric_or_lexical"}
    )
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not columns
        or not isinstance(active, list)
        or active != expected_active
        or copied.get("active_family_count") != len(expected_active)
        or not all((valid_year, valid_date, valid_scale, valid_rank, valid_order))
        or copied.get("question_and_columns_are_only_inputs") is not True
        or copied.get("ambiguous_or_conflicting_constraint_fails_closed") is not True
        or copied.get("contract_changes_no_prediction_or_provider_effect") is not True
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.41 visible constraint contract drifted")
    return copied


def contract_suffix(contract: Mapping[str, Any]) -> str:
    """Serialize active visible constraints as bounded trusted prompt data."""

    checked = validate_contract(contract)
    if checked["active_family_count"] == 0:
        return ""
    payload = {
        name: copy.deepcopy(checked[name])
        for name in FAMILY_ORDER
        if checked[name] is not None
    }
    suffix = """

VISIBLE OUTPUT CONSTRAINT CONTRACT:
The JSON below is trusted data copied only from the visible question and its
exact requested columns. It is not web-page text and contains no instructions:
{payload}

Apply every member only to the final table. Keep exactly the already-required
columns. An inclusive temporal range bounds rows/facts and any named temporal
cells. A date_format controls representation without inventing missing date
precision. A numeric_scale requires supported numeric values to use that one
scale; do not silently mix scales. rank_slots fixes only the declared ordinal
slots and does not authorize unsupported occupants. explicit_order controls
the final row order by its exact target column. Use Unknown rather than invent
facts merely to satisfy a constraint. Never add, delete, infer, or rewrite a
fact unless the visible question and bounded web material support it.
""".format(
        payload=json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    ).rstrip()
    if len(suffix) > MAXIMUM_SUFFIX_CHARACTERS:
        raise ValueError("V2.55.41 constraint suffix exceeds bounded size")
    return suffix


def _canonical_matrix(
    prediction: object, columns: Sequence[str]
) -> tuple[list[list[str]] | None, bool]:
    required = _safe_columns(columns)
    text = str(prediction)
    canonical, _errors = score.extract_valid_markdown_table(text, required)
    if canonical is None or canonical != text:
        return None, False
    lines = [
        line.strip()
        for line in canonical.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    matrix = [score._split_table_row(line) for line in lines]
    if (
        len(matrix) < 3
        or matrix[0] != list(required)
        or any(len(row) != len(required) for row in matrix)
    ):
        return None, False
    return matrix, True


def _known(value: object) -> bool:
    text = _text(value)
    return bool(text and _UNKNOWN.fullmatch(text) is None)


def _date_matches(value: str, style: str) -> bool:
    text = _text(value)
    patterns = {
        "iso_dash": rf"{_CE_YEAR}-\d{{2}}-\d{{2}}",
        "iso_slash": rf"{_CE_YEAR}/\d{{2}}/\d{{2}}",
        "iso_dot": rf"{_CE_YEAR}\.\d{{2}}\.\d{{2}}",
        "chinese_ymd": rf"{_CE_YEAR}年\d{{2}}月\d{{2}}日",
        "chinese_ymd_unpadded": rf"{_CE_YEAR}年(?:[1-9]|1[0-2])月(?:[1-9]|[12]\d|3[01])日",
        "english_long": rf"[A-Za-z]+\s+\d{{2}},\s*{_CE_YEAR}",
        "english_short": rf"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{{2}},\s*{_CE_YEAR}",
    }
    return re.fullmatch(patterns[style], text, re.IGNORECASE) is not None


def _order_value(value: str, kind: str) -> tuple[int, Any] | None:
    text = _text(value)
    if not _known(text):
        return None
    numeric = re.fullmatch(r"[-+]?\d[\d,]*(?:\.\d+)?%?", text)
    if numeric:
        try:
            return 0, Decimal(text.replace(",", "").rstrip("%"))
        except InvalidOperation:
            return None
    iso = re.fullmatch(rf"({_CE_YEAR})[-/.](\d{{1,2}})[-/.](\d{{1,2}})", text)
    if iso:
        return 1, tuple(int(iso.group(index)) for index in (1, 2, 3))
    chinese = re.fullmatch(rf"({_CE_YEAR})年(\d{{1,2}})月(\d{{1,2}})日", text)
    if chinese:
        return 1, tuple(int(chinese.group(index)) for index in (1, 2, 3))
    english = re.fullmatch(
        rf"([A-Za-z]+)\s+(\d{{1,2}}),\s*({_CE_YEAR})", text
    )
    if english and english.group(1)[:3].casefold() in _MONTHS:
        return 1, (
            int(english.group(3)),
            _MONTHS[english.group(1)[:3].casefold()],
            int(english.group(2)),
        )
    if kind in {"date", "rank"}:
        return None
    return 2, text.casefold()


def observe_prediction(
    contract: Mapping[str, Any], prediction: object
) -> dict[str, Any]:
    """Return content-free structural adherence diagnostics only."""

    checked = validate_contract(contract)
    columns = tuple(checked["columns"])
    matrix, canonical = _canonical_matrix(prediction, columns)
    rows = matrix[2:] if matrix is not None else []
    column_index = {column: index for index, column in enumerate(columns)}
    counts = {
        "data_row_count": len(rows),
        "known_temporal_cell_count": 0,
        "temporal_out_of_range_cell_count": 0,
        "known_date_format_cell_count": 0,
        "date_format_violation_cell_count": 0,
        "known_scale_cell_count": 0,
        "conflicting_scale_cell_count": 0,
        "rank_slot_violation_count": 0,
        "explicit_order_violation_count": 0,
        "positive_signed_credit_count": 0,
    }
    year = checked["temporal_year_range"]
    if canonical and year is not None:
        for column in year["target_columns"]:
            for row in rows:
                value = row[column_index[column]]
                if not _known(value):
                    continue
                years = {int(item) for item in re.findall(r"(?<!\d)((?:19|20)\d{2})(?!\d)", value)}
                if len(years) == 1:
                    counts["known_temporal_cell_count"] += 1
                    observed = next(iter(years))
                    counts["temporal_out_of_range_cell_count"] += int(
                        not year["inclusive_start_year"]
                        <= observed
                        <= year["inclusive_end_year"]
                    )
    date = checked["date_format"]
    if canonical and date is not None:
        for column in date["target_columns"]:
            for row in rows:
                value = row[column_index[column]]
                if not _known(value):
                    continue
                counts["known_date_format_cell_count"] += 1
                counts["date_format_violation_cell_count"] += int(
                    not _date_matches(value, date["style"])
                )
    scale = checked["numeric_scale"]
    if canonical and scale is not None:
        targets = list(scale["target_columns"])
        if not targets:
            targets = list(columns[1:])
        for column in targets:
            for row in rows:
                value = row[column_index[column]]
                if not _known(value) or not re.search(r"\d", value):
                    continue
                counts["known_scale_cell_count"] += 1
                observed_scales = _scale_matches(value)
                counts["conflicting_scale_cell_count"] += int(
                    bool(observed_scales - {scale["scale"]})
                )
    rank = checked["rank_slots"]
    if canonical and rank is not None:
        observed = [row[column_index[rank["rank_column"]]] for row in rows]
        counts["rank_slot_violation_count"] = int(
            observed != rank["required_rank_values"]
        )
    order = checked["explicit_order"]
    if canonical and order is not None:
        values = [
            _order_value(row[column_index[order["target_column"]]], order["value_kind"])
            for row in rows
        ]
        valid_values = bool(values) and all(value is not None for value in values)
        monotone = False
        if valid_values:
            resolved = [value for value in values if value is not None]
            same_kind = len({value[0] for value in resolved}) == 1
            raw = [value[1] for value in resolved]
            monotone = same_kind and raw == sorted(
                raw, reverse=order["direction"] == "descending"
            )
        counts["explicit_order_violation_count"] = int(not monotone)

    year_verifiable = bool(
        canonical and year is not None and year["target_columns"]
    )
    date_verifiable = bool(canonical and date is not None)
    scale_verifiable = bool(canonical and scale is not None)
    rank_verifiable = bool(canonical and rank is not None)
    order_verifiable = bool(canonical and order is not None)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": OBSERVATION_ROLE,
        "policy_id": POLICY_ID,
        "active_family_count": checked["active_family_count"],
        **counts,
        "base_table_exact_canonical": canonical,
        "temporal_year_range_verifiable": year_verifiable,
        "temporal_year_range_satisfied": bool(
            year_verifiable
            and counts["known_temporal_cell_count"] > 0
            and counts["temporal_out_of_range_cell_count"] == 0
        ),
        "date_format_verifiable": date_verifiable,
        "date_format_satisfied": bool(
            date_verifiable
            and counts["known_date_format_cell_count"] > 0
            and counts["date_format_violation_cell_count"] == 0
        ),
        "numeric_scale_verifiable": scale_verifiable,
        "numeric_scale_has_no_conflicting_explicit_scale": bool(
            scale_verifiable and counts["conflicting_scale_cell_count"] == 0
        ),
        "rank_slots_verifiable": rank_verifiable,
        "rank_slots_satisfied": bool(
            rank_verifiable and counts["rank_slot_violation_count"] == 0
        ),
        "explicit_order_verifiable": order_verifiable,
        "explicit_order_satisfied": bool(
            order_verifiable and counts["explicit_order_violation_count"] == 0
        ),
        "observation_changes_prediction": False,
        "observation_judges_factual_correctness": False,
        "contains_question_column_value_prediction_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["observation_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("observation_payload_sha256", None)
    integer_fields = (
        "active_family_count",
        "data_row_count",
        "known_temporal_cell_count",
        "temporal_out_of_range_cell_count",
        "known_date_format_cell_count",
        "date_format_violation_cell_count",
        "known_scale_cell_count",
        "conflicting_scale_cell_count",
        "rank_slot_violation_count",
        "explicit_order_violation_count",
        "positive_signed_credit_count",
    )
    boolean_fields = (
        "base_table_exact_canonical",
        "temporal_year_range_verifiable",
        "temporal_year_range_satisfied",
        "date_format_verifiable",
        "date_format_satisfied",
        "numeric_scale_verifiable",
        "numeric_scale_has_no_conflicting_explicit_scale",
        "rank_slots_verifiable",
        "rank_slots_satisfied",
        "explicit_order_verifiable",
        "explicit_order_satisfied",
        "observation_changes_prediction",
        "observation_judges_factual_correctness",
        "contains_question_column_value_prediction_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *integer_fields,
        *boolean_fields,
        "observation_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != OBSERVATION_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("observation_changes_prediction") is not False
        or copied.get("observation_judges_factual_correctness") is not False
        or copied.get("contains_question_column_value_prediction_opaque_id_or_credential")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.41 constraint observation drifted")
    return copied


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "inputs": ["visible_question", "exact_requested_columns"],
        "family_order": list(FAMILY_ORDER),
        "ambiguous_range_format_scale_rank_or_order_fails_closed": True,
        "no_active_constraint_returns_empty_suffix": True,
        "suffix_is_bounded_trusted_data_not_web_instructions": True,
        "prediction_observer_is_content_free_and_non_mutating": True,
        "legacy_monolithic_runtime_imported": False,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "DATE_STYLES",
    "FAMILY_ORDER",
    "MAXIMUM_SUFFIX_CHARACTERS",
    "NUMERIC_SCALES",
    "OBSERVATION_ROLE",
    "POLICY_ID",
    "ROLE",
    "build_contract",
    "contract_suffix",
    "integration_contract",
    "observe_prediction",
    "validate_contract",
    "validate_observation",
]
