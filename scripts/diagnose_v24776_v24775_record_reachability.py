#!/usr/bin/env python3
"""Post-freeze exact-record reachability diagnosis for V2.47.75.

This append-only diagnostic reads only the already-frozen visible-task results,
pages, scheduler receipts, and content-free forward chain.  It never opens the
private population design, mapping, gold, category, split, evaluator, score,
reward, or quality surfaces and performs no network, model, search, fetch, or
benchmark action.

Runtime-private identities, URLs, page text, and candidate values are reduced
to aggregate counts and one aggregate manifest digest before publication.  The
counterfactual parser is deliberately field-label bounded: in particular,
``Country rank`` and ``national`` are not Country records, and inauguration is
not treated as founding.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24333_programmatic_support_catalog import (  # noqa: E402
    CellTarget,
)
from deepwide_agent.v24365_entity_segment_projection import (  # noqa: E402
    _normalize as projection_normalize,
    validate_target_segment_catalog,
)
from deepwide_agent.v24743_generic_record_binding import (  # noqa: E402
    UNKNOWN,
    _baseline_matrix,
    _source_key,
)
from deepwide_agent.v24770_visible_entity_fair_semantic_runtime import (  # noqa: E402
    validate_result as validate_runtime_result,
)
from deepwide_agent import (  # noqa: E402
    v24775_visible_entity_fair_execution_contract as contract,
)
from scripts.audit_v24775_visible_entity_fair_forward import (  # noqa: E402
    validate_audit as validate_forward_audit,
)


OUTPUT = Path(
    "results/v24776_v24775_record_reachability_diagnosis_v1_20260807.json"
)
ROLE = "v24776_v24775_postfreeze_record_reachability_diagnosis"
STATUS_ACQUISITION = "second_independent_source_acquisition_is_next_necessary_falsification"
STATUS_PROJECTION = "bounded_structured_record_projection_is_next_necessary_falsification"
STATUS_SUPPORT = "projection_to_support_binding_is_next_necessary_falsification"
STATUS_INTEGRATION = "support_to_candidate_integration_is_next_necessary_falsification"
STATUSES = frozenset(
    {STATUS_ACQUISITION, STATUS_PROJECTION, STATUS_SUPPORT, STATUS_INTEGRATION}
)
MAX_RECORD_LINES = 24
MAX_RECORD_CHARACTERS = 2_400
YEAR_PATTERN = re.compile(r"(?<!\d)(?:1[0-9]{3}|20[0-9]{2}|21[0-9]{2})(?!\d)")
SOURCE_FILES = (
    Path("scripts/diagnose_v24776_v24775_record_reachability.py"),
    Path("tests/test_diagnose_v24776_v24775_record_reachability.py"),
    Path("src/deepwide_agent/v24775_visible_entity_fair_execution_contract.py"),
    Path("src/deepwide_agent/v24770_visible_entity_fair_semantic_runtime.py"),
    Path("src/deepwide_agent/v24365_entity_segment_projection.py"),
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
)


def _label_key(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", " ", text)
    return " ".join(text.split())


FOUNDING_LABELS = frozenset(
    {
        "founded",
        "founded date",
        "date founded",
        "year founded",
        "founded year",
        "established",
        "established date",
        "date established",
        "year established",
        "establishment",
        "establishment date",
        "date of establishment",
        "establishment year",
        "founding year",
        "tanggal berdiri",
        "tahun berdiri",
        "tanggal didirikan",
        "tahun didirikan",
    }
)
COUNTRY_LABELS = frozenset({"country", "country name", "negara"})


# A closed English-name vocabulary keeps field values strict and replayable.
# It is not used to infer a country from prose or from benchmark metadata.
_COUNTRY_NAMES = """
Afghanistan|Albania|Algeria|Andorra|Angola|Antigua and Barbuda|Argentina|Armenia|Australia|Austria|Azerbaijan
Bahamas|Bahrain|Bangladesh|Barbados|Belarus|Belgium|Belize|Benin|Bhutan|Bolivia|Bosnia and Herzegovina|Botswana|Brazil|Brunei|Bulgaria|Burkina Faso|Burundi
Cabo Verde|Cambodia|Cameroon|Canada|Central African Republic|Chad|Chile|China|Colombia|Comoros|Costa Rica|Croatia|Cuba|Cyprus|Czechia|Czech Republic
Democratic Republic of the Congo|Denmark|Djibouti|Dominica|Dominican Republic|Ecuador|Egypt|El Salvador|Equatorial Guinea|Eritrea|Estonia|Eswatini|Ethiopia
Fiji|Finland|France|Gabon|Gambia|Georgia|Germany|Ghana|Greece|Grenada|Guatemala|Guinea|Guinea-Bissau|Guyana|Haiti|Honduras|Hungary
Iceland|India|Indonesia|Iran|Iraq|Ireland|Israel|Italy|Ivory Coast|Jamaica|Japan|Jordan|Kazakhstan|Kenya|Kiribati|Kuwait|Kyrgyzstan
Laos|Latvia|Lebanon|Lesotho|Liberia|Libya|Liechtenstein|Lithuania|Luxembourg|Madagascar|Malawi|Malaysia|Maldives|Mali|Malta|Marshall Islands|Mauritania|Mauritius|Mexico|Micronesia|Moldova|Monaco|Mongolia|Montenegro|Morocco|Mozambique|Myanmar
Namibia|Nauru|Nepal|Netherlands|New Zealand|Nicaragua|Niger|Nigeria|North Korea|North Macedonia|Norway|Oman|Pakistan|Palau|Palestine|Panama|Papua New Guinea|Paraguay|Peru|Philippines|Poland|Portugal|Qatar
Republic of the Congo|Romania|Russia|Rwanda|Saint Kitts and Nevis|Saint Lucia|Saint Vincent and the Grenadines|Samoa|San Marino|Sao Tome and Principe|Saudi Arabia|Senegal|Serbia|Seychelles|Sierra Leone|Singapore|Slovakia|Slovenia|Solomon Islands|Somalia|South Africa|South Korea|South Sudan|Spain|Sri Lanka|Sudan|Suriname|Sweden|Switzerland|Syria
Taiwan|Tajikistan|Tanzania|Thailand|Timor-Leste|Togo|Tonga|Trinidad and Tobago|Tunisia|Turkey|Turkmenistan|Tuvalu|Uganda|Ukraine|United Arab Emirates|United Kingdom|United States|United States of America|Uruguay|Uzbekistan|Vanuatu|Vatican City|Venezuela|Vietnam|Yemen|Zambia|Zimbabwe
"""
COUNTRY_VALUES = {
    _label_key(name): " ".join(name.split())
    for name in _COUNTRY_NAMES.replace("\n", "|").split("|")
    if name.strip()
}
COUNTRY_VALUES.update(
    {
        "republic of india": "India",
        "republic of indonesia": "Indonesia",
        "united states of america": "United States",
        "u s a": "United States",
        "u s": "United States",
        "great britain": "United Kingdom",
    }
)


def _read(relative: Path) -> dict[str, Any]:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.47.76 repository path escaped")
    path = ROOT / relative
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.76 expected ordinary repository object: {relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.76 expected JSON object")
    return value


def _unknown(value: object) -> bool:
    return " ".join(str(value or "").split()).casefold() in UNKNOWN


def _entity_pattern(entity: str) -> re.Pattern[str]:
    needle = unicodedata.normalize("NFKC", entity).strip()
    if len(needle) < 2:
        raise ValueError("V2.47.76 visible identity is too short")
    return re.compile(rf"(?<![\w]){re.escape(needle)}(?![\w])", re.IGNORECASE)


def _entity_hits(text: str, entities: Sequence[str]) -> set[str]:
    normalized = unicodedata.normalize("NFKC", text)
    return {
        entity for entity in entities if _entity_pattern(entity).search(normalized)
    }


def _pipe_label_value(line: str) -> tuple[str, str] | None:
    if "|" not in line:
        return None
    cells = [" ".join(cell.split()) for cell in line.strip().strip("|").split("|")]
    cells = [cell for cell in cells if cell and _label_key(cell)]
    if len(cells) < 2:
        return None
    return cells[0], " ".join(cells[1:])


def _pipe_cells(line: str) -> list[str] | None:
    raw = unicodedata.normalize("NFKC", str(line)).strip()
    if not (raw.startswith("|") and raw.endswith("|")):
        return None
    cells = [" ".join(cell.split()) for cell in raw[1:-1].split("|")]
    return cells if cells else None


def _table_rule(cells: Sequence[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) is not None
        for cell in cells
    )


def _table_target_candidates(
    lines: Sequence[str], *, entity: str, column: str
) -> set[str]:
    aliases = FOUNDING_LABELS if column == "Founded" else COUNTRY_LABELS
    output: set[str] = set()
    index = 0
    while index + 1 < len(lines):
        header = _pipe_cells(lines[index])
        rule = _pipe_cells(lines[index + 1])
        if (
            header is None
            or rule is None
            or len(header) < 2
            or len(rule) != len(header)
            or not _table_rule(rule)
            or _label_key(header[0]) != "organization"
        ):
            index += 1
            continue
        field_indexes = [
            position
            for position, label in enumerate(header)
            if position > 0 and _label_key(label) in aliases
        ]
        row_index = index + 2
        while row_index < len(lines):
            row = _pipe_cells(lines[row_index])
            if row is None or len(row) != len(header) or _table_rule(row):
                break
            if " ".join(row[0].split()) == entity:
                for position in field_indexes:
                    values = (
                        _founding_values(row[position])
                        if column == "Founded"
                        else _country_values(row[position])
                    )
                    output.update(values)
            row_index += 1
        index = max(index + 1, row_index)
    return output


def _delimited_label_value(line: str) -> tuple[str, str] | None:
    match = re.fullmatch(
        r"\s*(?P<label>[^:：\t|]{1,120}?)\s*(?:[:：\t]|\.{2,}|[-–—]{2,})\s*(?P<value>.+?)\s*",
        line,
    )
    if match is None:
        return None
    return match.group("label"), match.group("value")


def _bare_label_value(line: str, aliases: frozenset[str]) -> tuple[str, str] | None:
    canonical = " ".join(unicodedata.normalize("NFKC", line).split())
    for alias in sorted(aliases, key=len, reverse=True):
        match = re.fullmatch(
            rf"(?i:{re.escape(alias)})\s+(?P<value>.+)", canonical
        )
        if match is not None:
            return alias, match.group("value")
    return None


def _founding_values(raw: str) -> set[str]:
    return set(YEAR_PATTERN.findall(unicodedata.normalize("NFKC", raw)))


def _country_values(raw: str) -> set[str]:
    text = unicodedata.normalize("NFKC", raw)
    text = re.sub(r"\[[^\]]{0,30}\]", "", text)
    text = re.split(r"[;；\n]", text, maxsplit=1)[0]
    text = re.sub(r"\([^)]{0,100}\)\s*$", "", text)
    key = _label_key(text.strip(" .,:：;；-–—"))
    value = COUNTRY_VALUES.get(key)
    return {value} if value is not None else set()


def _labelled_values(line: str, column: str) -> set[str]:
    aliases = FOUNDING_LABELS if column == "Founded" else COUNTRY_LABELS
    bound = _pipe_label_value(line) or _delimited_label_value(line)
    if bound is None:
        bound = _bare_label_value(line, aliases)
    if bound is None:
        return set()
    label, raw_value = bound
    if _label_key(label) not in aliases:
        return set()
    return _founding_values(raw_value) if column == "Founded" else _country_values(raw_value)


_FOUNDING_NARRATIVE_PATTERNS = (
    re.compile(
        r"(?:was\s+|is\s+)?(?:founded|established|formed|incorporated)"
        r"\s*(?:in|on|during)?[^.!?;。！？；\n]{0,56}?"
        r"(?P<year>(?:1[0-9]{3}|20[0-9]{2}|21[0-9]{2}))",
        re.IGNORECASE,
    ),
    re.compile(
        r"berdiri\s+sejak[^.!?;。！？；\n]{0,32}?"
        r"(?P<year>(?:1[0-9]{3}|20[0-9]{2}|21[0-9]{2}))",
        re.IGNORECASE,
    ),
    re.compile(
        r"didirikan[^.!?;。！？；\n]{0,56}?(?:pada\s+tahun\s+|tahun\s+)?"
        r"(?P<year>(?:1[0-9]{3}|20[0-9]{2}|21[0-9]{2}))",
        re.IGNORECASE,
    ),
)


def _same_line_founding_values(line: str, entity: str) -> set[str]:
    pattern = _entity_pattern(entity)
    output: set[str] = set()
    for mention in pattern.finditer(line):
        left = max(
            (line.rfind(boundary, 0, mention.start()) for boundary in ".!?;。！？；"),
            default=-1,
        )
        right_candidates = [
            index
            for boundary in ".!?;。！？；"
            if (index := line.find(boundary, mention.end())) >= 0
        ]
        right = min(right_candidates) if right_candidates else len(line)
        local = line[left + 1 : right]
        if pattern.search(local) is None:
            continue
        for relation in _FOUNDING_NARRATIVE_PATTERNS:
            for match in relation.finditer(local):
                output.add(match.group("year"))
    return output


def extract_target_candidates(
    content: str,
    *,
    entities: Sequence[str],
    entity: str,
    column: str,
) -> set[str]:
    """Extract strict identity+field values from one already-fetched page."""

    if column not in {"Founded", "Country"} or entity not in entities:
        raise ValueError("V2.47.76 target surface drifted")
    normalized = unicodedata.normalize("NFKC", str(content))
    lines = normalized.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    patterns = {value: _entity_pattern(value) for value in entities}
    output = _table_target_candidates(lines, entity=entity, column=column)
    for index, line in enumerate(lines):
        if patterns[entity].search(line) is None:
            continue
        hits = {value for value, pattern in patterns.items() if pattern.search(line)}
        if hits != {entity}:
            continue
        if column == "Founded":
            output.update(_same_line_founding_values(line, entity))
        for mention in patterns[entity].finditer(line):
            suffix = line[mention.end() :].strip(" \t:：|-–—")
            if suffix:
                output.update(_labelled_values(suffix, column))

        identity_line = " ".join(
            line.strip().strip("#*_`~[]() ").split()
        ) == entity
        if not identity_line:
            continue
        characters = 0
        for following in lines[index + 1 : index + 1 + MAX_RECORD_LINES]:
            characters += len(following) + 1
            if characters > MAX_RECORD_CHARACTERS:
                break
            if not following.strip():
                break
            following_hits = {
                value for value, pattern in patterns.items() if pattern.search(following)
            }
            if following_hits.difference({entity}):
                break
            values = _labelled_values(following, column)
            if not values:
                break
            output.update(values)
    return output


def _coverage_bucket(value: int) -> str:
    return "0" if value == 0 else "1" if value == 1 else "2+"


def _histogram(values: Sequence[int]) -> dict[str, int]:
    counts = Counter(_coverage_bucket(value) for value in values)
    return {key: counts[key] for key in ("0", "1", "2+")}


def _source(page: Mapping[str, Any]) -> tuple[str, str]:
    final_url = str(page["final_url"])
    parsed = urlsplit(final_url)
    host = (parsed.hostname or "").casefold().strip(".")
    if parsed.scheme.casefold() != "https" or not host:
        raise ValueError("V2.47.76 frozen page address drifted")
    return host, _source_key(host)


def _projection_sources(
    catalog: Mapping[str, Any],
) -> tuple[dict[tuple[str, str], set[str]], set[tuple[str, str]]]:
    validated = validate_target_segment_catalog(catalog)
    projected: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in validated["projections"]:
        pages = (
            validated["original_core_pages"]
            if item["scope"] == "core"
            else validated["original_reserve_pages"]
        )
        ordinal = int(item["page_ordinal"])
        if not 1 <= ordinal <= len(pages):
            raise ValueError("V2.47.76 projection page ordinal drifted")
        source = _source_key(str(pages[ordinal - 1]["host"]))
        projected[
            (str(item["target_binding_sha256"]), str(item["normalized_value_sha256"]))
        ].add(source)
    support_pairs = {
        (str(item["target_binding_sha256"]), str(item["candidate_value_sha256"]))
        for item in validated["active_catalog"]["base_catalog"]["support_sets"]
        if item["baseline_cell_unknown"] is True
    }
    return projected, support_pairs


def _pair_hash(target: CellTarget, candidate: str) -> tuple[str, str]:
    normalized = projection_normalize(candidate)
    return target.binding_sha256, hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def classify_record_cells(
    observations: Mapping[str, Mapping[str, set[str]]],
    fields: Mapping[str, str],
) -> tuple[dict[str, int], dict[str, dict[str, int]], set[tuple[str, str]]]:
    """Classify target hashes without returning any private value or source."""

    total = Counter()
    by_field: dict[str, Counter[str]] = defaultdict(Counter)
    safe_pairs: set[tuple[str, str]] = set()
    for binding, column in fields.items():
        values = observations.get(binding, {})
        source_counts = [len(sources) for sources in values.values()]
        if not values:
            state = "unreachable_cell_count"
        elif len(values) > 1:
            state = "conflicting_cell_count"
        elif source_counts[0] >= 2:
            state = "two_source_same_value_cell_count"
            safe_pairs.add((binding, next(iter(values))))
        else:
            state = "one_source_same_value_cell_count"
        total[state] += 1
        by_field[column][state] += 1
    names = (
        "unreachable_cell_count",
        "one_source_same_value_cell_count",
        "two_source_same_value_cell_count",
        "conflicting_cell_count",
    )
    aggregate = {name: total[name] for name in names}
    breakdown = {
        column: {name: by_field[column][name] for name in names}
        for column in sorted(set(fields.values()))
    }
    return aggregate, breakdown, safe_pairs


def choose_status(
    *,
    safe_pair_count: int,
    safe_pairs_with_two_projection_sources: int,
    safe_pairs_with_support: int,
    final_changed_cell_count: int,
) -> str:
    if safe_pair_count == 0:
        return STATUS_ACQUISITION
    if safe_pairs_with_two_projection_sources < safe_pair_count:
        return STATUS_PROJECTION
    if safe_pairs_with_support < safe_pair_count:
        return STATUS_SUPPORT
    if final_changed_cell_count == 0:
        return STATUS_INTEGRATION
    raise ValueError("V2.47.76 frozen NO-GO is inconsistent with reachable changes")


def _private_manifest_digest(rows: Sequence[Mapping[str, str]]) -> str:
    ordered = sorted(
        (dict(row) for row in rows),
        key=lambda row: tuple(row[key] for key in sorted(row)),
    )
    return contract.payload_sha256(ordered)


def _assert_public_surface(
    value: Mapping[str, Any], *, private_literals: Sequence[str] = ()
) -> None:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    lowered = serialized.casefold()
    if "http://" in lowered or "https://" in lowered:
        raise ValueError("V2.47.76 public diagnosis contains an address")
    secret_markers = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
    if any(marker in lowered for marker in secret_markers):
        raise ValueError("V2.47.76 public diagnosis contains a credential marker")
    for literal in private_literals:
        canonical = str(literal).strip()
        if canonical and json.dumps(canonical, ensure_ascii=False) in serialized:
            raise ValueError("V2.47.76 public diagnosis contains a private literal")


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward = contract.validate_forward_result(_read(contract.FORWARD_RESULT))
    summary = contract.validate_run_summary(_read(contract.RUN_SUMMARY))
    freeze = contract.validate_prediction_freeze(_read(contract.PREDICTION_FREEZE))
    audit = validate_forward_audit(_read(contract.FORWARD_AUDIT))
    if (
        forward["terminal_arm_predictions"] != 16
        or summary["valid_task_results"] != contract.SELECTED_COUNT
        or audit["forward_health_go"] is not True
        or audit["mechanism_go"] is not False
        or freeze["all_predictions_terminal_before_private_truth_or_quality_open"] is not True
        or freeze["private_truth_or_quality_path_opened_or_hashed"] is not False
        or forward["quality_or_evaluator_called"] is not False
        or audit["forward_result_sha256"] != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or audit["prediction_freeze_sha256"] != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or audit["run_summary_sha256"] != contract.sha256(ROOT / contract.RUN_SUMMARY)
    ):
        raise RuntimeError("V2.47.76 frozen parent chain drifted")

    requested_coverage: list[int] = []
    usable_identity_coverage: list[int] = []
    unknown_fields: dict[str, str] = {}
    observations: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    projection_sources: dict[tuple[str, str], set[str]] = defaultdict(set)
    support_pairs: set[tuple[str, str]] = set()
    private_manifest: list[dict[str, str]] = []
    task_manifest: list[dict[str, str | int]] = []
    private_literals: set[str] = set()
    counters: Counter[str] = Counter()
    frozen_adapter: Counter[str] = Counter()

    for ordinal in range(1, contract.SELECTED_COUNT + 1):
        relative = contract.TASK_ROOT / f"task_{ordinal:04d}" / contract.RESULT_NAME
        result = validate_runtime_result(_read(relative))
        task_manifest.append(
            {"ordinal": ordinal, "result_sha256": contract.sha256(ROOT / relative)}
        )
        entities = [str(value) for value in result["private_visible_entities"]]
        private_literals.update(entities)
        baseline = str(result["predictions"]["baseline"])
        columns, rows = _baseline_matrix(baseline)
        if tuple(columns) != contract.EXPECTED_COLUMNS or [row[0] for row in rows] != entities:
            raise RuntimeError("V2.47.76 visible baseline identity drifted")

        requested_vector = result["scheduler_receipt"][
            "requested_aligned_source_count_vector"
        ]
        if len(requested_vector) != len(entities):
            raise RuntimeError("V2.47.76 requested coverage vector drifted")
        requested_coverage.extend(int(value) for value in requested_vector)
        counters["fetch_request_count"] += int(
            result["scheduler_receipt"]["fetch_request_count"]
        )

        targets: list[CellTarget] = []
        for row in rows:
            for column_index in range(1, len(columns)):
                target = CellTarget(row[0], columns[column_index], row[column_index])
                if target.baseline_unknown:
                    targets.append(target)
                    unknown_fields[target.binding_sha256] = columns[column_index]
        counters["unknown_cell_count"] += len(targets)

        exact_sources: dict[str, set[str]] = {entity: set() for entity in entities}
        pages = result["parent_result"]["private_replay_pages"]
        counters["usable_fetched_page_count"] += len(pages)
        for page in pages:
            host, source = _source(page)
            content = str(page["content"])
            private_literals.add(str(page["final_url"]))
            hits = _entity_hits(content, entities)
            counters["usable_page_entity_hit_count"] += len(hits)
            for entity in hits:
                exact_sources[entity].add(source)
            page_digest = contract.payload_sha256(
                {
                    "final_url": str(page["final_url"]),
                    "content": content,
                    "fetch_integrity": bool(page["fetch_integrity"]),
                }
            )
            for target in targets:
                candidates = extract_target_candidates(
                    content,
                    entities=entities,
                    entity=target.row_key,
                    column=target.column,
                )
                for candidate in candidates:
                    private_literals.add(candidate)
                    pair = _pair_hash(target, candidate)
                    observations[pair[0]][pair[1]].add(source)
                    private_manifest.append(
                        {
                            "target_binding_sha256": pair[0],
                            "normalized_value_sha256": pair[1],
                            "source_key_sha256": hashlib.sha256(source.encode()).hexdigest(),
                            "page_sha256": page_digest,
                        }
                    )
        usable_identity_coverage.extend(
            len(exact_sources[entity]) for entity in entities
        )

        current_projection, current_support = _projection_sources(
            result["private_semantic_catalog"]
        )
        for pair, sources in current_projection.items():
            projection_sources[pair].update(sources)
        support_pairs.update(current_support)

        adapter_receipt = result["parent_result"]["adapter_result"]["receipt"]
        binding_receipt = adapter_receipt["binding_receipt"]
        frozen_adapter["ordinary_record_count"] += int(
            adapter_receipt["ordinary_record_count"]
        )
        frozen_adapter["changed_cell_count"] += int(
            binding_receipt["changed_cell_count"]
        )
        frozen_adapter["insufficient_corroboration_cell_count"] += int(
            binding_receipt["insufficient_corroboration_cell_count"]
        )
        frozen_adapter["conflicting_cell_count"] += int(
            binding_receipt["conflicting_cell_count"]
        )

    states, by_field, safe_pairs = classify_record_cells(observations, unknown_fields)
    record_pairs = {
        (binding, value_hash)
        for binding, values in observations.items()
        for value_hash in values
    }
    record_source_links = {
        (binding, value_hash, source)
        for binding, values in observations.items()
        for value_hash, sources in values.items()
        for source in sources
    }
    projection_source_links = {
        (binding, value_hash, source)
        for (binding, value_hash), sources in projection_sources.items()
        for source in sources
    }
    safe_with_two_projection = {
        pair for pair in safe_pairs if len(projection_sources.get(pair, set())) >= 2
    }
    safe_with_support = safe_pairs.intersection(support_pairs)
    status = choose_status(
        safe_pair_count=len(safe_pairs),
        safe_pairs_with_two_projection_sources=len(safe_with_two_projection),
        safe_pairs_with_support=len(safe_with_support),
        final_changed_cell_count=int(summary["changed_cell_count"]),
    )

    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": status,
        "parents": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "task_result_manifest_sha256": contract.payload_sha256(task_manifest),
        },
        "source_manifest": {
            str(path): contract.sha256(ROOT / path) for path in SOURCE_FILES
        },
        "frozen_forward": {
            "selected_tasks": contract.SELECTED_COUNT,
            "terminal_arm_predictions": int(forward["terminal_arm_predictions"]),
            "valid_task_results": int(summary["valid_task_results"]),
            "forward_wall_seconds": summary["forward_wall_seconds"],
            "forward_health_go": True,
            "mechanism_go": False,
            "changed_task_count": int(summary["changed_task_count"]),
            "changed_cell_count": int(summary["changed_cell_count"]),
        },
        "acquisition_funnel": {
            "entity_slot_count": len(requested_coverage),
            "fetch_request_count": counters["fetch_request_count"],
            "usable_fetched_page_count": counters["usable_fetched_page_count"],
            "usable_page_entity_hit_count": counters["usable_page_entity_hit_count"],
            "requested_aligned_source_coverage_histogram": _histogram(requested_coverage),
            "usable_exact_identity_source_coverage_histogram": _histogram(
                usable_identity_coverage
            ),
        },
        "unknown_surface": {
            "unknown_cell_count": len(unknown_fields),
            "unknown_cell_count_by_field": dict(sorted(Counter(unknown_fields.values()).items())),
        },
        "strict_exact_record_reachability": {
            **states,
            "cell_state_count_by_field": by_field,
            "record_target_value_pair_count": len(record_pairs),
            "record_source_observation_count": len(record_source_links),
            "safe_two_source_same_value_pair_count": len(safe_pairs),
            "private_observation_manifest_sha256": _private_manifest_digest(
                private_manifest
            ),
            "exact_visible_identity_required": True,
            "exact_field_label_or_same_identity_sentence_predicate_required": True,
            "country_field_label_is_exact_not_substring": True,
            "country_rank_or_national_treated_as_country": False,
            "inauguration_treated_as_founding": False,
        },
        "frozen_exact_adapter": {
            key: frozen_adapter[key]
            for key in (
                "ordinary_record_count",
                "changed_cell_count",
                "insufficient_corroboration_cell_count",
                "conflicting_cell_count",
            )
        },
        "projection_and_support_binding": {
            "record_pairs_with_any_legacy_projection": len(
                record_pairs.intersection(projection_sources)
            ),
            "record_pairs_missing_legacy_projection": len(
                record_pairs.difference(projection_sources)
            ),
            "record_source_links_preserved_by_legacy_projection": len(
                record_source_links.intersection(projection_source_links)
            ),
            "record_source_links_lost_before_legacy_projection": len(
                record_source_links.difference(projection_source_links)
            ),
            "safe_pairs_with_two_legacy_projection_sources": len(
                safe_with_two_projection
            ),
            "safe_pairs_with_legacy_support_set": len(safe_with_support),
            "legacy_unknown_eligible_support_set_count": int(
                summary["projection_backed_support_set_count"]
            ),
        },
        "diagnosis": {
            "parser_only_can_reach_the_unchanged_two_source_gate_on_frozen_pages": bool(
                safe_pairs
            ),
            "single_source_parser_gain_is_sufficient_for_safe_change": False,
            "unchanged_two_independent_source_gate_retained": True,
            "same_population_forward_replay_would_be_valid": False,
            "next_optimization_surface": (
                "query_source_diversification_and_fetch_reliability"
                if status == STATUS_ACQUISITION
                else "bounded_multilingual_structured_record_projection"
                if status == STATUS_PROJECTION
                else "projection_to_support_catalog_binding"
                if status == STATUS_SUPPORT
                else "support_to_candidate_integration"
            ),
        },
        "source_policy": {
            "runtime_task_input_contract": ["opaque_id", "question"],
            "frozen_private_pages_and_receipts_opened_only_after_prediction_freeze": True,
            "private_identity_address_page_or_candidate_persisted": False,
            "privileged_runtime_metadata_read": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "same_forward_artifact_rewritten": False,
        },
        "claim_scope": {
            "mechanism_bottleneck_diagnosed": True,
            "deepwidebench_quality_measured": False,
            "benchmark_improvement_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "append_only_query_source_fetch_design": status == STATUS_ACQUISITION,
            "append_only_structured_record_projector_design": status == STATUS_PROJECTION,
            "append_only_support_binding_design": status == STATUS_SUPPORT,
            "append_only_integration_design": status == STATUS_INTEGRATION,
            "same_population_forward_retry_resume_or_rerun": False,
            "fresh_external_activation_or_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    validated = validate_diagnosis(value)
    _assert_public_surface(validated, private_literals=sorted(private_literals))
    return validated


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    status = copied.get("status")
    funnel = copied.get("acquisition_funnel", {})
    reachability = copied.get("strict_exact_record_reachability", {})
    binding = copied.get("projection_and_support_binding", {})
    authorization = copied.get("authorization", {})
    histograms = (
        funnel.get("requested_aligned_source_coverage_histogram"),
        funnel.get("usable_exact_identity_source_coverage_histogram"),
    )
    state_names = (
        "unreachable_cell_count",
        "one_source_same_value_cell_count",
        "two_source_same_value_cell_count",
        "conflicting_cell_count",
    )
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or status not in STATUSES
        or copied.get("frozen_forward", {}).get("forward_health_go") is not True
        or copied.get("frozen_forward", {}).get("mechanism_go") is not False
        or copied.get("source_manifest")
        != {str(path): contract.sha256(ROOT / path) for path in SOURCE_FILES}
        or any(
            not isinstance(histogram, Mapping)
            or set(histogram) != {"0", "1", "2+"}
            or any(
                isinstance(number, bool) or not isinstance(number, int) or number < 0
                for number in histogram.values()
            )
            or sum(histogram.values()) != funnel.get("entity_slot_count")
            for histogram in histograms
        )
        or any(
            isinstance(reachability.get(name), bool)
            or not isinstance(reachability.get(name), int)
            or reachability[name] < 0
            for name in state_names
        )
        or sum(reachability[name] for name in state_names)
        != copied.get("unknown_surface", {}).get("unknown_cell_count")
        or reachability.get("safe_two_source_same_value_pair_count")
        != reachability.get("two_source_same_value_cell_count")
        or binding.get("record_pairs_with_any_legacy_projection", 0)
        + binding.get("record_pairs_missing_legacy_projection", 0)
        != reachability.get("record_target_value_pair_count")
        or binding.get("record_source_links_preserved_by_legacy_projection", 0)
        + binding.get("record_source_links_lost_before_legacy_projection", 0)
        != reachability.get("record_source_observation_count")
        or copied.get("diagnosis", {}).get(
            "parser_only_can_reach_the_unchanged_two_source_gate_on_frozen_pages"
        )
        is not (reachability.get("safe_two_source_same_value_pair_count", 0) > 0)
        or authorization
        != {
            "append_only_query_source_fetch_design": status == STATUS_ACQUISITION,
            "append_only_structured_record_projector_design": status == STATUS_PROJECTION,
            "append_only_support_binding_design": status == STATUS_SUPPORT,
            "append_only_integration_design": status == STATUS_INTEGRATION,
            "same_population_forward_retry_resume_or_rerun": False,
            "fresh_external_activation_or_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or copied.get("claim_scope")
        != {
            "mechanism_bottleneck_diagnosed": True,
            "deepwidebench_quality_measured": False,
            "benchmark_improvement_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.76 diagnosis drifted")
    _assert_public_surface(copied)
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    publish_new(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": diagnosis["status"],
                "usable_fetched_pages": diagnosis["acquisition_funnel"][
                    "usable_fetched_page_count"
                ],
                "safe_two_source_same_value_cells": diagnosis[
                    "strict_exact_record_reachability"
                ]["two_source_same_value_cell_count"],
                "same_population_rerun_authorized": diagnosis["authorization"][
                    "same_population_forward_retry_resume_or_rerun"
                ],
            },
            sort_keys=True,
        )
    )
