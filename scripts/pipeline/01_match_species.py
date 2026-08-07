# ============================================================
# Scientific question / 科学问题:
# 两爬新纪录表中的物种如何与《中国生物物种名录》(2026, 脊索动物门)
# 建立可追溯、可复核的分类学对应关系？
# How can species in the herp new-record table be traceably
# matched to the Catalogue of Life China (2026, Chordata)?
#
# Objective / 分析目标:
# 多层级匹配：拉丁名精确 → 中文名精确(含名录别名) → 双名截取 →
# 无空格/粘连修复 → 中文亚种归并 → 人工核定异名表 → 种加词词干
# 推断(带目/科相容性校验) → 属级 → 中文名同长换字/增删一字模糊
# (带种加词一致性约束)。每行输出名录对应行、匹配方式与复核标记。
# Layered matching with order/family-compatibility guards.
#
# Input / 输入数据:
# - 动物界-脊索动物门-2026-10714.xlsx (名录 / catalogue)
# - 两栖爬行动物数据合并表-8.7最新版.xlsx 总表 (记录表 / records)
#
# Output / 预期输出:
# - match_result.pkl: 每行 (cat_idx, genus_idx, method, flags)
# - 终端打印匹配统计与复核样例 / stats and review samples printed
#
# Key assumptions / 关键假设:
# - 名录为分类地位与现行有效拉丁名的权威标准。
# - 记录表原 scientific_name 保留为发表时所用名，不改写。
# - 跨目的种加词碰撞一律拒绝（属转移不会跨目）。
# Main packages / 主要包: pandas, openpyxl
# ============================================================

import pickle
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # 仓库根目录 / repo root
CAT_PATH = str(ROOT / "source_data/动物界-脊索动物门-2026-10714.xlsx")
REC_PATH = str(ROOT / "source_data/两栖爬行动物数据合并表-8.7最新版.xlsx")
OUT_DIR = Path(__file__).parent / "intermediate"
OUT_DIR.mkdir(exist_ok=True)

HERP_CLASSES = ("两栖纲", "爬行纲")

# 人工核定的异名/处理对应表（仅收录证据充分者）
# Curated synonym map (only well-supported treatments), record-name -> catalogue Latin
CURATED = {
    "Polypedates leucomystax": ("Polypedates megacephalus", "中国大陆种群现多处理为斑腿泛树蛙，请复核"),
    "Rana kunyuensis": ("Rana coreana", "昆嵛林蛙现多处理为朝鲜林蛙的异名，请复核"),
    "Megophrys tuberogrannulus": ("Boulenophrys tuberogranulatus", "原名拼写含双写笔误"),
    "Sinovipera sichuanensis": ("Trimeresurus sichuanensis", "华蝮属已并入竹叶青蛇属"),
    "Altiphylax medogense": ("Cyrtodactylus/Cyrtopodion 组合", ""),  # 占位，下方以实名覆盖
}
CURATED["Altiphylax medogense"] = ("Cyrtopodion medogense", "墨脱高山蜥按名录归墨脱弯脚虎")
CURATED["Coluber spinalis"] = ("Orientocoluber spinalis", "黄脊游蛇现归 Orientocoluber")
CURATED["Paa yunnanensis"] = ("Gynandropaa yunnanensis", "双团棘胸蛙（旧名）现为云南棘蛙，请复核")
CURATED["Paas yunnanensis"] = ("Gynandropaa yunnanensis", "原表属名 Paas 为 Paa 之笔误；双团棘胸蛙现为云南棘蛙，请复核")
CURATED["Theloderma asperum"] = ("Theloderma albopunctatum", "中国的马来棱皮树蛙记录现多归白斑棱皮树蛙，请复核")
CURATED["Megophrys pachyproctus"] = ("Jingophrys pachyproctus", "粗肛角蟾现归靖角蟾属（凸肛靖角蟾），请复核")
CURATED["Megophrys shimentaina"] = ("Boulenophrys shimentaina", "石门台角蟾现归 Boulenophrys")

# 仅有中文名时的核定映射 / curated zh-only mappings
CURATED_ZH = {
    "方花丽斑蛇": ("Archelaphe bella", "方花丽斑蛇为方花蛇旧称"),
}

# 属级别名（原属整体更名）/ genus aliases for wholesale renames
GENUS_ALIAS = {"Leptolalax": "Paramegophrys"}

