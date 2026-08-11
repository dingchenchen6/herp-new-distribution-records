# ============================================================
# Objective / 分析目标:
# 落实 755 行"排除-待人工判定"的终审裁定（基于网盘原文核实）：
# 1) 更新 06_pending_adjudication.csv 的最终裁定与依据
# 2) 同步 03_record_screening_log.csv 的 Verdict
# 3) 将已验证的事件行加入事件表（沙坝龙蜥×云南，王剀等2019）
# Apply the final, literature-verified verdicts for the 755
# pending rows; sync audit tables; add the one verified event.
# 运行后需重跑 06d(保护状态)、05(汇总)、07(统计) / rerun 06d,05,07 after.
# ============================================================

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADJ = ROOT / "audit_quality_control/06_manual_adjudication/06_pending_adjudication.csv"
SCR = ROOT / "audit_quality_control/03_record_screening/03_record_screening_log.csv"
EV = ROOT / "data/CHNR_provincial_new_records.csv"

# 终审裁定（原表行号 -> (裁定, 置信度, 依据)）/ final verdicts
V = {}
def put(rows, verdict, conf, basis):
    for r in rows:
        V[str(r)] = (verdict, conf, basis)

# —— 文献核实的排除 / literature-verified exclusions ——
put([512, 2164, 2165], "排除-非省级首次记录", "高",
    "已核原文《江西齐云山自然保护区两栖爬行动物资源调查与区系分析》(动物学杂志2008,43(6):68-76)：海南棱蜥与福建华珊瑚蛇为江西第二发现地、海南闪鳞蛇为第三采集地，均非省级首次")
put([1953, 2014], "排除-分布确认（非首次记录）", "高",
    "已核原文《湖北省无尾两栖动物三新记录种与宜章臭蛙湖北种群的补充描述》(四川动物2025,44(2))：宜章臭蛙为'确认分布记录'；该文三新记录种（中华湍蛙、贵师掌突蟾、桑植角蟾）均已在事件表")
put([2184], "排除-分类修订（非新纪录）", "高",
    "已核原文《湖南省花臭蛙复合体分类及分布格局》(动物学杂志2017,52(4))：为湖南既有种群的分类学再划分")
put([578], "排除-色型个体报道", "高", "已核原文《青海海北发现一例淡黄色高原林蛙》：色型记录，非分布新纪录")
put([599], "排除-省内分布影像确认", "高", "已核原文《影像证实海南尖峰岭多处有圆鼻巨蜥分布》：省内确认，非省级首次")
put([192], "排除-修订文伴随（产地订正）", "高",
    "已核原文王剀等2019(四川动物38(5))：昆明龙蜥为产地信息订正（西双版纳→大理鸡足山），云南已知分布")
put([60, 95], "排除-伴随物种（省内已知）", "中", "淡肩角蟾福建已知分布；新种描述文伴随记录")
put([70], "排除-伴随物种（省内已知）", "中", "雨神角蟾模式产地即福建；新种描述文伴随记录")
put([80, 89], "排除-伴随物种（省内已知）", "中", "短肢角蟾福建已知分布；新种描述文伴随记录")
put([110, 115], "排除-伴随物种（省内已知）", "中", "中国林蛙陕西已知分布；描述文伴随记录")
put([139, 141, 1354], "排除-伴随物种（省内已知）", "中", "峨山掌突蟾四川（峨眉山模式产地）已知分布")
put([161, 169], "排除-系统学文献伴随", "中", "Cynops 系统学研究材料；潮汕蝾螈广东/蓝尾蝾螈云南均为已知分布")
put([1287], "排除-分类修订伴随", "中", "Calotes 修订文；云南树蜥云南为已知分布")
put([1418], "排除-分类学文献伴随", "中", "Hebius sauteri 组分类研究；台湾为已知分布")
put([1093, 2227], "排除-新种表已收录", "高", "荔波角蟾已在新种表，该行为描述文重复行")
put([2226], "排除-新种表已收录", "高", "雷山角蟾已在新种表，该行为描述文重复行")
put([1420, 1514, 1731, 148], "排除-无省级信息（系统学/命名学文献）", "高", "无省份归属，为系统发育/命名学讨论行")
put([1006], "排除-国外类群", "高", "Podarcis muralis 欧洲研究，无中国省份")
put([1401], "排除-国外记录", "高", "老挝水龙蜥为老挝研究材料")
put([67, 71, 82, 294, 344, 637, 1932, 1933, 1936, 2035, 2036, 2037, 2038, 2050],
    "排除(建议)-无引用且该省为已知分布", "中",
    "无文献引用；物种在该省为长期已知分布（疑为名录/调查残行），无法构成可溯源的省级首次记录")

# —— 转入事件表（已验证）/ verified event ——
put([1820], "转入事件表", "高",
    "已核原文王剀等2019(四川动物38(5):481-495)：云南中西部'草绿龙蜥'系沙坝龙蜥误定，为沙坝龙蜥在云南省（及中国）的首次确认记录")
put([1823], "排除-再记录（与行1820同事件）", "高", "与行1820同种同省同文献")

