# -*- coding: utf-8 -*-
"""🔧 تصحيح ردود البوت (ezz-auto2) — يفرق بين «أوامر مستنية» و«مراكز منفَّذة»."""
P = "ops/workers/ezz-auto2.js"
s = open(P, encoding="utf-8").read()

# ── ١) replyPortfolio: عرض المراكز المنفَّذة بدل «أوامر مستنية» ──
old = (
    '  if (d && Array.isArray(d.orders) && d.orders.length) {\n'
    '    L.push("");\n'
    '    L.push("📝 أوامر مستنية تنفيذك (" + d.orders.length + ") — " + money(d.total) + " ج.م");\n'
    '    if (live && live.pl !== null && live.pl !== undefined) {\n'
    '      L.push("💡 لو نُفِّذت بسعر التوصية: " + (live.pl >= 0 ? "ربح " : "خسارة ") + money(Math.abs(live.pl)) + " ج.م (" + (live.pl / nf(d.total) * 100).toFixed(2) + "%)");\n'
    '    }\n'
    '  } else {\n'
    '    L.push("");\n'
    '    L.push("📝 مفيش أوامر مسجّلة في الداتا.");\n'
    '  }\n'
)
new = (
    '  const executed = !!(d && d.status === "executed");\n'
    '  if (executed && nPos) {\n'
    '    L.push("");\n'
    '    L.push("📊 مراكزك المنفَّذة (" + nPos + ")");\n'
    '    if (live && live.pl !== null && live.pl !== undefined) {\n'
    '      L.push("💡 الربح/الخسارة الآن: " + (live.pl >= 0 ? "ربح " : "خسارة ") + money(Math.abs(live.pl)) + " ج.م (" + (live.pl / nf(d.total) * 100).toFixed(2) + "%)");\n'
    '    }\n'
    '    L.push("⛔ البيع يدوي في ثاندر — أنا بيحلل وببلّغ بس.");\n'
    '  } else if (d && Array.isArray(d.orders) && d.orders.length) {\n'
    '    L.push("");\n'
    '    L.push("📝 أوامر مستنية تنفيذك (" + d.orders.length + ") — " + money(d.total) + " ج.م");\n'
    '    if (live && live.pl !== null && live.pl !== undefined) {\n'
    '      L.push("💡 لو نُفِّذت بسعر التوصية: " + (live.pl >= 0 ? "ربح " : "خسارة ") + money(Math.abs(live.pl)) + " ج.م (" + (live.pl / nf(d.total) * 100).toFixed(2) + "%)");\n'
    '    }\n'
    '    L.push("⛔ القرار في إيدك — التنفيذ يدوي في ثاندر.");\n'
    '  } else {\n'
    '    L.push("");\n'
    '    L.push("📝 مفيش أوامر مسجّلة في الداتا.");\n'
    '  }\n'
)
assert s.count(old) == 1, ("portfolio block", s.count(old))
s = s.replace(old, new)

# ── ٢) replyOrders: نفس التفرقة + عرض سعر الدخول للمراكز المنفَّذة ──
old2 = (
    '  L.push("📝 أوامر مستنية تنفيذك (" + d.orders.length + ")");\n'
    '  L.push("التاريخ: " + (d.date || "") + " · الإجمالي: " + money(d.total) + " ج.م");\n'
    '  L.push("");\n'
    '  for (const o of d.orders) {\n'
    '    L.push("• " + (o.name || o.code) + " (" + o.code + ") — " + nf(o.qty) + " سهم");\n'
    '    L.push("سعر التوصية: " + nf(o.price).toFixed(2));\n'
)
new2 = (
    '  const executed = !!(d.status === "executed");\n'
    '  if (executed) {\n'
    '    L.push("📊 مراكزك المنفَّذة (" + d.orders.length + ") — " + money(d.total) + " ج.م");\n'
    '  } else {\n'
    '    L.push("📝 أوامر مستنية تنفيذك (" + d.orders.length + ")");\n'
    '  }\n'
    '  L.push("التاريخ: " + (d.date || "") + " · الإجمالي: " + money(d.total) + " ج.م");\n'
    '  L.push("");\n'
    '  for (const o of d.orders) {\n'
    '    const pos = s.positions[o.code];\n'
    '    const qty = pos ? nf(pos.qty, nf(o.qty)) : nf(o.qty);\n'
    '    const entry = pos ? nf(pos.avg_price, nf(o.price)) : nf(o.price);\n'
    '    L.push("• " + (o.name || o.code) + " (" + o.code + ") — " + qty + " سهم");\n'
    '    L.push(executed ? "سعر الدخول: " : "سعر التوصية: " + entry.toFixed(2));\n'
)
assert s.count(old2) == 1, ("orders block", s.count(old2))
s = s.replace(old2, new2)

