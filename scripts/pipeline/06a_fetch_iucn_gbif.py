# ============================================================
# Objective / 分析目标:
# 通过 GBIF Species API 为 CHNR 全部物种获取 IUCN 红色名录类别
# （名录现行名优先，发表名回退），输出参照表与覆盖率。
# Fetch IUCN Red List categories for all CHNR species via the
# GBIF Species API (accepted name first, published name fallback).
# Input : data/CHNR_provincial_new_records.csv, data/CHNR_new_species.csv
# Output: source_data/conservation/iucn_gbif.csv
# Note  : 网络请求约 0.15s/次礼貌限速 / polite rate limiting.
# ============================================================

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "source_data" / "conservation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

API = "https://api.gbif.org/v1"
HEADERS = {"User-Agent": "CHNR-dataset/0.1 (conservation status join)"}


def get_json(url: str):
    """GET JSON with basic error tolerance / 容错的 GET JSON."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def iucn_for_name(name: str):
    """名称→backbone→IUCN 类别 / name to IUCN category via backbone."""
    q = urllib.parse.quote(name)
    m = get_json(f"{API}/species/match?name={q}&kingdom=Animalia")
    if not m or m.get("matchType") in (None, "NONE"):
        return None, None, None
    key = m.get("usageKey")
    if key is None:
        return None, None, None
    time.sleep(0.15)
    c = get_json(f"{API}/species/{key}/iucnRedListCategory")
    cat = (c or {}).get("category")
    code = (c or {}).get("code") or cat
    return code, m.get("scientificName"), m.get("matchType")


def main() -> None:
    ev = pd.read_csv(ROOT / "data/CHNR_provincial_new_records.csv", dtype=str)
    ns = pd.read_csv(ROOT / "data/CHNR_new_species.csv", dtype=str)
    names = {}
    for df in (ev, ns):
        for _, r in df.iterrows():
            acc = r.get("Scientific_name_COL_China_2026")
            pub = r.get("Scientific_name_as_published")
            key = acc if pd.notna(acc) else pub
            if pd.notna(key):
                names.setdefault(key, pub if pd.notna(pub) else None)

    rows = []
    for i, (acc, pub) in enumerate(sorted(names.items()), 1):
        code, matched, mtype = iucn_for_name(acc)
        source_name = acc
        if code in (None, "NOT_EVALUATED", "NE") and pub and pub != acc:
            code2, matched2, mtype2 = iucn_for_name(pub)
            if code2 not in (None, "NOT_EVALUATED", "NE"):
                code, matched, mtype, source_name = code2, matched2, mtype2, pub
        rows.append({"species": acc, "IUCN_category": code,
                     "gbif_matched_name": matched, "gbif_match_type": mtype,
                     "query_used": source_name})
        if i % 40 == 0:
            print(f"  {i}/{len(names)} done")
        time.sleep(0.15)

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "iucn_gbif.csv", index=False, encoding="utf-8-sig")
    n_cat = out["IUCN_category"].notna().sum()
    print(f"物种 {len(out)}，获得 IUCN 类别 {n_cat}（{n_cat/len(out):.0%}）")
    print(out["IUCN_category"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