# —— 转入新种表（建议·待复核）/ recommended moves to new-species table ——
NS_REC = {76: "三明角蟾", 68: "戴云角蟾", 1094: "林氏角蟾", 1101: "龙头山臭蛙",
          1118: "腺皱琴蛙", 1137: "腺棘琴蛙", 1145: "腺耳琴蛙",
          1262: "布氏齿突蟾", 1265: "瘤突齿突蟾", 1266: "吴氏齿突蟾",
          1313: "红斑高山蝮", 1583: "攀枝花脊蛇", 1584: "屏边脊蛇",
          1601: "十万大山掌突蟾", 1346: "井冈角蟾(该行物种名缺失，据文献补)", 101: "陈氏蛙"}
for r, zh in NS_REC.items():
    put([r], "转入新种表(建议·待复核)", "复核",
        f"{zh}不在新种表且为该描述文献的对象种，疑为被误搁的新种描述行；请对照原文确认后转入")
put([104], "排除-重复（与行101同条目）", "复核", "与行101同种同省同文献")

# —— 仍需人工（8行，均给出倾向）/ residual manual with leanings ——
put([132, 2017], "待人工-倾向核对（西藏记录）", "需人工",
    "Jiang et al. 文献未能取得；棘疣树蛙/棘皮树蛙之西藏记录可能为新纪录报道或墨脱已知分布，请查原文")
put([1371, 1376], "待人工-倾向转入事件表", "需人工",
    "Guo et al.：艾氏坭蛇/山坭蛇之西藏记录疑为中国/西藏新纪录报道，请查原文确认")
put([1597, 2145], "待人工-倾向转入事件表", "需人工",
    "Yan et al.：北小跳蛙/北方印蛙之西藏记录疑为中国新纪录报道，请查原文确认")
put([2161, 2162], "待人工-倾向转入事件表", "需人工",
    "Zhong et al.：单后颞鳞腹链蛇/布莱克威腹链蛇之云南记录疑为中国新纪录报道，请查原文确认")


def main() -> None:
    adj = pd.read_csv(ADJ, dtype=str)
    n_up = 0
    for i, r in adj.iterrows():
        sr = str(r["Source_row"])
        if sr in V:
            verdict, conf, basis = V[sr]
            adj.at[i, "建议裁定"], adj.at[i, "置信度"], adj.at[i, "裁定依据"] = verdict, conf, basis
            n_up += 1
    adj.to_csv(ADJ, index=False, encoding="utf-8-sig")

    scr = pd.read_csv(SCR, dtype=str)
    vmap = dict(zip(adj["Source_row"], adj["建议裁定"]))
    mask = scr["Verdict"] == "排除-待人工判定"
    scr.loc[mask, "Verdict"] = scr.loc[mask, "Source_row"].map(
        lambda s: f"终审:{vmap.get(str(s), '排除-待人工判定')}")
    scr.to_csv(SCR, index=False, encoding="utf-8-sig")

    # 新增已验证事件：沙坝龙蜥×云南 / add the verified event
    ev = pd.read_csv(EV, dtype=str)
    if not ((ev["Chinese_name_as_published"] == "沙坝龙蜥") &
            (ev["New_distribution_province"] == "云南")).any():
        src = pd.read_excel(ROOT / "source_data/两栖爬行动物数据合并表-8.7修订完善版.xlsx",
                            sheet_name="总表", dtype=str).set_index("原表行号").loc["1820"]
        row = {c: None for c in ev.columns}
        row.update({
            "ID": str(int(pd.to_numeric(ev["ID"]).max()) + 1), "Source_row": "1820",
            "Class_CN": "爬行纲",
            "Chinese_name_COL_China_2026": "沙坝龙蜥", "Scientific_name_COL_China_2026": "Diploderma chapaense",
            "Chinese_name_as_published": "沙坝龙蜥", "Scientific_name_as_published": "Diploderma chapaense",
            "Reported_rank": "species",
            "OrderCN_COL_China_2026": "有鳞目", "OrderLA_COL_China_2026": "Squamata",
            "FamilyCN_COL_China_2026": "鬣蜥科", "FamilyLA_COL_China_2026": "Agamidae",
            "GenusCN_COL_China_2026": "攀蜥属", "GenusLA_COL_China_2026": "Diploderma",
            "Taxon_match_method": "人工终审", "Taxon_match_note": "误定订正产生的省级首次记录（原云南'草绿龙蜥'）",
            "New_distribution_province": "云南", "Province_basis": "原文明示",
            "Discovery_sites": src.get("locality_zh"),
            "Longitude": src.get("longitude_dd"), "Latitude": src.get("latitude_dd"),
            "Coordinate_basis": "原文报道坐标" if pd.notna(src.get("latitude_dd")) else None,
            "Evidence_type": "标本", "Voucher": src.get("voucher"),
            "Record_type": "新纪录", "Record_type_basis": "人工终审（误定订正）",
            "Source_citation": "王剀,任金龙,蒋珂,等. 龙蜥属Diploderma部分物种的分类及分布记录修订[J].四川动物,2019,38(5):481-495.",
            "Source_publication_year": "2019", "Source_authors": "王剀、任金龙、蒋珂等",
            "Source_journal": "四川动物", "DOI": "10.11984/j.issn.1000-7083.20180405",
        })
        ev = pd.concat([ev, pd.DataFrame([row])], ignore_index=True)
        ev.to_csv(EV, index=False, encoding="utf-8-sig")
        print("已新增事件: 沙坝龙蜥×云南 (ID", row["ID"], ")")

    print(f"裁定更新 {n_up} 行；筛选日志已同步")
    print(adj["置信度"].value_counts().to_string())


if __name__ == "__main__":
    main()
