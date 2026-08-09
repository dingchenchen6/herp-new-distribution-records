# ============================================================
# Objective / 分析目标:
# 数据集终审：两处微修复（湖蛙行注记与纲归置、字段一致性）、
# 全量统计定稿，输出 manuscript_stats.json 与 Table1（按目汇总），
# 供数据论文文稿引用（文稿中所有数字必须出自本文件）。
# Final audit: micro-fixes, frozen summary statistics, and the
# per-order Table 1. Every number cited in the manuscript must
# come from manuscript_stats.json produced here.
# ============================================================

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAT_PATH = "/Users/dingchenchen/Downloads/动物界-脊索动物门-2026-10714.xlsx"


def main() -> None:
    ev = pd.read_csv(ROOT / "data/CHNR_provincial_new_records.csv", dtype=str)
    ns = pd.read_csv(ROOT / "data/CHNR_new_species.csv", dtype=str)

    # ---- 微修复 / micro-fixes ----
    i = ev.index[ev["Scientific_name_as_published"].isna()]
    if len(i):
        i = i[0]
        ev.at[i, "Class_CN"] = "两栖纲"
        note = ("发表名'湖蛙'（新疆）无学名与引用信息；疑为湖侧褶蛙 Pelophylax "
                "ridibundus（中国名录未收录，名录仅收中亚侧褶蛙 P. terentievi），"
                "身份待人工溯源")
        ev.at[i, "Taxon_match_note"] = note
        ev.to_csv(ROOT / "data/CHNR_provincial_new_records.csv",
                  index=False, encoding="utf-8-sig")

    # ---- 统计 / statistics ----
    cat = pd.read_excel(CAT_PATH)
    herp_cat = cat[cat["纲中文名"].isin(["两栖纲", "爬行纲"])]
    pool_by_order = herp_cat.groupby("目中文名").size().to_dict()
    pool_by_class = herp_cat.groupby("纲中文名").size().to_dict()

    def uniq_papers(df):
        key = df["DOI"].fillna("") + "|" + df["Source_citation"].fillna("") \
            + "|" + df["Source_authors"].fillna("") + df["Source_publication_year"].fillna("")
        return key[key != "|"].nunique()

    sp_col = ev["Scientific_name_COL_China_2026"]
    years = pd.to_numeric(ev["Source_publication_year"], errors="coerce")
    nyears = pd.to_numeric(ns["Source_publication_year"], errors="coerce")

    dup_log = pd.read_csv(ROOT / "audit_quality_control/05_duplicate_review/05_1_duplicate_resolution_log.csv", dtype=str)
    scr = pd.read_csv(ROOT / "audit_quality_control/03_record_screening/03_record_screening_log.csv", dtype=str)
    tax = pd.read_csv(ROOT / "audit_quality_control/02_taxonomy_harmonisation/02_taxonomy_review.csv", dtype=str)
    coord_aud = pd.read_csv(ROOT / "audit_quality_control/04_coordinate_georeferencing/04_2_coordinate_audit.csv", dtype=str)

    stats = {
        "events": {
            "n": int(len(ev)),
            "by_class": ev["Class_CN"].value_counts().to_dict(),
            "species_resolved": int(sp_col.nunique()),
            "species_unresolved_rows": int(sp_col.isna().sum()),
            "orders": int(ev["OrderCN_COL_China_2026"].nunique()),
            "families": int(ev["FamilyLA_COL_China_2026"].nunique()),
            "genera": int(ev["GenusLA_COL_China_2026"].nunique()),
            "provinces": int(ev["New_distribution_province"].nunique()),
            "year_min": int(years.min()), "year_max": int(years.max()),
            "papers": int(uniq_papers(ev)),
            "coord_pct": round(ev["Longitude"].notna().mean() * 100, 1),
            "coord_basis": ev["Coordinate_basis"].value_counts().to_dict(),
            "date_pct": round(ev["Discovery_date"].notna().mean() * 100, 1),
            "altitude_pct": round(ev["Altitude_m"].notna().mean() * 100, 1),
            "habitat_cats": ev["Habitat_category"].value_counts().to_dict(),
            "evidence": ev["Evidence_type"].value_counts().to_dict(),
            "record_type": ev["Record_type"].value_counts().to_dict(),
            "iucn": ev["IUCN_RED_LIST"].value_counts().to_dict(),
            "china_redlist": ev["CHINA_RED_LIST"].value_counts(dropna=False).to_dict(),
            "protection": ev["China_Protection_Class"].str.extract(r"^(一级|二级)")[0].value_counts().to_dict(),
            "endemic": ev["Endemic_to_China"].value_counts().to_dict(),
            "endemic_species": int(ev[ev["Endemic_to_China"] == "YES"]["Scientific_name_COL_China_2026"].nunique()),
            "match_methods": ev["Taxon_match_method"].value_counts().to_dict(),
            "redoc_removed": int(len(dup_log)),
        },
        "new_species": {
            "n": int(len(ns)),
            "by_class": ns["Class_CN"].value_counts().to_dict(),
            "species": int(ns["Scientific_name_as_published"].nunique()),
            "year_min": int(nyears.min()), "year_max": int(nyears.max()),
            "papers": int(uniq_papers(ns)),
            "coord_pct": round(ns["Longitude"].notna().mean() * 100, 1),
            "provinces": int(ns["Province"].nunique()),
            "in_col2026_pct": round(ns["Scientific_name_COL_China_2026"].notna().mean() * 100, 1),
        },
        "screening": scr["decision"].value_counts().to_dict() if "decision" in scr.columns else scr.iloc[:, -1].value_counts().to_dict(),
        "taxonomy_corrections": int(len(tax)),
        "coordinate_flags": int(len(coord_aud)),
        "catalogue_pool": {"by_class": pool_by_class, "by_order": pool_by_order},
    }
    (ROOT / "docs").mkdir(exist_ok=True)
    with open(ROOT / "docs/manuscript_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1, default=str)

    # ---- Table 1: 按目汇总 / per-order summary ----
    rows = []
    for (cls, ocn), sub in ev.groupby(["Class_CN", "OrderCN_COL_China_2026"]):
        ola = sub["OrderLA_COL_China_2026"].dropna().iloc[0] if sub["OrderLA_COL_China_2026"].notna().any() else ""
        nsp = sub["Scientific_name_COL_China_2026"].nunique()
        pool = pool_by_order.get(ocn, None)
        rows.append({
            "Class": cls, "Order": ola, "Order_CN": ocn,
            "Newly_recorded_species": nsp, "New_record_events": len(sub),
            "Source_papers": uniq_papers(sub),
            "Pct_of_events": round(len(sub) / len(ev) * 100, 1),
            "Coverage_of_Chinese_pool_pct":
                round(nsp / pool * 100, 1) if pool else None,
        })
    t1 = pd.DataFrame(rows).sort_values("New_record_events", ascending=False)
    t1.to_csv(ROOT / "results/Table1_order_summary.csv", index=False, encoding="utf-8-sig")

    print(json.dumps(stats["events"], ensure_ascii=False, indent=1, default=str)[:1500])
    print("\nTable1:")
    print(t1.to_string(index=False))


if __name__ == "__main__":
    main()
