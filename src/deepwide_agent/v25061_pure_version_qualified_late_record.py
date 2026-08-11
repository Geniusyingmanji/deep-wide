"""Capability-small V2.50.60-compatible late-record representation.

This module intentionally copies the pure representation semantics needed by
the V2.50.61 external mechanism gate into one dependency-free unit.  It parses
only the caller-supplied visible question and same-forward public page.  It has
no file, environment, process, network, search, model, evaluator, benchmark,
score, reward, history, or credential capability.

The emitted representation and content-free receipts are byte-for-byte and
field-for-field compatible with V2.50.60 for the supported input domain.  The
copy is deliberate: importing the historical implementation would make its
large production runtime dependency closure reachable from a zero-model gate.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit


POLICY_ID = "v25060_version_qualified_consensus_late_record_v1"
ROLE = "v25060_version_qualified_consensus_late_record"
RECEIPT_ROLE = "v25060_content_free_version_qualified_late_record_receipt"
PAGE_CHARACTER_CAP = 5_000
MAXIMUM_INPUT_PAGE_CHARACTERS = 3_000_000
MINIMUM_RAW_PREFIX_CHARACTERS = 512
MAXIMUM_FIELD_VALUE_CHARACTERS = 1_000
MAXIMUM_IDENTITY_CHARACTERS = 256
MAXIMUM_LEADING_LINES = 12

_PARENT_POLICY_ID = "v24980_identity_target_bound_late_page_projection_v1"
_PARENT_RECEIPT_ROLE = "v24980_content_free_late_page_projection_receipt"
_TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
}
_IDENTITY_SEPARATOR = re.compile(r"[\s._+\-/]+", re.UNICODE)
_TITLE_SEPARATOR = re.compile(r"\s+(?:\||·|–|—|-)\s+|:\s+")
_VERSIONED_SURFACE = re.compile(
    r"^(?P<identity>.+?)(?:\s+|-)v?"
    r"(?P<version>\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z][0-9A-Za-z.-]*)?)$",
    re.IGNORECASE,
)
_PIPE_FIELD = re.compile(
    r"^(?P<label>[^|\r\n]{1,240}?)\s*:?[ \t]*\|[ \t]*"
    r"(?P<value>[^|\r\n]+?)\s*$"
)
_COLON_FIELD = re.compile(
    r"^(?P<label>[^|:\r\n]{1,240}?)\s*:\s+(?P<value>[^|\r\n]+?)\s*$"
)
_DETAIL_LINE = re.compile(
    r"^(?P<label>[^|\r\n]{1,240}?)\s*:\s*\|\s*(?P<value>.+?)\s*$"
)
_GENERIC_IDENTITY_SEGMENTS = frozenset(
    {
        "about",
        "details",
        "detail",
        "docs",
        "documentation",
        "download",
        "home",
        "html",
        "index",
        "latest",
        "official",
        "overview",
        "package",
        "packages",
        "project",
        "projects",
        "readme",
        "release",
        "releases",
        "search",
        "site",
        "web",
        "www",
    }
)

_COUNT_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_schema_column_count",
    "visible_target_field_count",
    "labelled_identity_binding_count",
    "exact_consensus_identity_binding_count",
    "url_identity_candidate_count",
    "qualified_title_identity_candidate_count",
    "qualified_leading_identity_candidate_count",
    "version_qualified_consensus_binding_count",
    "unique_bound_identity_count",
    "target_detail_candidate_count",
    "uniquely_bound_target_field_count",
    "duplicate_or_conflicting_target_count",
    "late_target_field_count",
    "discovered_record_count",
    "admissible_record_count",
    "admissible_bound_observation_count",
    "retained_record_count",
    "retained_bound_observation_count",
    "compact_prefix_characters",
    "raw_prefix_characters_retained",
    "output_characters",
    "projection_failure_count",
    "positive_signed_credit_count",
)
_PARENT_COUNT_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_schema_column_count",
    "discovered_record_count",
    "discovered_row_key_count",
    "conflicting_coordinate_count",
    "admissible_record_count",
    "admissible_bound_observation_count",
    "retained_record_count",
    "retained_bound_observation_count",
    "oversized_record_count",
    "compact_prefix_characters",
    "raw_prefix_characters_retained",
    "output_characters",
    "projection_failure_count",
    "positive_signed_credit_count",
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _canonicalize_url(url: str) -> str:
    raw = str(url).strip()
    if not raw:
        return ""
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
            return ""
        if parsed.username or parsed.password:
            return ""
        _ = parsed.port
    except ValueError:
        return ""
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_")
        and key.casefold() not in _TRACKING_QUERY_KEYS
    ]
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            path,
            urlencode(query),
            "",
        )
    )


# The following visible-schema parser is the pure part of the frozen V2.42.86
# parser.  Keeping it local prevents its model/runtime imports from entering
# the forward dependency closure.
_SCHEMA_ANCHORS = (
    re.compile(r"(?:表格中的)?(?:列名|栏名)(?:依次)?(?:为|是)\s*[：:]\s*", re.IGNORECASE),
    re.compile(r"(?:the\s+)?column\s+(?:names?|headers?)[^:\n]{0,180}[：:]\s*", re.IGNORECASE),
    re.compile(
        r"(?:with|using|provide|include)\s+(?:the\s+)?following\s+columns?"
        r"(?:\s*\([^\n)]*\))?[^:\n]{0,80}[：:]\s*",
        re.IGNORECASE,
    ),
    re.compile(
        r"columns?\s*(?:are|is|should\s+be|must\s+be|as\s+follows)"
        r"[^:\n]{0,120}[：:]\s*",
        re.IGNORECASE,
    ),
)
_INSTRUCTION_CUE = re.compile(
    r"(?:[-*•]\s*)?(?:the\s+|if\s+|please\s+|do\s+not\s+|don't\s+|format\s+|"
    r"note\s*:|notes\s*:|for\s+|list\s+|use\s+|awards?\s+only\b|"
    r"不要|请直接|输出格式|时间类型|若|如果)",
    re.IGNORECASE,
)
_SEGMENT_INSTRUCTION_CUE = re.compile(
    r"(?:[-*•]\s*)?(?:if\s+|please\s+|do\s+not\s+|don't\s+|format\s+|"
    r"note\s*:|notes\s*:|instructions?\s*:|as\s+for\s+|each\s+row\b|"
    r"不要|请直接|输出格式|时间类型|若|如果|无法统计|输出采用)",
    re.IGNORECASE,
)


def _column_clause(raw: str) -> str:
    text = str(raw).lstrip()
    stack: list[str] = []
    quote: str | None = None
    quote_start = -1
    closing = {"(": ")", "（": "）", "[": "]", "【": "】", "{": "}"}
    for index, character in enumerate(text):
        if quote is not None:
            if character == quote:
                quote = None
                quote_start = -1
            elif character == "\n" or (
                character in "。；;"
                and _INSTRUCTION_CUE.match(text[index + 1 :].lstrip())
            ):
                if quote_start >= 0:
                    return text[:quote_start].rstrip(" .。；;")
            continue
        if character in {'"', "“", "‘"}:
            quote = {"“": "”", "‘": "’"}.get(character, character)
            quote_start = index
            continue
        if character in closing:
            stack.append(closing[character])
            continue
        if stack and character == stack[-1]:
            stack.pop()
            continue
        if stack:
            continue
        if character == "\n":
            return text[:index].strip()
        if re.match(
            r"(?:注|注意|说明|instructions?)\s*[:：]",
            text[index:],
            re.IGNORECASE,
        ):
            return text[:index].rstrip(" ,，.。；;")
        if character in "。；;":
            return text[:index].strip()
        if character == ".":
            suffix = text[index + 1 :].lstrip()
            if (
                _INSTRUCTION_CUE.match(suffix)
                or (
                    suffix
                    and (
                        suffix[0].isupper()
                        or re.match(r"[\u4e00-\u9fff]", suffix)
                    )
                )
                or not suffix
            ):
                return text[:index].strip()
    return text.strip().strip("。.;；")


def _top_level_split(raw: str) -> list[str]:
    values: list[str] = []
    current: list[str] = []
    stack: list[str] = []
    quote: str | None = None
    escaped = False
    closing = {"(": ")", "（": "）", "[": "]", "【": "】", "{": "}"}
    for character in str(raw):
        if escaped:
            current.append(character)
            escaped = False
            continue
        if character == "\\":
            current.append(character)
            escaped = True
            continue
        if quote is not None:
            current.append(character)
            if character == quote:
                quote = None
            continue
        if character in {'"', "“", "‘"}:
            quote = {"“": "”", "‘": "’"}.get(character, character)
            current.append(character)
            continue
        if character in closing:
            stack.append(closing[character])
            current.append(character)
            continue
        if stack and character == stack[-1]:
            stack.pop()
            current.append(character)
            continue
        if character in {",", "，", "、", "|", "\n"} and not stack:
            values.append("".join(current))
            current = []
            continue
        current.append(character)
    values.append("".join(current))
    if len(values) == 1:
        tokens = str(raw).split()
        if 2 <= len(tokens) <= 20 and all(
            re.search(r"[\u4e00-\u9fff]", token) for token in tokens
        ):
            return tokens
    return values


def _clean_column(value: str) -> str:
    text = str(value).strip().replace("\u00a0", " ")
    text = re.sub(r"^\s*(?:[-*•]+\s*|\(?\d+\)?[.、)]\s*)", "", text)
    text = re.sub(r"[\s`。.;；]+$", "", text)
    text = re.sub(r"^(?:and|以及|及)\s+", "", text, flags=re.IGNORECASE)
    return text.strip()


def _normalize_column(value: object) -> str:
    return re.sub(r"[\s`*_：:]+", "", str(value or "")).casefold()


def extract_robust_visible_columns(question: str) -> list[str]:
    visible = str(question or "")
    matches: list[tuple[int, int]] = []
    for pattern in _SCHEMA_ANCHORS:
        matches.extend((match.start(), match.end()) for match in pattern.finditer(visible))
    for _start, end in sorted(matches):
        clause = _column_clause(visible[end:])
        columns: list[str] = []
        for raw_value in _top_level_split(clause):
            value = _clean_column(raw_value)
            if not value:
                continue
            if _SEGMENT_INSTRUCTION_CUE.match(value):
                break
            columns.append(value)
        normalized = [_normalize_column(value) for value in columns]
        if (
            1 <= len(columns) <= 20
            and all(len(value) <= 80 for value in columns)
            and all(normalized)
            and len(set(normalized)) == len(normalized)
        ):
            return columns
    return []


def _normalize(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _canonical(value: object) -> str:
    return _normalize(value).casefold()


def _identity_key(value: object) -> str:
    text = _IDENTITY_SEPARATOR.sub(" ", _canonical(value)).strip(" ,:;|()[]{}")
    return " ".join(text.split())


def _safe_surface(value: object, *, maximum: int) -> str | None:
    text = _normalize(value).strip(" |\t\r\n")
    if (
        not text
        or len(text) > maximum
        or "\x00" in text
        or any(ord(character) < 32 for character in text)
        or _canonical(text) in {"unknown", "n/a", "na", "none", "null", "-"}
    ):
        return None
    return text


def _safe_identity(value: object) -> str | None:
    text = _normalize(value).strip(" \t\r\n|:;,-–—")
    key = _identity_key(text)
    if (
        not text
        or not key
        or len(text) > MAXIMUM_IDENTITY_CHARACTERS
        or "\x00" in text
        or any(ord(character) < 32 for character in text)
        or key in {"unknown", "n a", "na", "none", "null"}
        or re.fullmatch(r"[-.:;,/]+", text) is not None
    ):
        return None
    return text


def _page(raw: Mapping[str, Any]) -> tuple[dict[str, str], str]:
    if not isinstance(raw, Mapping):
        raise ValueError("V2.50.61 page is not a mapping")
    url = _canonicalize_url(str(raw.get("url") or ""))
    title = _normalize(raw.get("title") or "")[:500]
    value = raw.get("text")
    if value is None:
        value = raw.get("raw_content")
    if value is None:
        value = raw.get("content")
    text = str(value or "")
    if (
        not url
        or not text
        or "\x00" in text
        or len(text) > MAXIMUM_INPUT_PAGE_CHARACTERS
    ):
        raise ValueError("V2.50.61 page identity or text drifted")
    return {"url": url, "title": title, "content": text}, text


def _schema(question: str) -> tuple[str, ...]:
    return tuple(str(value) for value in extract_robust_visible_columns(question))


def _labelled_identity(value: object, row_label: str) -> str | None:
    text = _normalize(value)
    label = _normalize(row_label)
    if not text or not label:
        return None
    pattern = re.compile(
        rf"(?<!\w){re.escape(label)}(?!\w)"
        rf"(?:\s*[:#=|–—-]\s*|\s+)(?P<identity>.+?)\s*$",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        return None
    identity = _safe_identity(matches[0].group("identity"))
    if identity is None or any(mark in identity for mark in (" | ", " — ", " – ")):
        return None
    return identity


def _surface_candidates(
    title: str, text: str, row_label: str
) -> tuple[dict[str, str], dict[str, str]]:
    titles: dict[str, str] = {}
    title_identity = _labelled_identity(title, row_label)
    if title_identity is not None:
        titles[_identity_key(title_identity)] = title_identity
    leading: dict[str, str] = {}
    lines = [line for line in str(text).splitlines() if _normalize(line)]
    for line in lines[:MAXIMUM_LEADING_LINES]:
        identity = _labelled_identity(line, row_label)
        if identity is not None:
            leading.setdefault(_identity_key(identity), identity)
    return titles, leading


def _detail_field_map(
    text: str, targets: Sequence[str]
) -> tuple[dict[str, str], int, int, int]:
    aliases = {_canonical(target): str(target) for target in targets}
    values: dict[str, list[str]] = {key: [] for key in aliases}
    lines = [_normalize(raw) for raw in str(text).splitlines()]
    raw_count = 0
    target_count = 0
    for index, line in enumerate(lines):
        if not line:
            continue
        match = _DETAIL_LINE.fullmatch(line)
        if match is not None:
            raw_count += 1
            key = _canonical(match.group("label"))
            if key in aliases:
                target_count += 1
                safe = _safe_surface(
                    match.group("value"), maximum=MAXIMUM_FIELD_VALUE_CHARACTERS
                )
                if safe is not None:
                    values[key].append(safe)
            continue
        key = _canonical(line)
        if key in aliases:
            raw_count += 1
            target_count += 1
            following = next((value for value in lines[index + 1 :] if value), "")
            safe = _safe_surface(following, maximum=MAXIMUM_FIELD_VALUE_CHARACTERS)
            if safe is not None and _canonical(safe) not in aliases:
                values[key].append(safe)
            continue
        for alias, display in aliases.items():
            label_pattern = re.escape(_normalize(display)).replace(r"\ ", r"\s+")
            sentence = re.fullmatch(
                rf"{label_pattern}\s+(?P<value>.+?)\.", line, re.IGNORECASE
            )
            if sentence is None:
                continue
            raw_count += 1
            target_count += 1
            safe = _safe_surface(
                sentence.group("value"), maximum=MAXIMUM_FIELD_VALUE_CHARACTERS
            )
            if safe is not None:
                values[alias].append(safe)
            break
    conflicts = sum(
        len(items) != 1 or len({_canonical(value) for value in items}) != 1
        for items in values.values()
    )
    fields = {
        aliases[key]: items[0]
        for key, items in values.items()
        if len(items) == 1
    }
    return fields, raw_count, target_count, conflicts


def _row_label_candidates(text: str, row_label: str) -> dict[str, str]:
    fields, _raw, _target, conflicts = _detail_field_map(text, [row_label])
    if conflicts != 0 or set(fields) != {row_label}:
        return {}
    identity = _safe_identity(fields[row_label])
    return {_identity_key(identity): identity} if identity is not None else {}


def _url_identity_keys(url: str) -> set[str]:
    parsed = urlsplit(str(url))
    values = [unquote(part) for part in parsed.path.split("/") if part]
    values.extend(unquote(value) for _key, value in parse_qsl(parsed.query))
    output: set[str] = set()
    for raw in values:
        safe = _safe_identity(raw)
        if safe is not None:
            output.add(_identity_key(safe))
        stem = re.sub(r"\.(?:html?|json|xml|txt)$", "", raw, flags=re.IGNORECASE)
        if stem != raw:
            safe_stem = _safe_identity(stem)
            if safe_stem is not None:
                output.add(_identity_key(safe_stem))
    return output


def _bound_labelled_identity(
    *, title: str, text: str, url: str, row_label: str
) -> tuple[str | None, dict[str, int]]:
    titles, leading = _surface_candidates(title, text, row_label)
    row_fields = _row_label_candidates(text, row_label)
    path_keys = _url_identity_keys(url)
    all_keys = set(titles) | set(leading) | set(row_fields)
    joint = [
        key
        for key in sorted(all_keys)
        if key in path_keys
        and key in titles
        and (key in leading or key in row_fields)
    ]
    identity = None
    if len(joint) == 1:
        key = joint[0]
        identity = titles.get(key) or leading.get(key) or row_fields.get(key)
    return identity, {
        "title_identity_candidate_count": len(titles),
        "leading_identity_candidate_count": len(leading),
        "row_label_identity_candidate_count": len(row_fields),
        "url_path_identity_candidate_count": len(path_keys),
        "jointly_bound_identity_count": len(joint),
    }


def _identity_candidate(value: object) -> str | None:
    safe = _safe_identity(value)
    if safe is None:
        return None
    key = _identity_key(safe)
    tokens = tuple(key.split())
    if (
        key in _GENERIC_IDENTITY_SEGMENTS
        or (tokens and all(token in _GENERIC_IDENTITY_SEGMENTS for token in tokens))
        or len(key) < 2
        or key.isdecimal()
        or re.fullmatch(r"v?\d+(?:[._-]\d+)+", key, re.IGNORECASE) is not None
    ):
        return None
    return safe


def _surface_segments(value: object) -> dict[str, str]:
    text = _normalize(value).strip("#*_=~ \t\r\n")
    if not text:
        return {}
    output: dict[str, str] = {}
    for raw in _TITLE_SEPARATOR.split(text):
        candidate = _identity_candidate(raw.strip("#*_=~ [](){}"))
        if candidate is not None:
            output.setdefault(_identity_key(candidate), candidate)
    return output


def _url_candidates(url: str) -> dict[str, str]:
    try:
        parsed = urlsplit(str(url))
    except ValueError:
        return {}
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
        return {}
    output: dict[str, str] = {}
    for raw in (unquote(part) for part in parsed.path.split("/") if part):
        stem = re.sub(
            r"\.(?:html?|json|xml|txt|php|aspx?)$", "", raw, flags=re.IGNORECASE
        )
        candidate = _identity_candidate(stem)
        if candidate is not None:
            output.setdefault(_identity_key(candidate), candidate)
    return output


def _consensus_identity(
    *, title: str, text: str, url: str
) -> tuple[str | None, dict[str, int]]:
    urls = _url_candidates(url)
    titles = _surface_segments(title)
    leading: dict[str, str] = {}
    lines = [line for line in str(text).splitlines() if _normalize(line)]
    title_echo_excluded = False
    content_lines: list[str] = []
    for line in lines:
        if not title_echo_excluded and _normalize(line) == _normalize(title):
            title_echo_excluded = True
            continue
        content_lines.append(line)
    for line in content_lines[:MAXIMUM_LEADING_LINES]:
        for key, value in _surface_segments(line).items():
            leading.setdefault(key, value)
    joint = sorted(set(urls) & set(titles) & set(leading))
    identity = titles[joint[0]] if len(joint) == 1 else None
    return identity, {
        "url_identity_candidate_count": len(urls),
        "title_segment_identity_candidate_count": len(titles),
        "leading_segment_identity_candidate_count": len(leading),
        "consensus_identity_binding_count": len(joint),
    }


def _versioned_segments(value: object) -> dict[tuple[str, str], str]:
    text = _normalize(value).strip("#*_=~ \t\r\n")
    if not text:
        return {}
    output: dict[tuple[str, str], str] = {}
    for raw in _TITLE_SEPARATOR.split(text):
        segment = raw.strip("#*_=~ [](){}")
        match = _VERSIONED_SURFACE.fullmatch(segment)
        if match is None:
            continue
        identity = _identity_candidate(match.group("identity"))
        if identity is None:
            continue
        key = (_identity_key(identity), match.group("version").casefold())
        output.setdefault(key, identity)
    return output


def _version_qualified_consensus(
    *, title: str, text: str, url: str
) -> tuple[str | None, dict[str, int]]:
    urls = _url_candidates(url)
    titles = _versioned_segments(title)
    leading: dict[tuple[str, str], str] = {}
    lines = [line for line in str(text).splitlines() if _normalize(line)]
    title_echo_excluded = False
    content_lines: list[str] = []
    for line in lines:
        if not title_echo_excluded and _normalize(line) == _normalize(title):
            title_echo_excluded = True
            continue
        content_lines.append(line)
    for line in content_lines[:MAXIMUM_LEADING_LINES]:
        for key, identity in _versioned_segments(line).items():
            leading.setdefault(key, identity)
    joint: list[tuple[str, str]] = []
    for identity_key in sorted(set(urls)):
        title_versions = {version for name, version in titles if name == identity_key}
        leading_versions = {
            version for name, version in leading if name == identity_key
        }
        if len(title_versions) == 1 and title_versions == leading_versions:
            joint.append((identity_key, next(iter(title_versions))))
    identity = urls[joint[0][0]] if len(joint) == 1 else None
    return identity, {
        "url_identity_candidate_count": len(urls),
        "qualified_title_identity_candidate_count": len(titles),
        "qualified_leading_identity_candidate_count": len(leading),
        "version_qualified_consensus_binding_count": len(joint),
    }


def _line_vector(text: str) -> list[tuple[int, str]]:
    output: list[tuple[int, str]] = []
    offset = 0
    for raw in str(text).splitlines(keepends=True):
        output.append((offset, _normalize(raw)))
        offset += len(raw)
    if not output and text:
        output.append((0, _normalize(text)))
    return output


def _field_map_with_positions(
    text: str, targets: Sequence[str]
) -> tuple[dict[str, str], dict[str, int], int, int]:
    aliases = {_canonical(target): str(target) for target in targets}
    if len(aliases) != len(targets):
        return {}, {}, 0, len(targets)
    values: dict[str, list[tuple[str, int]]] = {key: [] for key in aliases}
    lines = _line_vector(text)
    target_candidates = 0

    def safe_field(raw: object) -> str | None:
        safe = _safe_surface(raw, maximum=MAXIMUM_FIELD_VALUE_CHARACTERS)
        return safe if safe is not None and "|" not in safe else None

    for index, (offset, line) in enumerate(lines):
        if not line:
            continue
        direct = _PIPE_FIELD.fullmatch(line) or _COLON_FIELD.fullmatch(line)
        if direct is not None:
            key = _canonical(direct.group("label"))
            if key not in aliases:
                continue
            target_candidates += 1
            safe = safe_field(direct.group("value"))
            if safe is not None and _canonical(safe) not in aliases:
                values[key].append((safe, offset))
            continue
        key = _canonical(line)
        if key not in aliases:
            for alias, display in aliases.items():
                label_pattern = re.escape(_normalize(display)).replace(
                    r"\ ", r"\s+"
                )
                sentence = re.fullmatch(
                    rf"{label_pattern}\s+(?P<value>.+?)\.", line, re.IGNORECASE
                )
                if sentence is None:
                    continue
                target_candidates += 1
                safe = safe_field(sentence.group("value"))
                if safe is not None:
                    values[alias].append((safe, offset))
                break
            continue
        target_candidates += 1
        following = next(
            (
                (next_offset, next_line)
                for next_offset, next_line in lines[index + 1 :]
                if next_line
            ),
            None,
        )
        if following is None:
            continue
        next_offset, next_line = following
        safe = safe_field(next_line)
        if safe is not None and _canonical(safe) not in aliases:
            values[key].append((safe, next_offset))
    conflicts = sum(
        len(items) != 1
        or len({_canonical(value) for value, _offset in items}) != 1
        for items in values.values()
    )
    fields = {
        aliases[key]: items[0][0]
        for key, items in values.items()
        if len(items) == 1
    }
    positions = {
        aliases[key]: items[0][1]
        for key, items in values.items()
        if len(items) == 1
    }
    return fields, positions, target_candidates, conflicts


def _bound_record(
    question: str, page: Mapping[str, Any]
) -> tuple[dict[str, str] | None, dict[str, int], dict[str, str], str]:
    normalized_page, raw_text = _page(page)
    schema = _schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    labelled_identity = None
    labelled_count = 0
    exact_identity = None
    exact_count = 0
    qualified_identity = None
    qualified_counts = {
        "url_identity_candidate_count": 0,
        "qualified_title_identity_candidate_count": 0,
        "qualified_leading_identity_candidate_count": 0,
        "version_qualified_consensus_binding_count": 0,
    }
    fields: dict[str, str] = {}
    positions: dict[str, int] = {}
    target_candidates = conflicts = failure = 0
    try:
        if len(schema) >= 2:
            labelled_identity, labelled = _bound_labelled_identity(
                title=normalized_page["title"],
                text=raw_text,
                url=normalized_page["url"],
                row_label=schema[0],
            )
            labelled_count = int(
                labelled_identity is not None
                and labelled["jointly_bound_identity_count"] == 1
            )
            exact_identity, exact_counts = _consensus_identity(
                title=normalized_page["title"],
                text=raw_text,
                url=normalized_page["url"],
            )
            exact_count = int(
                exact_identity is not None
                and exact_counts["consensus_identity_binding_count"] == 1
            )
            qualified_identity, qualified_counts = _version_qualified_consensus(
                title=normalized_page["title"],
                text=raw_text,
                url=normalized_page["url"],
            )
            fields, positions, target_candidates, conflicts = _field_map_with_positions(
                raw_text, targets
            )
    except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
        failure = 1
        labelled_identity = exact_identity = qualified_identity = None
        labelled_count = exact_count = 0
        qualified_counts = {name: 0 for name in qualified_counts}
        fields = {}
        positions = {}
        target_candidates = conflicts = 0

    identities: dict[str, str] = {}
    for identity in (labelled_identity, exact_identity, qualified_identity):
        if identity is not None:
            identities.setdefault(_identity_key(identity), identity)
    identity = next(iter(identities.values())) if len(identities) == 1 else None
    unique_fields = len(fields)
    late_fields = sum(
        positions.get(target, -1) >= PAGE_CHARACTER_CAP for target in targets
    )
    complete = bool(
        identity is not None
        and len(schema) >= 2
        and unique_fields == len(targets)
        and conflicts == 0
        and failure == 0
    )
    admissible = bool(complete and late_fields >= 1)
    record = (
        {schema[0]: identity, **{target: fields[target] for target in targets}}
        if admissible
        else None
    )
    counts = {
        "input_page_count": 1,
        "input_content_characters": len(raw_text),
        "input_characters_beyond_parent_prefix": max(
            0, len(raw_text) - PAGE_CHARACTER_CAP
        ),
        "visible_schema_column_count": len(schema),
        "visible_target_field_count": len(targets),
        "labelled_identity_binding_count": labelled_count,
        "exact_consensus_identity_binding_count": exact_count,
        **qualified_counts,
        "unique_bound_identity_count": len(identities),
        "target_detail_candidate_count": target_candidates,
        "uniquely_bound_target_field_count": unique_fields,
        "duplicate_or_conflicting_target_count": conflicts,
        "late_target_field_count": late_fields,
        "discovered_record_count": int(complete),
        "admissible_record_count": int(admissible),
        "admissible_bound_observation_count": len(targets) if admissible else 0,
        "projection_failure_count": failure,
    }
    return record, counts, normalized_page, raw_text


def _content_free_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": _PARENT_RECEIPT_ROLE,
        "policy_id": _PARENT_POLICY_ID,
        **{name: int(value[name]) for name in _PARENT_COUNT_FIELDS},
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "exact_parent_prefix_handoff": bool(value["exact_parent_prefix_handoff"]),
        "canonical_source_identity_bound": True,
        "visible_target_schema_bound": True,
        "page_local_record_identity_bound": True,
        "conflicting_coordinates_omitted": True,
        "compact_records_atomic_and_unsplit": True,
        "same_forward_decoded_page_only": True,
        "parent_page_character_cap_preserved": True,
        "parent_page_character_count_preserved": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_url_title_page_record_value_prediction_answer_hash_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return _validate_content_free_receipt(output)


def _validate_content_free_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "canonical_source_identity_bound",
        "visible_target_schema_bound",
        "page_local_record_identity_bound",
        "conflicting_coordinates_omitted",
        "compact_records_atomic_and_unsplit",
        "same_forward_decoded_page_only",
        "parent_page_character_cap_preserved",
        "parent_page_character_count_preserved",
        "entropy_information_gain_shadow_only",
    )
    false_flags = (
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "contains_question_url_title_page_record_value_prediction_answer_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    boolean_fields = (
        "candidate_evidence_changed",
        "mechanism_engaged",
        "exact_parent_prefix_handoff",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_PARENT_COUNT_FIELDS,
        *boolean_fields,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != _PARENT_RECEIPT_ROLE
        or copied.get("policy_id") != _PARENT_POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _PARENT_COUNT_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in boolean_fields)
        or copied["input_page_count"] != 1
        or copied["input_characters_beyond_parent_prefix"]
        != max(0, copied["input_content_characters"] - PAGE_CHARACTER_CAP)
        or copied["retained_record_count"] > copied["admissible_record_count"]
        or copied["retained_bound_observation_count"]
        > copied["admissible_bound_observation_count"]
        or copied["output_characters"]
        != min(copied["input_content_characters"], PAGE_CHARACTER_CAP)
        or copied["raw_prefix_characters_retained"] > PAGE_CHARACTER_CAP
        or copied["positive_signed_credit_count"] != 0
        or copied["projection_failure_count"] not in {0, 1}
        or copied["mechanism_engaged"]
        is not (
            copied["retained_record_count"] > 0
            and copied["retained_bound_observation_count"] > 0
            and copied["candidate_evidence_changed"] is True
            and copied["projection_failure_count"] == 0
        )
        or copied["exact_parent_prefix_handoff"]
        is not (copied["candidate_evidence_changed"] is False)
        or copied["exact_parent_prefix_handoff"]
        and (
            copied["compact_prefix_characters"] != 0
            or copied["retained_record_count"] != 0
            or copied["retained_bound_observation_count"] != 0
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.61 inherited content-free receipt drifted")
    return copied


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "exact_parent_prefix_handoff": bool(value["exact_parent_prefix_handoff"]),
        "exact_and_labelled_parent_identity_routes_preserved": True,
        "version_qualified_route_requires_exact_url_name_and_same_version_on_two_page_surfaces": True,
        "one_exact_decoder_title_echo_excluded_from_leading_surface": True,
        "query_parameters_never_supply_identity": True,
        "target_fields_exact_label_unique_and_same_page": True,
        "at_least_one_complete_target_observation_beyond_parent_prefix_required": True,
        "source_url_record_identity_target_and_value_atomically_bound": True,
        "compact_record_atomic_and_unsplit": True,
        "same_forward_decoded_page_only": True,
        "parent_page_character_cap_and_count_preserved": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
        "contains_question_identity_url_title_page_record_value_prediction_answer_hash_or_credential": False,
        "file_environment_process_network_search_model_or_evaluator_accessed": False,
        "benchmark_or_evaluator_launch_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    bool_fields = (
        "candidate_evidence_changed",
        "mechanism_engaged",
        "exact_parent_prefix_handoff",
    )
    true_flags = (
        "exact_and_labelled_parent_identity_routes_preserved",
        "version_qualified_route_requires_exact_url_name_and_same_version_on_two_page_surfaces",
        "one_exact_decoder_title_echo_excluded_from_leading_surface",
        "query_parameters_never_supply_identity",
        "target_fields_exact_label_unique_and_same_page",
        "at_least_one_complete_target_observation_beyond_parent_prefix_required",
        "source_url_record_identity_target_and_value_atomically_bound",
        "compact_record_atomic_and_unsplit",
        "same_forward_decoded_page_only",
        "parent_page_character_cap_and_count_preserved",
    )
    false_flags = (
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read",
        "contains_question_identity_url_title_page_record_value_prediction_answer_hash_or_credential",
        "file_environment_process_network_search_model_or_evaluator_accessed",
        "benchmark_or_evaluator_launch_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *bool_fields,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    counts_valid = all(
        not isinstance(copied.get(name), bool)
        and isinstance(copied.get(name), int)
        and copied[name] >= 0
        for name in _COUNT_FIELDS
    )
    target_count = copied.get("visible_target_field_count", 0)
    discovered = bool(
        counts_valid
        and copied.get("unique_bound_identity_count") == 1
        and target_count > 0
        and copied.get("uniquely_bound_target_field_count") == target_count
        and copied.get("duplicate_or_conflicting_target_count") == 0
        and copied.get("projection_failure_count") == 0
    )
    admissible = bool(discovered and copied.get("late_target_field_count", 0) >= 1)
    retained = copied.get("retained_record_count") == 1
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not counts_valid
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied["input_page_count"] != 1
        or copied["input_characters_beyond_parent_prefix"]
        != max(0, copied["input_content_characters"] - PAGE_CHARACTER_CAP)
        or target_count != max(0, copied["visible_schema_column_count"] - 1)
        or copied["labelled_identity_binding_count"] not in {0, 1}
        or copied["exact_consensus_identity_binding_count"] not in {0, 1}
        or copied["version_qualified_consensus_binding_count"]
        > min(
            copied["url_identity_candidate_count"],
            copied["qualified_title_identity_candidate_count"],
            copied["qualified_leading_identity_candidate_count"],
        )
        or copied["unique_bound_identity_count"] > 3
        or copied["late_target_field_count"]
        > copied["uniquely_bound_target_field_count"]
        or copied["discovered_record_count"] != int(discovered)
        or copied["admissible_record_count"] != int(admissible)
        or copied["admissible_bound_observation_count"]
        != (target_count if admissible else 0)
        or copied["retained_record_count"] > copied["admissible_record_count"]
        or copied["retained_bound_observation_count"]
        != (target_count if retained else 0)
        or copied["output_characters"]
        != min(copied["input_content_characters"], PAGE_CHARACTER_CAP)
        or copied["raw_prefix_characters_retained"] > PAGE_CHARACTER_CAP
        or copied["projection_failure_count"] not in {0, 1}
        or copied["positive_signed_credit_count"] != 0
        or copied["candidate_evidence_changed"] is not retained
        or copied["mechanism_engaged"] is not retained
        or copied["exact_parent_prefix_handoff"] is retained
        or (retained and copied["compact_prefix_characters"] <= 0)
        or copied["exact_parent_prefix_handoff"]
        and (
            copied["compact_prefix_characters"] != 0
            or copied["retained_record_count"] != 0
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.61 version-qualified receipt drifted")
    return copied


def extract_record(question: str, page: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.61 visible question is absent")
    record, _counts, _normalized, _text = _bound_record(question, page)
    if record is None:
        raise ValueError("V2.50.61 version-qualified record is not admissible")
    return record


def build_representation(
    question: str,
    page: Mapping[str, Any],
    *,
    page_character_cap: int = PAGE_CHARACTER_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.50.61 visible question is absent")
    if page_character_cap != PAGE_CHARACTER_CAP:
        raise ValueError("V2.50.61 parent page cap drifted")
    record, counts, normalized_page, raw_text = _bound_record(question, page)
    schema = _schema(question)
    targets = schema[1:] if len(schema) >= 2 else ()
    raw_prefix = raw_text[:PAGE_CHARACTER_CAP]
    representation = raw_prefix
    compact_chars = 0
    raw_retained = len(raw_prefix)
    if record is not None:
        identity = record[schema[0]]
        compact = "\n".join(
            (
                "[VERSION-QUALIFIED CONSENSUS-BOUND LATE RECORD]",
                "untrusted_public_page_record=true",
                "source_url=" + normalized_page["url"],
                "row_key_label=" + json.dumps(schema[0], ensure_ascii=False),
                "target_columns="
                + json.dumps(list(targets), ensure_ascii=False, separators=(",", ":")),
                json.dumps(
                    {
                        "record_id": hashlib.sha256(
                            (
                                normalized_page["url"]
                                + "\x1f"
                                + _identity_key(identity)
                            ).encode("utf-8")
                        ).hexdigest()[:24],
                        "row": identity,
                        "cells": [[target, record[target]] for target in targets],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "[/VERSION-QUALIFIED CONSENSUS-BOUND LATE RECORD]",
            )
        )
        marker = "\n[INHERITED RAW PAGE PREFIX]\n"
        raw_budget = len(raw_prefix) - len(compact) - len(marker)
        if raw_budget >= MINIMUM_RAW_PREFIX_CHARACTERS:
            representation = compact + marker + raw_text[:raw_budget]
            compact_chars = len(compact)
            raw_retained = min(len(raw_text), raw_budget)
    changed = representation != raw_prefix
    retained = int(changed and record is not None)
    target_count = len(targets)
    counts.update(
        {
            "retained_record_count": retained,
            "retained_bound_observation_count": target_count if retained else 0,
            "compact_prefix_characters": compact_chars if retained else 0,
            "raw_prefix_characters_retained": raw_retained if retained else len(raw_prefix),
            "output_characters": len(representation),
            "positive_signed_credit_count": 0,
            "candidate_evidence_changed": changed,
            "mechanism_engaged": bool(retained),
            "exact_parent_prefix_handoff": not changed,
        }
    )
    receipt = _receipt(counts)
    inherited = _content_free_receipt(
        {
            "input_page_count": 1,
            "input_content_characters": len(raw_text),
            "input_characters_beyond_parent_prefix": max(
                0, len(raw_text) - PAGE_CHARACTER_CAP
            ),
            "visible_schema_column_count": len(schema),
            "discovered_record_count": counts["discovered_record_count"],
            "discovered_row_key_count": counts["discovered_record_count"],
            "conflicting_coordinate_count": counts[
                "duplicate_or_conflicting_target_count"
            ],
            "admissible_record_count": counts["admissible_record_count"],
            "admissible_bound_observation_count": counts[
                "admissible_bound_observation_count"
            ],
            "retained_record_count": retained,
            "retained_bound_observation_count": target_count if retained else 0,
            "oversized_record_count": 0,
            "compact_prefix_characters": compact_chars if retained else 0,
            "raw_prefix_characters_retained": raw_retained if retained else len(raw_prefix),
            "output_characters": len(representation),
            "projection_failure_count": counts["projection_failure_count"],
            "positive_signed_credit_count": 0,
            "candidate_evidence_changed": changed,
            "mechanism_engaged": bool(retained),
            "exact_parent_prefix_handoff": not changed,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "control_evidence": raw_prefix,
        "candidate_evidence": representation,
        "control_evidence_sha256": hashlib.sha256(raw_prefix.encode()).hexdigest(),
        "candidate_evidence_sha256": hashlib.sha256(
            representation.encode()
        ).hexdigest(),
        "content_free_receipt": inherited,
        "version_qualified_late_record_receipt": receipt,
        "same_forward_decoded_page_only": True,
        "same_exact_character_budget": len(raw_prefix) == len(representation),
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
        "file_environment_process_network_search_model_or_evaluator_accessed": False,
        "benchmark_or_evaluator_launch_authorized": False,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_representation(
        value,
        question=question,
        page=page,
        page_character_cap=page_character_cap,
        replay=False,
    )


def validate_representation(
    value: Mapping[str, Any],
    *,
    question: str,
    page: Mapping[str, Any],
    page_character_cap: int = PAGE_CHARACTER_CAP,
    replay: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    control = copied.get("control_evidence")
    candidate = copied.get("candidate_evidence")
    inherited = copied.get("content_free_receipt")
    receipt = copied.get("version_qualified_late_record_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "control_evidence",
        "candidate_evidence",
        "control_evidence_sha256",
        "candidate_evidence_sha256",
        "content_free_receipt",
        "version_qualified_late_record_receipt",
        "same_forward_decoded_page_only",
        "same_exact_character_budget",
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read",
        "file_environment_process_network_search_model_or_evaluator_accessed",
        "benchmark_or_evaluator_launch_authorized",
        "artifact_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(control, str)
        or not isinstance(candidate, str)
        or len(control) != len(candidate)
        or len(control) > page_character_cap
        or copied.get("control_evidence_sha256")
        != hashlib.sha256(control.encode()).hexdigest()
        or copied.get("candidate_evidence_sha256")
        != hashlib.sha256(candidate.encode()).hexdigest()
        or not isinstance(inherited, Mapping)
        or _validate_content_free_receipt(inherited) != dict(inherited)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or inherited["output_characters"] != len(candidate)
        or receipt["output_characters"] != len(candidate)
        or inherited["visible_schema_column_count"]
        != receipt["visible_schema_column_count"]
        or inherited["discovered_record_count"] != receipt["discovered_record_count"]
        or inherited["admissible_record_count"] != receipt["admissible_record_count"]
        or inherited["retained_record_count"] != receipt["retained_record_count"]
        or receipt["candidate_evidence_changed"] is not (candidate != control)
        or copied.get("same_forward_decoded_page_only") is not True
        or copied.get("same_exact_character_budget") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
                "entropy_or_information_gain_assigns_signed_credit",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read",
                "file_environment_process_network_search_model_or_evaluator_accessed",
                "benchmark_or_evaluator_launch_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.61 version-qualified representation drifted")
    if replay and copied != build_representation(
        question, page, page_character_cap=page_character_cap
    ):
        raise ValueError("V2.50.61 representation is not reproducible")
    return copied


__all__ = [
    "MAXIMUM_INPUT_PAGE_CHARACTERS",
    "PAGE_CHARACTER_CAP",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_representation",
    "extract_record",
    "extract_robust_visible_columns",
    "payload_sha256",
    "validate_receipt",
    "validate_representation",
]
