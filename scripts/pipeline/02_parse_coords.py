# ============================================================
# Scientific question / 科学问题:
# 两爬新纪录表的经纬度字段能否统一为可分析的十进制度，
# 并识别出格式、半球、经纬互换与省界不一致等问题？
# Can lat/long fields be unified into decimal degrees with
# format, hemisphere, swap, and province-consistency checks?
#
# Objective / 分析目标:
# 解析 十进制°N / 度分 / 度分秒 / 全角字符 / 负值 / 范围 等格式，
# 输出每行 lat_dd, lon_dd 与问题标签清单。
# Parse all coordinate formats; emit decimal degrees + issue tags.
#
# Input / 输入数据: 两栖爬行动物数据合并表-8.7最新版.xlsx 总表
# Output / 预期输出: coords.pkl（逐行解析结果）+ 终端异常报告
# Key assumptions / 关键假设:
# - 负值+N/E 表示南/西半球（国外记录），按数值取负。
# - 范围值取中点并标记。
# - 省界框为近似外包框（±0.5°缓冲），仅用于粗筛。
# Main packages / 主要包: pandas
# ============================================================

import pickle
import re
import unicodedata
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # 仓库根目录 / repo root
REC_PATH = str(ROOT / "source_data/两栖爬行动物数据合并表-8.7最新版.xlsx")
OUT_DIR = Path(__file__).parent / "intermediate"
OUT_DIR.mkdir(exist_ok=True)

# 中国省级行政区近似外包框 / rough province bounding boxes
# (lon_min, lon_max, lat_min, lat_max)
PROV_BBOX = {
    "北京": (115.4, 117.5, 39.4, 41.1), "天津": (116.7, 118.1, 38.5, 40.3),
    "河北": (113.4, 119.9, 36.0, 42.7), "山西": (110.2, 114.6, 34.5, 40.8),
    "内蒙古": (97.1, 126.1, 37.4, 53.4), "辽宁": (118.8, 125.8, 38.7, 43.5),
    "吉林": (121.6, 131.3, 40.8, 46.3), "黑龙江": (121.1, 135.1, 43.4, 53.6),
    "上海": (120.8, 122.2, 30.6, 31.9), "江苏": (116.3, 121.9, 30.7, 35.3),
    "浙江": (118.0, 123.0, 27.0, 31.2), "安徽": (114.8, 119.7, 29.4, 34.7),
    "福建": (115.8, 120.7, 23.5, 28.4), "江西": (113.5, 118.5, 24.4, 30.1),
    "山东": (114.7, 122.8, 34.3, 38.5), "河南": (110.3, 116.7, 31.3, 36.4),
    "湖北": (108.3, 116.2, 29.0, 33.3), "湖南": (108.7, 114.3, 24.6, 30.2),
    "广东": (109.6, 117.4, 20.1, 25.6), "广西": (104.4, 112.1, 20.8, 26.4),
    "海南": (108.6, 111.1, 18.1, 20.2), "重庆": (105.2, 110.2, 28.1, 32.3),
    "四川": (97.3, 108.6, 26.0, 34.4), "贵州": (103.6, 109.6, 24.6, 29.3),
    "云南": (97.5, 106.2, 21.1, 29.3), "西藏": (78.3, 99.2, 26.8, 36.5),
    "陕西": (105.4, 111.3, 31.7, 39.6), "甘肃": (92.3, 108.8, 32.5, 42.8),
    "青海": (89.3, 103.1, 31.6, 39.3), "宁夏": (104.2, 107.7, 35.2, 39.4),
    "新疆": (73.4, 96.4, 34.3, 49.2), "台湾": (119.3, 122.2, 21.7, 25.7),
    "香港": (113.8, 114.5, 22.1, 22.6), "澳门": (113.5, 113.7, 22.0, 22.3),
}
BUF = 0.5   # 省界缓冲 / province buffer in degrees
CN = (73.0, 135.5, 3.0, 53.9)  # 中国粗略范围（含南海诸岛）/ rough China bbox

COORD_PAT = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*[°度]\s*"
    r"(?:(\d+(?:\.\d+)?)\s*[′'’分]\s*)?"
    r"(?:(\d+(?:\.\d+)?)\s*[″\"”秒]\s*)?"
    r"([NSEWnsew])?")


