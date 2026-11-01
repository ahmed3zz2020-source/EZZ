# مصادر التقرير اليومي — EZZ

## GitHub (ahmed3zz2020-source/EZZ) — الأساس

القراءة عبر GitHub API (الكاش ٥ دقايق على raw العادي ⇒ استخدم الـAPI):
```bash
curl -s -m 25 -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.raw" \
  "https://api.github.com/repos/ahmed3zz2020-source/EZZ/contents/<PATH>?ref=main"
```

| المسار | المحتوى | الأولوية |
|---|---|---|
| `logs/<YYYY-MM-DD>.md` | سجل اليوم سطر سطر | ⭐ أول |
| `logs/<أمس>.md` | سياق أمس | ⭐ أول |
| `core/state.json` | حالة المؤسسة (phase · decisions · agents) | ⭐ أول |
| `core/tasks.json` | المهام (open / blocked / done) | ⭐ أول |
| `web/state.json` | مرآة مركز القيادة (أحدث من KV) | ⭐ أول |
| `web/opportunities.json` | مرآة رادار الفرص (أدق من KV) | ⭐ أول |
| `CHANGELOG.md` | آخر ١٠ أسطر = آخر تغيّرات | ⭐ ثاني |
| `topics/*.md` | آخر سطر لكل ملف = آخر حالة | ⭐ ثاني |
| `templates/daily-brief.md` | قالب التقرير | ⭐ أول (قبل الكتابة) |

مستودع `office`:
```bash
curl -s -m 25 -H "Authorization: Bearer ${GITHUB_TOKEN}" -H "Accept: application/vnd.github.raw" \
  "https://api.github.com/repos/ahmed3zz2020-source/office/contents/logs/<YYYY-MM-DD>.md?ref=main"
```

## Cloudflare KV — احتياطي

حساب `74e046678adabf0706024b97b205882b` · namespace `ezz-central-memory` = `5a651f83b4b249f2995f6138225ada8f`

```bash
curl -s -m 25 -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  "https://api.cloudflare.com/client/v4/accounts/74e046678adabf0706024b97b205882b/storage/kv/namespaces/5a651f83b4b249f2995f6138225ada8f/values/core/state.json"
```

مفاتيح: `core/state.json` · `core/tasks.json` · `core/agents.json` · `core/inbox` · `core/opportunities.json` · `core/opportunities.rev2.json` · `core/gate_secret`

## مرآة مركز القيادة

`web/state.json` ⇒ `https://ezz-command.ahmed3zz2020.workers.dev/` (Worker · 200)

## تيليجرام

- بوت المؤسسة: `@EzzDeskBot` (id `8756131456`) — `OFFICE_TELEGRAM_TOKEN`
- الإرسال: `https://ezz-gate-send.ahmed3zz2020.workers.dev/send` — `{"chat_id":"2073907990","text":"..."}`
- chat_id الثابت للمؤسسة: `2073907990`
- ⛔ البوت الذهبي (`TELEGRAM_TOKEN`) محجوز لمحرك الذهب — لا تستخدمه للاستقبال.

## حالة المصادر (١ نوفمبر ٢٠٢٦)

- ✅ `web/state.json` موجود في المستودع (commit `1a1788ec`)
- ✅ `core/tasks.json` و `core/state.json` موجودان في الـKV (لأপে لم يُنشأ نسخة GitHub منهما — المصدر هو الـKV)
- ⚠️ `core/tasks.json` غير موجود على GitHub ⇒ 404 عند القراءة ⇒ الـKV هو المصدر الوحيد للمهام.
