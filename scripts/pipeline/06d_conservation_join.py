# ============================================================
# Objective / 分析目标:
# 将三类保护状态参照表接入 CHNR 两个数据表的四个字段：
#   IUCN_RED_LIST        <- GBIF Species API (IUCN Red List)
#   CHINA_RED_LIST       <- 中国生物多样性红色名录-脊椎动物卷(2020, 官方PDF)
#   China_Protection_Class <- 国家重点保护野生动物名录(2021, 经官方扫描版抽样校验)
#   Endemic_to_China     <- 红色名录"特有种"列
# 匹配级联：现行拉丁名精确 -> 发表名精确 -> 中文名精确 -> 种加词词干
# (纲内) -> 属级(所有种)条目。全部匹配路径写入审计表。
# Join conservation reference tables into the four CHNR fields
# with a cascade matcher and a full join-audit trail.
# Input : data/*.csv, source_data/conservation/*.csv
# Output: data/*.csv (updated), data/CHNR_v0.1.xlsx (rebuilt),
#         source_data/conservation/conservation_join_audit.csv
# ============================================================

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CONS = ROOT / "source_data/conservation"

# 已确立的属拆分/合并对（与 01_match_species.py 同源并扩充红色名录
# 2020 时代常用组合）/ established genus split-merge pairs, extended
# with combinations used by the 2020 Red List and 2021 NPWA
TRANSFER_PAIRS = {frozenset(p) for p in [
    ("Tylototriton", "Yaotriton"), ("Tylototriton", "Liangshantriton"),
    ("Japalura", "Diploderma"), ("Rhacophorus", "Zhangixalus"),
    ("Rhacophorus", "Polypedates"), ("Cynops", "Hypselotriton"),
    ("Pachytriton", "Paramesotriton"), ("Odorrana", "Bamburana"),
    ("Amolops", "Bamburana"), ("Philautus", "Raorchestes"),
    ("Enhydris", "Myrrophis"), ("Typhlops", "Indotyphlops"),
    ("Rana", "Odorrana"), ("Rana", "Pseudorana"), ("Rana", "Sylvirana"),
    ("Sylvirana", "Boulengerana"), ("Hylarana", "Sylvirana"),
    ("Hylarana", "Boulengerana"), ("Leptobrachium", "Vibrissaphora"),
    ("Bufo", "Torrentophryne"), ("Bufo", "Bufotes"),
    ("Bufo", "Duttaphrynus"), ("Bufo", "Strauchbufo"),
    ("Ingerophrynus", "Qiongbufo"),
    ("Megophrys", "Boulenophrys"), ("Megophrys", "Xenophrys"),
    ("Megophrys", "Jingophrys"), ("Megophrys", "Atympanophrys"),
    ("Megophrys", "Brachytarsophrys"), ("Megophrys", "Ophryophryne"),
    ("Leptobrachella", "Paramegophrys"), ("Leptolalax", "Paramegophrys"),
    ("Chirixalus", "Chiromantis"), ("Chirixalus", "Rohanixalus"),
    ("Trimeresurus", "Sinovipera"), ("Trimeresurus", "Viridovipera"),
    ("Trimeresurus", "Popeia"), ("Trimeresurus", "Himalayophis"),
    ("Trimeresurus", "Craspedocephalus"),
    ("Gonyosoma", "Rhadinophis"), ("Gonyosoma", "Rhynchophis"),
    ("Elaphe", "Oreocryptophis"), ("Ptyas", "Cyclophiops"),
    ("Lycodon", "Dinodon"), ("Hebius", "Amphiesma"),
    ("Gekko", "Ptychozoon"), ("Takydromus", "Platyplacopus"),
    ("Plestiodon", "Eumeces"), ("Sinomicrurus", "Calliophis"),
    ("Orientocoluber", "Coluber"), ("Pseudohynobius", "Liua"),
]}


def stem(ep: str) -> str:
    """种加词词干 / epithet stem tolerant of gender endings."""
    ep = ep.lower()
    ep = re.sub(r"ii$", "i", ep)
    return re.sub(r"(us|a|um|is|e)$", "", ep)


def binom_stem(la: str) -> Optional[str]:
    toks = str(la).split()
    if len(toks) >= 2 and re.match(r"^[a-z-]+$", toks[1]):
        return stem(toks[1])
    return None


def zh_primary(zh: str) -> str:
    base = re.sub(r"[（(].*?[)）]", "", str(zh))
    return re.split(r"[/、]", base)[0].strip()


