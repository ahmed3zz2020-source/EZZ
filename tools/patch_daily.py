# -*- coding: utf-8 -*-
"""🔧 تصحيح التقرير اليومي — يفرق بين «أوامر مستنية تنفيذك» و«مراكزك المنفَّذة»."""
import io

P = "ops/workers/ezz-daily.js"
s = open(P, encoding="utf-8").read()

# ── ١) الهيدر: نضيف positions + executed ──
old_head = (
    'function buildReport(state, tasks, port, meta, live, dec) {\n'
    '  const L = [];\n'
    '  const capital = nf(port && port.capital, 100000);\n'
    '  const cash = nf(port && port.cash, capital);\n'
    '  const nPos = Object.keys((port && port.positions) || {}).length;\n'
    '  const orders = (dec && Array.isArray(dec.orders)) ? dec.orders : [];\n'
)
new_head = (
    'function buildReport(state, tasks, port, meta, live, dec) {\n'
    '  const L = [];\n'
    '  const capital = nf(port && port.capital, 100000);\n'
    '  const cash = nf(port && port.cash, capital);\n'
    '  const positions = (port && port.positions) || {};\n'
    '  const nPos = Object.keys(positions).length;\n'
    '  const orders = (dec && Array.isArray(dec.orders)) ? dec.orders : [];\n'
    '  // ⭐ حالة القرار: اتنفّذ (بتأكيد المالك) ولا لسه مستني تنفيذ\n'
    '  const executed = !!(dec && dec.status === "executed");\n'
)
assert s.count(old_head) == 1, ("head", s.count(old_head))
s = s.replace(old_head, new_head)

# ── ٢) الكتلة الجديدة:_centers منفَّذة ──
BLOCK = (
    '  if (executed && nPos) {\n'
    '    // ✅ المراكز منفَّذة ⇒ عرض المراكز الحقيقية + الربح/الخسارة مقابل سعر الدخول\n'
    '    L.push("");\n'
    '    L.push("📊 مراكزك المنفَّذة (" + nPos + ")");\n'
    '    L.push("");\n'
    '    let unreal = 0, mv = 0;\n'
    '    for (const o of orders) {\n'
    '      const pos = positions[o.code];\n'
    '      const qty = pos ? nf(pos.qty, nf(o.qty)) : nf(o.qty);\n'
    '      const entry = pos ? nf(pos.avg_price, nf(o.price)) : nf(o.price);\n'
    '      const stop = pos && pos.stop ? nf(pos.stop) : nf(o.stop);\n'
    '      L.push("• " + (o.name || o.code) + " (" + o.code + ") — " + qty + " سهم");\n'
    '      L.push("سعر الدخول: " + entry.toFixed(2));\n'
    '      const p = (live && live.prices) ? live.prices[o.code] : null;\n'
    '      if (p && typeof p.price === "number") {\n'
    '        const pl = (p.price - entry) * qty, pc = (p.price - entry) / entry * 100;\n'
    '        unreal += pl; mv += p.price * qty;\n'
    '        L.push("السعر الآن: " + p.price.toFixed(2));\n'
    '        L.push("التغيّر: " + (pc >= 0 ? "+" : "") + pc.toFixed(2) + "%");\n'
    '        L.push((pl >= 0 ? "الربح: " : "الخسارة: ") + money(Math.abs(pl)) + " ج.م");\n'
    '        if (stop && p.price <= stop) L.push("🔴 تحت وقف الخسارة (" + stop.toFixed(2) + ") — القرار في إيدك");\n'
    '      }\n'
    '      L.push("سعر الوقف: " + stop.toFixed(2));\n'
    '      L.push("");\n'
    '    }\n'
    '    if (live && live.prices) {\n'
    '      const eq = cash + mv;\n'
    '      L.push("💡 قيمة المراكز الآن: " + money(mv) + " ج.م");\n'
    '      L.push("إجمالي المحفظة (كاش + مراكز): " + money(eq) + " ج.م");\n'
    '      L.push("الربح/الخسارة غير المحققة: " + (unreal >= 0 ? "ربح " : "خسارة ") + money(Math.abs(unreal))\n'
    '        + " ج.م (" + (unreal / capital * 100).toFixed(2) + "% من رأس المال)");\n'
    '    }\n'
    '    L.push("⛔ البيع يدوي في ثاندر — عز استثمار بيحلل ويبلّغ، ما بياخدش قرار بيع لوحده.");\n'
    '  } else if (orders.length) {\n'
)

# ن_find الكتلة الأولى بالـindex داخل buildReport (مش الثانية في liveMarketAndPrices)
MARK = "  if (orders.length) {\n    L.push(\"\");\n"
assert s.count(MARK) == 1, ("open block", s.count(MARK))
i = s.index(MARK)
s = s[:i] + BLOCK + s[i + len("  if (orders.length) {"):]

open(P, "w", encoding="utf-8").write(s)
print("✅ اتعدّل", P)
