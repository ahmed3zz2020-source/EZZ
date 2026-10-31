# EZZ — عِز · الفهرس الرئيسي (EZZ_MASTER_INDEX)

**One Vision. One Organization. Intelligent Execution.**

مؤسسة رقمية ذكية تدير شغل ومال ومشروعات ومحتوى وعقود أحمد.
المرجع الكامل: [CONSTITUTION.md](CONSTITUTION.md) · البنية: [MEMORY.md](MEMORY.md) · التنفيذ: [PROTOCOL.md](PROTOCOL.md)

---

## 1) خريطة المؤسسة

| # | القسم | الملف | الوكيل المسؤول |
|---|---|---|---|
| 1 | EZZ — CEO | [CONSTITUTION.md](CONSTITUTION.md) §1 | Mavis (المدير) |
| 2 | EZZ Media | [AGENTS-REGISTRY.md](AGENTS-REGISTRY.md) | EZZ-Social-Launch · EZZ-Growth · EZZ-Visual |
| 3 | EZZ Business | [AGENTS-REGISTRY.md](AGENTS-REGISTRY.md) · [projects/](projects/) | EZZ-Business · EZZ-Contracts |
| 4 | EZZ Intelligence | [AGENTS-REGISTRY.md](AGENTS-REGISTRY.md) | EZZ-Tech · EZZ-Audit |
| 5 | EZZ Operations | [PROTOCOL.md](PROTOCOL.md) | EZZ-Operations · EZZ-Finance |

## 2) ملفات المؤسسة

```
CONSTITUTION.md      دستور المؤسسة (القواعد · الصلاحيات · المبادئ)
PROTOCOL.md          بروتوكول التنفيذ + بروتوكول الموافقة + قوالب التقارير
AGENTS-REGISTRY.md   السجل المركزي للوكلاء (الوظيفة · الصلاحيات · مؤشرات الأداء)
MEMORY.md            بنية الذاكرة المركزية (٤ نطاقات · التحديث · الاسترجاع · النسخ)
PROVIDER-ADAPTER.md  طبقة استقلال المزوّد (كيف ينتقل EZZ لمزوّد آخر)
CHANGELOG.md         سجل التغييرات (append-only)
docs/CAPABILITIES.md تقرير الإمكانيات المقيس (ما ينفع وما لا ينفع)
docs/PHASE-PLAN.md   خطة المراحل السبعة + معايير الانتقال
docs/ORG-CHART.md    الهيكل · التصعيد · نظام الرقابة
topics/              ملاحظات كل وكيل (append-only · نطاق حصر)
logs/                السجل اليومي (سطر لكل مهمة)
decisions/           سجل القرارات (كل قرار في ملف)
templates/           قوالب: موافقة · تقرير يومي · أسبوعي · شهري · مجلس · مهمة
projects/            ملف لكل مشروع (OCTA · عزيز الدين)
scripts/ezz-mem.py   أداة الذاكرة (add · log · search · backup · restore)
```

## 3) الذاكرة — ٤ نطاقات

| النطاق | المحتوى | مكان التخزين |
|---|---|---|
| **EZZ Personal** | الحياة الشخصية · الأهداف · المواعيد | KV مشفّر + Drive خاص |
| **EZZ Business** | الشركات · العقارات · العملاء · الشركاء | KV + Drive خاص |
| **EZZ Media** | شخصية عز · المحتوى · السوشيال · التسويق · المعلنون | GitHub (عام) + Drive |
| **OCTA** | المشروع التقني · المنتج · المستخدمون | مستودع `octa` + `octa-prices` |
| **EZZ Core** | الدستور · القرارات · السجلات · التقارير | GitHub (هذا المستودع) |

⭐ **القاعدة:** المستودع **عام** ⇒ لا بيانات شخصية ولا مبالغ ولا أرقام قومية ولا أسرار.
البيانات الحسّاسة = Cloudflare KV (حساب أحمد) أو Drive (خاص) — مش في GitHub.

## 4) كيف تسترجع سياق المؤسسة (٣ خطوات)

1. اقرأ `CONSTITUTION.md` ثم `PROTOCOL.md` (دقيقتان).
2. اقرأ `CHANGELOG.md` آخر ٣٠ سطر + `decisions/` + `logs/YYYY-MM-DD.md` آخر يومين.
3. راجع `topics/<agent>.md` للوكيل المسؤول + `projects/<project>.md` للمشروع.

لو `scripts/ezz-mem.py` موجود ⇒ `python3 scripts/ezz-mem.py search "<كلمة>"` بيبحث في كل الملفات دفعة واحدة.

## 5) حالة التأسيس (٣١ أكتوبر ٢٠٢٦)

| البند | الحالة |
|---|---|
| المستودع | ✅ `ahmed3zz2020-source/EZZ` (عام — التوكن `public_repo` يمنع الخاص) |
| الدستور | ✅ CONSTITUTION.md |
| سجل الوكلاء | ✅ AGENTS-REGISTRY.md |
| الذاكرة | ✅ MEMORY.md + KV `ezz-central-memory` (نُشئ واشتغلت الكتابة) |
| الأدوات | ✅ scripts/ezz-mem.py |
| مركز القيادة (ويب) | 🟡 Cloudflare Pages — المشروع اتعمل، النشر محتاج تصحيح |
| Telegram | ⛔ محتاج بوت جديد من أحمد (استقبال) |
| WhatsApp | ⛔ مفيش تكامل رسمي متاح — بديل: Telegram + بريد |
| Railway | ⛔ التوكن قراءة فقط ⇒ مفيش deploy |
| D1 / R2 | ⛔ التوكن ما فيهوش الصلاحية |

## 6) قواعد لا تُكسر (مختصر — الكامل في الدستور)

1. ما نخترعش بيانات — رقم بلا مصدر = «لا توجد بيانات».
2. لا إنفاق بلا موافقة المالك.
3. لا نشر محتوى للناس بلا الصلاحية.
4. لا أسرار في GitHub.
5. لا تحذف قراراً سابقاً بصمت — السجل append-only.
6. لا تَدّعِ إنجازاً بلا دليل.
7. لا مجاملة في تقييم الأداء.
8. لا تُخفي خطأ — اعترف وصحّح.
9. لا تكاثر الوكلاء بلا حاجة.
10. كل مهمة منتهية = سطر في السجل + سطر في topic النطاق.
