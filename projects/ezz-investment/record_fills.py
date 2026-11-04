# -*- coding: utf-8 -*-
"""
🧾 تسجيل تنفيذ أوامر ٣١ أكتوبر — تأكيد المالك على تيليجرام (٤ نوفمبر ٢٠٢٦).

⛔ **الأساس:** تأكيد المالك الصريح على بوت تيليجرام (chat 2073907990):
   - «انا اشتريت فى الاسهم كله بناء على توصيتك»  (inbox id 557159681 · 2026-11-04)
   - «انا نفذت الأوامر فعلا»                      (inbox id 557159685)
   - «بنفس الاسعار الى انت وصيت بيه»              (inbox id 557159686)
   ⇒ سعر التنفيذ = سعر التوصية · الكمية = كمية التوصية (٤ أوامر).

⛔ **السلوك:** fail-closed — لو أي شرط غلط ⇒ ما فيهمّش تعديل.

▶️ python3 projects/ezz-investment/record_fills.py --dry-run   # معاينة
▶️ python3 projects/ezz-investment/record_fills.py             # تنفيذ
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter.ledger import KV, Journal, Ledger  # noqa: E402
from config import KV_NAMESPACE_ID  # noqa: E402

DRY = "--dry-run" in sys.argv
NS = KV_NAMESPACE_ID
ACCOUNT = "74e046678adabf0706024b97b205882b"
KEY_LEDGER = "portfolio/ezz-investment"
KEY_DECISIONS = "portfolio/decisions.json"
KEY_JOURNAL = "journal/"

INBOX_PROOF = ["557159681", "557159685", "557159686"]


def kv_raw(key):
    import urllib.request
    tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    url = ("https://api.cloudflare.com/client/v4/accounts/%s/storage/kv/namespaces/%s/values/%s"
           % (ACCOUNT, NS, key))
    req = urllib.request.Request(url, headers={"Authorization": "Bearer %s" % tok,
                                                "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def kv_put(key, payload):
    import urllib.request
    tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    url = ("https://api.cloudflare.com/client/v4/accounts/%s/storage/kv/namespaces/%s/values/%s"
           % (ACCOUNT, NS, key))
    req = urllib.request.Request(url, data=payload.encode("utf-8"), method="PUT",
                                 headers={"Authorization": "Bearer %s" % tok,
                                          "Content-Type": "text/plain; charset=utf-8",
                                          "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status in (200, 201)


def main():
    kv = KV()
    led = Ledger(kv)

    # ── ١) حراسة: الدفتر لازم يكون فيه أوامر معلّقة known ──
    dec = json.loads(kv_raw(KEY_DECISIONS))
    orders = dec.get("orders") or []
    if len(orders) != 4:
        print("❌ متوقّف: decisions.json فيها %d أمر (المتوقّع 4) — ما فيهمّش تعديل." % len(orders))
        return 2
    if led.data.get("positions"):
        print("❌ متوقّف: الدفتر فيه مراكز بالفعل ⇒ تمنع التنفيذ المزدوج.")
        return 2

    # ── ٢) تحقّق: كل سهم لازم يكون في التوصية + التوصية لسه «awaiting_owner_execution» ──
    if dec.get("status") != "awaiting_owner_execution":
        print("❌ متوقّف: حالة القرار %r مش awaiting_owner_execution." % dec.get("status"))
        return 2

    plan = []
    for o in orders:
        for f in ("code", "qty", "price", "stop"):
            if o.get(f) in (None, ""):
                print("❌ متوقّف: الأمر %r ناقص %s." % (o.get("code"), f))
                return 2
        qty = int(o["qty"])
        price = float(o["price"])
        gross = qty * price
        plan.append({"code": o["code"], "name": o.get("name"), "qty": qty, "price": price,
                     "stop": float(o["stop"]), "sector": o.get("sector"),
                     "gross": round(gross, 2), "risk_egp": round((price - float(o["stop"])) * qty, 2)})

    total = round(sum(p["gross"] for p in plan), 2)
    capital = float(led.data.get("capital") or 0)
    cash = float(led.data.get("cash") or 0)

    # ── ٣) تحقّق سياسات (نفس قوانين config.POLICY) ──
    from config import POLICY
    errs = []
    for p in plan:
        w = p["gross"] / capital * 100 if capital else 0
        if w > POLICY["max_position_pct"] + 0.01:
            errs.append("%s وزن %.2f%% > %.0f%%" % (p["code"], w, POLICY["max_position_pct"]))
        rp = p["risk_egp"] / capital * 100 if capital else 0
        if rp > POLICY["risk_per_trade_max_pct"] + 0.01:
            errs.append("%s مخاطرة %.2f%% > %.1f%%" % (p["code"], rp, POLICY["risk_per_trade_max_pct"]))
    if total > cash + 0.01:
        errs.append("الإجمالي %.2f > النقد %.2f" % (total, cash))
    if len(plan) > POLICY["max_positions"]:
        errs.append("عدد المراكز %d > %d" % (len(plan), POLICY["max_positions"]))
    if errs:
        print("❌ متوقّف (سياسة): " + " | ".join(errs))
        return 2

    # ── ٤) عرض (dry-run) أو تنفيذ ──
    print("=== %s ===" % ("معاينة (dry-run)" if DRY else "تنفيذ"))
    print("رأس المال: %.2f · النقد قبل: %.2f · إجمالي الشراء: %.2f · النقد بعد: %.2f"
          % (capital, cash, total, cash - total))
    for p in plan:
        print("  %-5s %-38s %6d @ %8.2f = %10.2f  وقف %.2f (مخاطرة %.2f)"
              % (p["code"], (p["name"] or "")[:38], p["qty"], p["price"], p["gross"], p["stop"], p["risk_egp"]))
    if DRY:
        print("\nℹ️ استُخدم --dry-run ⇒ ما فيهمّش تعديل.")
        return 0

    # ── ٥) التنفيذ: أنامر ← موافقة ← تعبئة (نفس مسار engine.py --fill) ──
    stamp = "20261104"
    for p in plan:
        oid = "BUY-%s-%s" % (p["code"], stamp)
        led.new_order(oid, p["code"], "buy", p["qty"], p["price"], stop=p["stop"],
                      sector=p["sector"], thesis="توصية ٣١ أكتوبر · تنفيذ مؤكد من المالك ٤ نوفمبر",
                      risk_egp=p["risk_egp"], notes="تأكيد المالك على تيليجرام (inbox %s)" % ",".join(INBOX_PROOF))
        led.approve(oid)
        o = led.apply_fill(oid, p["price"], qty=p["qty"], date="2026-11-04")
        print("✅ %s اتسجّل: %s @ %.2f × %d" % (oid, o["code"], p["price"], p["qty"]))

    # ── ٦) السجل (journal) ──
    jr = Journal(kv, prefix=KEY_JOURNAL)
    for p in plan:
        jr.append({"type": "fill", "code": p["code"], "qty": p["qty"], "price": p["price"],
                   "stop": p["stop"], "date": "2026-11-04", "source": "owner_confirmation_telegram",
                   "proof": "inbox ids " + ",".join(INBOX_PROOF)})

    # ── ٧) تحديث حالة القرار ⇒ «نفّذ» (عشان التقرير ما يقولش «مستنية تنفيذك») ──
    dec["status"] = "executed"
    dec["executed_at"] = "2026-11-04"
    dec["executed_source"] = "owner_confirmation_telegram (inbox %s)" % ",".join(INBOX_PROOF)
    for o in dec.get("orders") or []:
        o["status"] = "filled"
        o["fill_price"] = o.get("price")
        o["fill_date"] = "2026-11-04"
    dec["cash_after"] = round(cash - total, 2)
    ok = kv_put(KEY_DECISIONS, json.dumps(dec, ensure_ascii=False))
    print("✅ decisions.json اتحدّث ⇒ status=executed (%s)" % ("نجح" if ok else "⛔ فشل"))

    # ── ٨) النتيجة النهائية ──
    led2 = Ledger(kv)
    print("\n=== الدفتر بعد التنفيذ ===")
    print("النقد: %.2f · مراكز: %d · تكلفة مشتراة: %.2f"
          % (float(led2.data.get("cash") or 0), len(led2.data.get("positions") or {}), total))
    for code, pos in sorted((led2.data.get("positions") or {}).items()):
        print("  %-5s %6d @ %.4f  وقف %.2f" % (code, pos.get("qty"), pos.get("avg_price"), pos.get("stop") or 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
