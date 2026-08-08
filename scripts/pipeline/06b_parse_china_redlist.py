# ============================================================
# Objective / 分析目标:
# 从《中国生物多样性红色名录—脊椎动物卷(2020)》官方 PDF 解析
# 爬行类与两栖类的 濒危等级 与 特有种(√) 两列。
# Parse category and endemism columns for reptiles & amphibians
# from the official China Biodiversity Red List (2020) PDF.
# Input : source_data/conservation/mee2023_china_redlist_vertebrates_2020.pdf
# Output: source_data/conservation/china_redlist_herp.csv
# Method: pdfplumber 词坐标；√ 按 y 距离归属最近主行。
# ============================================================

import re
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "source_data/conservation/mee2023_china_redlist_vertebrates_2020.pdf"
OUT = ROOT / "source_data/conservation/china_redlist_herp.csv"

CATS = {"CR", "EN", "VU", "NT", "LC", "DD", "RE", "EW", "EX"}
BINOM = re.compile(r"^[A-Z][a-z-]+$")


def parse_pages(pdf, start, end, class_cn):
    """以等级词为行锚、按坐标带收词重建表行（容忍学名换行）。
    Anchor rows on category words; gather same-band words so that
    wrapped scientific names are still captured."""
    rows = []
    for pno in range(start, end):
        page = pdf.pages[pno]
        words = page.extract_words(keep_blank_chars=False)
        anchors = [w for w in words if w["text"] in CATS]
        for a in anchors:
            band = [w for w in words
                    if abs((w["top"] + w["bottom"]) / 2 - (a["top"] + a["bottom"]) / 2) < 12
                    and w is not a]
            left = sorted((w for w in band if w["x0"] < a["x0"]), key=lambda w: (w["top"], w["x0"]))
            right = [w for w in band if w["x0"] > a["x1"]]
            # 学名：取"其后第一个拉丁词是小写"的最后一个大写属名
            # binomial: last capitalized token directly followed (in latin
            # token order) by a lowercase epithet — skips family names
            latin = None
            toks = [w["text"] for w in left]
            is_genus = lambda t: (BINOM.match(t)
                                  and not re.search(r"(idae|inae)$", t))
            lat_toks = [(i, t) for i, t in enumerate(toks)
                        if is_genus(t) or re.match(r"^[a-z-]+$", t)]
            for k, (i, t) in enumerate(lat_toks):
                if is_genus(t) and k + 1 < len(lat_toks):
                    nxt = lat_toks[k + 1][1]
                    if re.match(r"^[a-z-]+$", nxt):
                        latin = f"{t} {nxt}"
            if latin is None:
                # 属名换行到带外：仅对拉丁词放宽纵向窗口 / widen band for
                # latin tokens when the genus wrapped outside the band
                wide = [w for w in words
                        if abs((w["top"] + w["bottom"]) / 2
                               - (a["top"] + a["bottom"]) / 2) < 24
                        and w["x0"] < a["x0"] and is_genus(w["text"])]
                ep = next((t for _, t in lat_toks if re.match(r"^[a-z-]+$", t)), None)
                if wide and ep:
                    g = min(wide, key=lambda w: abs((w["top"] + w["bottom"]) / 2
                                                    - (a["top"] + a["bottom"]) / 2))
                    latin = f"{g['text']} {ep}"
            zh = next((t for t in reversed([w["text"] for w in left])
                       if re.search(r"[一-鿿]", t) and not re.search(r"科$|目$", t)), None)
            endemic = any(w["text"] == "√" for w in right)
            if latin:
                rows.append({"Class_CN": class_cn, "Chinese_name": zh,
                             "Scientific_name": latin, "ChinaRedList": a["text"],
                             "Endemic": "YES" if endemic else "NO"})
    return rows


def main() -> None:
    with pdfplumber.open(PDF) as pdf:
        # 定位分节页 / locate section pages via page text
        rep_start = amp_start = fish_start = None
        for i, page in enumerate(pdf.pages):
            t = (page.extract_text() or "")[:200]
            if "红色名录·爬行类" in t and rep_start is None:
                rep_start = i
            elif "红色名录·两栖类" in t and amp_start is None:
                amp_start = i
            elif re.search(r"红色名录·(淡水|内陆)?鱼类", t) and fish_start is None and amp_start is not None:
                fish_start = i
        print(f"页定位: 爬行 {rep_start}, 两栖 {amp_start}, 鱼类 {fish_start}")
        rows = parse_pages(pdf, rep_start, amp_start, "爬行纲")
        rows += parse_pages(pdf, amp_start, fish_start or len(pdf.pages), "两栖纲")

    df = pd.DataFrame(rows).drop_duplicates(subset=["Scientific_name"], keep="first")
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"解析物种: {len(df)}")
    print(df.groupby(["Class_CN", "ChinaRedList"]).size().to_string())
    print("特有种数:")
    print(df.groupby("Class_CN")["Endemic"].apply(lambda s: (s == "YES").sum()).to_string())
    # 抽查 / spot checks
    for name in ["Andrias davidianus", "Alligator sinensis", "Testudo horsfieldii",
                 "Bufo gargarizans", "Quasipaa spinosa"]:
        m = df[df["Scientific_name"] == name]
        print(name, "->", m[["ChinaRedList", "Endemic"]].to_dict("records"))


if __name__ == "__main__":
    main()
