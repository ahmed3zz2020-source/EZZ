# EZZ Central Memory — بنية الذاكرة

آخر تحديث: ٣١ أكتوبر ٢٠٢٦ · المرجع: [CONSTITUTION.md](CONSTITUTION.md) §6 · الأداة: `scripts/ezz-mem.py`

---

## ١) المبدأ

الذاكرة مركزية ومستقلة عن المحادثة وعن المزوّد: لو حُذفت المحادثة أو تعطّل النظام أو تغيّر النموذج ⇒ نستعيد هوية المؤسسة وقراراتها ووكلاءها ومشروعاتها وخططها وسجل أعمالها.

**مصدر الحقيقة لكل طبقة:**

| الطبقة | التخزين | الحساسية | المفتاح |
|---|---|---|---|
| **EZZ Core** | GitHub `EZZ` (عام) | غير حسّاسة | بلا مفتاح |
| **EZZ Media** | GitHub `EZZ` + Drive | غير حسّاسة | بلا مفتاح |
| **EZZ Business** | Cloudflare KV `ezz-central-memory` + Drive خاص | حسّاسة | توكن Cloudflare |
| **EZZ Personal** | Cloudflare KV (مشفّر) + Drive خاص | حسّاسة جداً | Fernet |
| **OCTA** | مستودعات `octa` · `octa-prices` | خاصة بالمشروع | بلا مفتاح |

⛔ **القيد الحقيقي المُقيس:** توكن GitHub الحالي `public_repo` فقط ⇒ **لا مستودع خاص** (403 مُقيس). ⇒ أي بيانات حسّاسة تُخزَّن خارج GitHub، أو تُشفَّر قبل أن تدخله.

## ٢) بنية الملفات

```
CONSTITUTION.md      الدستور (لا يُعدَّل إلا باعتماد)
PROTOCOL.md          التنفيذ والموافقة
AGENTS-REGISTRY.md   فهرس الوكلاء
MEMORY.md            هذا الملف
PROVIDER-ADAPTER.md  استقلال المزوّد
CHANGELOG.md         سجل التغييرات (append-only)
decisions/           قرار واحد في ملف (N年前的N: D-0001 …)
topics/<agent>.md    ملاحظات الوكيل (append-only · نطاق حصر)
logs/YYYY-MM-DD.md   سجل يومي (سطر لكل مهمة)
projects/<p>.md      ملف لكل مشروع
templates/           القوالب
docs/                التقارير والمخططات
scripts/ezz-mem.py   أداة الذاكرة
```

**قاعدة النطاق:** كل وكيل يكتب في `topics/<agent>.md` فقط + سطر واحد في `logs/`.
`topics/lessons.md` = EZZ-Audit وحده. `CONSTITUTION/PROTOCOL/REGISTRY` = المدير وحده.

## ٣) قاعدة البيانات (المتغيّرة)

**Cloudflare KV — namespace `ezz-central-memory`** (id: `5a651f83b4b249f2995f6138225ada8f`).
مُقيس: إنشاء ✅ · كتابة ✅ · قراءة ✅ · حذف ✅.
**سقف الكتابة:** 1000/يوم على مستوى الـaccount كله ⇒ ⛔ لا تكتب في كل نبضة. القاعدة: **اكتب عند التغيّر فقط** (لا heartbeat).
**مفاتيح مقترحة:**
```
core/state.json        حالة المؤسسة (آخر تحديث ·_phase ·_open_decisions)
core/agents.json       حالة كل وكيل + تقييمه + آخر خطأ
core/tasks.json        المهام المفتوحة (id · مالك · حالة · أولوية · موعد)
core/decisions.json    فهرس القرارات (id · عنوان · تاريخ · حالة)
core/opportunities.json رادار الفرص (فرصة · عائد · تكلفة · وقت · مخاطرة · حالة)
core/metrics.json      مؤشرات الأداء (حسب القسم)
scopes/personal.enc    نطاق شخصي (مشفّر)
scopes/business.enc    نطاق أعمال (مشفّر)
scopes/media.json      نطاق الإعلام (غير حسّاس)
```
**الكتابة بـ:**
```bash
curl -X PUT "https://api.cloudflare.com/client/v4/accounts/<ACC>/storage/kv/namespaces/<NS>/values/<KEY>"   -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" --data-binary @file.json
```

## ٤) التشفير (للبيانات الحسّاسة داخل نطاق عام)

