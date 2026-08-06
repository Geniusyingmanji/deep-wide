#!/usr/bin/env python3
"""Build evaluator-only ROR gold and provenance for the V2.46.39 task vector."""

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
    if str(path) not in sys.path: sys.path.insert(0, str(path))

from deepwide_agent.v24639_ror_external_contract import ENTITY_GROUPS, visible_task  # noqa: E402


COMMIT = "aab1443afefefa8460e69ab01bccceff0a8544d4"
VERSION = "v2.11"
GOLD = Path("evaluation/v24639_ror_gold_v1.csv")
PROVENANCE = Path("evaluation/v24639_ror_gold_provenance_v1.json")
RECORDS = (
    (("0019x5d05", "8ea8845ead649a52f4339fe4f2a730a591810891", "FR"), ("01c6ft524", "2ef491b6fe8d784a7f2e4f16d3ef081f2474c651", "CN"), ("00cfam450", "8e395002311aca550d0bbd6f738fe4a8b26ef7cb", "DE"), ("00my2qv06", "106bc58d107d6c34f3ef2fc5c964523ff1fe4b20", "SO")),
    (("01pfn9t54", "6a5130c0e5fb409554a61d99d0e6bb704d4f43b6", "ID"), ("00h99vg60", "77de83fa27f9110a600a4e99a9572d30114be93d", "CN"), ("01kzn7k21", "c67c8201cdd926dc12a14685dc2ab14bd175ee9a", "IR"), ("001w7jn25", "810376849f99e44affbc2b316e61046c8f798b54", "DE")),
    (("01m48c907", "55b87ed8de046e9251aa7628054627bef86bf526", "ID"), ("00e83fj44", "38cdd9b7b84156b8f501b61fc440e0cdb6feb771", "US"), ("012m7e804", "852636416fd94c7d483c6a5d4dd919ea6b48700d", "SA"), ("00xdyh091", "6e1d59b8e3bc1f4b622c8a11699bbd4d0acd1c39", "CA")),
    (("0149xnh58", "50f00f1dd3b19fabfd9995218ce19ce7155567bf", "ID"), ("0121cjp70", "491057fb5d1bdc71cc42af9b99c94fc8bebadeb0", "AU"), ("01e67n130", "4095d8c96aec57e7599d0c8bcd64a97081668678", "CA"), ("01etvnv23", "538a1d5385699b78362df442c0156888616196f9", "GB")),
    (("00xs0en04", "2d471e3f285952a19a50fca0b270f30be0d6bd66", "IN"), ("00f7qhf41", "03ff1a25ca8613aaf99f6b620e250b078fdb7105", "EC"), ("006a6pc29", "ecfd4070626341b46ca4e0c222cdd367be1500e1", "UA"), ("01anbmy79", "ae04603d7d6a505b55591939fac0acebe53862f6", "CI")),
    (("017rnyz40", "97c048aac1683ac13cc63b2a5c575a208f5e98bd", "FR"), ("00me74e98", "52919f9e70d131ce81447edd1e31badd3c0bd3f7", "NG"), ("0006b9y14", "1cbdc887296fce754f284971b18cee35a44239ce", "PT"), ("0123nxb25", "6c74678301f778dc1502dafa0b538d070960a5a4", "IL")),
    (("01bh2s525", "681ea84cc5c39a4162ac564c9ad8f4e41648f40e", "US"), ("009frb846", "6b23413313e0de0c66a287705fc1c2b4de5ac76e", "FR"), ("01m7dbh13", "fcf2fbba1b85f094e1986d75dbc54239f6d5b885", "AZ"), ("00k195394", "091f3fb9534dc4623b7cf34e494b9a8fffdc01a0", "DE")),
    (("00b16vp10", "42bc1bf0822032eb11cc1092e0583d8a844809dc", "CN"), ("0113dje58", "37b55c9ddf9097a8e527db9c85f311fe1bb16f82", "IN"), ("00p4kjh08", "ab3d1c9abc4e55f5ee6faba24ab31f52956e4414", "ES"), ("010xn0p45", "b177304ce02f3f657bfff3193bc7eb4f2444a5ca", "MY")),
    (("011e3e176", "9127e4eba7cf97b1142b542592ca3ea47c7656d4", "CA"), ("01kv0ya56", "a640abd7668d68757763d5cc64787a3f7bca33fe", "MX"), ("018qrbr66", "d3074a2a08837d9ff77e56462bf635ca842e943a", "BD"), ("00p6hm978", "072e1855cf7579fbdfa6b6bcb6d45b8118b1ffdd", "ES")),
    (("0144sj678", "7d75318bbe20b343899a922526ef48d4d43e1637", "CL"), ("00hgtpv71", "037324e59d6793a5575066b3dcacbe3898b0f263", "NG"), ("01apwpt12", "06b7401a1f51098e3ff79ef62424e03b3ad70e62", "US"), ("00c71vf80", "8b61ca35c06d1f1550595c2578fde169c8004be4", "BR")),
    (("00davry38", "8d78416d471504ba08addce21c57b957bebfc93a", "MX"), ("01qgecw57", "aba677b195072b09a1c38e07940e73e24451abaf", "GB"), ("00ac4gz35", "6331c1ed410c8d47430394dedf70007336e4b601", "NG"), ("00c3tgx29", "e9637df78805a5a17e22d1dd3fd4d7193f2969ee", "BR")),
    (("01jmtsv84", "f73c291801f69c9ada75b2f4ad8ea5d9fd508151", "IN"), ("00pfs7x68", "db2c84fdd7ab2d39d676b343b0461bfe2a888cff", "PH"), ("01ev6yf32", "cfb8c8c69ac0206644dbf92a09dbb700786c6f8a", "IL"), ("01px5cv07", "045887811d00d1c639087ca8697f6e7670b12719", "IL")),
)