# 允许的跨科转移对（历史分类调整）/ allowed cross-family transfer pairs
FAMILY_PAIRS = {frozenset({"Ranidae", "Dicroglossidae"})}

# 已确立的属拆分/合并对：当记录的原属仍存在于名录时，仅允许这些属间的
# 种加词推断（防止"变色树蜥→变色沙蜥"式的假朋友）。
# Established genus split/merge pairs: cross-genus epithet inference out
# of an extant genus is only allowed within these pairs.
TRANSFER_PAIRS = {frozenset(p) for p in [
    ("Tylototriton", "Yaotriton"), ("Tylototriton", "Liangshantriton"),
    ("Japalura", "Diploderma"), ("Rhacophorus", "Zhangixalus"),
    ("Rhacophorus", "Polypedates"), ("Cynops", "Hypselotriton"),
    ("Pachytriton", "Paramesotriton"), ("Odorrana", "Bamburana"),
    ("Amolops", "Bamburana"), ("Philautus", "Raorchestes"),
    ("Enhydris", "Myrrophis"), ("Typhlops", "Indotyphlops"),
    ("Rana", "Odorrana"), ("Rana", "Pseudorana"), ("Rana", "Sylvirana"),
    ("Sylvirana", "Boulengerana"), ("Leptobrachium", "Vibrissaphora"),
    ("Bufo", "Torrentophryne"), ("Bufo", "Bufotes"),
    ("Bufo", "Duttaphrynus"), ("Bufo", "Strauchbufo"),
]}

# 明确不应做种级匹配的名称 / names explicitly blocked from species matching
CURATED_BLOCK = {
    "Seuratascaris schmackeri": "该名为蛙体内寄生线虫（Seuratascaris 属），并非两栖爬行动物记录本身，请核实该行来源",
}


