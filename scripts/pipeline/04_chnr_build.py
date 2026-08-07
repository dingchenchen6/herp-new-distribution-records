# ============================================================
# Scientific question / 科学问题:
# 参照 CBNR（中国鸟类新纪录数据集, Ding et al.）的事件定义与
# 清洗流程，把两爬合并表整理为可发布的省级新纪录事件数据集。
# Following the CBNR pipeline, convert the merged herp table
# into a clean provincial new-record event dataset (CHNR).
#
# Objective / 分析目标:
# 1) 行级筛选：省级新纪录事件 vs 新种描述 vs 排除（非两爬/国外/
#    属级/类型不明），全程留痕（03 筛选日志）
# 2) 省份规范化 + 多省拆分 + 点-省空间匹配（CBNR 省界 shapefile）
# 3) 物种×省份去重（最早发表年规则, 05 日志）
# 4) 字段标准化：日期 ISO、海拔、生境大类、凭证类型
# 5) 输出 CBNR 式数据包（dataset + audit_quality_control + README）
#
# Input / 输入数据:
# - 两栖爬行动物数据合并表-8.7修订完善版.xlsx（总表, 45列）
# - CBNR 省界 province_boundaries.shp (EPSG:4326)
# Output / 预期输出:
# - ~/Downloads/China_Herp_New_Record_CHNR_v0.1/ 数据包
# Key assumptions / 关键假设:
# - 事件单元 = 物种×省份首次记录（同 CBNR）；亚种级记录保留并标记
#   （与 CBNR 的排除处理不同，见 README 偏差说明）。
# - 省级首次性未逐篇核验，暂以"最早发表年"近似（README 已声明）。
# Main packages / 主要包: pandas, geopandas, shapely, openpyxl
# ============================================================

import re
import shutil
import unicodedata
from pathlib import Path
from typing import List, Optional, Tuple

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[2]  # 仓库根目录 / repo root
SRC = str(ROOT / "source_data/两栖爬行动物数据合并表-8.7修订完善版.xlsx")
SHP = str(ROOT / "scripts/figure1a_province_map/input/province_boundaries.shp")
OUT = ROOT  # 数据与审计直接写入仓库 / write into the repo tree
HERP_CLASSES = ("两栖纲", "爬行纲")

# 省名规范：官方全称 -> 简名 / official -> short province names
PROV_SHORT = {
    "北京市": "北京", "天津市": "天津", "河北省": "河北", "山西省": "山西",
    "内蒙古自治区": "内蒙古", "辽宁省": "辽宁", "吉林省": "吉林", "黑龙江省": "黑龙江",
    "上海市": "上海", "江苏省": "江苏", "浙江省": "浙江", "安徽省": "安徽",
    "福建省": "福建", "江西省": "江西", "山东省": "山东", "河南省": "河南",
    "湖北省": "湖北", "湖南省": "湖南", "广东省": "广东", "广西壮族自治区": "广西",
    "海南省": "海南", "重庆市": "重庆", "四川省": "四川", "贵州省": "贵州",
    "云南省": "云南", "西藏自治区": "西藏", "陕西省": "陕西", "甘肃省": "甘肃",
    "青海省": "青海", "宁夏回族自治区": "宁夏", "新疆维吾尔自治区": "新疆",
    "台湾省": "台湾", "香港特别行政区": "香港", "澳门特别行政区": "澳门",
}
SHORT2FULL = {v: k for k, v in PROV_SHORT.items()}
# 台湾县市与常见别写归并 / Taiwan counties & variants folded to province
PROV_ALIAS = {
    "台东县": "台湾", "宜兰县": "台湾", "南投县": "台湾", "台北县": "台湾",
    "台北": "台湾", "新北": "台湾", "彭佳屿": "台湾",
}

HABITAT_RULES = [
    ("溪流/河流", r"溪|河|急流|瀑|水沟"),
    ("森林", r"林|阔叶|针叶|竹"),
    ("湿地/静水水体", r"湿地|沼泽|水塘|池|湖|水库"),
    ("农田/种植园", r"农田|稻田|田|茶园|耕地|果园"),
    ("灌丛/草地", r"灌|草"),
    ("洞穴", r"洞"),
    ("海滨/海洋", r"海"),
    ("人工生境", r"路|公路|房|村|建筑|水泥|庭院|校园"),
    ("荒漠/沙地", r"荒漠|沙"),
    ("高山流石滩/石山", r"石海|流石|岩|石山|喀斯特"),
]

