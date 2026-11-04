#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
☁️ تحويل Worker من module (export default) ⇒ service-worker style.

⭐ ليه: Cloudflare API (multipart upload) بيقرا الجزء كـ**script** ⇒ `export default` مرفوضة
   ("Uncaught SyntaxError: Unexpected token 'export'").
   الحل: نفس الـhandler بالظبط + addEventListener ⇒ سلوك مطابق.

⛔ الـbindings (KV / service / secret) بتتقرأ كـ**globals** في service-worker style
   ⇒ بنعمل object `env` من الـglobals ونمرّره للـhandler.

▶️ python3 tools/to_sw.py ops/workers/ezz-daily.js /tmp/ezz-daily.sw.js
"""
import re
import sys


def to_service_worker(src: str) -> str:
    marker = "export default {"
    i = src.index(marker)
    head, tail = src[:i], src[i:]

    obj = tail[len("export default "):].rstrip()
    assert obj.startswith("{") and obj.endswith("}"), "شكل export default غير متوقّع"

    # ⭐ الـbindings كـglobals ⇒ نبني env منهم. أسماء المتغيّرات تُحسب وقت التشغيل
    #    (typeof check) عشان متكسرش لو binding مش موجود.
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
        '\n// \u2b50\ufe0f service-worker style: نفس الـhandler بالظبط (Cloudflare API multipart \u21d2 export default ممنوعة)\n'
        'const __ezzHandler = ' + obj + ';\n\n'
        + env_tpl +
        '\naddEventListener("fetch", (event) => {\n'
        '  event.respondWith(__ezzHandler.fetch(event, __ezzEnv(), event.context));\n'
        '});\n\n'
        'addEventListener("scheduled", (event) => {\n'
        '  event.waitUntil(__ezzHandler.scheduled(event, __ezzEnv(), event.context));\n'
        '});\n'
    )
    return head + wrapper


def main():
    src_path, out_path = sys.argv[1], sys.argv[2]
    s = open(src_path, encoding="utf-8").read()
    out = to_service_worker(s)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print("✅ %s ⇒ %s (%d bytes)" % (src_path, out_path, len(out.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