def norm_text(s) -> Optional[str]:
    """全角转半角并压缩空白 / Normalize full-width chars, collapse spaces."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = unicodedata.normalize("NFKC", str(s)).strip()
    s = re.sub(r"\s+", " ", s)
    return s if s else None


def zh_variants(zh: str) -> List[str]:
    """拆分名录中文名的括号/斜杠别名 / Split parenthetical & slash aliases."""
    out = []
    base = re.sub(r"[（(].*?[)）]", "", zh).strip()
    for part in re.split(r"[/、]", base):
        if part.strip():
            out.append(part.strip())
    for m in re.findall(r"[（(](.*?)[)）]", zh):
        for part in re.split(r"[/、]", m):
            if part.strip():
                out.append(part.strip())
    return out or [zh]


def latin_binomial(name: str) -> Optional[str]:
    """取拉丁名前两词（去 subsp. 等）/ First two tokens of a Latin name."""
    toks = [t for t in name.split() if t.lower() not in ("subsp.", "subsp", "ssp.", "ssp")]
    if len(toks) >= 2 and re.match(r"^[A-Z][a-z-]+$", toks[0]) and re.match(r"^[a-z-]+$", toks[1]):
        return f"{toks[0]} {toks[1]}"
    return None


def epithet_stem(ep: str) -> str:
    """种加词词干化以吸收属转移的词尾性变化 / Stem epithet for gender endings."""
    ep = ep.lower()
    ep = re.sub(r"ii$", "i", ep)
    ep = re.sub(r"(us|a|um|is|e)$", "", ep)
    return ep


def is_subseq(a: str, b: str) -> bool:
    """a 是否为 b 的保序子序列 / Whether a is an ordered subsequence of b."""
    it = iter(b)
    return all(c in it for c in a)


class CatalogueIndex:
    """名录多路索引 / Multi-key index over the catalogue."""

    def __init__(self, cat: pd.DataFrame):
        self.cat = cat
        self.la: Dict[str, int] = {}
        self.zh: Dict[str, List[int]] = {}
        self.binom: Dict[str, List[int]] = {}
        self.nospace: Dict[str, List[int]] = {}
        self.genus: Dict[str, List[int]] = {}
        self.stem: Dict[str, List[int]] = {}          # 仅两爬 / herp only
        self.epithets: Dict[str, List[int]] = {}      # 仅两爬 / herp only
        self.genus_order: Dict[str, str] = {}
        self.family_order: Dict[str, str] = {}
        self.herp_zh: Dict[str, List[int]] = {}
        self.family_latin: Dict[str, str] = {}  # 科中文名→科拉丁名 / zh family -> Latin
        self.genus_zh: Dict[str, str] = {}      # 属拉丁名→属中文名 / genus -> zh genus
        for i, r in cat.iterrows():
            la, zh = norm_text(r["物种拉丁名"]), norm_text(r["物种中文名"])
            is_herp = r["纲中文名"] in HERP_CLASSES
            order = r["目中文名"]
            for col in ("属拉丁名", "科拉丁名", "科中文名"):
                v = norm_text(r[col])
                if v:
                    d = self.genus_order if col == "属拉丁名" else self.family_order
                    d.setdefault(v, order)
            fzh, fla = norm_text(r["科中文名"]), norm_text(r["科拉丁名"])
            if fzh and fla:
                self.family_latin.setdefault(fzh, fla)
            g0, gzh = norm_text(r["属拉丁名"]), norm_text(r["属中文名"])
            if g0 and gzh:
                self.genus_zh.setdefault(g0, gzh)
            if la:
                self.la.setdefault(la, i)
                b = latin_binomial(la) or la
                if " " in b:
                    self.binom.setdefault(b, []).append(i)
                    self.nospace.setdefault(b.replace(" ", "").lower(), []).append(i)
                    ep = b.split()[1]
                    if is_herp:
                        self.stem.setdefault(epithet_stem(ep), []).append(i)
                        if len(ep) >= 6:
                            self.epithets.setdefault(ep.lower(), []).append(i)
            if zh:
                for v in zh_variants(zh):
                    self.zh.setdefault(v, []).append(i)
                    if is_herp:
                        self.herp_zh.setdefault(v, []).append(i)
            g = norm_text(r["属拉丁名"])
            if g:
                self.genus.setdefault(g, []).append(i)

    def pick_herp_first(self, idxs: List[int]) -> int:
        """同名冲突时优先两爬 / Prefer herp classes on homonym collisions."""
        for i in idxs:
            if self.cat.loc[i, "纲中文名"] in HERP_CLASSES:
                return i
        return idxs[0]

    def record_order(self, rec_row) -> Optional[str]:
        """由记录行自带的属/科推断目 / Infer order from the record's own genus/family."""
        la = norm_text(rec_row.get("scientific_name"))
        if la:
            g = la.split()[0]
            if g in self.genus_order:
                return self.genus_order[g]
        for col in ("genus_en", "family_en", "family_zh"):
            v = norm_text(rec_row.get(col))
            if v:
                v = re.sub(r"^Genus\s+", "", v)
                if v in self.genus_order:
                    return self.genus_order[v]
                if v in self.family_order:
                    return self.family_order[v]
        return None

    def record_family(self, rec_row) -> Optional[str]:
        """记录行自带科名（规范为名录科拉丁名）/ Record's own family as Latin."""
        v = norm_text(rec_row.get("family_en"))
        if v and v in self.family_order:
            return v
        v = norm_text(rec_row.get("family_zh"))
        if v and v in self.family_latin:
            return self.family_latin[v]
        return None


def stems_agree(la: Optional[str], cat_la: str) -> bool:
    """记录拉丁名与候选名录名的种加词词干是否一致 / Epithet stems agree?"""
    if not la:
        return True  # 无拉丁名时不构成否决 / no veto without a Latin name
    b = latin_binomial(la)
    if not b:
        return True  # 无法解析视为不否决 / unparseable does not veto
    return epithet_stem(b.split()[1]) == epithet_stem(cat_la.split()[1])


