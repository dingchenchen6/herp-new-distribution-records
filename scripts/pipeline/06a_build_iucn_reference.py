# ============================================================
# Objective / 分析目标:
# 用 IUCN 官方最新名录分发包（DwC-A, hosted-datasets.gbif.org/
# datasets/iucn/iucn-latest.zip，IUCN 发布）为 CHNR 全部物种建立
# IUCN 参照表：类别、IUCN 现行学名、taxonID、评估来源年份；
# 匹配含 IUCN 自身异名映射与词干回退（同属护栏）。
# Build the IUCN reference for all CHNR species from IUCN's own
# latest checklist distribution (accepted names + synonymy),
# with category, IUCN accepted name, taxonID and assessment year.
# Input : source_data/conservation/iucn_latest_dwca/{taxon,distribution}.txt
#         data/CHNR_provincial_new_records.csv, data/CHNR_new_species.csv
# Output: source_data/conservation/iucn_reference.csv
# Note  : 数据包本体不入库（IUCN 条款不允许再分发），仅本地使用。
# ============================================================

import csv
import re
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DWCA = ROOT / "source_data/conservation/iucn_latest_dwca"
OUT = ROOT / "source_data/conservation/iucn_reference.csv"

HERP_CLASSES = {"AMPHIBIA", "REPTILIA"}
CAT_CODE = {
    "Least Concern": "LC", "Near Threatened": "NT", "Vulnerable": "VU",
    "Endangered": "EN", "Critically Endangered": "CR", "Data Deficient": "DD",
    "Extinct": "EX", "Extinct in the Wild": "EW",
    "Lower Risk/least concern": "LC*", "Lower Risk/near threatened": "NT*",
    "Lower Risk/conservation dependent": "NT*",
}


def stem(ep: str) -> str:
    ep = ep.lower()
    ep = re.sub(r"ii$", "i", ep)
    return re.sub(r"(us|a|um|is|e)$", "", ep)


def main() -> None:
    # 1) 等级与评估来源 / categories + assessment source per taxonID
    status: Dict[str, tuple] = {}
    with open(DWCA / "distribution.txt", encoding="utf-8", errors="ignore") as f:
        for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(row) < 6 or row[2] != "Global":
                continue
            m = re.search(r"(20\d\d(?:-\d)?)\.RLTS", row[3] or "")
            year = m.group(1) if m else None
            status[row[0]] = (row[5], year)

    # 2) 两爬分类核心表：现行名与异名 / herp accepted names and synonyms
    acc_binom: Dict[str, str] = {}       # binomial -> taxonID (accepted)
    syn_binom: Dict[str, str] = {}       # synonym binomial -> accepted taxonID
    acc_name: Dict[str, str] = {}        # taxonID -> accepted binomial
    stems: Dict[tuple, set] = {}         # (genus-less stem) -> accepted ids
    # 两遍扫描：IUCN 异名行不携带纲信息，须按 acceptedNameUsageID 归属
    # two passes: synonym rows carry no class, resolve via acceptedNameUsageID
    with open(DWCA / "taxon.txt", encoding="utf-8", errors="ignore") as f:
        taxon_rows = [row for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
                      if len(row) >= 14]
    for row in taxon_rows:
        if row[4] not in HERP_CLASSES or row[12] != "accepted":
            continue
        genus, ep = row[7], row[8]
        if row[10] != "species" or not genus or not ep:
            continue
        binom = f"{genus} {ep}"
        acc_binom.setdefault(binom, row[0])
        acc_name[row[0]] = binom
        stems.setdefault(stem(ep), set()).add(row[0])
    herp_ids = set(acc_name)
    for row in taxon_rows:
        if row[12] != "synonym" or row[13] not in herp_ids:
            continue
        genus, ep = row[7], row[8]
        if not genus or not ep:
            # 部分异名行未拆分属/种加词，回退解析 scientificName
            # fall back to splitting scientificName when fields are empty
            toks = str(row[1]).split()
            if len(toks) >= 2 and re.match(r"^[A-Z][a-z-]+$", toks[0]) \
                    and re.match(r"^[a-z-]+$", toks[1]):
                genus, ep = toks[0], toks[1]
            else:
                continue
        binom = f"{genus} {ep}"
        syn_binom.setdefault(binom, row[13])
        stems.setdefault(stem(ep), set()).add(row[13])

    def lookup(name: Optional[str]) -> tuple:
        """名称 -> (taxonID, via) / resolve a binomial against IUCN."""
        if not name:
            return None, ""
        toks = str(name).split()
        if len(toks) < 2:
            return None, ""
        binom = f"{toks[0]} {toks[1]}"
        if binom in acc_binom:
            return acc_binom[binom], "IUCN现行名精确"
        if binom in syn_binom:
            return syn_binom[binom], "IUCN异名映射"
        hits = stems.get(stem(toks[1]), set())
        hits = {h for h in hits if acc_name.get(h, " ").split()[0] == toks[0]}
        if len(hits) == 1:
            return next(iter(hits)), "同属词干"
        return None, ""

    # 3) CHNR 物种集 / CHNR species set
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
    for key, pub in sorted(names.items()):
        tid, via = lookup(key)
        used = key
        if tid is None and pub and pub != key:
            tid, via = lookup(pub)
            used = pub
        cat_raw, year = status.get(tid, (None, None)) if tid else (None, None)
        rows.append({
            "species": key,
            "IUCN_category": CAT_CODE.get(cat_raw, cat_raw) if cat_raw else None,
            "IUCN_category_raw": cat_raw,
            "IUCN_scientific_name": acc_name.get(tid) if tid else None,
            "IUCN_taxonID": tid, "IUCN_assessment_version": year,
            "matched_via": via or None, "query_used": used if tid else None,
        })
    out = pd.DataFrame(rows)

    # GBIF 快照回退：极少数在分发包中缺失但已有评估的种 / GBIF fallback
    gbif_path = ROOT / "source_data/conservation/iucn_gbif.csv"
    if gbif_path.exists():
        gbif = pd.read_csv(gbif_path, dtype=str)
        gmap = {r["species"]: r["IUCN_category"] for _, r in gbif.iterrows()
                if pd.notna(r["IUCN_category"]) and r["IUCN_category"] not in ("NE", "NOT_EVALUATED")}
        n_fb = 0
        for i, r in out.iterrows():
            if pd.isna(r["IUCN_category"]) and r["species"] in gmap:
                out.at[i, "IUCN_category"] = gmap[r["species"]]
                out.at[i, "matched_via"] = "GBIF快照回退"
                n_fb += 1
        print(f"GBIF 快照回退补充: {n_fb} 种")

    out.to_csv(OUT, index=False, encoding="utf-8-sig")

    n = len(out)
    n_cat = out["IUCN_category"].notna().sum()
    print(f"物种 {n}，IUCN 类别覆盖 {n_cat}（{n_cat/n:.0%}）；其余为 IUCN 未评估(NE)")
    print(out["IUCN_category"].value_counts(dropna=False).to_string())
    print("匹配方式:")
    print(out["matched_via"].value_counts(dropna=False).to_string())
    print("评估版本分布(前8):")
    print(out["IUCN_assessment_version"].value_counts().head(8).to_string())


if __name__ == "__main__":
    main()
