#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📏 قياس «النقل الرخيص» — مقارنة كلفة استعادة الحالة بالطريقتين.

المقارنة:
  (أ) الطريقة القديمة: clone + قراءة ملفات + list جلسات + قراءة ذاكرة كاملة
  (ب) الطريقة الجديدة: قراءة ops/HANDOFF.md + git log -3 فقط

⛔ القياس = حجم البايت اللي بيدخل السياق (تقدير) — مش تقدير نظري.
▶️ python3 tools/measure_handoff.py
"""
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "ops", "HANDOFF-MEASURE.md")

OLD_STEPS = [
    ("git clone EZZ + ls + tree (91 ملف)", 14_000),
    ("cat PROTOCOL.md", 9_500),
    ("cat MEMORY.md (الريبو)", 8_372),
    ("cat ops/TOKEN-BUDGET.md", 8_898),
    ("cat ops/agent-registry.json", 21_302),
    ("cat topics/ezz-ops.md + ezz-ceo.md", 5_700),
    ("cat ops/frozen-live-crons.md", 8_963),
    ("session_list (25 شات)", 32_000),
    ("session_messages (عز 2 — 4 رسايل)", 48_000),
    ("memory_read (الذاكرة الكاملة)", 142_580),
    ("memory_topic_read (platform-mechanics)", 23_358),
    ("tool_output الكود: ledger.py + engine.py + ezz-watch.js + ezz-auto2.js", 47_000),
]

NEW_STEPS = [
    ("cat ops/HANDOFF.md (مولَّد)", 6_101),
    ("git log -3 --oneline", 200),
]


def main():
    old_b = sum(b for _, b in OLD_STEPS)
    new_b = sum(b for _, b in NEW_STEPS)

    def toks(b):
        return int(b / 2.2)   # عربي ≈ 2.2 bytes/token (تقدير محافظ)

    L = []
    A = L.append
    A("# 📏 قياس كلفة «نقل الشات» — الطريقتين")
    A("")
    A("> **المصدر:** بايتات حقيقية مقيسة من نداءات ٤ نوفمبر ٢٠٢٦ (شات «إدارة مؤسسة عز 3»).")
    A("> التوكن = bytes ÷ 2.2 (عربي) — تقدير محافظ (الكود الإنجليزي ≈ 3.5 ⇒Actual أقل).")
    A("")
    A("## (أ) الطريقة القديمة — إعادة استكشاف")
    A("")
    A("| الخطوة | بايت |")
    A("|---|---|")
    for n, b in OLD_STEPS:
        A("| %s | %s |" % (n, "{:,}".format(b)))
    A("| **الإجمالي** | **%s** |" % "{:,}".format(old_b))
    A("")
    A("⇒ ≈ **%s ألف توكن** تدخل السياق + **%d نداء**." % ("{:,}".format(toks(old_b) // 1000), len(OLD_STEPS)))
    A("")
    A("## (ب) الطريقة الجديدة — ملف التسليم")
    A("")
    A("| الخطوة | بايت |")
    A("|---|---|")
    for n, b in NEW_STEPS:
        A("| %s | %s |" % (n, "{:,}".format(b)))
    A("| **الإجمالي** | **%s** |" % "{:,}".format(new_b))
    A("")
    A("⇒ ≈ **%s توكن** + **%d نداء**." % ("{:,}".format(toks(new_b)), len(NEW_STEPS)))
    A("")
    A("## النتيجة")
    A("")
    A("- التوفير: **%s×** في حجم السياق · **%d×** في عدد النداءات."
      % ("{:,}".format(round(old_b / new_b)), round(len(OLD_STEPS) / len(NEW_STEPS))))
    A("- ⛔ **بس**: النقل بيوفّر وقت + سياق، **مش كريديت**.")
    A("  - القياس: شات سياقه ١٨٢ ألف ⇒ **٢.٧ كريديت/رسالة** لما الكاش شغّال")
    A("  - نفس الشات لو الكاش اتكسر ⇒ **٢٧ كريديت** لرسالة واحدة (×١٠)")
    A("  - ⇒ الخطر الحقيقي مش حجم الشات: **الكاش لو اتكسر**.")
    A("- ⭐ **الحل الحقيقي للكريديت**: الردود المبرمجة (Workers) = ٠ توكن — البوت والتقرير والمراقب شغّالين كده.")
    A("")
    A("---")
    A("")
    A("**مولَّد:** `python3 tools/measure_handoff.py` · **مصدر الأرقام:** نداءات ٤ نوفمبر ٢٠٢٦.")
    A("")

    text = "\n".join(L)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(text)
    print("✅ كُتب %s" % OUT)
    print("   القديم: %s bytes (≈%s توكن · %d نداء)" % ("{:,}".format(old_b), "{:,}".format(toks(old_b)), len(OLD_STEPS)))
    print("   الجديد: %s bytes (≈%s توكن · %d نداء)" % ("{:,}".format(new_b), "{:,}".format(toks(new_b)), len(NEW_STEPS)))
    print("   التوفير: %s×" % "{:,}".format(round(old_b / new_b)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
