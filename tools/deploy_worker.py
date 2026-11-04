#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
☁️ نشر Worker على Cloudflare — multipart مع الـmetadata الكامل.

⛔ **الرفع بيمسح الـbindings لو الـmetadata ناقص** ⇒ الـmetadata مبني من
   `GET /workers/scripts/<name>/settings` (يتضمّن السر بدون قيمته) + main_module.

▶️ python3 tools/deploy_worker.py ezz-daily ops/workers/ezz-daily.js
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

CF_ACCOUNT = "74e046678adabf0706024b97b205882b"
API = "https://api.cloudflare.com/client/v4"


def api(method, path, body=None, raw=False, ctype=None):
    tok = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    data = body
    headers = {"Authorization": "Bearer %s" % tok, "User-Agent": "Mozilla/5.0"}
    if body is not None and not raw:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=90) as r:
        payload = r.read().decode("utf-8")
        if raw:
            return r.status, payload
        return r.status, json.loads(payload)


def to_service_worker(src: str) -> str:
    """
    ⭐ Cloudflare API (multipart) بيقرا الجزء كـ**script** ⇒ `export default` مرفوضة.
    ⇒ نحوّل لـservice-worker style: نفس الـhandler + addEventListener (سلوك مطابق).
    والـbindings بتتقرا كـglobals ⇒ نبني `env` منهم.
    """
    marker = "export default {"
    if marker not in src:
        return src  # أصلاً service-worker style
    i = src.index(marker)
    head, tail = src[:i], src[i:]
    obj = tail[len("export default "):].rstrip()
    if not (obj.startswith("{") and obj.endswith("}")):
        raise ValueError("شكل export default غير متوقّع")
    env_tpl = (
        'function __ezzEnv() {\n'
        '  const e = {};\n'
        '  if (typeof M !== "undefined") e.M = M;\n'
        '  if (typeof P !== "undefined") e.P = P;\n'
        '  if (typeof GATE_BOT_TOKEN !== "undefined") e.GATE_BOT_TOKEN = GATE_BOT_TOKEN;\n'
        '  if (typeof SEND !== "undefined") e.SEND = SEND;\n'
        '  if (typeof DAILY !== "undefined") e.DAILY = DAILY;\n'
        '  return e;\n'
        '}\n'
    )
    wrapper = (
        '\n// ⭐ service-worker style: نفس الـhandler بالظبط (multipart API ⇐ export default ممنوعة)\n'
        'const __ezzHandler = ' + obj + ';\n\n' + env_tpl +
        '\naddEventListener("fetch", (event) => {\n'
        '  event.respondWith(__ezzHandler.fetch(event, __ezzEnv(), event.context));\n'
        '});\n\n'
        'addEventListener("scheduled", (event) => {\n'
        '  event.waitUntil(__ezzHandler.scheduled(event, __ezzEnv(), event.context));\n'
        '});\n'
    )
    return head + wrapper


def build_multipart(meta, filename, script_text):
    """
    multipart/form-data:
      part 1 — metadata (application/json) فيه bindings + main_module
      part 2 — الكود بـContent-Type: **application/javascript+module**
    ⛔ السر لازم يتمرّر بنصّه الصريح ("text") وإلا رفض (10021).
    ⭐ الـContent-Type للجزء لازم يكون `+module` وإلا Cloudflare بيقرا الكود كـscript
       ⇒ "Main module must be an ES module" (أو "Unexpected token 'export'").
    """
    b = "----ezzboundary" + uuid.uuid4().hex
    out = []
    out.append(("--" + b + "\r\n"
                'Content-Disposition: form-data; name="metadata"\r\n'
                "Content-Type: application/json\r\n\r\n").encode("utf-8"))
    out.append(json.dumps(meta, ensure_ascii=False).encode("utf-8"))
    out.append(("\r\n--" + b + "\r\n"
                'Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                "Content-Type: application/javascript+module\r\n\r\n" % (filename, filename)).encode("utf-8"))
    out.append(script_text.encode("utf-8"))
    out.append(("\r\n--" + b + "--\r\n").encode("utf-8"))
    return b"".join(out), "multipart/form-data; boundary=" + b


def main():
    if len(sys.argv) < 3:
        print("الاستخدام: python3 tools/deploy_worker.py <name> <script.js>")
        return 2
    name, path = sys.argv[1], sys.argv[2]
    script = open(path, encoding="utf-8").read()  # ESM (export default) — الـ+module content type بيشتغل

    # ١) اجلب الـbindings الحالية (بدون قيم السرّ)
    st, s = api("GET", "/accounts/%s/workers/scripts/%s/settings" % (CF_ACCOUNT, name))
    bindings = (s.get("result") or {}).get("bindings") or []
    if not bindings:
        print("❌ مفيش bindings — الرفع هيكسر الـworker. توقّف.")
        return 2

    # ١ب) السر: لازم يتمرّر بنصّه الصريح
    SECRET_ENV = {"GATE_BOT_TOKEN": "TELEGRAM_BOT_TOKEN"}
    up = []
    for b in bindings:
        if b.get("type") == "secret_text":
            env = SECRET_ENV.get(b["name"])
            val = os.environ.get(env, "").strip() if env else ""
            if not val:
                print("❌ مفيش قيمة للسر %s (المتوقّع $%s في البيئة). توقّف." % (b["name"], env))
                return 2
            up.append({"name": b["name"], "type": "secret_text", "text": val})
        else:
            up.append(b)

    # ٢) metadata + multipart
    meta = {"main_module": os.path.basename(path), "bindings": up,
            "compatibility_date": "2024-09-23", "compatibility_flags": [], "usage_model": "standard"}
    body, ctype = build_multipart(meta, os.path.basename(path), script)

    endpoint = "/accounts/%s/workers/services/%s/environments/production/content" % (CF_ACCOUNT, name)
    try:
        st, resp = api("PUT", endpoint, body=body, raw=True, ctype=ctype)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        print("⬆️  %s ⇒ HTTP %s" % (name, e.code))
        try:
            print("   ", json.loads(detail)["errors"][0]["message"][:400])
        except Exception:
            print("   ", detail[:400])
        return 1
    print("⬆️  %s ⇒ HTTP %s" % (name, st))
    if st not in (200, 201):
        print(resp[:1500])
        return 1
    try:
        j = json.loads(resp)
        print("   success:", j.get("success"), "errors:", j.get("errors"))
        if not j.get("success"):
            return 1
    except Exception:
        print("   (رد غير JSON — الـHTTP 200 يعني نجاح)")

    # ٣) تأكيد الـbindings لسا موجودة بعد الرفع
    st, s2 = api("GET", "/accounts/%s/workers/scripts/%s/settings" % (CF_ACCOUNT, name))
    after = (s2.get("result") or {}).get("bindings") or []
    before_names = sorted(b.get("name") for b in bindings)
    after_names = sorted(b.get("name") for b in after)
    print("   bindings قبل:", before_names)
    print("   bindings بعد :", after_names)
    if before_names != after_names:
        print("❌ الـbindings اتغيّرت — فيه مشكلة. لازم ترفع تاني بالـmetadata الصح.")
        return 1
    print("✅ الـbindings سليمة")
    return 0


if __name__ == "__main__":
    sys.exit(main())