class RefTable:
    """参照表多路索引 / multi-key index over a reference table."""

    def __init__(self, df: pd.DataFrame, la_col: str, zh_col: str, cls_col: Optional[str]):
        self.df = df
        self.la, self.zh, self.stems = {}, {}, {}
        for i, r in df.iterrows():
            la = str(r[la_col]).strip()
            self.la.setdefault(la, i)
            # 拼写变体：horsfieldi/horsfieldii 双 i 归并 / spelling variants
            self.la.setdefault(re.sub(r"i+$", "i", la), i)
            if zh_col and pd.notna(r[zh_col]):
                self.zh.setdefault(zh_primary(r[zh_col]), i)
            st = binom_stem(la)
            if st:
                key = (r[cls_col] if cls_col else "", st)
                self.stems.setdefault(key, set()).add(i)

    def find(self, la_acc, la_pub, zhs, cls) -> Tuple[Optional[int], str]:
        for la, how in ((la_acc, "拉丁名精确(现行名)"), (la_pub, "拉丁名精确(发表名)")):
            if la:
                i = self.la.get(str(la).strip()) or self.la.get(re.sub(r"i+$", "i", str(la).strip()))
                if i is not None:
                    return i, how
        for z in zhs:
            if z and z in self.zh:
                return self.zh[z], "中文名精确"
        for la in (la_acc, la_pub):
            st = binom_stem(la) if la else None
            if st:
                hits = self.stems.get((cls, st), set()) or self.stems.get(("", st), set())
                if len(hits) == 1:
                    j = next(iter(hits))
                    # 词干命中需属名相同或中文名佐证，防"pictus"式假朋友
                    # stem hit needs same genus OR zh corroboration
                    ref = self.df.loc[j]
                    ref_genus = str(ref["Scientific_name"]).split()[0]
                    our_genera = {str(x).split()[0] for x in (la_acc, la_pub) if x}
                    same_genus = ref_genus in our_genera
                    pair_ok = any(frozenset({ref_genus, g}) in TRANSFER_PAIRS
                                  for g in our_genera)
                    ref_zh = zh_primary(ref.get("Chinese_name", "")) if pd.notna(ref.get("Chinese_name")) else ""
                    zh_ok = any(z and ref_zh and (z == ref_zh
                                or (len(z) == len(ref_zh)
                                    and sum(a != b for a, b in zip(z, ref_zh)) <= 1))
                                for z in zhs)
                    if same_genus or pair_ok or zh_ok:
                        return j, "种加词词干"
        return None, ""


