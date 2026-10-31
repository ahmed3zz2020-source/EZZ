# -*- coding: utf-8 -*-
"""
🧠 طبقة الفهم الاستثماري المستقلة (عز).

⛔ القاعدة الذهبية: النتيجة النهائية لـOCTA **مدخل** عندنا — مش قرار.
   ⭐ إحنا بنحسب العوامل الستة بأنفسنا من الحقول الخام + المقارنة القطاعية،
     وبنكتشف التعارضات، وبنقارن اجتهادنا بنتيجة OCTA ونوثّق الفرق.
   ⭐ لو نتيجة OCTA عكست اجتهادنا ⇒ بنقول صراحةً ومين صحّ.

🧭 العوامل الستة (أوزانها في config.FACTOR_WEIGHTS):
   momentum · quality · value · liquidity · risk · catalyst
"""
from config import FACTOR_WEIGHTS, GATES


# ⭐ أوزان محرّك OCTA (٦ محاور — portfolio مستبعد بوزن صفر).
# 📌 نستخدمها بس نماشي النتيجة الأصلية بعدد — مش بنلعب فيها.
OCTA_AXIS_WEIGHTS = {"technical": 0.20, "fundamental": 0.24, "liquidity": 0.20,
                      "news": 0.05, "sentiment": 0.04, "risk": 0.27}


def octa_base_score(all_axes):
    """🅰️ نتيجة OCTA الأساسية (قبل خصم المخاطرة) — للمقارنة فقط."""
    if not all_axes:
        return None
    tot = wsum = 0.0
    for ax, w in OCTA_AXIS_WEIGHTS.items():
        v = num(all_axes.get(ax))
        if v is not None:
            tot += v * w
            wsum += w
    return round(tot / wsum, 1) if wsum else None


def num(v):
    """🔢 رقم نظيف أو None (NaN/فارغ ⇒ None مش صفر)."""
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def scale(x, lo, hi):
    """📐 تحويل خطي من lo..hi ⇒ 0..100."""
    if x is None or hi == lo:
        return None
    return max(0.0, min(100.0, 100.0 * (x - lo) / (hi - lo)))


def _mean(parts):
    parts = [p for p in parts if p is not None]
    if not parts:
        return None, 0
    return sum(parts) / len(parts), len(parts)


# ────────────────────── الدمج مع المصدر الطازج ──────────────────────
# ⭐ خريطة الأسماء: الطبقة الطازجة (egx_full) بتستخدم أسماء مختصرة.
FRESH_MAP = {
    "pe": "pe", "pb": "pb", "roe": "roe", "beta": "beta",
    "div_yield": "s_dy", "gross_margin": "s_gm", "roa": "s_roa",
    "mkt_cap": "mc", "cagr3y": "cagr3y", "from_52hi": "frm52hi",
    "max_dd": "mdd", "max_dd_1y": "mdd1y", "high_52": "h52", "low_52": "l52",
    "ma50_fresh": "s_ma50", "ma200_fresh": "s_ma200", "float_shares": "s_flt",
}


def merge_fresh(universe, fresh):
    """🔗 ادمج الطبقة الطازجة في الكون: يملأ الناقص ويضيف حقول جديدة.
    ⛔ ما بيكتبش ولا بيمسحش قيمة موجودة — بيملاّ الناقص بس."""
    if not fresh:
        return universe, {"filled": {}, "added": {}}
    stats = {"filled": {}, "added": {}}
    for s in universe:
        c = s.get("code")
        f = fresh.get(c) if isinstance(fresh, dict) else None
        if not f:
            continue
        for dst, src in FRESH_MAP.items():
            v = f.get(src)
            if v in (None, "", 0) and src not in ("cagr3y",):
                continue
            if dst not in s or s.get(dst) in (None, ""):
                s[dst] = v
                stats["filled"].setdefault(dst, 0)
                stats["filled"][dst] += 1
    return universe, stats


def sector_medians(universe):
    """🏭 متوسطات القطاع من الكون المدمج (P/E · P/B) — أدق من متوسط عام."""
    out = {}
    for s in universe:
        sec = s.get("sector")
        if not sec:
            continue
        d = out.setdefault(sec, {"pe": [], "pb": [], "count": 0})
        d["count"] += 1
        for k in ("pe", "pb"):
            v = num(s.get(k))
            if v and v > 0:
                d[k].append(v)
    for sec, d in out.items():
        for k in ("pe", "pb"):
            vals = sorted(d[k])
            if vals:
                n = len(vals)
                d["median_" + k] = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
    return out