def match_row(rec_row, idx: CatalogueIndex) -> Tuple[Optional[int], Optional[int], str, List[str]]:
    """返回 (species_hit, genus_level_hit, method, flags) / Match one record row."""
    zh, la = norm_text(rec_row.get("species_zh")), norm_text(rec_row.get("scientific_name"))
    if zh:
        zh = re.sub(r"[（(].*?[)）]", "", zh).strip() or zh
    flags: List[str] = []
    la_hit = idx.la.get(la) if la else None
    zh_hit = idx.pick_herp_first(idx.zh[zh]) if zh and zh in idx.zh else None

    # 1/2. 精确命中 / exact hits (Latin preferred; disagreement flagged)
    if la_hit is not None and zh_hit is not None and la_hit != zh_hit:
        flags.append("中文名与拉丁名在名录中指向不同物种，请复核")
    if la_hit is not None:
        return la_hit, None, "拉丁名精确", flags
    if zh_hit is not None:
        return zh_hit, None, "中文名精确", flags

    rec_order = idx.record_order(rec_row)

    # 3. 双名截取（三名法亚种归并）/ binomial from trinomial
    if la:
        b = latin_binomial(la)
        if b and b != la and b in idx.binom:
            flags.append("按三名法亚种归并至种")
            return idx.pick_herp_first(idx.binom[b]), None, "亚种归并至种", flags
        # 4a. 无空格修复 / fused full-name repair (e.g. Ranalatouchii = Rana latouchii)
        key = re.sub(r"[^a-z]", "", la.lower())
        if key in idx.nospace:
            return idx.pick_herp_first(idx.nospace[key]), None, "拉丁名空格修复", flags
        # 4b. 粘连旧属名+种加词的后缀修复 / fused old-genus + epithet suffix repair
        if re.match(r"^[A-Za-z]+$", la):
            cands = []
            for ep, idxs in idx.epithets.items():
                if la.lower().endswith(ep) and len(la) > len(ep):
                    cands.extend(idxs)
            cands = sorted(set(cands))
            if len(cands) == 1:
                flags.append("拉丁名疑为旧属名与种加词粘连，按种加词修复，请复核")
                return cands[0], None, "拉丁名粘连修复", flags

    # 5. 中文亚种后缀归并 / strip Chinese subspecies suffix
    if zh and zh.endswith("亚种"):
        for cut in (4, 3, 2):
            base = zh[:-cut]
            if len(base) >= 2 and base in idx.zh:
                flags.append(f"按亚种归并至“{base}”")
                return idx.pick_herp_first(idx.zh[base]), None, "中文亚种归并", flags

    # 6. 人工核定异名表 / curated synonym maps (Latin- and zh-keyed)
    if la:
        b = latin_binomial(la) or la
        if b in CURATED:
            tgt, note = CURATED[b]
            if tgt in idx.la:
                if note:
                    flags.append(note)
                return idx.la[tgt], None, "核定异名", flags
    if zh and zh in CURATED_ZH:
        tgt, note = CURATED_ZH[zh]
        if tgt in idx.la:
            if note:
                flags.append(note)
            return idx.la[tgt], None, "核定异名", flags

    # 7. 种加词词干推断（属转移异名），带目/科相容性与原属存在性护栏
    #    epithet-stem inference with order/family guards and a
    #    corroboration requirement when the original genus still
    #    exists in the catalogue (transfers out of extant genera
    #    need independent zh evidence, else demoted to suggestion).
    if la:
        b = latin_binomial(la) or (la if len(la.split()) == 2 else None)
        if b and " " in b and b in CURATED_BLOCK:
            flags.append(CURATED_BLOCK[b])
            return None, None, "未匹配-疑非目标类群", flags
        if b and " " in b:
            rec_genus = b.split()[0]
            rec_family = idx.record_family(rec_row)
            st = epithet_stem(b.split()[1])
            cands = sorted(set(idx.stem.get(st, [])))
            if rec_order:
                cands = [c for c in cands
                         if idx.cat.loc[c, "目中文名"] == rec_order]
                minlen = 3
            else:
                minlen = 5
            if rec_family:  # 科级相容 / family compatibility
                cands = [c for c in cands
                         if idx.cat.loc[c, "科拉丁名"] == rec_family
                         or frozenset({idx.cat.loc[c, "科拉丁名"], rec_family}) in FAMILY_PAIRS]
            if len(st) >= minlen and len(cands) == 1:
                hit = cands[0]
                cand_genus = idx.cat.loc[hit, "属拉丁名"]
                if (rec_genus in idx.genus and cand_genus != rec_genus
                        and frozenset({rec_genus, cand_genus}) not in TRANSFER_PAIRS):
                    # 原属仍在名录且非已确立的转移对：降级为建议
                    # extant genus + unestablished pair: demote to suggestion
                    cand_zh = norm_text(idx.cat.loc[hit, "物种中文名"]) or ""
                    flags.append(f"名录中存在种加词相同的“{cand_zh} {idx.cat.loc[hit, '物种拉丁名']}”，"
                                 f"但原属{rec_genus}仍在名录、两属非已知拆分对，请人工确认")
                    hit = None  # 继续按属级填分类 / fall through to genus-level fill
                if hit is not None:
                    flags.append("按种加词推断为名录中该名的异名对应种，请复核")
                    return hit, None, "种加词推断", flags

    # 8. 属级记录 / genus-level records ("Xenophrys sp.", bare genus,
    #    or demoted synonym suggestions keeping a safe genus-level fill)
    if la:
        g = re.sub(r"\s+(sp|spp|cf|aff)\.?.*$", "", la).strip()
        had_epithet = " " in g
        g = g.split()[0] if had_epithet else g
        g = GENUS_ALIAS.get(g, g)
        if re.match(r"^[A-Z][a-z-]+$", g) and g in idx.genus:
            method = "种未收录-按属填分类" if had_epithet else "属级"
            return None, idx.genus[g][0], method, flags

    # 9. 中文名模糊：同长换一字 或 增删一字（子序列），需种加词不矛盾
    #    zh fuzzy: 1-char substitution at equal length, or 1-char indel
    if zh and len(zh) >= 3:
        cands = []
        for name, idxs in idx.herp_zh.items():
            ok = (len(name) == len(zh) and len(zh) >= 4
                  and sum(a != b for a, b in zip(name, zh)) == 1)
            if not ok and abs(len(name) - len(zh)) == 1:
                short, long_ = sorted((name, zh), key=len)
                ok = is_subseq(short, long_)
            if ok:
                i = idx.pick_herp_first(idxs)
                if not stems_agree(la, idx.cat.loc[i, "物种拉丁名"]):
                    continue
                # 与词干层相同的原属存在性护栏 / same extant-genus guard
                b0 = latin_binomial(la) if la else None
                if b0:
                    rg, cg = b0.split()[0], idx.cat.loc[i, "属拉丁名"]
                    if (rg in idx.genus and cg != rg
                            and frozenset({rg, cg}) not in TRANSFER_PAIRS):
                        continue
                cands.append((name, i))
        uniq = sorted(set(i for _, i in cands))
        if len(uniq) == 1:
            flags.append(f"中文名疑有出入，按名录“{cands[0][0]}”匹配，请复核")
            return uniq[0], None, "中文名模糊", flags

    return None, None, "未匹配", flags


