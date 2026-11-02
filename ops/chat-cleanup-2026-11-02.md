# 🧹 تنظيف شاتات المنصّة — التقرير النهائي (٢ نوفمبر ٢٠٢٦)

## ⭐ السبب الجذري: التسمية ≠ الإزالة
حملة إعادة التسمية السابقة (~٣٠٠ شات `[cron]`) **غيّرت العنوان بس**. الشات نفسه ظلّ موجوداً في قائمة/بحث الشاتات ⇒ المالك شاف «لسه فيه حاجات كتير».
**الدرس:** لازم عملية أرشفة/حذف فعلية عبر الـAPI.

## الأرقام
| المرحلة | العدد |
|---|---|
| إجمالي الجلسات قبل | **661** |
| unarchived قبل | **595** |
| محذوف (delete حقيقي) | **371** (335 زهيمة مُعلَّمة + 36 leftovers أتمتة) |
| مُؤرشف (hidden عن القائمة النشطة) | **110** (فروع sub-agent) |
| **unarchived بعد (القائمة النشطة)** | **116** (= شاتات المالك الحقيقية + 5 شاتات الوكلاء) |
| **archived بعد** | **176** (62 فرع قديم بعناوين حقيقية + 4 محمية + 110 من الأتمتة) |
| **الإجمالي بعد** | **292** |
| markers زهيمة في القائمة النشطة | **0** ✅ |

**المحمية (باقية):** `451540640772192` · `451186582618233` · `450478957814049` · `458154202509460`

## الـAPI المستخدمة (archon-server مباشر — مش MCP)
- `POST /api/v1/sessions/list`  body `{"page":{"limit":100,"cursor":"<next_cursor>"},"archive_filter":1|2}`
  - `archive_filter`: **1=Unarchived · 2=Archived** · مفيش All (الافتراضي Unarchived)
  - `page` = object مش رقم · الترقيم بـcursor لحد ما `has_more=false`
- `POST /api/v1/sessions/get`    body `{"session_id":"<string>"}`
- `POST /api/v1/sessions/update` body `{"session_id":"<string>","archived":true}` أو `{"title":"..."}`
- `POST /api/v1/sessions/delete` body `{"session_id":"<string>"}` ⇒ 200 `{}` ⇒ الجلسة بتختفي نهائياً
- ⛔ كل الـids **strings** (number ⇒ 400 Mismatch type) · الـSK من tcpdump على منفذ 8080 (بيتجدّد) · الهوية من 403 بتاع `control_harness`.

## ⭐ مُصنِّف تلقائي: شات أداة vs شات مستخدم
الجلسات اللي عملها cron/أداة **ما فيها** `device_platform` ولا `query` في `extra_data_json`؛ شاتات المستخدم Typed فيها الاتنين.
⇒ classifier: `("device_platform" in ex) or ('"query"' in ex)` ⇒ شات مستخدم (لا يُحذف تلقائياً).
ده اللي خلّى الحذف يبقى آمن: **371 جلسة متحذفة، صفر شات مستخدم اتمّس.**

## ⛔ طبقة الأدوات (MCP) مينفعش تعمل ده
- `session_update` بـ`session_id` رقمي ⇒ «/session_id: Expected string» (تحويل نوع عشوائي، ≈٢ من ٢٠ نجاح).
- `session_update` بـ`archived:true` ⇒ «/archived: Expected boolean» ⇒ **البوليان بيتحول لنص دايماً** ⇒ الأرشفة/الحذف عبر الأداة **مستحيل**.
- `session_list` العام = payload ضخم (200+ شات) ⇒ متعملهوش إلا لضرورة.
⇒ الحل الوحيد = **archon API مباشر من bash** (الوصلة أعلاه).
