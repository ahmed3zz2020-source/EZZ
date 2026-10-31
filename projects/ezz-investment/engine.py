# -*- coding: utf-8 -*-
"""
🚀 محرّك محفظة عز استثمار — المنسّق الأعلى.

⭐ المبدأ (بالنيابة عن المالك):
   «كل الإدارة معاك — عز استثمار. المالك هو التنفيذ فقط في الوسيط (ثاندر)
    لحد ما نلاقي وسيط في السوق المصري يسمح بربط برمجي.
    التوصية ≠ الأمر ≠ التنفيذ.»

📦 الطبقات:
   adapter/octa.py       → قراءة OCTA (قراءة فقط)
   adapter/intelligence  → اجتهادنا المستقل (٦ عوامل) + كشف التعارض
   adapter/validation    → تحقق مستقل (٣ مصادر + خارجي اختياري)
   adapter/ledger        → الدفتر + سجل القرارات + KV
   engine.py             → الخطط + التقارير + تيليجرام

▶️ التشغيل:
   python3 engine.py --slot intraday        # تقرير ١٣:٤٥ القاهرة
   python3 engine.py --slot night           # تقرير ٢٣:٠٠ القاهرة
   python3 engine.py --slot night --dry-run # بدون إرسال
   python3 engine.py --fill ORD-XXX --price 45.8   # تسجيل تنفيذ مؤكد
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter.intelligence import (detect_conflicts, divergence, evaluate, gate,  # noqa: E402
                                  merge_fresh, regime, sector_medians)
from adapter.ledger import KV, Journal, Ledger  # noqa: E402
from adapter.octa import OctaAdapter  # noqa: E402
from adapter.validation import crosscheck, freshness  # noqa: E402
from config import (HTTP_TIMEOUT, KV_KEY_META, KV_KEY_REPORTS, POLICY,  # noqa: E402
                    TELEGRAM_CHAT_ID, TELEGRAM_TOKEN_ENV)

CAP = os.environ.get("EZZ_INITIAL_CAPITAL", "100000")
SEP = "━━━━━━━━━━━━━━━━━━━━━━"


# ─────────────────────────── أدوات عرض ───────────────────────────
def money(x):
    return "—" if x is None else ("{:,.2f}".format(x))


def pct(x, sign=True):
    if x is None:
        return "—"
    return ("{:+.2f}%".format(x) if sign else "{:.2f}%".format(x))


def money0(x):
    return "—" if x is None else ("{:,.0f}".format(x))


# ─────────────────────────── بناء الخطة ───────────────────────────
def size_position(equity, price, stop, liq_cap_egp=None):
    """📐 حجم المركز: مخاطرة ١٫٥–٢٪ + سقف ٢٠٪ وزن + سقف السيولة."""
    if not price or not stop or stop >= price:
        return None
    # ⭐ نستهدف أعلى band's end (٢٪) — والسقف النهائي هو وزن ٢٠٪.
    #   لو سقف الوزن منع الوصول لـ١٫٥٪ ⇒ مخاطرة أقل = أأمن، مش خطأ.
    risk_pct = POLICY["risk_per_trade_max_pct"]
    budget = equity * risk_pct / 100.0
    dist = price - stop
    qty = budget / dist
    cap = equity * POLICY["max_position_pct"] / 100.0
    if liq_cap_egp:
        cap = min(cap, float(liq_cap_egp))
    qty = min(qty, cap / price)
    qty = int(qty // 10 * 10)
    if qty <= 0:
        return None
    risk = qty * dist
    return {"qty": qty, "notional": round(qty * price, 2), "risk_egp": round(risk, 2),
            "risk_pct": round(risk / equity * 100, 2), "stop": round(stop, 2),
            "weight_pct": round(qty * price / equity * 100, 2)}


def pick_stop(row, detail):
    """🛑 وقف الخسارة: أقرب دعم فني تحت السعر، وإلا ٧٪."""
    price = row.get("price")
    sup = None
    tech = (detail or {}).get("technical") or {}
    lv = (tech.get("levels") or {})
    for k in ("دعم_1", "support_1", "دعم1"):
        v = lv.get(k)
        if v:
            sup = float(v)
            break
    if not sup:
        for k, v in lv.items():
            if "دعم" in str(k) and v:
                sup = float(v)
                break
    fallback = price * 0.93
    if sup and price * 0.90 < sup < price * 0.985:
        return round(sup * 0.99, 2)
    return round(fallback, 2)


def adv_value(candles, price):
    """💧 متوسط قيمة التداول اليومي (ج.م) من آخر ٢٠ شمعة."""
    vals = []
    for c in (candles or [])[-20:]:
        v = c.get("v")
        if v and price:
            try:
                vals.append(float(v) * float(price))
            except (TypeError, ValueError):
                pass
    if not vals:
        return None
    return sum(vals) / len(vals)


def max_safe_position(adv):
    """🛡️ أقصى مركز آمن = ٥٪ من قيمة التداول اليومي (مش ٥٠٪!)."""
    if not adv:
        return None
    return adv * 0.05


def build_plan(rows, ledger, eq, detail_by_code):
    """🧭 الخطة: خروج أولاً (وقف/انفلات سند) ثم دخول (بأبواب صارمة)."""
    plan = {"exits": [], "entries": [], "holds": [], "watch": [], "rejected": []}

    # ── المراكز الحالية: وقف أو انقلاب سند ──
    for code, pos in (ledger.data.get("positions") or {}).items():
        row = next((r for r in rows if r["code"] == code), None)
        if not row:
            continue
        px = row.get("price")
        stop = pos.get("stop")
        reasons = []
        if stop and px and px <= stop:
            reasons.append("وقف الخسارة اتحقق (%.2f ≤ %.2f)" % (px, stop))
        if row.get("my_score") is not None and row["my_score"] < 45:
            reasons.append("درجتي نزلت تحت ٤٥")
        hard = [c for c in (row.get("conflicts") or [])
                if c in ("سيولة ضعيفة", "مخاطرة عالية", "تغطية بيانات ضعيفة")]
        reasons += hard
        if reasons:
            plan["exits"].append({"code": code, "name": row.get("name"), "price": px,
                                   "qty": pos.get("qty"), "stop": stop, "reasons": reasons,
                                   "sector": pos.get("sector")})
        else:
            plan["holds"].append({"code": code, "name": row.get("name"), "price": px,
                                  "score": row.get("my_score"), "stop": stop,
                                  "qty": pos.get("qty")})

    # ── الدخول ──
    # ⭐ كسر التعادل: لو فيه أكتر من مرشّح قريب من القمة ⇒ الأعلى سيولة يتقدّم.
    #   السبب: في محفظة ١٠٠ ألف،中心和 نقدر نخرج منه أهم من نقاط زيادة.
    scored = [r for r in rows if r.get("my_score") is not None]
    if scored:
        top = max(r["my_score"] for r in scored)
        tier = [r for r in scored if r["my_score"] >= top - 2.0]
        tier.sort(key=lambda r: ((r.get("factors") or {}).get("liquidity") or 0), reverse=True)
        rest = [r for r in rows if r not in tier]
        rows = tier + rest
    used_sector = dict(eq.get("sector_exposure") or {})
    eq_local = dict(eq)
    n_open = eq.get("n_positions", 0)
    open_risk = eq.get("open_risk_pct", 0.0)
    for row in rows:
        code = row["code"]
        if any(p["code"] == code for p in plan["exits"]) or any(p["code"] == code for p in plan["holds"]):
            continue
        g = gate(row)
        if g:
            if row.get("my_score") and row["my_score"] >= 48 and len(plan["watch"]) < POLICY["max_watch_items"]:
                plan["watch"].append({"code": code, "name": row.get("name"), "price": row.get("price"),
                                      "score": row.get("my_score"), "why": g[:2],
                                      "conflicts": row.get("conflicts") or []})
            continue
        if n_open >= POLICY["max_positions"]:
            continue
        # ⛔ ٣ أوامر كحد أقصى في الرسالة الواحدة — والباقي يروح قائمة الرادار
        if len(plan["entries"]) >= 3:
            continue
        if open_risk >= POLICY["open_risk_max_pct"]:
            continue
        detail = detail_by_code.get(code) or {}
        stop = pick_stop(row, detail)
        adv = adv_value(detail.get("candles"), row["price"])
        liq_cap = max_safe_position(adv)
        sz = size_position(eq["equity"], row["price"], stop, liq_cap)
        if not sz:
            continue
        # ⭐ مخاطرة أقل من ١٪ بسبب سقف السيولة = صفقة لا تُقاس ⇒ مرفوض
        if liq_cap and sz["risk_pct"] < 1.0:
            plan["rejected"].append({
                "code": code, "name": row.get("name"),
                "reason": "السيولة محدودة ⇒ المخاطرة الفعلية %s%% أقل من ١%%" % money(sz["risk_pct"])})
            if len(plan["watch"]) < POLICY["max_watch_items"]:
                plan["watch"].append({"code": code, "name": row.get("name"),
                                      "price": row.get("price"), "score": row.get("my_score"),
                                      "why": ["سيولة ضعيفة — مخاطرة أقل من ١٪"],
                                      "conflicts": row.get("conflicts") or []})
            continue
        # ⭐ مركز أصغر من الحد الأدنى = عملية غير مجدية ⇒ مرفوض (ومش «شراء صغير»)
        if sz["notional"] < POLICY["min_position_egp"]:
            plan["rejected"].append({
                "code": code, "name": row.get("name"),
                "reason": "الحجم %s ج.م أصغر من الحد الأدنى (%s) — سقف السيولة %s" % (
                    money0(sz["notional"]), money0(POLICY["min_position_egp"]),
                    money0(liq_cap) if liq_cap else "—")})
            if len(plan["watch"]) < POLICY["max_watch_items"]:
                plan["watch"].append({"code": code, "name": row.get("name"),
                                      "price": row.get("price"), "score": row.get("my_score"),
                                      "why": ["سقف السيولة %s ج.م" % (money0(liq_cap) if liq_cap else "—")],
                                      "conflicts": row.get("conflicts") or []})
            continue
        sec = row.get("sector") or "—"
        if used_sector.get(sec, 0.0) + sz["weight_pct"] > POLICY["max_sector_pct"]:
            plan["rejected"].append({"code": code, "name": row.get("name"),
                                     "reason": "سقف القطاع %.0f%%" % POLICY["max_sector_pct"]})
            continue
        order = {"code": code, "side": "buy", "qty": sz["qty"], "limit_price": row["price"],
                 "stop": sz["stop"], "sector": sec, "risk_egp": sz["risk_egp"],
                 "target1": round(row["price"] * 1.13, 2), "target2": round(row["price"] * 1.24, 2),
                 "thesis": thesis_of(row), "reason": " | ".join(str(x) for x in row.get("conflicts") or [])}
        eq_local["open_risk_pct"] = open_risk
        eq_local["n_positions"] = n_open
        bad = ledger.policy_check(order, None, eq_local)
        if bad:
            plan["rejected"].append({"code": code, "name": row.get("name"), "reason": bad[0]})
            continue
        used_sector[sec] = used_sector.get(sec, 0.0) + sz["weight_pct"]
        n_open += 1
        open_risk += sz["risk_pct"]
        plan["entries"].append(dict(order, price=row["price"], name=row.get("name"),
                                    score=row.get("my_score"), factors=row.get("factors"),
                                    octa=row.get("octa_score"), divergence=row.get("divergence"),
                                    notional=sz["notional"], weight_pct=sz["weight_pct"],
                                    risk_pct=sz["risk_pct"], liq_cap=liq_cap, detail=detail))
    return plan


def thesis_of(row):
    """🧠 سطر الفرضية: ليه ده بالذات؟"""
    f = row.get("factors") or {}
    parts = []
    if f.get("momentum"):
        parts.append("زخم %d" % f["momentum"])
    if f.get("quality"):
        parts.append("جودة %d" % f["quality"])
    if f.get("value"):
        parts.append("قيمة %d" % f["value"])
    if f.get("liquidity"):
        parts.append("سيولة %d" % f["liquidity"])
    d = (row.get("detail") or {}).get("value") or {}
    if d.get("pe_vs_sector"):
        parts.append("P/E %s× متوسط القطاع" % d["pe_vs_sector"])
    return " · ".join(parts) if parts else "اجتهاد المحرّك"


# ─────────────────────────── التقارير ───────────────────────────
def render_intraday(ctx):
    L = []
    A = ctx["date_ar"]
    L.append("📊 عز استثمار — قرار الجلسة")
    L.append("🗓 %s · %s" % (A, ctx["slot_time"]))
    reg = ctx["regime"]
    egx = ctx["egx30"]
    L.append("🟢 السوق: %s | EGX30 %s (%s)" % (reg.get("state"), money0(egx.get("value")),
                                               pct(egx.get("change"))))
    eq = ctx["eq"]
    L.append("")
    L.append("💼 المحفظة · %s ج.م" % money0(eq.get("capital")))
    L.append("🟢 مستثمر %s · ⚪ كاش %s" % (money0(eq.get("invested")), money0(eq.get("cash"))))
    L.append("📈 العائد %s · 🔓 مخاطرة مفتوحة %s" % (pct(eq.get("return_pct"), False),
                                                     pct(eq.get("open_risk_pct"), False)))
    L.append("")
    L.append(SEP)
    if ctx["plan"]["exits"]:
        L.append("🔴 المطلوب تنفيذه — خروج")
    else:
        L.append("🟢 المطلوب تنفيذه")
    L.append(SEP)
    n = 0
    for e in ctx["plan"]["exits"]:
        n += 1
        L.append("🔴 %d) بيع · %s · %s" % (n, e["code"], e["name"]))
        L.append("   🔢 %s سهم | 💵Execution عند %s" % (e["qty"], money(e["price"])))
        L.append("   🧠 السبب: %s" % " · ".join(e["reasons"]))
        L.append("   📌 بعد التنفيذ ابعتلي: «بعت %s» وأسجّلها" % e["code"])
    for e in ctx["plan"]["entries"]:
        n += 1
        L.append("🟢 %d) شراء · %s · %s" % (n, e["code"], e["name"]))
        L.append("   🔢 %s سهم | 💵 من %s لـ %s" % (e["qty"], money(e["price"] * 0.99),
                                                  money(e["price"] * 1.01)))
        L.append("   🧮 ≈ %s ج.م · ⚖️ وزن %s%% · 🔒 سقف السيولة %s" % (
            money0(e["notional"]), money0(e["weight_pct"]),
            money0(e.get("liq_cap")) if e.get("liq_cap") else "—"))
        L.append("   ⛱ وقف %s · مخاطرة %s ج.م (%s%%)" % (money(e["stop"]), money0(e["risk_egp"]),
                                                        money(e["risk_pct"],)))
        L.append("   🎯 هدف أول %s · هدف تاني %s" % (money(e["target1"]), money(e["target2"])))
        L.append("   🧠 %s" % e["thesis"])
        L.append("   ⚖️ اجتهادي %s · نتيجة OCTA %s (فرق %s)" % (
            money(e["score"]), money(e["octa"]) if e.get("octa") is not None else "—",
            ("%+d" % e["divergence"]) if e.get("divergence") is not None else "—"))
        L.append("   ⏱ صالح لآخر جلسة قبل الجلسة الجاية")
        L.append("   ❌ يلغى لو: نزل تحت وقف أو ظهرت إفادة سلبية")
        L.append("   📌 بعد التنفيذ ابعتلي: «دخلت %s عند %s»" % (e["code"], money(e["price"])))
    if not n:
        L.append("⚪ مفيش أوامر الآن — السوق مش بيستاهل المخاطرة دلوقتي")
    L.append("")
    L.append("⚪ لا بيع · ⚪ لا شراء تاني")
    if ctx["plan"].get("rejected"):
        L.append("🚫 مرفوض بالسياسة: %s" % " · ".join(
            "%s (%s)" % (r["code"], r["reason"]) for r in ctx["plan"]["rejected"][:3]))
    if ctx["plan"]["holds"]:
        L.append("🟦 مراكز قائمة: %s" % " · ".join(h["code"] for h in ctx["plan"]["holds"]))
    L.append("")
    if ctx["plan"]["watch"]:
        L.append("👀 تحت الرادار — لا تتدخل")
        for w in ctx["plan"]["watch"]:
            why = " · ".join(w["why"])[:70]
            L.append("• %s — %s (%s)" % (w["code"], why, money(w["price"])))
    L.append("")
    L.append("📈 المحفظة بعد التنفيذ")
    after_inv = eq.get("invested", 0) + sum(e["notional"] for e in ctx["plan"]["entries"])
    after_cash = eq.get("cash", 0) - sum(e["notional"] for e in ctx["plan"]["entries"])
    L.append("مستثمر %s ← %s · كاش %s ← %s" % (money0(eq.get("invested")), money0(after_inv),
                                                money0(eq.get("cash")), money0(after_cash)))
    L.append("")
    L.append(ctx["data_note"])
    return "\n".join(L)


def render_night(ctx):
    L = []
    L.append("📊 عز استثمار — مسح الليلة")
    L.append("🗓 %s · %s" % (ctx["date_ar"], ctx["slot_time"]))
    L.append("📅 بيانات آخر جلسة: %s" % ctx["session_ar"])
    reg = ctx["regime"]
    egx = ctx["egx30"]
    L.append("🟢 السوق: %s | EGX30 %s (%s) · عرض السوق %s%%" % (
        reg.get("state"), money0(egx.get("value")), pct(egx.get("change")),
        money0(reg.get("breadth_pct"))))
    eq = ctx["eq"]
    L.append("")
    L.append("💼 المحفظة · %s ج.م · العائد %s · مخاطرة مفتوحة %s" % (
        money0(eq.get("capital")), pct(eq.get("return_pct"), False), pct(eq.get("open_risk_pct"), False)))
    L.append("🟢 مستثمر %s · ⚪ كاش %s" % (money0(eq.get("invested")), money0(eq.get("cash"))))
    L.append("")
    L.append(SEP)
    L.append("🧭 خطة الجلسة الجاية — الأولوية")
    L.append(SEP)
    n = 0
    for e in ctx["plan"]["entries"]:
        n += 1
        L.append("%d) شراء %s (%s) — %s سهم · من %s · وقف %s" % (
            n, e["code"], e["name"], e["qty"], money(e["price"]), money(e["stop"])))
        L.append("   🧠 %s" % e["thesis"])
    for e in ctx["plan"]["exits"]:
        n += 1
        L.append("%d) بيع %s (%s) — %s سهم · السبب: %s" % (
            n, e["code"], e["name"], e["qty"], " · ".join(e["reasons"])))
    if not n:
        L.append("⚪ مفيش أوامر — خلّي الكاش دلوقتي")
    L.append("")
    L.append("👀 اللي تحت الرادار — راقبهم")
    for w in ctx["plan"]["watch"]:
        L.append("• %s %s (%s) — %s" % (w["code"], w["name"], money(w["price"]),
                                         " · ".join(w["why"])[:60]))
    if ctx["plan"].get("rejected"):
        L.append("🚫 مرفوض بالسياسة: %s" % " · ".join(
            "%s (%s)" % (r["code"], r["reason"]) for r in ctx["plan"]["rejected"][:3]))
    if ctx["plan"]["holds"]:
        L.append("")
        L.append("🟦 مراجعة المراكز القائمة")
        for h in ctx["plan"]["holds"]:
            L.append("• %s %s — درجتي %s · وقف %s" % (h["code"], h["name"], money(h["score"]),
                                                        money(h["stop"])))
    L.append("")
    L.append("📊 مؤشرات المقارنة")
    for k, v in (ctx["benchmarks"] or {}).items():
        L.append("• %s: %s (%s) · شهر %s · سنة %s" % (
            k, money0(v.get("value")), pct(v.get("change")),
            pct(v.get("perf_1m"), False), pct(v.get("perf_y"), False)))
    if ctx.get("gold"):
        g = ctx["gold"]
        L.append("• 🥇 جرام ٢٤ قيراط: %s ج.م · دولار: %s" % (money(g.get("gram_egp")),
                                                            money(g.get("egp_per_usd"))))
    L.append("")
    L.append(ctx["data_note"])
    return "\n".join(L)


# ─────────────────────────── تيليجرام ───────────────────────────
def send_telegram(text, dry=False):
    token = os.environ.get(TELEGRAM_TOKEN_ENV) or os.environ.get("OFFICE_BOT_TOKEN") or ""
    if not token:
        return False, "مفيش توكن بوت"
    if dry:
        return True, "dry-run — مش بيبعت"
    body = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text,
                       "disable_web_page_preview": True}).encode()
    req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % token,
                                 data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        return bool(d.get("ok")), d.get("result", {}).get("message_id")
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:150]


AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
             "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
AR_DAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def date_ar(iso):
    try:
        y, m, d = [int(x) for x in iso.split("-")]
        import datetime
        dt = datetime.date(y, m, d)
        return "%s %d %s" % (AR_DAYS[dt.weekday()], d, AR_MONTHS[m - 1])
    except Exception:  # noqa: BLE001
        return iso


# ─────────────────────────── التشغيل ───────────────────────────
def main():
    args = sys.argv[1:]
    slot = "intraday"
    dry = False
    fill_oid = None
    fill_price = None
    msg = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--slot":
            slot = args[i + 1]; i += 2
        elif a == "--dry-run":
            dry = True; i += 1
        elif a == "--fill":
            fill_oid = args[i + 1]; i += 2
        elif a == "--price":
            fill_price = float(args[i + 1]); i += 2
        elif a == "--msg":
            msg = args[i + 1]; i += 2
        else:
            i += 1

    if msg:
        ok, mid = send_telegram(msg, dry=dry)
        print("أُرسل: %s (message_id=%s)" % (ok, mid))
        return 0

    kv = KV()
    ledger = Ledger(kv)
    if fill_oid:
        o = ledger.apply_fill(fill_oid, fill_price)
        jr = Journal(kv)
        jr.append({"type": "fill", "order_id": fill_oid, "code": o["code"],
                   "price": fill_price, "qty": o.get("fill_qty"),
                   "source": "owner_confirmation"})
        print("✅ اتسجّل التنفيذ: %s @ %s" % (fill_oid, fill_price))
        return 0

    ad = OctaAdapter(timeout=HTTP_TIMEOUT)
    ad.session()
    universe, snapshot = ad.universe()
    indices = ad.indices()
    session_date = ad.session_date(indices)
    sector = ad.sector_stats()
    divs = ad.dividends()
    gold = ad.gold()
    health = ad.health()

    try:
        ledger.seed(float(CAP))
    except Exception as e:  # noqa: BLE001
        print("⚠️ التهيئة اتأخّرت: %s" % str(e)[:110])
    # ⭐ ادمج الطبقة الطازجة (أساسيات اليوم) — تملأ الناقص وتضيف حقول
    try:
        fresh = (ad.egx_full() or {}).get("stocks") or {}
    except Exception as e:  # noqa: BLE001
        print("⚠️ egx_full: %s" % str(e)[:80])
        fresh = {}
    universe, mstats = merge_fresh(universe, fresh)
    sector = sector_medians(universe) or sector
    print("🧩 الدمج مع الطبقة الطازجة: %s" % json.dumps(mstats.get("filled") or {}, ensure_ascii=False))
    rows = evaluate(universe, sector, divs)
    for r in rows:
        r["conflicts"] = detect_conflicts(r)
        r["divergence"] = divergence(r)
    rows.sort(key=lambda r: (r["my_score"] is None, -(r["my_score"] or 0)))
    # ⭐ النتيجة النهائية من explain (base + تعديلات) للمرشّحين الأ(top)
    prices = {r["code"]: r["price"] for r in rows if r.get("price")}
    eq = ledger.equity(prices)

    # تفاصيل أعمق للمرشّحين بس (تكلفة محدودة)
    detail_by_code = {}
    for r in rows[:8]:
        try:
            detail_by_code[r["code"]] = ad.detail(r["code"])
        except Exception:  # noqa: BLE001
            detail_by_code[r["code"]] = {}
        try:
            detail_by_code[r["code"]]["candles"] = ad.candles(r["code"], n=20)
        except Exception:  # noqa: BLE001
            pass
        ex = (detail_by_code.get(r["code"]) or {}).get("explain") or {}
        exp = ex.get("explanation") or {}
        if exp.get("base_score") is not None:
            fin = float(exp.get("base_score")) + float(exp.get("adjustment_total") or 0)
            r["octa_score"] = round(fin, 1)
            r["divergence"] = divergence(r)

    # تحقق مستقل على أفضل ٣
    checks = []
    for r in rows[:3]:
        try:
            c = ad.candles(r["code"], n=5)
        except Exception:  # noqa: BLE001
            c = []
        checks.append(crosscheck(r["code"], r["price"], c,
                                 (detail_by_code.get(r["code"]) or {}).get("technical")))
    fresh = freshness(session_date, snapshot, health)

    plan = build_plan(rows, ledger, eq, detail_by_code)

    # ⭐ خط الأساس (أول تشغيل) — نقطة بداية المقارنة
    meta = kv.get_json(KV_KEY_META, None)
    if not meta:
        meta = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "session_date": session_date, "capital": float(CAP),
                "benchmarks": {}, "note": "نقطة البداية — أول تشغيل"}
        for ix in indices.get("indices") or []:
            ln = ix.get("live_now") or {}
            meta["benchmarks"][ix["id"]] = {"value": ln.get("value"), "change": ln.get("change"),
                                           "perf_1m": ln.get("perf_1m"), "perf_y": ln.get("perf_y")}
        meta["gold"] = {"gram_egp": gold.get("gram_egp"), "egp_per_usd": gold.get("egp_per_usd")}
        kv.put(KV_KEY_META, meta)

    ctx = {
        "date_ar": date_ar(time.strftime("%Y-%m-%d")),
        "session_ar": date_ar(session_date) if session_date else "—",
        "slot_time": "١٣:٤٥ القاهرة" if slot == "intraday" else "٢٣:٠٠ القاهرة",
        "regime": regime(indices, universe),
        "egx30": next((ix.get("live_now") or {} for ix in indices.get("indices") or []
                       if ix.get("id") == "EGX30"), {}),
        "eq": eq, "plan": plan, "gold": gold,
        "benchmarks": {ix["id"]: (ix.get("live_now") or {}) for ix in indices.get("indices") or []},
        "data_note": "🔎 لقطة %s · آخر جلسة %s · تحقق: %s" % (
            snapshot, session_date or "—",
            "✅ متسق" if all(c.get("ok") for c in checks) else "⚠️ في اختلاف"),
    }
    text = render_intraday(ctx) if slot == "intraday" else render_night(ctx)
    if len(text) > POLICY["max_report_chars"]:
        text = text[:POLICY["max_report_chars"] - 40] + "\n⋯ (اتقطعت آخر رسالة)"
    ok, mid = send_telegram(text, dry=dry)
    key = "%s%s-%s" % (KV_KEY_REPORTS, time.strftime("%Y-%m-%d"), slot)
    if not dry:
        try:
            kv.put(key, {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "text": text,
                         "sent": ok, "message_id": mid, "slot": slot})
        except Exception as e:  # noqa: BLE001
            print("⚠️ تعذّر حفظ التقرير في KV: %s" % str(e)[:110])

    # سجل القرار
    jr = Journal(kv)
    journal_entry = {"type": "report", "slot": slot, "snapshot": snapshot,
               "session_date": session_date, "regime": ctx["regime"].get("state"),
               "equity": eq.get("equity"), "cash": eq.get("cash"),
               "return_pct": eq.get("return_pct"),
               "entries": [{"code": e["code"], "qty": e["qty"], "price": e["price"],
                            "stop": e["stop"], "score": e["score"], "thesis": e["thesis"],
                            "risk_egp": e["risk_egp"]} for e in plan["entries"]],
               "exits": [{"code": e["code"], "reasons": e["reasons"]} for e in plan["exits"]],
               "watch": [{"code": w["code"], "score": w["score"]} for w in plan["watch"]],
               "validation": checks, "freshness": fresh}
    if not dry:
        try:
            jr.append(journal_entry)
        except Exception as e:  # noqa: BLE001
            print("⚠️ تعذّر كتابة السجل: %s" % str(e)[:110])

    # الأوامر ⇒ سجل (بانتظار موافقة المالك)
    if not dry:
        stamp = time.strftime("%H%M%S")
        for e in plan["entries"]:
            oid = "BUY-%s-%s" % (e["code"], stamp)
            ledger.new_order(oid, e["code"], "buy", e["qty"], e["price"], stop=e["stop"],
                             target1=e["target1"], target2=e["target2"], thesis=e["thesis"],
                             risk_egp=e["risk_egp"], sector=e["sector"], reason=e.get("reason", ""))
        for e in plan["exits"]:
            oid = "EXIT-%s-%s" % (e["code"], stamp)
            ledger.new_order(oid, e["code"], "sell", e["qty"], e["price"],
                             notes=" · ".join(e["reasons"]), sector=e.get("sector"))
        ledger.record_equity(eq.get("equity", 0))
        try:
            ledger.save()
        except Exception as e:  # noqa: BLE001
            print("⚠️ تعذّر حفظ الدفتر: %s" % str(e)[:110])

    print(text)
    print("\n--- 🔬 تشخيص أعلى ١٢ مرشّح ---")
    print("%-7s %-26s %6s %5s %5s %5s %5s %5s %5s %5s  %s" % ("code", "name", "score", "mom", "qual", "val", "liq", "risk", "cat", "gro", "gate"))
    for r in rows[:12]:
        f = r.get("factors") or {}
        print("%-7s %-26s %6s %5s %5s %5s %5s %5s %5s %5s  %s" % (
            r["code"], (r.get("name") or "")[:25], r.get("my_score"),
            f.get("momentum"), f.get("quality"), f.get("value"), f.get("liquidity"),
            f.get("risk"), f.get("catalyst"), f.get("growth"), " · ".join(gate(r))[:40]))
    print("\n--- meta ---")
    print(json.dumps({"sent": ok, "message_id": mid, "entries": len(plan["entries"]),
                      "exits": len(plan["exits"]), "equity": eq.get("equity"),
                      "snapshot": snapshot, "session_date": session_date}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