Fernet متاح (cryptography 38.0.4) + OpenSSL 3.0.20 + gpg.
- المفتاح **لا يُحفظ في GitHub ولا في Drive المشترك** — يُحفظ في Cloudflare KV تحت `core/keys/fernet` (قراءة محدودة) أو عند المالك.
- ⚠️ **المفتاح في KV = حماية من القارئ العام، لا منTextsGold المالك.** للحماية الكاملة: المفتاح عند المالك فقط.
- الاستخدام: `python3 scripts/ezz-mem.py enc <in> <out>` / `dec`.

## ٥) التحديث (إلزامي)

عند: اتفاق · قرار · وكيل · صلاحية · مشروع · مهمة · هدف · نتيجة اجتماع · استراتيجية · خطأ مؤسسي · أداة جديدة:
1. صنّف في مكانه. 2. احفظ في الملف/الـKV. 3. سجّل التاريخ والمصدر. 4. اربط بالقرار/المشروع. 5. `CHANGELOG.md`. 6. نسخة احتياطية. 7. قابل للاسترجاع.

**أمر التحديث:**
```bash
python3 scripts/ezz-mem.py decision --id D-0007 --title "..." --status approved --summary "..."
python3 scripts/ezz-mem.py log "المهمة" "الوكيل" "الحالة" "الخطوة الجاية"
python3 scripts/ezz-mem.py topic <agent> "سطر ملاحظة"
```

## ٦) الاسترجاع والبحث

```bash
python3 scripts/ezz-mem.py search "رعاية"      # يبحث في كل ملفات المستودع + KV
python3 scripts/ezz-mem.py context             # يطبع سياق المؤسسة المختصر
python3 scripts/ezz-mem.py export out.json      # نسخة كاملة قابلة للنقل
```
البحث = `grep` على ملفات المستودع + قراءة KV. بلا فهرسة خارجية (مفيش D1).

## ٧) النسخ الاحتياطي والاستعادة

- **المستودع:** كل commit = نسخة. `git clone` = استعادة كاملة ⇒ في أي مكان.
- **KV:** نسخة يومية → `backups/kv/YYYY-MM-DD.json` (مشفر للنطاقات الحسّاسة) + Push لـGitHub كملف مشفّر.
- **Drive:** المخرجات (تقارير · عقود ·وسائط) — نسخة خارجية-redundant.
- **اختبار الاستعادة (إلزامي دورياً):**
```bash
python3 scripts/ezz-mem.py restore-test   # يسترجع آخر نسخة ويقارن البصمة
```
**خطة الطوارئ:** تعطل Railway ⇒ GitHub+KV يكفيان · فقدان GitHub ⇒ الـDrive + نسخة الـKV المشفّرة · اختراق حساب ⇒ تدوير التوكنات + المفتاح · تسريب مفتاح ⇒ تدوير + إعادة تشفير · حذف بيانات ⇒ استعادة من النسخة · تعطل المزوّد ⇒ النظام كله على GitHub/KV/Drive ⛔ لا يعتمد على المزوّد.

## ٨) قابلية النقل (لا حصرية للمزوّد)

كل المنطق في ملفات + JSON. لا كود مخصّص للمزوّد داخل منطق العمل.
طبقة المزوّد: [PROVIDER-ADAPTER.md](PROVIDER-ADAPTER.md) — إعدادات معيارية (endpoint · مفتاح · نماذج · الميزات) ⇒ تبديل المزوّد = تعديل ملف + تبديل cron agent.
⛔ لا تُخزَّن مفاتيح المزوّد في المستودع.

## ٩) حماية الذاكرة (منع التخريب)

⛔ لا وكيل يحذف الذاكرة أو يعطّل النسخ أو يغيّر الصلاحيات العليا أو يزيل سجل الرقابة أو يعدّل الدستور بلا صلاحية CEO صريحة.
**آلية:** GitHub history = سجل غير قابل للتعديل النسيان (لا حذف صامت) · `CHANGELOG.md` = سجل مقروء · `decisions/` = كل قرار بملف + تاريخ + حالة (معتمد/مقترح/معلق/مرفوض) — لا يُحذف، يُعلَّم superseded.

## ١٠) خريطة الاسترجاع السريعة

| توّد الحاجة | اقرأ |
|---|---|
| مين्या وكل-keyframes | `AGENTS-REGISTRY.md` + `topics/<agent>.md` |
| إيه القرارات | `decisions/` + `core/decisions.json` |
| إيه اللي اتعمل | `logs/YYYY-MM-DD.md` + `CHANGELOG.md` |
| حالة المشروع | `projects/<p>.md` |
| إيه القواعد | `CONSTITUTION.md` + `PROTOCOL.md` |
| الفرص | `core/opportunities.json` + `topics/ezz-opportunity.md` |
| الأرقام | `core/metrics.json` (دائماً بمصدر) |
