---
name: octa-feature-ship
description: Ship a new OCTA page, tab, or indicator without the silent-death failure - the feature element, its TOOL_PAGES entry, the KEEP list, the TOOLS registry, the octaPageInit bootstrap, and the CSS class must all land together, then be verified on the real preview at 390px. Use when adding or changing an OCTA page, tab, market-depth panel, radar view, or any new front-end element. Not for the EZZ foundation apps.
---

# إضافة ميزة/صفحة في OCTA بدون «موت صامت»

## ⛔ القاعدة

**ميزة جديدة = ٥ حركات في نفس الـcommit. ناقصة واحدة = الصفحة بتظهر فاضية أو ميّتة بصمت.**

| # | الحركة | إيه اللي بيحصل لو ناقص |
|---|---|---|
| ١ | عنصر الـHTML + الـid بتاعه | ما فيش حاجة تت.render |
| ٢ | `TOOL_PAGES` | الصفحة مش بتتعرَّف أصلاً |
| ٣ | `KEEP` | البيانات بتتمسح بعد أول تحديث |
| ٤ | `TOOLS` | الأداة مش متاحة للـLLM |
| ٥ | `octaPageInit` | الصفحة تفتح فاضية (الـbootstrap مش شغّال) |

## الخطوة-by-خطوة

### ١ — ابحث عن الشكل القائم أولاً
```bash
grep -n "TOOL_PAGES" <file>       # شكل الصفحة
grep -n "KEEP" <file>             # قائمة الحفظ
grep -n "TOOLS" <file>            # سجل الأدوات
grep -n "octaPageInit" <file>     # التهيئة
```
⭐ **متعملش ميزة جديدة من الصفر** — اسأل: في ميزة شبهها أقدر أعدّل عليها؟

### ٢ — الـCSS
**كلاس CSS ⇒ لازم يبقى موجود في ملف الـCSS.** كلاس في الـJS بس = عنصر بيتّعرض من غير تنسيق (مش صفحة ميتة، بس شكلها مكسور).
⭐ لو الكلاس موجود في الـJS بس ⇒ افتح الـCSS وأضفه (الملف الكتير منفصل).

### ٣ — خلّي كل الحركات في الـcommit الواحد
⛔ الـcommit مقسوم = مراجعة بتت approving نص الشغل. **الـcommit الواحد = atomic.**

### ٤ — ⛔ لا دالة جوّه بلوك شرطي
```js
if (someCondition) { function doThing() {...} }   // ⛔ كود ميت
```
⭐ **الفحص:** `grep -c "doThing" <file>` ⇒ لو 1 (التعريف بس) ⇒ ميت.
السبب: بلوك شرطي ما بياخدش path التنفيذ في كتير من الحالات.

### ٥ — ⛔ `final_score` بلا clamp
كل نتيجة درجة 0-100 ⇒ **نصلّح المصدر في الـbackend**، ممنوع القصّ في العرض.

### ٦ — ⛔ تحويل الحقول ٣ طبقات
`data_egx.json` (n/p/c) → `loadEgxFile()` (s_*) → OS_DB → `vTechSignals()`
ربط غلط = كارت فاضي. ⛔ aliases: `price`≠`p` · `mcap`≠`mc` · `avgVol30`≠`av30`.
⛔ فلتر رجّع 0 = **التطبيع مش الدالة** — راجع التطبيع الأول.

### ٧ — ⛔ اختبر بالعميل الحقيقي مش بـcurl لوحده
`curl` بيعدّي والـclient بيفشل بصمت.
⭐ المتصفح الحقيقي (Playwright/chromium) هو الوحيد الحاسم — البورصة المصرية محجوبة عن curl.

### ٨ — التحقق الحيّ (قبل ما تقول «خلصت»)
- المعاينة: `https://octa-preview.ahmed3zz2020.workers.dev` (⛔ **ممنوع** النشر على `octashares.com` بدون إذن صريح)
- افتح الصفحة الجديدة على **390px** (موبايل) ⇒ العنصر ظهر؟ اتعبّى؟ البيانات وصلت؟
- `/api/health` بيرجع 200 حتى لو الـdeploy ما حصلش ⇒ **دليل النشر = `data_version` + مطابقة القيمة الحية مع `index_history.json`**
- ⛔ 530/502 = cold start مش خطأ ⇒ أعد المحاولة.

## ⛔ ممنوع

تعديل production secret (تدوير `SECRET` = كل الحسابات بتتمسح ⇒ rotate من غير migration ممنوع) · نشر على الإنتاج · نشر بيانات محفظة أو أرقام حسّاسة في GitHub (المستودعات عامة ⇒ مكانها KV + Drive) · كتابة اسم أداة ذكاء اصطناعي في الواجهة.
