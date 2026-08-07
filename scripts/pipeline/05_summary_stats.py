# ============================================================
# Objective / 分析目标:
# 两栖纲与爬行纲分别输出描述性汇总（目、省、年、物种数），
# 供数据论文表格与图件引用。
# Per-class (Amphibia vs Reptilia) descriptive summaries by
# order, province, year and species, for tables and figures.
# Input : data/CHNR_provincial_new_records.csv, data/CHNR_new_species.csv
# Output: results/CHNR_summary_*.csv
# ============================================================

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # 仓库根目录 / repo root
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

ev = pd.read_csv(ROOT / "data/CHNR_provincial_new_records.csv", dtype=str)
ns = pd.read_csv(ROOT / "data/CHNR_new_species.csv", dtype=str)

ev["species_key"] = ev["Scientific_name_COL_China_2026"].fillna(
    ev["Scientific_name_as_published"]).fillna(ev["Chinese_name_as_published"])
ev["year"] = pd.to_numeric(ev["Source_publication_year"], errors="coerce")

# 1) 纲×目 / class x order
by_order = (ev.groupby(["Class_CN", "OrderCN_COL_China_2026", "OrderLA_COL_China_2026"])
            .agg(events=("ID", "count"), species=("species_key", "nunique"),
                 provinces=("New_distribution_province", "nunique"))
            .reset_index())
by_order.to_csv(OUT / "CHNR_summary_by_class_order.csv", index=False, encoding="utf-8-sig")

# 2) 纲×省 / class x province
by_prov = (ev.groupby(["Class_CN", "New_distribution_province"])
           .agg(events=("ID", "count"), species=("species_key", "nunique"))
           .reset_index()
           .sort_values(["Class_CN", "events"], ascending=[True, False]))
by_prov.to_csv(OUT / "CHNR_summary_by_class_province.csv", index=False, encoding="utf-8-sig")

# 3) 纲×年 / class x publication year
by_year = (ev.dropna(subset=["year"])
           .groupby(["Class_CN", "year"])
           .agg(events=("ID", "count"), species=("species_key", "nunique"))
           .reset_index())
by_year["year"] = by_year["year"].astype(int)
by_year.to_csv(OUT / "CHNR_summary_by_class_year.csv", index=False, encoding="utf-8-sig")

# 4) 新种表：纲×年 / new species by class x year
ns["year"] = pd.to_numeric(ns["Source_publication_year"], errors="coerce")
ns_year = (ns.dropna(subset=["year"])
           .groupby(["Class_CN", "year"]).size().rename("new_species").reset_index())
ns_year["year"] = ns_year["year"].astype(int)
ns_year.to_csv(OUT / "CHNR_summary_new_species_by_class_year.csv",
               index=False, encoding="utf-8-sig")

print("纲×目:")
print(by_order.to_string(index=False))
print(f"\n事件总数 {len(ev)}；两栖 {sum(ev['Class_CN']=='两栖纲')}，爬行 {sum(ev['Class_CN']=='爬行纲')}")
print(f"新种条目 {len(ns)}；两栖 {sum(ns['Class_CN']=='两栖纲')}，爬行 {sum(ns['Class_CN']=='爬行纲')}")