# ─────────────────────────── العوامل ───────────────────────────
def momentum(s):
    """📈 زخم مستقل: أداء متعدد الفترات + موقع السعر من المتوسطات + RSI."""
    parts, notes, detail = [], [], {}
    p1, p3, p6, py = (num(s.get(k)) for k in ("perf_1m", "perf_3m", "perf_6m", "perf_y"))
    if None not in (p1, p3, p6):
        raw = (0.32 * scale(p1, -15, 15) + 0.26 * scale(p3, -20, 25)
               + 0.24 * scale(p6, -20, 35) + 0.18 * scale(py or 0, -30, 60))
        parts.append(raw)
        detail["perf"] = {"1m": p1, "3m": p3, "6m": p6, "y": py}
    else:
        notes.append("أداء تاريخي ناقص")

    price = num(s.get("price"))
    emas = {k: num(s.get(k)) for k in ("ema20", "ema50", "ema200")}
    above = [1 for v in emas.values() if v and price and price > v]
    if above and price:
        parts.append(100.0 * len(above) / len(above))
        detail["above_emas"] = "%d/3" % len(above)

    f52 = num(s.get("from_52hi"))
    if f52 is not None:
        # ⭐ المسافة من القمة السنوية: قريب من القمة = زخم، بعيد = تعافي
        parts.append(scale(f52, -45, -2))
        detail["from_52hi"] = f52
    rsi = num(s.get("rsi"))
    if rsi is not None:
        if rsi < 30:
            v = 25.0
        elif rsi < 45:
            v = 45.0
        elif rsi <= 65:
            v = 85.0
        elif rsi <= 75:
            v = 62.0
        else:
            v = 32.0
        parts.append(v)
        detail["rsi"] = rsi

    v, n = _mean(parts)
    if v is None:
        return None, notes + ["مفيش بيانات زخم"], detail
    return v, notes, detail


def quality(s):
    """🛡️ جودة مالية مستقلة: ROE · هامش صافي · مديونية · التوزيعات."""
    parts, notes, detail = [], [], {}
    roe = num(s.get("roe"))
    if roe is not None:
        parts.append(scale(roe, 0, 35))
        detail["roe"] = roe
    else:
        notes.append("ROE غير متاح")
    nm = num(s.get("net_margin"))
    if nm is not None:
        parts.append(scale(nm, -5, 30))
        detail["net_margin"] = nm
    else:
        notes.append("هامش صافي غير متاح")
    de = num(s.get("de_ratio"))
    if de is not None:
        sec = s.get("sector") or ""
        soft = sec in ("بنوك", "خدمات مالية", "مقاولات", "عقارات")
        parts.append(scale(de, 120 if soft else 80, 0.4 if soft else 0.6))
        detail["de_ratio"] = de
    dy = num(s.get("div_yield"))
    if dy is not None:
        parts.append(scale(dy, 0, 8))
        detail["div_yield"] = dy
    roa = num(s.get("roa"))
    if roa is not None:
        parts.append(scale(roa, 0, 25))
        detail["roa"] = roa
    gm = num(s.get("gross_margin"))
    if gm is not None:
        parts.append(scale(gm, 2, 55))
        detail["gross_margin"] = gm
    v, n = _mean(parts)
    if v is None:
        return None, notes + ["مفيش بيانات جودة"], detail
    return v, notes, detail


def value(s, sector):
    """💎 قيمة نسبية: P/E و P/B مقارنةً بمتوسط القطاع."""
    parts, notes, detail = [], [], {}
    med = sector or {}
    pe, pb = num(s.get("pe")), num(s.get("pb"))
    mpe = num(med.get("median_pe") or med.get("median_p_e"))
    mpb = num(med.get("median_pb"))
    if pe and pe > 0 and mpe and mpe > 0:
        parts.append(scale(mpe / pe, 0.55, 2.0))
        detail["pe_vs_sector"] = round(mpe / pe, 2)
    elif pe and pe > 0:
        parts.append(scale(pe, 40, 6))
        detail["pe_abs"] = pe
        notes.append("مفيش متوسط P/E للقطاع")
    if pb and pb > 0 and mpb and mpb > 0:
        parts.append(scale(mpb / pb, 0.6, 2.2))
        detail["pb_vs_sector"] = round(mpb / pb, 2)
    elif pb and pb > 0:
        parts.append(scale(pb, 6, 0.5))
        detail["pb_abs"] = pb
    v, n = _mean(parts)
    if v is None:
        return None, notes + ["مفيش بيانات تقييم"], detail
    return v, notes, detail