def main() -> None:
    ev = pd.read_csv(ROOT / "data/CHNR_provincial_new_records.csv", dtype=str)
    ns = pd.read_csv(ROOT / "data/CHNR_new_species.csv", dtype=str)

    iucn = pd.read_csv(CONS / "iucn_reference.csv", dtype=str)
    iucn_map: Dict[str, str] = {r["species"]: r["IUCN_category"]
                                for _, r in iucn.iterrows()
                                if pd.notna(r["IUCN_category"])}
    crl = RefTable(pd.read_csv(CONS / "china_redlist_herp.csv", dtype=str),
                   "Scientific_name", "Chinese_name", "Class_CN")
    npwa_df = pd.read_csv(CONS / "npwa2021_herp.csv", dtype=str)
    npwa = RefTable(npwa_df[npwa_df["is_group"] != "True"],
                    "Scientific_name", "Chinese_name", "Class_CN")
    npwa_genus = {str(r["Scientific_name"]).split()[0]: r
                  for _, r in npwa_df[npwa_df["is_group"] == "True"].iterrows()}

    audit = []

    def enrich(df: pd.DataFrame, table: str) -> pd.DataFrame:
        for col in ["IUCN_RED_LIST", "CHINA_RED_LIST", "Scientific_name_ChinaRedList",
                    "China_Protection_Class", "Endemic_to_China"]:
            df[col] = None  # 每次接入前重置，避免陈值 / reset to avoid stale values
        for i, r in df.iterrows():
            la_acc = r.get("Scientific_name_COL_China_2026")
            la_pub = r.get("Scientific_name_as_published")
            la_acc = la_acc if pd.notna(la_acc) else None
            la_pub = la_pub if pd.notna(la_pub) else None
            zhs = [zh_primary(r[c]) for c in
                   ("Chinese_name_COL_China_2026", "Chinese_name_as_published")
                   if c in df.columns and pd.notna(r.get(c))]
            cls = r.get("Class_CN")
            key = la_acc or la_pub

            # IUCN：未收录于 IUCN 名录者按定义为 NE / unlisted = NE
            if key in iucn_map:
                df.at[i, "IUCN_RED_LIST"] = iucn_map[key]
            elif key:
                df.at[i, "IUCN_RED_LIST"] = "NE"
            # 中国红色名录 + 特有性 / China Red List + endemism
            j, how = crl.find(la_acc, la_pub, zhs, cls)
            if j is not None:
                row = crl.df.loc[j]
                df.at[i, "CHINA_RED_LIST"] = row["ChinaRedList"]
                # 红色名录自用拉丁名（可能为异名组合）/ red list's own name
                df.at[i, "Scientific_name_ChinaRedList"] = row["Scientific_name"]
                df.at[i, "Endemic_to_China"] = row["Endemic"]
                audit.append({"table": table, "species": key, "field": "CHINA_RED_LIST",
                              "value": row["ChinaRedList"], "matched_name": row["Scientific_name"],
                              "via": how})
            # 保护级别 / protection class
            j, how = npwa.find(la_acc, la_pub, zhs, cls)
            if j is not None:
                row = npwa.df.loc[j]
                val = row["Protection_class"]
                if pd.notna(row.get("note")) and str(row.get("note")).strip():
                    val = f"{val}（{str(row['note']).strip()}）"
                df.at[i, "China_Protection_Class"] = val
                audit.append({"table": table, "species": key, "field": "Protection",
                              "value": val, "matched_name": row["Scientific_name"], "via": how})
            elif key and key.split()[0] in npwa_genus:
                g = npwa_genus[key.split()[0]]
                note = str(g.get("note") or "").strip()
                df.at[i, "China_Protection_Class"] = \
                    f"{g['Protection_class']}（{g['Chinese_name']}{'；' + note if note else ''}）"
                audit.append({"table": table, "species": key, "field": "Protection",
                              "value": g["Protection_class"], "matched_name": g["Scientific_name"],
                              "via": "属级(所有种)"})
        return df

    ev = enrich(ev, "events")
    ns = enrich(ns, "new_species")

    # 列序：红色名录学名紧随发表名 / place red-list name after published name
    def reorder(df: pd.DataFrame) -> pd.DataFrame:
        cols = [c for c in df.columns if c != "Scientific_name_ChinaRedList"]
        anchor = cols.index("Scientific_name_as_published") + 1
        return df[cols[:anchor] + ["Scientific_name_ChinaRedList"] + cols[anchor:]]

    ev, ns = reorder(ev), reorder(ns)

    ev.to_csv(ROOT / "data/CHNR_provincial_new_records.csv", index=False, encoding="utf-8-sig")
    ns.to_csv(ROOT / "data/CHNR_new_species.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(audit).to_csv(CONS / "conservation_join_audit.csv",
                               index=False, encoding="utf-8-sig")

    # 更新字段词典 / refresh field dictionary rows
    meta = pd.read_csv(ROOT / "data/CHNR_metadata.csv", dtype=str)
    meta.loc[meta["Field"].str.contains("IUCN_RED_LIST", na=False), "Description"] = (
        "IUCN_RED_LIST: IUCN红色名录类别，经GBIF Species API获取（含NE=未评估）；"
        "CHINA_RED_LIST: 中国生物多样性红色名录—脊椎动物卷(2020)（生态环境部·中国科学院公告2023年第15号）；"
        "Scientific_name_ChinaRedList: 红色名录(2020)自用拉丁名（与现行名不同即提示异名关系）；"
        "China_Protection_Class: 国家重点保护野生动物名录(2021年第3号公告)，一级/二级，括注'仅限野外种群'等备注，空=未列入；"
        "Endemic_to_China: 是否中国特有（红色名录2020'特有种'列，YES/NO）"
    )
    meta.to_csv(ROOT / "data/CHNR_metadata.csv", index=False, encoding="utf-8-sig")

    # 重建 Excel 汇总簿 / rebuild the bundled workbook
    with pd.ExcelWriter(ROOT / "data/CHNR_v0.1.xlsx", engine="openpyxl") as xw:
        ev.to_excel(xw, sheet_name="provincial_new_records", index=False)
        ns.to_excel(xw, sheet_name="new_species", index=False)
        (ev.groupby(["Class_CN", "OrderCN_COL_China_2026"]).size().rename("events")
         .reset_index().to_excel(xw, sheet_name="summary_order", index=False))
        (ev.groupby("New_distribution_province").size().rename("events")
         .reset_index().to_excel(xw, sheet_name="summary_province", index=False))
        (ev.groupby(["Class_CN", "CHINA_RED_LIST"]).size().rename("events")
         .reset_index().to_excel(xw, sheet_name="summary_redlist", index=False))

    # 覆盖率报告 / coverage report
    for name, df in (("事件表", ev), ("新种表", ns)):
        n = len(df)
        print(f"== {name} ({n}行) 覆盖率:")
        for col in ["IUCN_RED_LIST", "CHINA_RED_LIST", "China_Protection_Class",
                    "Endemic_to_China"]:
            print(f"   {col:24s} {df[col].notna().sum():4d} ({df[col].notna().sum()/n:.0%})")
    print("\n事件表 CHINA_RED_LIST 分布:")
    print(ev.groupby(["Class_CN", "CHINA_RED_LIST"]).size().to_string())
    print("\n事件表 保护级别 分布:")
    print(ev["China_Protection_Class"].value_counts().head(8).to_string())
    print("\n事件表 特有种:")
    print(ev.groupby(["Class_CN", "Endemic_to_China"]).size().to_string())


if __name__ == "__main__":
    main()