CLEAN_FIELDS = [
    "ID", "Class_CN", "Chinese_name_COL_China_2026", "Scientific_name_COL_China_2026",
    "Chinese_name_as_published", "Scientific_name_as_published", "Reported_rank",
    "OrderCN_COL_China_2026", "OrderLA_COL_China_2026",
    "FamilyCN_COL_China_2026", "FamilyLA_COL_China_2026",
    "GenusCN_COL_China_2026", "GenusLA_COL_China_2026",
    "Taxon_match_method", "Taxon_match_note",
    "Original_distribution", "New_distribution_province", "Province_basis",
    "Discovery_sites", "Longitude", "Latitude", "Coordinate_basis",
    "Altitude_raw", "Altitude_m", "Discovery_date", "Discovery_date_raw",
    "Habitat_category", "Habitat_raw", "Evidence_type", "Voucher",
    "Record_type", "Record_type_basis", "Duplicate_group",
    "IUCN_RED_LIST", "CHINA_RED_LIST", "China_Protection_Class", "Endemic_to_China",
    "Source_citation", "Source_publication_year", "Source_authors",
    "Source_journal", "DOI", "Source_row",
]


def norm(s) -> Optional[str]:
    """全角转半角并去空白 / normalize text or None."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = unicodedata.normalize("NFKC", str(s)).strip()
    return re.sub(r"\s+", " ", s) or None


def parse_provinces(raw: Optional[str]) -> Tuple[List[str], List[str]]:
    """省份字段 -> (中国省份简名列表, 未识别/外国部分) / split provinces."""
    if not raw:
        return [], []
    cn, other = [], []
    for part in re.split(r"[、,/;；和及]|与", raw):
        part = part.strip()
        if not part:
            continue
        part = re.sub(r"^中国", "", part)
        hit = None
        for short in SHORT2FULL:
            if part.startswith(short):
                hit = short
                break
        if hit is None:
            hit = PROV_ALIAS.get(part)
        if hit:
            if hit not in cn:
                cn.append(hit)
        else:
            other.append(part)
    return cn, other


def parse_dates(raw: Optional[str]) -> Optional[str]:
    """取最早日期并转 ISO / earliest date to ISO (YYYY[-MM[-DD]])."""
    if not raw:
        return None
    s = norm(raw) or ""
    found = []
    for m in re.finditer(r"(\d{4})\s*年\s*(?:(\d{1,2})\s*月)?\s*(?:(\d{1,2})\s*日)?", s):
        found.append((int(m.group(1)), int(m.group(2) or 0), int(m.group(3) or 0)))
    for m in re.finditer(r"(\d{4})-(\d{1,2})(?:-(\d{1,2}))?", s):
        found.append((int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)))
    months = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
              "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
              "december": 12}
    for m in re.finditer(r"(?:(\d{1,2})[\s–-]*)?([A-Za-z]+)\s+(\d{4})", s):
        mon = months.get(m.group(2).lower())
        if mon:
            found.append((int(m.group(3)), mon, int(m.group(1) or 0)))
    found = [f for f in found if 1900 <= f[0] <= 2026]
    if not found:
        return None
    y, mo, d = min(found)
    if mo and d:
        return f"{y:04d}-{mo:02d}-{d:02d}"
    if mo:
        return f"{y:04d}-{mo:02d}"
    return f"{y:04d}"


def parse_altitude(raw: Optional[str]) -> Optional[float]:
    """海拔解析：单值取值，多值/区间取均值 / parse altitude (mean of range)."""
    if not raw:
        return None
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(raw))]
    nums = [x for x in nums if 0 <= x <= 8900]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 1)


def habitat_category(raw: Optional[str]) -> Optional[str]:
    """生境文字 -> 大类 / harmonize habitat into broad categories."""
    if not raw:
        return None
    hits = [name for name, pat in HABITAT_RULES if re.search(pat, raw)]
    if not hits:
        return "其他/未归类"
    if len(hits) == 1:
        return hits[0]
    return "混合生境（" + "+".join(hits[:3]) + "）"


def evidence_type(remarks: Optional[str], voucher: Optional[str]) -> Optional[str]:
    """凭证类型 / evidence type from remarks + voucher."""
    text = (remarks or "") + " " + (voucher or "")
    out = []
    if re.search(r"有标本|标本：|specimen", text, re.I) or (voucher and not re.search(r"image|照片", voucher, re.I)):
        out.append("标本")
    if re.search(r"照片|拍摄|影像|photo|image", text, re.I):
        out.append("照片/影像")
    if re.search(r"活体观察|观察|observation", text, re.I):
        out.append("野外观察")
    if re.search(r"分子|DNA|序列|molecular|16S|COI", text, re.I):
        out.append("分子证据")
    if not out:
        if re.search(r"无标本", text):
            return "未提供凭证"
        return None
    return "、".join(dict.fromkeys(out))


def species_tied_to_citation(cite: str, zh: Optional[str], la: Optional[str]) -> bool:
    """该行物种是否为文献标题所指主体 / is this row's species named in the citation?"""
    if zh and len(zh) >= 3 and zh in cite:
        return True
    if la:
        toks = la.split()
        if len(toks) >= 2 and len(toks[1]) >= 4 and toks[1].lower() in cite.lower():
            return True
    return False


