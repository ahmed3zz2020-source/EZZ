# EZZ — Provider Adapter Layer (استقلال المزوّد)

الهدف: تغيير مزوّد النموذج **دون إعادة بناء المؤسسة**.
المرجع: [CONSTITUTION.md](CONSTITUTION.md) §6 · [MEMORY.md](MEMORY.md) §8

## ١) القاعدة

⛔ **منطق العمل لا يحوي سطراً واحداً يخص مزوّداً بعينه.** كل الاستدعاءات تمرّ عبر طبقة تكييف واحدة: `config/providers.json`.

```json
{
  "default": {
    "provider": "minimax",
    "base_url_env": "MINIMAX_BASE_URL",
    "key_env": "MINIMAX_API_KEY",
    "models": {
      "reasoning": "MINIMAX_MODEL_REASONING",
      "fast":     "MINIMAX_MODEL_FAST",
      "tts":      "MINIMAX_MODEL_TTS",
      "vision":   "MINIMAX_MODEL_VISION"
    },
    "features": {"tools": true, "vision": true, "tts": true, "video": true, "audio_transcribe": true}
  }
}
```

## ٢) ما الذي يجب أن يبقى محايداً

| العنصر | مكانه | محايد؟ |
|---|---|---|
| الدستور والبروتوكول | `CONSTITUTION.md` · `PROTOCOL.md` | ✅ نصوص |
| تعريفات الوكلاء | `AGENTS-REGISTRY.md` + `topics/` | ✅ نصوص + YAML خفيف |
| المهام والمشاريع | `projects/` · `tasks.json` | ✅ JSON |
| سجل القرارات | `decisions/` | ✅ Markdown/JSON |
| المؤشرات | `core/metrics.json` | ✅ JSON |
| **النماذج نفسها** | `config/providers.json` | ⛔ هنا فقط — ثانوي |
| **المفاتيح** | متغيرات البيئة / الأسرار | ⛔ **ممنوع في GitHub** |

## ٣) سجل الوكلاء — شكل محايد

```yaml
id: EZZ-Finance
department: Operations
role: المدير المالي
tools: [drive, xlsx, web_search, telegram]
models: {reasoning: fast, tts: fast}   # ← مرجع تجريبي، لا اسم مزوّد
permissions: {spend: none, publish: none, approve: owner}
kpis: [roi, reinvest_ratio]
schedule: {daily_brief: 07:00}
```

## ٤) خطة التبديل (عملية)

1. جهّز `providers.<new>` بنفس الشكل + `features` مطابقة.
2. ضع المفاتيح في متغيرات البيئة الجديدة (لا في المستودع).
3. `python3 scripts/ezz-mem.py doctor` ⇒ يفحص: كل خدمة مطلوبة متاحة؟ كل نموذج موجود؟ الميزات المطلوبة مفعّلة؟
4. شغّل **وكيلاً واحداً** (EZZ-Audit) في وضع محاكاة ⇒ قارن المخرجات على ٥ مهام معروفة.
5. لو النتيجة ⇒ وسّع على agent-by-agent. **لا تقلب كل الوكلاء مرة واحدة.**
6. سجّل في `CHANGELOG.md` + قرار `D-xxxx` (نقل المزوّد).

## ٥) ما لا يمكن نقله (بصراحة)

| العنصر | السبب | البديل |
|---|---|---|
| ذاكرة المنصة (topics) | مرتبطة بالوكيل | صدّرها كملفات ⇒ re-import |
| جدولة cron | مرتبطة بالمنصة | استبدلها بـcron نظامي أو خدمة جدولة مستقلة |
| تكامل تيليجرام | تيليجرام نفسه مستقل | ✅ يعمل مع أي مزوّد |
| سجلات Drive | مرتبطة بحساب أحمد | ✅ تصدير/استيراد JSON |

## ٦) اختبار النقل (إلزامي مرة واحدة على الأقل)

```bash
python3 scripts/ezz-mem.py export export.json     # كل الذاكرة في ملف واحد
python3 scripts/ezz-mem.py import export.json --dry-run
```
⛔ **معيار النجاح:** ملف التصدير + `context` يعيدان نفس المعلومات ⇒ المسجّل مستقل فعلاً.