def main() -> None:
    cat = pd.read_excel(CAT_PATH)
    rec = pd.read_excel(REC_PATH, sheet_name="总表", dtype=str)
    idx = CatalogueIndex(cat)

    results = []
    for _, r in rec.iterrows():
        sp_hit, g_hit, method, flags = match_row(r, idx)
        if method == "未匹配":
            zh = norm_text(r["species_zh"]) or ""
            rt = norm_text(r["record_type_zh"]) or ""
            if "新种" in rt or "新物种" in rt:
                method = "未匹配-新种未收录"
            elif zh.startswith("新种") or "新种" in zh:
                method = "未匹配-疑非目标类群"
        results.append({"cat_idx": sp_hit, "genus_idx": g_hit, "method": method, "flags": flags})

    with open(OUT_DIR / "match_result.pkl", "wb") as f:
        pickle.dump(results, f)

    stat = pd.Series([r["method"] for r in results]).value_counts()
    print("=== 匹配方式统计 ===")
    print(stat.to_string())
    print(f"\n带复核标记的行: {sum(1 for r in results if r['flags'])}")

    print("\n=== 推断/修复类匹配全样 (需复核) ===")
    for i, r in enumerate(results):
        if r["method"] in ("种加词推断", "中文名模糊", "拉丁名空格修复", "拉丁名粘连修复", "核定异名"):
            row = rec.iloc[i]
            hit = cat.loc[r["cat_idx"]]
            print(f"  行{i+2}: {row['species_zh']!r}/{row['scientific_name']!r}"
                  f" -> {hit['物种中文名']} {hit['物种拉丁名']} [{r['method']}]")

    print("\n=== 仍未匹配 (全部) ===")
    for i, r in enumerate(results):
        if r["method"].startswith("未匹配"):
            row = rec.iloc[i]
            print(f"  行{i+2} [{r['method']}]: zh={row['species_zh']!r} la={row['scientific_name']!r}")


if __name__ == "__main__":
    main()
