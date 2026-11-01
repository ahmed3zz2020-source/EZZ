---
name: ezz-daily-brief
description: Build and deliver EZZ's daily executive briefing - read the foundation sources (logs, state, tasks, opportunities) from GitHub and Cloudflare KV, write the full markdown report, update the command-center mirror, and send the compressed Telegram version from the EZZ bot. Use when asked for "التقرير اليومي", " briefing", "ملخص المؤسسة", "تقرير EZZ", "daily brief", or when running the daily EZZ-Brief cron. Not for the portfolio review (ezz-portfolio-review) or the overnight gold-bot health check.
---

# التقرير اليومي لمؤسسة EZZ

## المصادر (الأولوية بالترتيب)

1. **المرآة على GitHub** — أدق وأحدث من الـKV. اقرأ بـ`Accept: application/vnd.github.raw` (⛔ raw.githubusercontent العادي كاش ٥ دقايق).
   `logs/<أمس>.md` · `logs/<اليوم>.md` · `core/state.json` · `core/tasks.json` · `CHANGELOG.md` (آخر ١٠ أسطر) · `topics/*.md` (آخر سطر لكل ملف) · `web/state.json` · `web/opportunities.json`
2. **Cloudflare KV** (namespace `5a651f83b4b249f2995f6138225ada8f`) — احتياطي: `core/state.json` · `core/tasks.json` · `core/opportunities.json`
3. **office repo** — `logs/<أمس>.md` (عمليات OCTA وبوت الذهب)

## الخطوات

١. اقرأ كل المصادر. `web/opportunities.json` لو موجود ⇒ Opportunities منه؛ الـKV `core/opportunities.json` احتياطي.
٢. اكتب التقرير الكامل في `/workspace/output/EZZ-Daily-Briefing.md` بحسب `templates/daily-brief.md`:
   أول ٣ أولويات · ما أنجزه الوكلاء · ما يحتاج تدخل المالك · قرارات تنتظر الموافقة · أحسن فرصة · مهمة اليوم.
٣. حدّث مرآة مركز القيادة `web/state.json` (GET للـsha ثم PUT):
   `phase` · `updated` · `agents_defined` · `agents_active` · `agents_active_list` · `open_decisions` · `resolved_decisions` · `opportunities_count` · `top_opportunity` · `tasks_open` · `tasks_blocked` · `gold_bot` · `quality_gate`
٤. انسخ نسخة مضغوطة **≤ ٩٠٠ حرف** (سطر سطر · بلا جداول): أول ٣ أولويات · محتاج منك · أحسن فرصة (اسم + عائد + تكلفة + أول خطوة) · مهمة اليوم.
٥. ابعت النسخة على تيليجرام من بوت المؤسسة عبر عامل الإرسال (توكن البوت كسر، فأمان):
   ```bash
   printf '{"chat_id":"2073907990","text":"<النص بعد تنظيف الرموز>"}' > /tmp/ezz-tg.json
   curl -s -m 25 -X POST -H "Content-Type: application/json" --data @/tmp/ezz-tg.json https://ezz-gate-send.ahmed3zz2020.workers.dev/send
   ```
   ⛔ **لو بتعملها من بايثون ⇒ `User-Agent: Mozilla/5.0` إجباري.** `Python-urllib/3.11` بيرجع **403 بصمت** (نفس النص بالـcurl بيرجع 200). مش خطأ في النص ولا في التوكن.
   ⛔ **الرد لازم يكون `{"ok":true,"message_id":N}`** — لو مش كده ⇒ متعتبرش الإرسال نجح.
   ⛔ **متكررش الإرسال لتجربة** — كل محاولة بتوصّل رسالة حقيقية للمالك. لو اتبعتت بالغلط ⇒ `deleteMessage` بنفس `message_id`.
6. سطر واحد في `logs/<اليوم>.md` على EZZ + سطر في `topics/ezz-brief.md`.
7. اطبع: `DAILY_BRIEF_DONE <عدد الأولويات> | TG=<sent|skipped>`

## ⛔ قواعد صارمة

- **رسالة تيليجرام ⇒ بلا `parse_mode`.** أي `*` أو `_` أو `` ` `` بيرمي 400. نظّف الرموز قبل الإرسال.
- **JSON صالح.** أي `"` أو `\` داخل النص لازم يتحوّل لـ`\"` أو `\\`.
- **النسخة المضغوطة ≤ ٩٠٠ حرف.** اتقيس (`len(text)`) قبل الإرسال، مش تقدير.
- **ما تخترعش رقماً ولا مهمة ولا موعداً.** رقم بلا مصدر ⇒ «لا توجد بيانات».
- **ما تقترحش فرصة خارج** `core/opportunities.json` · **ما تنسخش** فرصة مرّت على EZZ-Audit.
- **ممنوع ذكر أي اسم أداة ذكاء اصطناعي** في التقرير.
- **ما تعملش** نشر · إنفاق · تنفيذ مالي · تعديل على بوت الذهب.
- **الملف الكامل** = `/workspace/output/EZZ-Daily-Briefing.md` (يتسلم للمالك) · **النسخة المضغوطة** = تيليجرام. الاتنين مش واحد.

## المرجع

`references/sources.md` — روابط ومسارات المصادر بالتفصيل وحالة كل مصدر.