# ── ٣) حساب الربح/الخسارة في replyOrders: يستخدم سعر الدخول الحقيقي ──
old3 = (
    '    const p = live && live.prices ? live.prices[o.code] : null;\n'
    '    if (p && typeof p.price === "number") {\n'
    '      const pl = p.price - nf(o.price), pc = pl / nf(o.price) * 100;\n'
    '      L.push("السعر الآن: " + p.price.toFixed(2));\n'
    '      L.push("التغيّر: " + (pc >= 0 ? "+" : "") + pc.toFixed(2) + "%");\n'
    '      L.push((pl >= 0 ? "الربح: " : "الخسارة: ") + money(Math.abs(pl * nf(o.qty))) + " ج.م");\n'
    '    }\n'
    '    L.push("سعر الوقف: " + nf(o.stop).toFixed(2));\n'
)
new3 = (
    '    const p = live && live.prices ? live.prices[o.code] : null;\n'
    '    if (p && typeof p.price === "number") {\n'
    '      const pl = p.price - entry, pc = pl / entry * 100;\n'
    '      L.push("السعر الآن: " + p.price.toFixed(2));\n'
    '      L.push("التغيّر: " + (pc >= 0 ? "+" : "") + pc.toFixed(2) + "%");\n'
    '      L.push((pl >= 0 ? "الربح: " : "الخسارة: ") + money(Math.abs(pl * qty)) + " ج.م");\n'
    '    }\n'
    '    const st = pos && pos.stop ? nf(pos.stop) : nf(o.stop);\n'
    '    L.push("سعر الوقف: " + st.toFixed(2));\n'
)
assert s.count(old3) == 1, ("pl block", s.count(old3))
s = s.replace(old3, new3)

# ── ٤) إعادة صياغة «لو نُفِّذت» ⇒ «لو نُفِّذت بسعر التوصية» يبقى للقائمة غير المنفَّذة ──
old4 = (
    '  if (live && live.pl !== null && live.pl !== undefined) {\n'
    '    L.push("💡 لو نُفِّذت الأوامر بسعر التوصية:");\n'
    '    L.push("القيمة الآن: " + money(live.now) + " ج.م");\n'
    '    L.push("مقابل التوصية: " + money(d.total) + " ج.م");\n'
    '    L.push("⇐ " + (live.pl >= 0 ? "ربح " : "خسارة ") + money(Math.abs(live.pl)) + " ج.م (" + (live.pl / nf(d.total) * 100).toFixed(2) + "%)");\n'
    '  }\n'
    '  L.push("⛔ القرار في إيدك — التنفيذ يدوي في ثاندر.");\n'
)
new4 = (
    '  if (!executed && live && live.pl !== null && live.pl !== undefined) {\n'
    '    L.push("💡 لو نُفِّذت الأوامر بسعر التوصية:");\n'
    '    L.push("القيمة الآن: " + money(live.now) + " ج.م");\n'
    '    L.push("مقابل التوصية: " + money(d.total) + " ج.م");\n'
    '    L.push("⇐ " + (live.pl >= 0 ? "ربح " : "خسارة ") + money(Math.abs(live.pl)) + " ج.م (" + (live.pl / nf(d.total) * 100).toFixed(2) + "%)");\n'
    '  }\n'
    '  if (!executed) L.push("⛔ القرار في إيدك — التنفيذ يدوي في ثاندر.");\n'
)
assert s.count(old4) == 1, ("summary block", s.count(old4))
s = s.replace(old4, new4)

open(P, "w", encoding="utf-8").write(s)
print("✅ اتعدّل", P)
