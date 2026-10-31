# -*- coding: utf-8 -*-
"""
🔍 طبقة التحقق المستقل.

⛔ هدفها: ما نثقش في رقم واحد. كل سعر بيتقابل مع مصدر تاني، وكل مصدر
   بيتقابل مع snapshot_id معلن.

✅ сейчас شغّالة: تحقق داخلي ٣ مصادر (الكون + الشموع + Technical) + تاريخ الجلسة الرسمي.
🟡 ترفع تلقائياً لمصدر خارجي لو اتوفّر مفتاح (oanor / EGX Live).
⛔ لو مصدرين اختلفوا ⇒ بنبلّغ عن الفرق، مش بنختار واحد في صمت.
"""
import json
import os
import time
import urllib.request

from .intelligence import num

UA = "Mozilla/5.0 (X11; Linux x86_64) EZZ-Validation/1.0"


def _get_json(url, headers=None, timeout=25):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def internal_consistency(code, universe_price, candles=None, technical=None):
    """🧪 تحقق داخلي: سعر الكون + إغلاق آخر شمعة + سعر الـTechnical."""
    out = {"code": code, "sources": {}, "ok": True, "discrepancy_pct": 0.0}
    vals = {}
    if universe_price:
        vals["universe"] = float(universe_price)
    if candles:
        last = candles[-1]
        if isinstance(last, dict) and num(last.get("c")):
            vals["candle_close"] = float(last["c"])
    if technical:
        tp = num(technical.get("price"))
        if tp:
            vals["technical"] = tp
    out["sources"] = vals
    if len(vals) < 2:
        out["ok"] = False
        out["note"] = "مصدر واحد بس — تحقق غير مكتمل"
        return out
    vals = list(vals.values())
    lo, hi = min(vals), max(vals)
    dev = (hi - lo) / lo * 100 if lo else 0.0
    out["discrepancy_pct"] = round(dev, 3)
    out["ok"] = dev <= 1.0
    if not out["ok"]:
        out["note"] = "فرق %.2f%% بين المصادر — لازم مراجعة" % dev
    return out


def external_quote(code):
    """🌐 مصدر خارجي مستقل (اختياري — بيعمل لو فيه مفتاح).
    ⭐ oanor: مصدر حي للبورصة المصرية + شاشة فرز + قيمة EGX30."""
    key = os.environ.get("OANOR_API_KEY", "").strip()
    if not key:
        return {"available": False, "reason": "مفيش OANOR_API_KEY — التحقق الخارجي غير مفعّل",
                "provider": "oanor"}
    try:
        d = _get_json("https://api.oanor.com/egx-api/v1/quote?codes=%s" % code,
                      headers={"x-oanor-key": key})
        quotes = d.get("data", {}).get("quotes") or []
        if not quotes:
            return {"available": False, "reason": "مفيش اقتباس", "provider": "oanor"}
        q = quotes[0]
        return {"available": True, "provider": "oanor", "price": num(q.get("price")),
                "timestamp": (d.get("meta") or {}).get("timestamp"),
                "source": q.get("source")}
    except Exception as e:  # noqa: BLE001
        return {"available": False, "reason": str(e)[:100], "provider": "oanor"}


def crosscheck(code, our_price, candles=None, technical=None, use_external=True):
    """🔎 التحقق الكامل لسعر واحد: داخلي + خارجي + تقرير الفرق."""
    res = internal_consistency(code, our_price, candles, technical)
    if use_external:
        ext = external_quote(code)
        res["external"] = ext
        if ext.get("available") and ext.get("price") and our_price:
            dev = abs(ext["price"] - our_price) / our_price * 100
            res["external_discrepancy_pct"] = round(dev, 3)
            if dev > 1.0:
                res["ok"] = False
                res["note"] = "فرق %.2f%% مع %s" % (dev, ext.get("provider"))
    return res


def freshness(session_date, snapshot_id=None, health=None):
    """🕒 حداثة البيانات: تاريخ الجلسة الرسمي + snapshot + عمر الأساسيات."""
    out = {"session_date": session_date, "snapshot_id": snapshot_id}
    h = health or {}
    ts = h.get("data_full_ts") or h.get("data_ts") or h.get("last_update")
    out["fundamentals_ts"] = ts
    if ts and session_date:
        try:
            a = time.mktime(time.strptime(str(ts)[:10], "%Y-%m-%d"))
            b = time.mktime(time.strptime(session_date, "%Y-%m-%d"))
            out["fundamentals_age_days"] = int((b - a) / 86400)
        except Exception:  # noqa: BLE001
            out["fundamentals_age_days"] = None
    out["price_kind"] = "إغلاق آخر جلسة" if session_date else "غير معروف"
    return out
