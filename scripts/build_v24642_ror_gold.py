#!/usr/bin/env python3
"""Build evaluator-only ROR gold and provenance for V2.46.42."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24642_ror_external_contract import (  # noqa: E402
    ENTITY_GROUPS,
    visible_task,
)


COMMIT = "aab1443afefefa8460e69ab01bccceff0a8544d4"
VERSION = "v2.11"
DIRECTORY_TREE_SHA1 = "473b00391664ad5a782605516ba0bea5b4d14e6b"
SLICE_START = 1_000
SLICE_STOP = 2_000
GOLD = Path("evaluation/v24642_ror_gold_v1.csv")
PROVENANCE = Path("evaluation/v24642_ror_gold_provenance_v1.json")
RECORDS = (
    (("026sfks30", "8a34131142967c1129b0d14d47862a356be8e3a6", "BE"), ("034tsnk78", "e3450b4908873ad5f84ebcf5bc16dddf5a8d2cfe", "PK"), ("0276z6433", "4e66d9d61c40d84df519a4b612be3f77de2cf0b7", "SG"), ("03dbskr59", "5d4562ec6407bcd4b78e26d0be84e98cc01c97a0", "CN")),
    (("01xpec842", "c9d8a11173259cccdaffc965d2d037f7ea537c3d", "ID"), ("039gj3815", "16ccf1bc29388d1b9896678d2a2d967bacf2947a", "IN"), ("022arna15", "352183ff75280df899f92a0ea2368bfa16cb6933", "AZ"), ("02dcqxm65", "8ac4556dbec1d3ae2066fe6dbebe5ed651a5cc7d", "DE")),
    (("02qzesy07", "d5df6dd68f79aa6c1eea257fc30dd74f163501c6", "ID"), ("033xjms15", "87f285d5dea21067419d7ff029e366fbfa7353d6", "IN"), ("01y9eam60", "121a9594e4a39d613993f62621e5ef6641e852d5", "ES"), ("034n5f383", "54b793e3a91ad56c0e34a49ce2fb5dd09c0aa8f3", "LY")),
    (("02xy0fs81", "a92ef2204883dd570147b9678198e4763a4c6b18", "UG"), ("0278hns33", "149ce3a9daeb5843d8a6ba84af4cde415e12c35c", "DE"), ("02xstm723", "5959cd6e5db9c22f78081611563b240147592259", "DE"), ("031kdpv26", "0b104496e43561f290bad1982064bb5527d93e53", "ES")),
    (("036k9f270", "7cecae370537c8bc6b6c2f2a533970bdd4c0b353", "ID"), ("036c30946", "dbed7bd88b271346ad4ebe9722c312e601dbba17", "KR"), ("02csnb181", "fb48320991b80d3c954d3c896c8da46d7b637097", "TW"), ("02m0f4428", "36f4ed626ca8bbde3ea2dc4b82b9e30ac65535e5", "NG")),
    (("02kdd6j62", "40bb7ac56897900ea47b29c9df46525ce012508f", "MG"), ("032hyw046", "4f99e1b2dda98858aa009c7beccb4c7a86f551cb", "IR"), ("02551xw73", "085375f67dc94036a611ac3b207ed311572bf9d2", "MK"), ("02gv4h649", "92027e6d15462dcfb667056160e24e12be8711ba", "GB")),
    (("03cfem402", "f0b4c1e327ddc8617ebd5655dafd3e98dd1d72f8", "FR"), ("032dx9458", "b5f591a41be4f82460b205071ac4000b277f6fa3", "CN"), ("02x4mx473", "38ea675464c1e9769c1216f7ac5e64294fe1314d", "BE"), ("01t6rqt91", "668b55075862241d128fb66882b75ef682a60218", "NZ")),
    (("01tjs6929", "495885ae0ea210619c98b9458c61f3d9ac6a847c", "AR"), ("02k01dh53", "d5f5def16aa4413d814c99d1e23088c7cda8178e", "CN"), ("02ym5cp77", "c596950167c7d5266fc8f8bf90dfb0e0984225af", "UZ"), ("033a7yg32", "52fe21f2c63019d3272f6dc97f5c9fabb8cfa1d7", "GT")),
    (("035xkbk20", "d4b7d2d9469d67752101f29fda417457f7c5acea", "FR"), ("028g18b61", "2b4c7df0a0619d2c3e0cbd92a777ef7c8d25c6d1", "AU"), ("021p56f43", "e86ec9515b7867503fadfa678bd70b67767599c4", "CH"), ("02j5dng57", "51a9a729073e0ad70e11f958ddbc24ad57022f17", "GN")),
    (("02s99ck98", "3b40093a117b5110772a96c0da373d0951589987", "US"), ("01ypxeq73", "19591f7cf8be9238f2274a1b20c8b321d8bd5d6a", "IN"), ("02zccb110", "cb357db445bc9ca69ecace6a82972d733ede9ce1", "CA"), ("02kgve346", "70c76f341e31c8c6a197dfa18ffb8455b5fa00ff", "US")),
    (("032naxt30", "20a6bade28341c40bac8da929c7a9792ec045e2f", "CA"), ("01tndtj91", "1f49dedb0ea3b972ff72756a4b7953c3920f2bdb", "US"), ("03ekzqa32", "4f8a1de5612abe4e86f6e33b01b975e815da20c4", "EG"), ("024mryy80", "f638feb58420630e5af302b8a6f2f15a07ed5e4b", "BR")),
    (("02ncy5p18", "9432c5f088e834ac031f6353356b4fe784478380", "FR"), ("03ac41p65", "e359974d2a348919df422db4d59ec3cbefbc74d3", "CA"), ("03562fh87", "c46a1d5bcd93dc79b49404a8923f9d623fbeffc4", "PT"), ("02ndvz068", "d7c0ab7fc047d5e8ff2a5f6d6b38434cd3711392", "AF")),
)


def fetch_record(record_id: str, expected_blob: str) -> tuple[dict, str]:
    url = (
        "https://raw.githubusercontent.com/ror-community/ror-records/"
        f"{COMMIT}/{VERSION}/{record_id}.json"
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read()
    git_blob = hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw, usedforsecurity=False
    ).hexdigest()
    if git_blob != expected_blob:
        raise RuntimeError("V2.46.42 ROR Git blob identity drifted")
    value = json.loads(raw)
    if value.get("id") != f"https://ror.org/{record_id}" or value.get("status") != "active":
        raise RuntimeError("V2.46.42 ROR identity or status drifted")
    return value, hashlib.sha256(raw).hexdigest()


def main() -> None:
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (GOLD, PROVENANCE)):
        raise FileExistsError("V2.46.42 evaluator-only surface exists")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=["opaque_id", "Organization", "ROR ID", "Country code"],
        lineterminator="\n",
    )
    writer.writeheader()
    provenance = []
    for ordinal, (group, records) in enumerate(zip(ENTITY_GROUPS, RECORDS, strict=True), 1):
        opaque_id = visible_task(ordinal)["opaque_id"]
        for entity, (record_id, blob, expected_country) in zip(group, records, strict=True):
            value, byte_sha = fetch_record(record_id, blob)
            labels = [
                name["value"].strip()
                for name in value.get("names", [])
                if "ror_display" in name.get("types", [])
            ]
            country = value["locations"][0]["geonames_details"]["country_code"]
            if labels != [entity] or country != expected_country:
                raise RuntimeError("V2.46.42 frozen ROR label or country drifted")
            writer.writerow(
                {
                    "opaque_id": opaque_id,
                    "Organization": entity,
                    "ROR ID": record_id,
                    "Country code": country,
                }
            )
            provenance.append(
                {
                    "record_id": record_id,
                    "git_blob_sha1": blob,
                    "record_bytes_sha256": byte_sha,
                }
            )
    provenance_value = {
        "artifact_version": 1,
        "role": "v24642_ror_gold_provenance",
        "commit": COMMIT,
        "version": VERSION,
        "directory_tree_sha1": DIRECTORY_TREE_SHA1,
        "lexicographic_slice_start_inclusive": SLICE_START,
        "lexicographic_slice_stop_exclusive": SLICE_STOP,
        "selection_rule": "ror_tree_json_positions_1000_1999_active_unique_display_no_parenthetical_country_prior_4384_entity_disjoint_sha256_rank_country_cap3_quartile_interleaved_groups",
        "records": provenance,
    }
    values = (
        (GOLD, output.getvalue()),
        (PROVENANCE, json.dumps(provenance_value, ensure_ascii=False, indent=2) + "\n"),
    )
    for relative, data in values:
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    print(
        json.dumps(
            {
                "rows": len(provenance),
                "gold_sha256": hashlib.sha256((ROOT / GOLD).read_bytes()).hexdigest(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
