#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧊 مولّد «ملف التسليم» — يجعل نقل الشات رخيصًا.

⭐ المبدأ: ملف التسليم = **مؤشرات لا payloads**.
   - فيه:وين كل حاجة + إيه المتّفق عليه + إيه المطلوب + حالة الأنظمة.
   - مافيهوش: أرقام المحفظة (المستودع عام ⇒ تسريب) ولا نص التاريخ.
   ⇒ الأرقام الحية تيجي وقت الحاجة من KV/Workers (صفر توكن).

⛔ كل سطر لازم يكون معاه مصدره · ⛔ أي مصدر فشل ⇒ «⛔ لا توجد بيانات» (مش تخمين).

▶️ التشغيل:
   python3 tools/handoff.py            # يكتب ops/HANDOFF.md
   python3 tools/handoff.py --print    # يطبع على الشاشة من غير كتابة
"""
import json
import os
import subprocess
import sys
import urllib.request

CF_ACCOUNT = "74e046678adabf0706024b97b205882b"
NS_CENTRAL = "5a651f83b4b249f2995f6138225ada8f"   # ezz-central-memory
NS_INVEST = "a4509b030f394d478736ed1d186778fb"   # ezz-investment

# kind: "get" = endpoint عادي · "post" = webhook (GET بيرجّع 404 بالتصميم)
WORKERS = {
    "ezz-auto2 (بوابة البوت)": ("https://ezz-auto2.ahmed3zz2020.workers.dev/telegram", "post"),
    "ezz-daily (التقرير اليومي)": ("https://ezz-daily.ahmed3zz2020.workers.dev/run?send=0", "get"),
    "ezz-watch (مراقب القرار)": ("https://ezz-watch.ahmed3zz2020.workers.dev/run?send=0", "get"),
    "ezz-gate-send (الإرسال)": ("https://ezz-gate-send.ahmed3zz2020.workers.dev/send", "post"),
}

# روابط الأرقام الحية (وقت الحاجة)
URL_DAILY = "https://ezz-daily.ahmed3zz2020.workers.dev/run?send=0"
URL_WATCH_STATUS = "https://ezz-watch.ahmed3zz2020.workers.dev/status"
URL_OCTA = "https://octa-prices-production-4ccb.up.railway.app"

OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ops", "HANDOFF.md")


# ─────────────────────────── أدوات ───────────────────────────
def sh(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=25).stdout.strip()
    except Exception:
        return ""


def kv_get(ns, key):
    """⛔ راجع: JSON ⇒ dict · نص ⇒ str · فشل ⇒ None."""
    tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not tok:
        return None
    url = ("https://api.cloudflare.com/client/v4/accounts/%s/storage/kv/namespaces/%s/values/%s"
           % (CF_ACCOUNT, ns, key))
    try:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer %s" % tok,
                                                    "User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return raw
    except Exception:
        return None


def http_alive(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def fmt(v):
    return "⛔ لا توجد بيانات" if v is None else str(v)


# ───────────────────────────.Build ───────────────────────────
def build():
    L = []
    A = L.append

    A("# 🧊 ملف التسليم — مؤسسة EZZ")
    A("")
    A("> **مولَّد آلياً** بـ`python3 tools/handoff.py` (لا يُكتب يدوي ⇒ ما يتقادمش).")
    A("> ⛔ **مؤشرات لا payloads** — الأرقام الحية تيجي من KV/Workers وقت الطلب (صفر توكن).")
    A("> ⛔ المستودع عام ⇒ **مافيش أرقام محفظة هنا**. المحفظة في KV `portfolio/ezz-investment`.")
    A("")

    # ── ١) مصدر الحقيقة ──
    A("## ١) وين كل حاجة (المصدر: الريبو)")
    A("")
    head = sh("git log -1 --format='%h %ad %s' --date=short")
    A("- ريبو `ahmed3zz2020-source/EZZ` · آخر commit: `%s`" % (head or "⛔ لا توجد بيانات"))
    A("- الدستور `CONSTITUTION.md` · البروتوكول `PROTOCOL.md` · الوكلاء `AGENTS-REGISTRY.md` + `ops/agent-registry.json`")
    A("- الذاكرة المركزية `MEMORY.md` (بنية) · السجل `logs/YYYY-MM-DD.md` · قرارات `decisions/`")
    A("- موضوعات الوكلاء `topics/<agent>.md` (append-only) · الميزانية `ops/TOKEN-BUDGET.md`")
    A("- **القواعد الحاكمة للوكلاء** `PROTOCOL.md` §١–§٤ (فئات الصلاحيات) · §٨ (بوابة الجودة) · §١٠ (تسليم النماذج)")
    A("- ⛔ **الوكلاء الـ3 الدائمة بس**: gold-watchdog · EZZ-Gate · EZZ-Brief — والباقي بالطلب.")
    A("  ⛔ **ممنوع cron جديد من غير طلب صريح من المالك** (قرار ١ نوفمبر).")
    A("- ⛔ **محتوى فيديو المحفظة متوقف نهائياً** (قرار ١ نوفمبر).")
    A("")

    # ── ٢) حالة المؤسسة ──
    A("## ٢) حالة المؤسسة (المصدر: KV core/state.json)")
    A("")
    st = kv_get(NS_CENTRAL, "core/state.json")
    if isinstance(st, dict):
        A("- المرحلة: %s · آخر تحديث: %s" % (fmt(st.get("phase")), fmt(st.get("updated"))))
        A("- وكلاء نشطون: %s · إجمالي المعرَّفين: %s"
          % (fmt(st.get("agents_active")), fmt(st.get("agents_defined"))))
        A("- قرارات مفتوحة: %s · قرارات مغلقة: %s"
          % (fmt(len(st.get("open_decisions") or [])), fmt(len(st.get("resolved_decisions") or []))))
        qg = st.get("quality_gate") or {}
        A("- بوابة الجودة: %s (أول تدقيق: %s خطأ — كلها اتصلحت)"
          % ("مفعلة" if qg.get("radar_requires_audit") else "⛔ لا توجد بيانات",
             fmt((qg.get("first_audit") or {}).get("errors"))))
    else:
        A("- ⛔ لا توجد بيانات")
    A("")

    # ── ٣) المطلوب من المالك ──
    A("## ٣) المطلوب من المالك (المصدر: KV core/tasks.json)")
    A("")
    tk = kv_get(NS_CENTRAL, "core/tasks.json")
    rows = []
    if isinstance(tk, dict):
        for t in (tk.get("open") or []):
            if t.get("status") in ("open", "blocked", "in_progress"):
                rows.append(t)
    rows.sort(key=lambda t: (t.get("priority") or "P9", t.get("id") or ""))
    if rows:
        A("| المعرّف | الأولوية | الحالة | المطلوب |")
        A("|---|---|---|---|")
        for t in rows[:12]:
            A("| %s | %s | %s | %s |" % (t.get("id"), t.get("priority"), t.get("status"), t.get("task")))
    else:
        A("- ⛔ لا توجد بيانات")
    A("")

    # ── ٤) حالة المحفظة (بلا أرقام) ──
    A("## ٤) المحفظة — حالة فقط (المصدر: KV ezz-investment)")
    A("")
    led = kv_get(NS_INVEST, "portfolio/ezz-investment")
    dec = kv_get(NS_INVEST, "portfolio/decisions.json")
    if isinstance(led, dict):
        pos = led.get("positions") or {}
        cap = float(led.get("capital") or 0)
        cash = float(led.get("cash") or 0)
        A("- مراكز مفتوحة: **%d** · نقد: %s من رأس المال · رموز المراكز: %s"
          % (len(pos), ("%.0f%%" % (cash / cap * 100)) if cap else "⛔ لا توجد بيانات",
             (", ".join(sorted(pos.keys())) if pos else "لا يوجد — الدفتر كاش 100%")))
    else:
        A("- ⛔ لا توجد بيانات")
    if isinstance(dec, dict):
        A("- آخر قرار توصيات: %s · حالته: %s · عدد الأوامر: %s"
          % (fmt(dec.get("date")), fmt(dec.get("status")), fmt(len(dec.get("orders") or []))))
    else:
        A("- ⛔ لا توجد بيانات")
    A("- ⛔ **التوصية ≠ الأمر ≠ التنفيذ** · التنفيذ يدوي في ثاندر (المالك وحده).")
    A("- ⛔ **لا صفقة تتسجّل من غير سعر تنفيذ من المالك.**")
    A("")

    # ── ٥) الأنظمة الحيّة ──
    A("## ٥) الأنظمة الحيّة (المصدر: HTTP على Workers)")
    A("")
    for name, (url, kind) in WORKERS.items():
        st_code = http_alive(url)
        if kind == "post":
            # ⛔ webhook بيستقبل POST بس ⇒ GET بيرجّع 404 بالتصميم (مش فشل)
            A("- %s ⇒ webhook (يستقبل POST فقط ⇒ GET 404 متوقّع) — الدليل الحيّ: آخر رسالة اتردّت + `core/inbox`" % name)
        else:
            A("- %s ⇒ %s" % (name, "حي ✅" if st_code == 200 else ("HTTP %s ⛔" % st_code if st_code else "⛔ لا توجد بيانات")))
    A("- كرونات المنصّة: ⛔ **كلها متوقفة** (قرار ١ نوفمبر) ⇒ صفر استهلاك خلفي.")
    A("- البوت والتقرير والمراقب **بالكود ⇒ صفر توكن** · يردّون حتى لو الكريديت خلص.")
    A("")

    # ── ٦) الأرقام من وين (وقت الحاجة) ──
    A("## ٦) الأرقام الحية — منين تجيبها وقت الحاجة (بلا ما تقرا التاريخ)")
    A("")
    A("| الحاجة | الأمر | التكلفة |")
    A("|---|---|---|")
    A("| حالة المحفظة + الربح/الخسارة | `curl` على KV `portfolio/ezz-investment` | ٠ |")
    A("| سعر لحظي لسهم | `curl` على `%s/api/explain/<code>` | ٠ |" % URL_OCTA)
    A("| المؤشرات والذهب | `curl` على `/api/indices` · `/api/gold` | ٠ |")
    A("| التقرير اليومي | `curl` على `%s` | ٠ |" % URL_DAILY)
    A("| آخر فحص المراقب | `curl` على `%s` | ٠ |" % URL_WATCH_STATUS)
    A("")

    # ── ٧) قاعدة النقل الرخيصة ──
    A("## ٧) ⛔ قاعدة النقل الرخيصة (المصدر: قياس ٤ نوفمبر ٢٠٢٦)")
    A("")
    A("| البديل | الكلفة |")
    A("|---|---|")
    A("| ❌ نقل الشات + إعادة استكشاف (clone + قراءة ملفات + session_list) | **٤٠–٧٠ ألف توكن** + ٢٠+ نداء |")
    A("| ✅ نقل الشات + قراءة `ops/HANDOFF.md` بس | **≈٢–٣ آلاف توكن** + نداء واحد |")
    A("")
    A("- ⛔ **ممنوع** `session_list` العام (payload ضخم) · ⛔ **ممنوع** `memory_read` الكامل (١٤٢ ك.ب).")
    A("- ⛔ **ممنوع** إعادة قراءة `PROTOCOL.md`/`MEMORY.md`/السجل — الرابط في §١ بيوفّرها عند اللزوم.")
    A("- 📌 اقرأ `ops/HANDOFF.md` + `git log -3` ⇒ كمّل. الباقي بالـ`grep` عند الحاجة بس.")
    A("- ⛔ **النقل بيوفّر وقت مش كريديت** — الكاش بيوفّر ١٠× لو اتحفظ (القياس: سياق ١٨٢ ألف = ٢.٧ كريديت/رسالة بالكاش مقابل ٢٧ لرسالة واحدة لو الكاش اتكسر).")
    A("")

    A("---")
    A("")
    A("**مولَّد:** `python3 tools/handoff.py` · **مصدر السطر:** `logs/2026-11-01.md` (آخر سطر) + ما سبق.")
    A("")
    return "\n".join(L)


def main():
    text = build()
    if "--print" in sys.argv:
        print(text)
        return 0
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print("✅ كُتب %s (%d bytes)" % (OUT_PATH, len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