def liquidity(s):
    """💧 سيولة مستقلة: حجم السوق + الحجم النسبي."""
    parts, notes, detail = [], [], {}
    cap = num(s.get("mkt_cap"))
    if cap and cap > 0:
        import math
        # ⭐ لوغاريتمي: ١٠٠ مليون ⇒ ٠ · ١٠ مليار ⇒ ٥٠ · ١٠٠ مليار ⇒ ٧٥
        lg = math.log10(cap)
        parts.append(max(0.0, min(100.0, (lg - 8.0) / 3.0 * 100.0)))
        detail["mkt_cap"] = cap
    else:
        notes.append("القيمة السوقية غير متاحة")
    rv = num(s.get("rel_volume"))
    if rv is not None:
        parts.append(scale(rv, 0.3, 3.0))
        detail["rel_volume"] = rv
    else:
        notes.append("الحجم النسبي غير متاح")
    v, n = _mean(parts)
    if v is None:
        return None, notes + ["مفيş بيانات سيولة"], detail
    return v, notes, detail


def risk(s):
    """🛡️ مخاطرة مستقلة: بيتا + مدى ATR + مستوى المخاطرة المعلن."""
    parts, notes, detail = [], [], {}
    beta = num(s.get("beta"))
    if beta is not None:
        parts.append(scale(beta, 1.8, 0.3))
        detail["beta"] = beta
    price = num(s.get("price"))
    atr = num(s.get("atr"))
    if price and atr:
        parts.append(scale(atr / price * 100, 4.5, 1.0))
        detail["atr_pct"] = round(atr / price * 100, 2)
    lvl = s.get("risk_level")
    if lvl:
        mp = {"منخفض": 90, "متوسط": 62, "مرتفع": 35, "مرتفع جداً": 15, "غير متاح": 50}
        parts.append(mp.get(lvl, 50))
        detail["risk_level"] = lvl
    else:
        notes.append("مفيش مستوى مخاطرة")
    mdd1 = num(s.get("max_dd_1y"))
    if mdd1 is not None:
        # ⭐ أقصى هبوط في سنة ⇒ مخاطرة حقيقية (مش مخاطرة نظرية)
        parts.append(scale(mdd1, 90, 12))
        detail["max_dd_1y"] = mdd1
    v, n = _mean(parts)
    if v is None:
        return None, notes + ["مفيش بيانات مخاطرة"], detail
    return v, notes, detail


def catalyst(s, divs_by_code):
    """⚡ محفّز: عائد التوزيعات + أحداث مسجّلة."""
    parts, notes, detail = [], [], {}
    dy = num(s.get("div_yield"))
    if dy is not None:
        parts.append(scale(dy, 0, 9))
        detail["div_yield"] = dy
    ev = divs_by_code.get(s.get("code")) or []
    if ev:
        parts.append(75.0)
        detail["events"] = len(ev)
    else:
        notes.append("مفيش أحداث مسجّلة")
    v, n = _mean(parts)
    if v is None:
        return None, notes, detail
    return v, notes, detail


def growth(s):
    """🌱 نمو مستقل: مركّب Earnings ٣ سنوات (CAGR) + قوة النمو السنوي."""
    cagr = num(s.get("cagr3y"))
    if cagr is None:
        return None, ["مفيش CAGR"], {}
    # ⭐ CAGR سالب = свинц ⇒ صفر. ٠–٢٠ = ضعيف · ٢٠–٥٠ = كويس · فوق ٥٠ = ممتاز
    v = scale(cagr, -10, 60)
    return v, [], {"cagr3y": cagr}


# ─────────────────────── التقييم والإشارات ───────────────────────
def evaluate(universe, sector_stats=None, divs=None):
    """🧮 تقييم كل سهم بالعوامل الستة + تغطية البيانات."""
    sec = sector_stats or {}
    divs_by = {}
    for d in (divs or []):
        c = d.get("code")
        if c:
            divs_by.setdefault(c, []).append(d)

    rows = []
    for s in universe:
        code = s.get("code")
        if not code or not num(s.get("price")):
            continue
        f_mom, n1, d1 = momentum(s)
        f_qual, n2, d2 = quality(s)
        f_val, n3, d3 = value(s, sec.get(s.get("sector")))
        f_liq, n4, d4 = liquidity(s)
        f_risk, n5, d5 = risk(s)
        f_cat, n6, d6 = catalyst(s, divs_by)
        f_gro, n7, d7 = growth(s)

        factors = {"momentum": f_mom, "quality": f_qual, "value": f_val,
                   "liquidity": f_liq, "risk": f_risk, "catalyst": f_cat,
                   "growth": f_gro}
        got = {k: v for k, v in factors.items() if v is not None}
        weights = {k: FACTOR_WEIGHTS[k] for k in got}
        tw = sum(weights.values())
        my = sum(factors[k] * weights[k] for k in got) / tw if tw else None

        notes = list(n1) + list(n2) + list(n3) + list(n4) + list(n5) + list(n6) + list(n7)
        coverage = len(got) / float(len(FACTOR_WEIGHTS))
        rows.append({
            "code": code, "name": s.get("name"), "sector": s.get("sector"),
            "price": num(s.get("price")),
            "my_score": round(my, 1) if my is not None else None,
            "factors": {k: (round(v, 1) if v is not None else None) for k, v in factors.items()},
            "detail": {"momentum": d1, "quality": d2, "value": d3,
                       "liquidity": d4, "risk": d5, "catalyst": d6, "growth": d7},
            "coverage": round(coverage, 2),
            "missing": [k for k, v in factors.items() if v is None],
            "octa_axes": s.get("all_axes") or {},
            "octa_score": octa_base_score(s.get("all_axes")),
            "data_grade": s.get("data_grade"), "risk_level": s.get("risk_level"),
            "stage": s.get("opportunity_stage"), "rsi": num(s.get("rsi")),
            "perf_1m": num(s.get("perf_1m")), "perf_y": num(s.get("perf_y")),
            "notes": notes,
        })
    return rows


