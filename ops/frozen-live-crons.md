# ⛔ الكرونات الحيّة اللي اتشالت (١ نوفمبر ٢٠٢٦) — بقرار المالك

**السبب:** إيقاف كل الشغل في الخلفية نهائياً (حرق الكريديت).
**الاستعادة:** `cron_create` بنفس الإعدادات دي + `session:{mode:'sessionId', session_id:'fixed'}` + `agent_name` بنفس الاسم.

---

## ١ — gold-watchdog · `458725814567285`
- الاسم: مراقب بوت الذهب (ساعة · جلسة دايمة)
- الجدول: `0 * * * *` · TZ: Africa/Cairo
- session: `{mode:'sessionId', session_id:'fixed'}` (المتجر بيخزّن `session_id: ""` ⇒ شات خاص بالكرون بيتعمل أول مرة وبعدها بيتعاد)
- prompt:
```
مهمة خفيفة: فحص صحّة محرّك إشارة الذهب + مزامنة الحالة + تشغيل التقرير اليومي — سطر واحد فقط.

١) شغّل السكربت (هو بيعمل كل حاجة: لو المحرك حي ⇒ يزامن الحالة في KV فقط · لو ميت ⇒ يسترجع ويشغّل):
bash -lc 'set -u; REPO=/opt/gold-signal-bot; if [ ! -f "$REPO/scripts/keepalive.sh" ]; then mkdir -p /opt && git -c http.sslVerify=false clone --depth 1 "https://ahmed3zz2020-source:${GITHUB_TOKEN}@github.com/ahmed3zz2020-source/gold-signal-bot.git" "$REPO"; fi; bash "$REPO/scripts/keepalive.sh"'
٢) اقرأ الأرقام: curl -s -m 20 -H "Authorization: Bearer ${BRIDGE_TOKEN}" https://gold-engine.octashares.com/status ⇒ ts · bars.m1 · bars.m15 · warm
٣) ⭐ التقرير اليومي (مرة واحدة/يوم · الساعة ٠٥:٠٠ UTC = ٠٧:٠٠ القاهرة) — نفّذ السطر ده بالظبط:
bash -lc 'if [ "$(date -u +%H)" = "05" ]; then curl -s -m 45 "https://ezz-daily.ahmed3zz2020.workers.dev/run?send=1"; else echo "SKIP_NOT_05"; fi'
   (لو الرد فيه ok:true ⇒ daily=sent · لو SKIP_NOT_05 ⇒ daily=skipped · لو فشل ⇒ daily=fail وبلّغ السبب)
   ⛔ التقرير مبني بالكود من بيانات حيّة ⇒ متكتبش تقرير تاني ولا تبعث رسالة من عندك. ⛔ متكررش النداء لو طلع sent.
٤) ⛔ ممنوع تعديل كود · ⛔ ممنوع تيليجرام (غير نداء التقرير في الخطوة ٣) · ⛔ ممنوع كتابة في GitHub إلا لو فيه خلل حقيقي (سطر واحد في logs/YYYY-MM-DD.md على مستودع office).

اطبع بالضبط: STATUS=<OK|RESTARTED|FAIL> | m1=<رقم> | m15=<رقم> | warm=<نعم|لا> | daily=<sent|skipped|fail|n-a> | note=<كلمة واحدة>
```

---

## ٢ — EZZ-Gate · `458725804241047`
- الاسم: بوابة عز (الأسئلة المفتوحة · ٣ ساعات · جلسة دايمة)
- الجدول: `0 */3 * * *` · TZ: Africa/Cairo
- session: `{mode:'sessionId', session_id:'fixed'}`
- prompt:
```
⛔ البوابة نفسها شغّالة بالكامل بالكود (Worker) — رد فوري على «الحالة · القرارات · الذهب · التكلفة · المحتوى» من غير أي موديل. دورك هنا بس: الأسئلة المفتوحة.

الخطوات:
١) اقرأ الـinbox من Cloudflare KV:
curl -s -m 25 -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" "https://api.cloudflare.com/client/v4/accounts/74e046678adabf0706024b97b205882b/storage/kv/namespaces/5a651f83b4b249f2995f6138225ada8f/values/core/inbox"
٢) ⛔ لو مفيش أي رسالة فيها needs_llm=true ⇒ اطبع GATE_DONE 0 وخلاص (متكتبش ولا تردّ ولا تقرا).
٣) لكل رسالة needs_llm=true (نص غير معروف أو صوت):
   - اكتب ردّاً قصيراً (≤٦٠٠ حرف · سطر سطر · عربي مصري · بلا مربعات · بلا markdown · بلا أسماء أدوات ذكاء اصطناعي).
   - ⛔ ما تخترعش رقماً: لو محتاج رقم مش موجود ⇒ «لا توجد بيانات». كل رقم من السجل لازم يكون معاه مصدره.
   - ⛔ ممنوع: تنفيذ كود · إنفاق · توقيع · نشر · تعديل بوت الذهب · تعديل على مستودع بوت الذهب · أي توصية شراء/بيع.
   - لو الرسالة صوت ⇒ اكتب: «وصلتني رسالة صوتية · محتاج أتفريغها».
   - لو الرسالة طلبت تنفيذه ⇒ سجّل مهمة في core/tasks.json (id · task · owner · priority · status=open) واشرح في الرد إن المهمة اتسجّلت.
٤) ابعت الرد على تيليجرام من بوت المؤسسة عبر عامل الإرسال:
   printf '{"chat_id":"<chat_id من الرسالة>","text":"<الرد>"}' > /tmp/ezz-tg.json
   curl -s -m 25 -X POST -H "Content-Type: application/json" -H "User-Agent: Mozilla/5.0" --data @/tmp/ezz-tg.json https://ezz-gate-send.ahmed3zz2020.workers.dev/send
   ⛔ ابعت من غير parse_mode · ⛔ الرد لازم يكون {"ok":true,"message_id":N} · ⛔ UA بايثون بيرجع 403 ⇒ Mozilla/5.0
⑤) أعد كتابة core/inbox: خلّي الرسائل المعالَجة بـhandled=true وneeds_llm=false (لا تحذفها — السجل).
⑥) سطر واحد في logs/$(TZ=Africa/Cairo date +%F).md على مستودع EZZ + سطر في topics/ezz-gate.md — ⛔ بس لو اتعالجت رسالة فعلاً.
٧) اطبع: GATE_DONE <عدد الرسائل المعالَجة>
```

