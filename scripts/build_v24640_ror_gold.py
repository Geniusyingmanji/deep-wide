#!/usr/bin/env python3
"""Build evaluator-only ROR gold and provenance for the V2.46.40 vector."""

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

from deepwide_agent.v24640_ror_external_contract import (  # noqa: E402
    ENTITY_GROUPS,
    visible_task,
)


COMMIT = "aab1443afefefa8460e69ab01bccceff0a8544d4"
VERSION = "v2.11"
GOLD = Path("evaluation/v24640_ror_gold_v1.csv")
PROVENANCE = Path("evaluation/v24640_ror_gold_provenance_v1.json")
RECORDS = (
    (
        ("00146e793", "aaf3f8c4b964132b518ce8326bc729852bc7b1dd", "IN"),
        ("01njn7795", "cd1539c43c269bec6a54fba0aa6d9a620f4a8a9f", "EE"),
        ("00kg2yq63", "6d8b6da779c797d0a07206b0016d84f1c9b29322", "DE"),
        ("00rev1511", "2f410d43493c17856e53f34d55d01123a7bb2cdf", "AU"),
    ),
    (
        ("0084x3h80", "28ecf5ebe3643e8426d70576a6640d78af454508", "FR"),
        ("00qcztw05", "8d47d1404b97c1173ddd0afedd68a2c6791946a2", "UZ"),
        ("001ps8w52", "0f789c572c1a11dd7a8a767e6d85cefdebfe4c8a", "CA"),
        ("01ks8be76", "5c53bee79b5bd56bc14a09f4358cf5e82ca74ec4", "EC"),
    ),
    (
        ("01cf2sz15", "7ff2461b01978bdc00e2f760e655d96766073a3a", "FR"),
        ("0127tex41", "deff1e37bcecc52bddce5b1ec6468f1b2fef32d8", "IN"),
        ("00j3eeb74", "fbc9ecbdf946b3183443c2b3eedb7c2302f03330", "JP"),
        ("0127fwn18", "be6e430a153304f6fb1415c8dfcfce98df943be3", "DE"),
    ),
    (
        ("00ryjkv54", "69d1bd4584789bf842f79032dc99a417ab8b31b3", "ID"),
        ("006ejbv88", "7ac9b4588819b0049fc6e55154e813e8c8a62593", "TZ"),
        ("0143c7g52", "6b89710cfa3c0f46452416f1742fc6d006a219db", "BT"),
        ("01aybmk16", "67f859be3bb9ef46d485a1ad0fe7ebc2d625edc3", "NG"),
    ),
    (
        ("00s38mz90", "2ac8f40ffbf76217f624fbb2b7e47484a55816cf", "MX"),
        ("015ypce77", "2beca9026264d261ecf5435a01640d5aab5b3065", "US"),
        ("01pv6r024", "9f6b0430775fa699fcc5c9e7d139b321808a0bfe", "AR"),
        ("00tjm9y94", "14d3889e9f73a8b2d6153bfdb9875fd8556f0006", "RO"),
    ),
    (
        ("017szad60", "881223d8bab335b2e2dad7cf4789e374a51a4bac", "ID"),
        ("0072htj14", "beb5e0e4dc113a5b40889906398b02a4ab3a9f90", "CA"),
        ("00x458g09", "4049199563efa2fc46bb5bd5b74ffb88188e35f0", "BR"),
        ("006g2sa40", "8b8ae4f6c8e6665d36eb438a1f5a09a034da6228", "BR"),
    ),
    (
        ("013691g33", "9185f3f13344465c678155d73e022a243e955626", "ID"),
        ("00cxaa614", "fd02007f3cb04d00b02a7db324bf173e44211c39", "NG"),
        ("01b0et865", "a80e78aceee7eee374ec715a01a1b077cdb26191", "CN"),
        ("01hafby60", "fbeefc820cb1e1015c7bf7c2f95a9c1ecce116ce", "AU"),
    ),
    (
        ("006xk1031", "ae0e84f6f3524b1a485a1865b26f530637b46265", "IN"),
        ("00yqy0q42", "c232473216191ffe0d86eedc4f39cbafda14b720", "CA"),
        ("01703db54", "6f9ca476da40b0452d468eeb3e1aaf1d9987bf20", "JP"),
        ("00eew5z52", "a11501037aec9c3f2ec68231c3812558816310ee", "IL"),
    ),
    (
        ("01502ca60", "916526cf0820264509d92b19ac6c08a2a82a5e2d", "FR"),
        ("00c9pzm73", "6c4c17deb821fd8ac1032cd6d700f9d3fa2014a8", "US"),
        ("00r0cn362", "9adf19b91bf529ead6166afadd32e3e0366fef93", "KE"),
        ("009g8rq41", "4a65eac8a06f50a6b5b09ae2c68b7fdbabb5ba70", "KR"),
    ),
    (
        ("017kggx87", "153d090529223a2614b09151997b6a401b49add2", "JP"),
        ("0190x2a66", "469debe31f40d4617c83d951d6d5221387249e30", "CN"),
        ("002agny75", "3b3d454702c1b489a64e86c2db4411f3c0ef9575", "PS"),
        ("00a06pm72", "21e979840a9d30fa6953368a54b0aa7e406d3f8e", "CY"),
    ),
    (
        ("00bx3rb98", "aa591d8b4bd6814d24bb0a5dbbd50b4a8ca5fd5c", "CN"),
        ("005xvx333", "a449e9a9fe82c2c2891e5fd4e78a21a1501906d3", "US"),
        ("00pa9y269", "16ef49aaffba1672fd0a5d03f1ff47d10c5c1dbf", "GB"),
        ("01462r250", "956ba3cafc24887afdbbd77925e48d1933b3882b", "CH"),
    ),
    (
        ("0016dbc19", "1747105782d692e947c8050dc8a0a43f5e4388f6", "CD"),
        ("01dv63r93", "605448f6dda99cd1b51fa588cea523517659abea", "BR"),
        ("00e7gc845", "d05e21a4ebb63426dfc749e4d99db19375d0764c", "UZ"),
        ("00wq97w77", "8442c36aec87fba8cfa749d361b2995ef6230811", "GE"),
    ),
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
        raise RuntimeError("V2.46.40 ROR Git blob identity drifted")
    value = json.loads(raw)
    if value.get("id") != f"https://ror.org/{record_id}" or value.get("status") != "active":
        raise RuntimeError("V2.46.40 ROR identity or status drifted")
    return value, hashlib.sha256(raw).hexdigest()


def main() -> None:
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (GOLD, PROVENANCE)):
        raise FileExistsError("V2.46.40 evaluator-only surface exists")
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
                raise RuntimeError("V2.46.40 frozen ROR label or country drifted")
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
    values = (
        (GOLD, output.getvalue()),
        (
            PROVENANCE,
            json.dumps(
                {
                    "artifact_version": 1,
                    "role": "v24640_ror_gold_provenance",
                    "commit": COMMIT,
                    "version": VERSION,
                    "selection_rule": "first_1000_active_unique_display_no_parenthetical_country_prior_4336_entity_disjoint_sha256_rank_country_cap3_quartile_interleaved_groups",
                    "records": provenance,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        ),
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