def detect_conflicts(row):
    """⚔️ إشارات متعارضة — اللي بتفرّق بين «موجّه» و«مرشّح عادي»."""
    f = row.get("factors") or {}
    out = []
    mom, qual, val, liq, rsk = (f.get(k) for k in ("momentum", "quality", "value", "liquidity", "risk"))
    if mom is not None and qual is not None and mom >= 65 and qual <= 45:
        out.append("زخم قوي لكن الجودة ضعيفة")
    if mom is not None and qual is not None and mom <= 40 and qual >= 65:
        out.append("جودة عالية لكن الزخم ميت")
    if val is not None and mom is not None and val >= 70 and mom <= 45:
        out.append("رخيص بس مفيش محفّز (value trap محتمل)")
    if liq is not None and liq < 40:
        out.append("سيولة ضعيفة")
    if rsk is not None and rsk <= 35:
        out.append("مخاطرة عالية")
    if row.get("rsi") is not None and row["rsi"] >= 75:
        out.append("RSI فوق ٧٥ — تشبّع")
    if row.get("perf_1m") is not None and row["perf_1m"] <= -12:
        out.append("هبوط قوي خلال شهر")
    if row.get("coverage", 1) < 0.55:
        out.append("تغطية بيانات ضعيفة")
    return out


def divergence(row):
    """⚖️ الفرق بين اجتهادنا ونتيجة OCTA (المدخل مش الحكم)."""
    mine, theirs = row.get("my_score"), row.get("octa_score")
    if mine is None or theirs is None:
        return None
    return round(mine - theirs, 1)


def regime(indices, universe):
    """🌡️ حالة السوق: صاعد / هابط / عرضي / متقلّب / سيولة ضعيفة."""
    egx30 = None
    for ix in (indices or {}).get("indices") or []:
        if ix.get("id") == "EGX30":
            egx30 = ix
    if not egx30:
        return {"state": "غير معروف", "note": "مفيش EGX30"}
    ln = egx30.get("live_now") or {}
    p1, py = num(ln.get("perf_1m")), num(ln.get("perf_y"))
    chg = num(ln.get("change"))

    up = sum(1 for s in (universe or []) if (num(s.get("change")) or 0) > 0)
    tot = len(universe or []) or 1
    breadth = 100.0 * up / tot
    spread = 0.0
    rets = [num(s.get("perf_1m")) for s in (universe or [])]
    rets = [r for r in rets if r is not None]
    if rets:
        spread = max(rets) - min(rets)

    if p1 is None:
        state = "غير معروف"
    elif p1 >= 5 and breadth >= 55:
        state = "صاعد"
    elif p1 >= 0 and breadth >= 45:
        state = "صاعد هابط"
    elif p1 <= -8 and breadth <= 40:
        state = "هابط"
    elif spread >= 60:
        state = "متقلّب"
    elif breadth < 30:
        state = "سيولة ضعيفة"
    else:
        state = "عرضي"
    return {"state": state, "egx30_1m": p1, "egx30_y": py,
            "breadth_pct": round(breadth, 1), "dispersion_1m": round(spread, 1), "change": chg}


def gate(row):
    """🚧 بوابات الدخول."""
    reasons = []
    if row.get("my_score") is None:
        reasons.append("مفيش درجة محسوبة")
    elif row["my_score"] < GATES["min_my_score"]:
        reasons.append("درجتي أقل من العتبة (%.0f)" % GATES["min_my_score"])
    if row.get("coverage", 1) < 0.55:
        reasons.append("تغطية بيانات ضعيفة")
    if row.get("rsi") is not None and row["rsi"] > GATES["max_rsi_entry"]:
        reasons.append("RSI فوق ٧٨")
    if row.get("perf_1m") is not None and row["perf_1m"] < GATES["min_perf_1m"]:
        reasons.append("هبوط شهري قوي")
    liq = (row.get("factors") or {}).get("liquidity")
    if liq is not None and liq < GATES["min_liquidity"]:
        reasons.append("سيولة ضعيفة")
    return reasons