---

## ٣ — EZZ-Brief · `458725814567283`
- الاسم: تحليل أسبوعي (EZZ Weekly Analysis · جلسة دايمة)
- الجدول: `0 8 * * 0` · TZ: Africa/Cairo
- session: `{mode:'sessionId', session_id:'fixed'}`
- prompt:
```
مهمتك: «التحليل الأسبوعي» لمؤسسة EZZ — الأرقام + المعنى + القرار المقترح + المراجعة الصريحة. (التقرير اليومي بالأرقام مبني بالكامل بالكود وبيتبعت كل يوم ٠٧:٠٠ القاهرة ⇒ ⛔ متكتبش تقرير يومي تاني.)

١) اقرأ (كلها بـcurl مع -H "Accept: application/vnd.github.raw" — ⛔ مش raw العادي إنه كاش ٥ دقايق):
   - EZZ: logs/<أمس>.md · logs/<اليوم>.md · core/state.json · core/tasks.json · CHANGELOG.md (آخر ١٠ أسطر) · topics/*.md (آخر سطر لكل ملف) · web/state.json · web/opportunities.json · ops/TOKEN-BUDGET.md
   - office: logs/<أمس>.md
   ⭐ لو web/opportunities.json موجود ⇒ استخدمه (أدق من الـKV).

٢) اكتب «التحليل الأسبوعي» في /workspace/output/EZZ-Weekly-Analysis.md:
   - what happened in the week (بالأرقام)
   - what it means (المعنى — التفسير، مش تكرار الأرقام)
   - what needs the owner's decision (قرارات + توصية صريحة)
   - what went wrong (مراجعة صريحة: أرقام غلطت · ترتيب اتغير · وعد اتكسر)
   - what the week ahead needs (أول ٣ أولويات + مهمة واحدة)
   ⭐ سطر «درس الأسبوع»
   ⛔ كل رقم لازم يكون معاه مصدره · ⛔ ما تخترعش رقم ولا مهمة ولا موعداً · ⛔ ما تقترحش فرصة خارج core/opportunities.json.

٣) حدّث مرآة مركز القيادة (web/state.json): phase · updated · agents_active · open_decisions · resolved_decisions · opportunities_count · top_opportunity · tasks_open · tasks_blocked · gold_bot · quality_gate. (GET للـsha ثم PUT)

٤) ⭐ نسخة تيليجرام مضغوطة (≤ ٩٠٠ حرف · سطر سطر · بلا جداول): رقم الأسبوع · أهم رقم · أهم قرار مطلوب · درس الأسبوع.
   ⚠️ ⛔ ابعت من غير parse_mode · ⚠️ نظّف الرموز قبل الإرسال.

⑤) ⭐ ابعتها من بوت المؤسسة عبر عامل الإرسال:
   printf '{"chat_id":"2073907990","text":"<النسخة بعد تنظيف الرموز>"}' > /tmp/ezz-tg.json
   curl -s -m 25 -X POST -H "Content-Type: application/json" -H "User-Agent: Mozilla/5.0" --data @/tmp/ezz-tg.json https://ezz-gate-send.ahmed3zz2020.workers.dev/send
   ⚠️ ⛔ UA بايثون بيرجع 403 ⇒ Mozilla/5.0 إجباري.

⑥) سطر واحد في logs/<اليوم>.md على EZZ + سطر في topics/ezz-brief.md.

⑦) ⛔ ما تخترعش رقماً ولا مهمة ولا موعداً · ⛔ ممنوع ذكر أي اسم أداة ذكاء اصطناعي.

⑧) اطبع: WEEKLY_ANALYSIS_DONE <عدد الأولويات> | TG=<sent|skipped>
```

---

## 📌 ملاحظة: عمليات الكود (صفر توكن — مش متوقفة)
- `ezz-auto` (بوابة تيليجرام) · `ezz-daily` (التقرير اليومي) · `ezz-gate-send` (الإرسال) — دي Workers بالـAPI ⇒ **مش بتاخد كريديت** ⇒ سيبتها شغّالة.