def infer_record_type(rt: Optional[str], cite: Optional[str], remarks: Optional[str],
                      match_method: str, zh: Optional[str], la: Optional[str]) -> Tuple[str, str]:
    """记录类型判定（含物种-文献绑定检查）/ record type with species-citation tie."""
    if rt:
        if "新物种" in rt or "新种" in rt:
            return "新物种", "原表标注"
        if "亚种" in rt:
            return "新亚种", "原表标注"
        if "新纪录" in rt or "新记录" in rt:
            if "其他" in rt:
                return "其他类记录", "原表标注"
            return "新纪录", "原表标注"
    if match_method == "未匹配-新种未收录":
        return "新物种", "据名录匹配情况推断"
    text = (cite or "") + " " + (remarks or "")
    if re.search(r"再发现|rediscover", text, re.I):
        return "其他类记录", "据引用推断（再发现）"
    if re.search(r"新纪录|新记录|新分布|分布新|首次记录|首次发现|new record|first record|new distribution|new provincial", text, re.I):
        return "新纪录", "据引用/备注推断"
    if re.search(r"新种|新物种|sp\. ?nov|new species", text, re.I):
        if cite and species_tied_to_citation(cite, zh, la):
            return "新物种", "据引用推断（物种见于文献标题）"
        return "伴随物种", "新种描述文献中的其他物种行，需人工判定"
    if re.search(r"区系|资源概况|多样性|物种名录|调查报告|herpetofauna|species list|diversity", text, re.I):
        return "调查清单", "据引用推断（区系/调查类文献的物种清单行）"
    return "未定", "无法判定"