def parse_one(raw, is_lat: bool) -> Tuple[Optional[float], List[str]]:
    """解析单个坐标字符串为十进制度 / Parse one coordinate string."""
    issues: List[str] = []
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None, issues
    s = unicodedata.normalize("NFKC", str(raw)).strip()
    if not s:
        return None, issues
    vals = []
    for m in COORD_PAT.finditer(s):
        deg = float(m.group(1))
        minu = float(m.group(2)) if m.group(2) else 0.0
        sec = float(m.group(3)) if m.group(3) else 0.0
        hemi = (m.group(4) or "").upper()
        sign = -1.0 if deg < 0 else 1.0
        v = abs(deg) + minu / 60 + sec / 3600
        v *= sign
        if hemi in ("S", "W"):
            v = -abs(v)
        vals.append(v)
    if not vals:
        # 纯数字（无度符）/ bare number fallback
        try:
            vals = [float(s)]
        except ValueError:
            issues.append(f"坐标无法解析: {s!r}")
            return None, issues
    v = vals[0]
    if len(vals) > 1:
        v = sum(vals) / len(vals)
        issues.append("坐标为范围值，已取中点")
    lim = 90 if is_lat else 180
    if abs(v) > lim:
        issues.append(f"{'纬度' if is_lat else '经度'}超出±{lim}°: {v:g}")
    return v, issues


def province_keys(prov) -> List[str]:
    """省份字段拆分并映射到已知省名 / Split & map province field."""
    if prov is None or (isinstance(prov, float) and pd.isna(prov)):
        return []
    s = unicodedata.normalize("NFKC", str(prov))
    out = []
    for part in re.split(r"[、,/和及]", s):
        part = part.strip()
        for name in PROV_BBOX:
            if part.startswith(name):
                out.append(name)
                break
    return out


def main() -> None:
    rec = pd.read_excel(REC_PATH, sheet_name="总表", dtype=str)
    results = []
    n_issue = 0
    for i, r in rec.iterrows():
        lat, iss1 = parse_one(r["latitude"], True)
        lon, iss2 = parse_one(r["longitude"], False)
        issues = iss1 + iss2
        swapped = False
        # 经纬互换检测：纬度超限而互换后两者均合理 / swap detection
        if lat is not None and lon is not None:
            if abs(lat) > 90 and abs(lon) <= 90 and abs(lat) <= 180:
                lat, lon = lon, lat
                swapped = True
                issues.append("纬度值超±90°且与经度互换后合理，十进制列已互换（原文未改）")
        in_china = None
        if lat is not None and lon is not None:
            in_china = (CN[0] <= lon <= CN[1]) and (CN[2] <= lat <= CN[3])
            if not in_china:
                issues.append("坐标位于中国范围之外（可能为国外记录）")
            else:
                provs = province_keys(r["province_zh"])
                if provs:
                    ok = any(
                        (b[0] - BUF <= lon <= b[1] + BUF) and (b[2] - BUF <= lat <= b[3] + BUF)
                        for b in (PROV_BBOX[p] for p in provs))
                    if not ok:
                        issues.append(f"坐标落在省份({ '、'.join(provs) })近似范围外，请核查")
        results.append({"lat_dd": lat, "lon_dd": lon, "issues": issues,
                        "swapped": swapped, "in_china": in_china})
        if issues:
            n_issue += 1
    with open(OUT_DIR / "coords.pkl", "wb") as f:
        pickle.dump(results, f)

    print(f"总行 {len(rec)}，坐标存在问题/标注的行: {n_issue}")
    print(f"解析出十进制坐标的行: {sum(1 for x in results if x['lat_dd'] is not None and x['lon_dd'] is not None)}")
    print(f"位于中国境外: {sum(1 for x in results if x['in_china'] is False)}")
    print()
    from collections import Counter
    cnt = Counter()
    for x in results:
        for t in x["issues"]:
            cnt[re.sub(r"[:：].*$", "", t)] += 1
    for k, v in cnt.most_common():
        print(f"  {v:4d}x {k}")
    print()
    print("=== 省界不符明细 ===")
    for i, x in enumerate(results):
        for t in x["issues"]:
            if "省份" in t:
                r = rec.iloc[i]
                print(f"  行{i+2}: {r['species_zh']} lat={x['lat_dd']:.3f} lon={x['lon_dd']:.3f} "
                      f"省={r['province_zh']} 地名={str(r['locality_zh'])[:30]}")
    print("=== 互换/超限明细 ===")
    for i, x in enumerate(results):
        for t in x["issues"]:
            if "互换" in t or "超出" in t or "无法解析" in t:
                r = rec.iloc[i]
                print(f"  行{i+2}: lat原文={r['latitude']!r} lon原文={r['longitude']!r} -> {t}")
                break


if __name__ == "__main__":
    main()