def fetch_record(record_id: str, expected_blob: str) -> tuple[dict, str]:
    url = f"https://raw.githubusercontent.com/ror-community/ror-records/{COMMIT}/{VERSION}/{record_id}.json"
    with urllib.request.urlopen(url, timeout=30) as response: raw = response.read()
    git_blob = hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()
    if git_blob != expected_blob:
        raise RuntimeError("V2.46.39 ROR Git blob identity drifted")
    value = json.loads(raw)
    if value.get("id") != f"https://ror.org/{record_id}" or value.get("status") != "active":
        raise RuntimeError("V2.46.39 ROR identity or status drifted")
    return value, hashlib.sha256(raw).hexdigest()


def main() -> None:
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (GOLD, PROVENANCE)):
        raise FileExistsError("V2.46.39 evaluator-only surface exists")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=["opaque_id", "Organization", "ROR ID", "Country code"], lineterminator="\n")
    writer.writeheader(); provenance = []
    for ordinal, (group, records) in enumerate(zip(ENTITY_GROUPS, RECORDS, strict=True), 1):
        opaque_id = visible_task(ordinal)["opaque_id"]
        for entity, (record_id, blob, expected_country) in zip(group, records, strict=True):
            value, byte_sha = fetch_record(record_id, blob)
            labels = [n["value"].strip() for n in value.get("names", []) if "ror_display" in n.get("types", [])]
            country = value["locations"][0]["geonames_details"]["country_code"]
            if labels != [entity] or country != expected_country:
                raise RuntimeError("V2.46.39 frozen ROR label or country drifted")
            writer.writerow({"opaque_id": opaque_id, "Organization": entity, "ROR ID": record_id, "Country code": country})
            provenance.append({"record_id": record_id, "git_blob_sha1": blob, "record_bytes_sha256": byte_sha})
    for path, data in (
        (GOLD, output.getvalue()),
        (PROVENANCE, json.dumps({"artifact_version": 1, "role": "v24639_ror_gold_provenance", "commit": COMMIT, "version": VERSION, "selection_rule": "first_1000_active_unique_display_no_parenthetical_country_prior_entity_disjoint_sha256_rank_country_cap3_balanced_groups", "records": provenance}, ensure_ascii=False, indent=2) + "\n"),
    ):
        path = ROOT / path; path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle: handle.write(data); handle.flush(); os.fsync(handle.fileno())
    print(json.dumps({"rows": len(provenance), "gold_sha256": hashlib.sha256((ROOT / GOLD).read_bytes()).hexdigest()}, sort_keys=True))


if __name__ == "__main__": main()