def main() -> None:
    rec = pd.read_excel(SRC, sheet_name="总表", dtype=str)
    prov_gdf = gpd.read_file(SHP)[["name", "geometry"]]

    def point_province(lon, lat) -> Optional[str]:
        """点-省空间匹配 / point-in-polygon province lookup."""
        hit = prov_gdf[prov_gdf.contains(Point(lon, lat))]
        if len(hit):
            return PROV_SHORT.get(hit.iloc[0]["name"], hit.iloc[0]["name"])
        return None

    screening = []   # 03 行级筛选日志 / row screening log
    events = []      # 事件候选 / event candidates
    newspecies = []  # 新种描述表 / new species table
    coord_audit = []  # 04 坐标审计 / coordinate audit

    for _, r in rec.iterrows():
        srow = r["原表行号"]
        gn = lambda c: norm(r.get(c))
        cls = gn("纲_名录")
        match_method = gn("名录匹配方式") or ""
        tags = gn("审查标记") or ""
        lon = float(r["longitude_dd"]) if pd.notna(r["longitude_dd"]) else None
        lat = float(r["latitude_dd"]) if pd.notna(r["latitude_dd"]) else None

        def screen(verdict, reason):
            screening.append({
                "Source_row": srow, "Chinese_name_raw": gn("species_zh"),
                "Scientific_name_raw": gn("scientific_name"),
                "Province_raw": gn("province_zh"), "Verdict": verdict, "Reason": reason,
                "Source_citation": gn("文献标准引用格式")})

        # --- 排除：非两爬 / exclude non-herp rows ---
        if cls and cls not in HERP_CLASSES:
            screen("排除", f"名录归{cls}，非两栖爬行动物")
            continue
        if "非两爬" in tags:
            screen("排除", "非两爬/问题条目：" + tags)
            continue
        if gn("species_zh") is None and gn("scientific_name") is None:
            screen("排除", "无物种信息")
            continue

        rt, rt_basis = infer_record_type(gn("record_type_zh"), gn("文献标准引用格式"),
                                         gn("remarks_zh"), match_method,
                                         gn("species_zh"), gn("scientific_name"))

        # --- 省份解析 / province resolution ---
        provs, foreign = parse_provinces(gn("province_zh"))
        prov_basis = "原表标注" if provs else None
        in_china = None
        if lon is not None and lat is not None:
            pt_prov = point_province(lon, lat)
            in_china = pt_prov is not None
            if provs and pt_prov and pt_prov not in provs:
                coord_audit.append({
                    "Source_row": srow, "Chinese_name": gn("species_zh"),
                    "Scientific_name": gn("scientific_name"),
                    "Province_stated": "、".join(provs), "Longitude": lon, "Latitude": lat,
                    "Matched_boundary_name": pt_prov,
                    "Screen_status": "省份不一致", "Screen_note": "坐标落点省份与标注省份不一致，请核查"})
            if not provs and pt_prov and not foreign:
                provs, prov_basis = [pt_prov], "据坐标空间匹配推定"

        # --- 新种描述 -> 伴随表 / new species descriptions ---
        if rt == "新物种":
            if foreign and not provs:
                screen("排除", "国外新种描述（省份为外国地名）")
                continue
            if in_china is False and not provs:
                screen("排除", "国外新种描述（坐标在中国境外）")
                continue
            newspecies.append({
                "Source_row": srow, "Class_CN": cls,
                "Chinese_name_COL_China_2026": gn("名录中文名"),
                "Scientific_name_COL_China_2026": gn("名录拉丁名"),
                "Chinese_name_as_published": gn("species_zh"),
                "Scientific_name_as_published": gn("scientific_name"),
                "OrderCN_COL_China_2026": gn("目中文名_名录"),
                "FamilyLA": gn("family_en"), "FamilyCN": gn("family_zh"),
                "GenusLA": gn("genus_en"), "GenusCN": gn("genus_zh"),
                "Type_locality": gn("locality_zh"),
                "Province": "、".join(provs) if provs else gn("province_zh"),
                "Longitude": lon, "Latitude": lat,
                "Altitude_raw": gn("elevation"),
                "Discovery_date": parse_dates(gn("collection_date")),
                "Habitat_raw": gn("habitat_zh"), "Voucher": gn("voucher"),
                "Evidence_type": evidence_type(gn("remarks_zh"), gn("voucher")),
                "Source_citation": gn("文献标准引用格式"),
                "Source_publication_year": gn("发表年份") or gn("year"),
                "Source_authors": gn("authors"), "Source_journal": gn("journal"),
                "DOI": gn("DOI")})
            screen("新种表", "新种描述，转入 CHNR_new_species")
            continue

        # --- 排除：类型/属级优先于省份缺失，审计原因更可解释 ---
        # record-type exclusions take precedence over missing-province
        if match_method == "属级" or re.search(r"\bsp{1,2}\.", gn("scientific_name") or ""):
            screen("排除", "属级记录，非种级事件")
            continue
        if rt == "其他类记录":
            screen("排除", "记录类型为'其他新纪录/再发现'等，未纳入省级新纪录事件表")
            continue
        if rt == "伴随物种":
            screen("排除-待人工判定", "新种描述文献中的伴随物种记录，非明确新纪录事件")
            continue
        if rt == "调查清单":
            screen("排除", "区系/多样性调查类文献的物种清单行，非新纪录事件")
            continue
        if rt == "未定":
            screen("排除-待人工判定", "记录类型无法判定（原表未标注且引用无线索）")
            continue
        if rt == "新亚种":
            screen("排除", "亚种级新分类单元描述")
            continue
        if not provs:
            if foreign:
                screen("排除", "国外记录（省份字段为外国地名：" + "、".join(foreign[:3]) + "）")
            elif in_china is False:
                screen("排除", "国外记录（坐标在中国境外）")
            else:
                screen("排除", "省级信息缺失且无法由坐标推定")
            continue

        # --- 生成事件（多省拆分） / build events with province split ---
        rank = "亚种（已归并至种级）" if ("亚种归并" in (gn("名录匹配备注") or "") or "亚种归并" in match_method) else "种"
        for p in provs:
            has_pt = (lon is not None and lat is not None
                      and (len(provs) == 1 or point_province(lon, lat) == p))
            coord_basis = None
            if has_pt:
                note = gn("坐标备注") or ""
                if "地理编码" in note or "定位" in note or gn("经纬度是否为后续补充") == "是":
                    coord_basis = "文字地名地理编码/后续补充"
                else:
                    coord_basis = "原文报道坐标"
            events.append({
                "Class_CN": cls,
                "Chinese_name_COL_China_2026": gn("名录中文名"),
                "Scientific_name_COL_China_2026": gn("名录拉丁名"),
                "Chinese_name_as_published": gn("species_zh"),
                "Scientific_name_as_published": gn("scientific_name"),
                "Reported_rank": rank,
                "OrderCN_COL_China_2026": gn("目中文名_名录"),
                "OrderLA_COL_China_2026": gn("目拉丁名_名录"),
                "FamilyCN_COL_China_2026": gn("family_zh"),
                "FamilyLA_COL_China_2026": gn("family_en"),
                "GenusCN_COL_China_2026": gn("genus_zh"),
                "GenusLA_COL_China_2026": gn("genus_en"),
                "Taxon_match_method": match_method,
                "Taxon_match_note": gn("名录匹配备注"),
                "Original_distribution": gn("original_distribution_zh"),
                "New_distribution_province": p,
                "Province_basis": prov_basis + ("；多省记录拆分" if len(provs) > 1 else ""),
                "Discovery_sites": gn("locality_zh"),
                "Longitude": lon if has_pt else None,
                "Latitude": lat if has_pt else None,
                "Coordinate_basis": coord_basis if has_pt else ("多省拆分-该省无点位" if len(provs) > 1 else None),
                "Altitude_raw": gn("elevation"),
                "Altitude_m": parse_altitude(gn("elevation")),
                "Discovery_date": parse_dates(gn("collection_date")),
                "Discovery_date_raw": gn("collection_date"),
                "Habitat_category": habitat_category(gn("habitat_zh")),
                "Habitat_raw": gn("habitat_zh"),
                "Evidence_type": evidence_type(gn("remarks_zh"), gn("voucher")),
                "Voucher": gn("voucher"),
                "Record_type": rt, "Record_type_basis": rt_basis,
                "Duplicate_group": None,
                "IUCN_RED_LIST": None, "CHINA_RED_LIST": None,
                "China_Protection_Class": None, "Endemic_to_China": None,
                "Source_citation": gn("文献标准引用格式"),
                "Source_publication_year": gn("发表年份") or gn("year"),
                "Source_authors": gn("authors"), "Source_journal": gn("journal"),
                "DOI": gn("DOI"), "Source_row": srow})
        screen("事件表", f"省级新纪录事件（{len(provs)}省）")

    ev = pd.DataFrame(events)

    # --- 05 物种×省份去重（最早发表年） / species-province dedup ---
    def species_key(row) -> str:
        return (row["Scientific_name_COL_China_2026"] or row["Scientific_name_as_published"]
                or row["Chinese_name_COL_China_2026"] or row["Chinese_name_as_published"] or "?")

    ev["_sp"] = ev.apply(species_key, axis=1)
    ev["_yr"] = pd.to_numeric(ev["Source_publication_year"], errors="coerce")
    dup_log = []
    keep_mask = pd.Series(True, index=ev.index)
    gid = 0
    for (sp, pv), g in ev.groupby(["_sp", "New_distribution_province"]):
        if len(g) == 1:
            continue
        gid += 1
        gname = f"DUP{gid:03d}"
        ev.loc[g.index, "Duplicate_group"] = gname
        yrs = g["_yr"]
        if yrs.notna().any():
            earliest = yrs.min()
            cand = g[yrs == earliest]
            retained = cand.index[0]
            status_extra = "同最早年多条，保留行序最先者，需人工裁定" if len(cand) > 1 else ""
        else:
            retained = g.index[0]
            status_extra = "发表年缺失，保留行序最先者，需人工裁定"
        for idx in g.index:
            is_keep = idx == retained
            if not is_keep:
                keep_mask[idx] = False
            dup_log.append({
                "Duplicate_group_id": gname, "Group_size": len(g),
                "Species_key": sp, "New_distribution_province": pv,
                "Source_row": ev.at[idx, "Source_row"],
                "Source_publication_year": ev.at[idx, "Source_publication_year"],
                "Resolution_status": ("retained" if is_keep else "removed_later_duplicate")
                                     + ("；" + status_extra if status_extra and is_keep else ""),
                "Retained_source_row": ev.at[retained, "Source_row"],
                "Source_citation": ev.at[idx, "Source_citation"]})

    clean = ev[keep_mask].drop(columns=["_sp", "_yr"]).reset_index(drop=True)
    clean.insert(0, "ID", range(1, len(clean) + 1))
    clean = clean[CLEAN_FIELDS]

    # --- 02 分类复核表 / taxonomy review table ---
    tax_review = clean[clean["Taxon_match_note"].notna()
                       | clean["Scientific_name_COL_China_2026"].isna()][
        ["ID", "Source_row", "Chinese_name_as_published", "Scientific_name_as_published",
         "Chinese_name_COL_China_2026", "Scientific_name_COL_China_2026",
         "Taxon_match_method", "Taxon_match_note"]].copy()

    # --- 04 坐标表 / coordinate tables ---
    coord_parsed = clean[["ID", "Source_row", "Chinese_name_COL_China_2026",
                          "Scientific_name_COL_China_2026", "New_distribution_province",
                          "Discovery_sites", "Longitude", "Latitude", "Coordinate_basis"]].copy()
    completion = clean[clean["Coordinate_basis"] == "文字地名地理编码/后续补充"][
        ["ID", "Source_row", "Chinese_name_COL_China_2026", "Scientific_name_COL_China_2026",
         "New_distribution_province", "Discovery_sites", "Longitude", "Latitude"]].copy()

    # --- 输出 / write package ---
    for sub in ["data", "docs", "audit_quality_control/02_taxonomy_harmonisation",
                "audit_quality_control/03_record_screening",
                "audit_quality_control/04_coordinate_georeferencing",
                "audit_quality_control/05_duplicate_review"]:
        (OUT / sub).mkdir(parents=True, exist_ok=True)

    # --- 新种表按物种去重（保留信息最全者） / dedup new-species table ---
    ns = pd.DataFrame(newspecies)
    ns_dup_log = pd.DataFrame()
    if len(ns):
        ns["_sp"] = ns["Scientific_name_COL_China_2026"].fillna(
            ns["Scientific_name_as_published"]).fillna(ns["Chinese_name_as_published"])
        ns["_completeness"] = ns.notna().sum(axis=1)
        ns["_yr"] = pd.to_numeric(ns["Source_publication_year"], errors="coerce")
        ns = ns.sort_values(["_sp", "_completeness", "_yr"],
                            ascending=[True, False, True])
        dup_mask = ns.duplicated("_sp", keep="first")
        ns_dup_log = ns[dup_mask][["Source_row", "_sp", "Source_citation",
                                   "Source_publication_year"]].copy()
        ns_dup_log.columns = ["Source_row", "Species_key", "Source_citation",
                              "Source_publication_year"]
        ns_dup_log["Resolution_status"] = "removed_duplicate_new_species_row"
        ns = ns[~dup_mask].drop(columns=["_sp", "_completeness", "_yr"]) \
            .sort_values("Source_row", key=lambda s: pd.to_numeric(s, errors="coerce")) \
            .reset_index(drop=True)
    ns.insert(0, "ID", range(1, len(ns) + 1))
    scr = pd.DataFrame(screening)
    dlog = pd.DataFrame(dup_log)
    caudit = pd.DataFrame(coord_audit)

    def wcsv(df, path):
        df.to_csv(OUT / path, index=False, encoding="utf-8-sig")

    wcsv(clean, "data/CHNR_provincial_new_records.csv")
    wcsv(ns, "data/CHNR_new_species.csv")
    wcsv(scr, "audit_quality_control/03_record_screening/03_record_screening_log.csv")
    wcsv(tax_review, "audit_quality_control/02_taxonomy_harmonisation/02_taxonomy_review.csv")
    wcsv(coord_parsed, "audit_quality_control/04_coordinate_georeferencing/04_1_parsed_coordinates.csv")
    if len(caudit):
        wcsv(caudit, "audit_quality_control/04_coordinate_georeferencing/04_2_coordinate_audit.csv")
    wcsv(completion, "audit_quality_control/04_coordinate_georeferencing/04_3_coordinate_completion_log.csv")
    wcsv(dlog, "audit_quality_control/05_duplicate_review/05_1_duplicate_resolution_log.csv")
    if len(ns_dup_log):
        wcsv(ns_dup_log, "audit_quality_control/05_duplicate_review/05_2_new_species_dedup_log.csv")

    # Excel 汇总工作簿 / bundled workbook
    with pd.ExcelWriter(OUT / "data/CHNR_v0.1.xlsx", engine="openpyxl") as xw:
        clean.to_excel(xw, sheet_name="provincial_new_records", index=False)
        ns.to_excel(xw, sheet_name="new_species", index=False)
        summ = (clean.groupby(["Class_CN", "OrderCN_COL_China_2026"]).size()
                .rename("events").reset_index())
        summ.to_excel(xw, sheet_name="summary_order", index=False)
        clean.groupby("New_distribution_province").size().rename("events").reset_index() \
            .to_excel(xw, sheet_name="summary_province", index=False)


    # --- 字段词典 / metadata dictionary ---
    meta_rows = [
        ("ID", "事件序号 / Sequential event ID"),
        ("Class_CN", "纲（两栖纲/爬行纲），据《中国生物物种名录》2026 / Class per COL China 2026"),
        ("Chinese_name_COL_China_2026", "名录现行中文名（含名录括号别名）/ Accepted Chinese name"),
        ("Scientific_name_COL_China_2026", "名录现行有效拉丁名；空=未收录或待定 / Accepted binomial; blank = unresolved"),
        ("Chinese_name_as_published", "原文献所用中文名 / Chinese name as published"),
        ("Scientific_name_as_published", "原文献所用拉丁名（保留异名与拼写）/ Scientific name as published"),
        ("Reported_rank", "种 或 亚种（已归并至种级）/ reported rank"),
        ("OrderCN/LA, FamilyCN/LA, GenusCN/LA _COL_China_2026", "目/科/属 中拉名，据名录（游蛇科按科级拼法 Colubridae）/ higher taxonomy per COL China 2026"),
        ("Taxon_match_method", "名录匹配方式（精确/亚种归并/核定异名/种加词推断/模糊等）/ matching method"),
        ("Taxon_match_note", "匹配复核备注；非空者建议人工复核 / review note"),
        ("Original_distribution", "原文所述既有分布 / distribution stated by source"),
        ("New_distribution_province", "新分布省级单元（简名）/ province of new record"),
        ("Province_basis", "省份来源（原表标注/据坐标空间匹配推定/多省拆分）/ basis of province"),
        ("Discovery_sites", "发现地点（原文文字）/ discovery site text"),
        ("Longitude/Latitude", "WGS84 十进制度 / WGS84 decimal degrees"),
        ("Coordinate_basis", "原文报道坐标 或 文字地名地理编码/后续补充 或 多省拆分-该省无点位 / coordinate provenance"),
        ("Altitude_raw / Altitude_m", "海拔原文 / 解析值（区间与多值取均值）/ raw and parsed altitude"),
        ("Discovery_date(_raw)", "ISO 最早发现日期 / 原文 / earliest date in ISO + raw"),
        ("Habitat_category / Habitat_raw", "生境大类（规则归并）/ 原文 / harmonized habitat + raw"),
        ("Evidence_type", "凭证类型（标本/照片影像/野外观察/分子证据/未提供）/ evidence type"),
        ("Voucher", "标本号 / voucher IDs"),
        ("Record_type / Record_type_basis", "记录类型与判定依据 / record type and its basis"),
        ("Duplicate_group", "物种×省份重复组号（本行为保留行）/ duplicate group id (this row retained)"),
        ("IUCN_RED_LIST / CHINA_RED_LIST / China_Protection_Class / Endemic_to_China",
         "占位列，待接入红色名录/保护名录/特有性 / placeholders for future joins"),
        ("Source_citation/…year/…authors/…journal/DOI", "文献信息 / source publication fields"),
        ("Source_row", "溯源：8.7修订完善版总表的原表行号 / provenance row in the revised source workbook"),
    ]
    wcsv(pd.DataFrame(meta_rows, columns=["Field", "Description"]),
         "data/CHNR_metadata.csv")

    # --- README / package documentation ---
    n_scr = scr["Verdict"].value_counts()
    readme = f"""# China Herpetofauna New Record dataset (CHNR) v0.1

中国两栖爬行动物省级新分布纪录数据集（草稿版 v0.1，{pd.Timestamp('2026-08-07').date()}）。
本包参照 CBNR（China Bird New Record dataset, Ding et al., Zenodo 10.5281/zenodo.20809949）
的事件定义、清洗流程与包结构，由《两栖爬行动物数据合并表-8.7修订完善版.xlsx》构建。

## 事件定义 / Event definition
分析单元为 物种×省级行政区 的首次文献记录（同 CBNR）。新种描述单列为伴随表；
非两爬类群、国外记录、属级记录、区系调查清单行、"其他/再发现"类记录均排除并留痕。

## 目录 / Folder overview
- dataset/
  - CHNR_provincial_new_records.csv  清洁省级新纪录事件表（{len(clean)} 行，{clean['Scientific_name_COL_China_2026'].nunique()} 种，{clean['New_distribution_province'].nunique()} 省级单元）
  - CHNR_new_species.csv             新种描述伴随表（{len(ns)} 种级条目）
  - CHNR_metadata.csv                字段词典
  - CHNR_v0.1.xlsx                   汇总工作簿（含按目/省汇总表）
- audit_quality_control/
  - 02_taxonomy_harmonisation/  分类匹配需复核行
  - 03_record_screening/        全部 {len(scr)} 源行的去留判定日志（事件表 {n_scr.get('事件表',0)}；新种表 {n_scr.get('新种表',0)}；排除 {n_scr.get('排除',0)}；排除-待人工判定 {n_scr.get('排除-待人工判定',0)}）
  - 04_coordinate_georeferencing/  坐标解析、省界一致性审计（{len(caudit)} 行不一致）与地名补全日志
  - 05_duplicate_review/        物种×省份去重日志（最早发表年规则；移除 {(~keep_mask).sum()} 行、{gid} 组）与新种表去重日志
- scripts/chnr_build.py         本包构建脚本（上游：match_species.py / parse_coords.py / assemble_output.py，
                                见 NEW DISTRIBUTION RECORDS/herp_table_revision/）

## 与 CBNR 的差异 / Deviations from CBNR
1. 分类主干仅用《中国生物物种名录》2026（脊索动物门）；未做 Frost ASW / Reptile Database 交叉，
   scientific_name_as_published 保留发表名以便后续对接。
2. 亚种级省级记录未删除，以 Reported_rank 标记（CBNR 为直接排除）。
3. 时间范围未截断（含 1978 等早期文献；CBNR 限 2000–2025）。
4. 保护状态四列为空占位，待接入中国脊椎动物红色名录、国家重点保护名录与特有性表。
5. 省级"首次性"未逐篇对照权威底本核验，暂以物种×省份最早发表年近似；
   待人工判定桶（{n_scr.get('排除-待人工判定',0)} 行：新种文献伴随物种 500、类型无线索 255）需人工过一遍。

## 已知局限 / Known caveats
- 名录未匹配的事件行（Scientific_name_COL_China_2026 为空）见 02 审计表，多为异名待考或名录未收录。
- 坐标以原文为准；文字地名地理编码行的精度见修订版"坐标备注"（<5 km 至县级不等）。
- 37 行坐标落点省份与标注省份不一致（04_2），需逐行核实。

数据许可建议 CC BY 4.0（与 CBNR 一致）。
"""
    (OUT / "docs" / "build_summary.md").write_text(readme, encoding="utf-8")

    # 统计 / report
    print(f"事件候选: {len(ev)}（多省拆分后）")
    print(f"清洁事件表: {len(clean)} 行；去重移除: {(~keep_mask).sum()}；重复组: {gid}")
    print(f"新种表: {len(ns)} 行（按种去重移除 {len(ns_dup_log)} 行）")
    print(f"筛选日志: {len(scr)} 行；判定分布:")
    print(scr["Verdict"].value_counts().to_string())
    print()
    print("排除原因 TOP:")
    print(scr[scr['Verdict'] == '排除']['Reason'].str.replace(r'（.*', '', regex=True)
          .value_counts().head(12).to_string())
    print()
    print(f"清洁表物种数(按名录名): {clean['Scientific_name_COL_China_2026'].nunique()}")
    print(f"覆盖省份: {clean['New_distribution_province'].nunique()}")
    print(f"坐标齐全事件: {clean['Longitude'].notna().sum()}")
    print(f"坐标审计(省份不一致): {len(caudit)}")


if __name__ == "__main__":
    main()
