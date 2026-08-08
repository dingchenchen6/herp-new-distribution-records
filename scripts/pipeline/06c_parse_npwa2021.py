# ============================================================
# Objective / 分析目标:
# 解析《国家重点保护野生动物名录》(2021) 的两栖纲与爬行纲条目
# （保护级别 一级/二级），来源为维基百科条目的结构化模板转录，
# 并与官方扫描版 PDF 抽样比对校验。
# Parse Class I/II protection levels for herps from the 2021
# National Key Protected Wildlife List (structured Wikipedia
# transcription of the official announcement; spot-validated
# against the official scanned PDF).
# Input : source_data/conservation/npwa_wiki.txt
# Output: source_data/conservation/npwa2021_herp.csv
# ============================================================

import re
from pathlib import Path

import pandas as pd
from zhconv import convert  # 繁转简 / traditional -> simplified

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "source_data/conservation/npwa_wiki.txt"
OUT = ROOT / "source_data/conservation/npwa2021_herp.csv"

# 物种模板与属级(所有种)模板 / species and genus-level templates
TPL = re.compile(r"\{\{Protect_(species[a-z0-9]?|genus_all)\s*\|([^|{}]+)\|([^|{}]+)\|([^|{}]+)\}\}"
                 r"(?:\|\|([^\n]*))?")


def norm_level(s: str) -> str:
    """罗马数字级别规范化 / normalize protection level."""
    s = s.strip()
    if s in ("Ⅰ", "I", "1", "一", "一级"):
        return "一级"
    if s in ("Ⅱ", "II", "2", "二", "二级"):
        return "二级"
    return s


def main() -> None:
    text = convert(SRC.read_text(encoding="utf-8", errors="ignore"), "zh-cn")

    # 纲名标记定位（表内行，繁/简均容）/ class markers inside the wikitable
    CLASSES = ["哺乳綱", "哺乳纲", "鳥綱", "鸟纲", "爬行綱", "爬行纲",
               "兩棲綱", "两栖纲", "文昌魚綱", "文昌鱼纲", "圆口纲", "圓口綱",
               "軟骨魚綱", "软骨鱼纲", "硬骨魚綱", "硬骨鱼纲", "肠鳃纲", "腸鰓綱",
               "昆蟲綱", "昆虫纲", "珊瑚綱", "珊瑚纲", "水螅綱", "水螅纲",
               "腹足綱", "腹足纲", "雙殼綱", "双壳纲", "頭足綱", "头足纲",
               "蛛形綱", "蛛形纲", "肢口綱", "肢口纲", "軟甲綱", "软甲纲"]
    sec_pos = sorted((m.start(), kw) for kw in CLASSES for m in re.finditer(kw, text))

    def section_of(pos: int) -> str:
        cur = ""
        for p, name in sec_pos:
            if p <= pos:
                cur = name
            else:
                break
        return cur

    rows = []
    for m in TPL.finditer(text):
        tpl, zh, la, lv = m.group(1), m.group(2).strip(), m.group(3).strip(), m.group(4)
        note = (m.group(5) or "").strip()
        sec = section_of(m.start())
        rows.append({"section": sec, "template": tpl, "Chinese_name": zh,
                     "Scientific_name": la, "Protection_class": norm_level(lv),
                     "note": note})
    df = pd.DataFrame(rows)
    print("各节条目数 / entries per section:")
    print(df["section"].value_counts().to_string())

    herp = df[df["section"].str.contains("两栖|爬行", na=False)].copy()
    herp["Class_CN"] = herp["section"].str.extract(r"(两栖|爬行)")[0] \
        .map({"两栖": "两栖纲", "爬行": "爬行纲"})
    herp["is_group"] = (herp["template"] == "genus_all") \
        | herp["Scientific_name"].str.contains(r"spp\.?|所有种", case=False) \
        | herp["Chinese_name"].str.contains("所有种")
    herp = herp[["Class_CN", "Chinese_name", "Scientific_name",
                 "Protection_class", "is_group", "note"]]
    herp.to_csv(OUT, index=False, encoding="utf-8-sig")

    print(f"\n两爬条目: {len(herp)}")
    print(herp.groupby(["Class_CN", "Protection_class"]).size().to_string())
    print(f"属级(所有种)条目: {herp['is_group'].sum()}")
    for n in ["大鲵", "镇海棘螈", "四爪陆龟", "鳄蜥", "大壁虎", "细痣瑶螈", "平胸龟"]:
        m2 = herp[herp["Chinese_name"].str.contains(n, na=False)]
        print(n, "->", m2[["Scientific_name", "Protection_class"]].to_dict("records"))


if __name__ == "__main__":
    main()
