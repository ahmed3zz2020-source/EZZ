#!/usr/bin/env python3
"""
ezz-mem.py — أداة الذاكرة المركزية لمؤسسة EZZ
المصدر الرسمي: MEMORY.md · Constitution §6

الأوامر:
  context                 ملخص سياق المؤسسة
  search <كلمة>          بحث في المستودع + KV
  log <مهمة> <وكيل> <حالة> <خطوة>   سطر في السجل اليومي
  topic <agent> <سطر>    سطر في topic وكيل
  decision --id D-0001 --title ".." --status approved --summary ".."
  agent --id EZZ-X --dept ".." --role ".."
  kv get <key> | kv set <key> <file> | kv list
  enc <in> <out> | dec <in> <out>
  export <out.json>       تصدير كل الذاكرة
  restore-test            اختبار استعادة آخر نسخة
  doctor                  فحص جاهزية البنية

⛔ لا تضع أسراراً في أي ملف تكتبه هنا.
"""
import base64, hashlib, json, os, subprocess, sys, datetime, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "ahmed3zz2020-source/EZZ"
BRANCH = "main"
ACC = "74e046678adabf0706024b97b205882b"
NS = "5a651f83b4b249f2995f6138225ada8f"
API_CF = f"https://api.cloudflare.com/client/v4/accounts/{ACC}/storage/kv/namespaces/{NS}/values/"
API_GH = f"https://api.github.com/repos/{REPO}/contents/"

def today():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")

def gh(path):
    tok = os.environ.get("GITHUB_TOKEN")
    r = urllib.request.Request(API_GH + path + "?ref=" + BRANCH)
    r.add_header("Authorization", "Bearer " + tok)
    r.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            d = json.load(resp)
        return base64.b64decode(d["content"]).decode("utf-8", "replace"), d["sha"]
    except Exception:
        return None, None

def gh_write(path, content, msg):
    tok = os.environ.get("GITHUB_TOKEN")
    sha = gh(path)[1]
    body = {"message": msg, "content": base64.b64encode(content.encode()).decode(), "branch": BRANCH}
    if sha:
        body["sha"] = sha
    r = urllib.request.Request(API_GH + path, data=json.dumps(body).encode(), method="PUT")
    r.add_header("Authorization", "Bearer " + tok)
    r.add_header("Content-Type", "application/json")
    r.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(r, timeout=40) as resp:
        return resp.status

def append_line(path, line):
    cur, _ = gh(path)
    cur = (cur or "").rstrip("\n") + "\n"
    return gh_write(path, cur + line + "\n", f"chore: append {path}")

def kv_get(key):
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not tok:
        return None
    r = urllib.request.Request(API_CF + key)
    r.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception:
        return None

def kv_set(key, data):
    tok = os.environ.get("CLOUDFLARE_API_TOKEN")
    r = urllib.request.Request(API_CF + key, data=data.encode(), method="PUT")
    r.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(r, timeout=40) as resp:
        return resp.status

def cmd_context():
    print("=== EZZ CONTEXT ===")
    for p in ["CONSTITUTION.md", "PROTOCOL.md", "AGENTS-REGISTRY.md", "CHANGELOG.md"]:
        c, _ = gh(p)
        if c:
            lines = [l for l in c.splitlines() if l.strip()]
            print(f"\n--- {p} ({len(lines)} سطر) ---")
            for l in lines[:12]:
                print("  " + l[:130])

def cmd_search(word):
    print(f"=== بحث: {word} ===")
    out = subprocess.run(["grep", "-rIn", "--include=*.md", "--include=*.json", word, ROOT],
                         capture_output=True, text=True).stdout
    print(out[:6000] or "  (لا نتائج في المستودع)")
    for k in ["core/state.json", "core/tasks.json", "core/opportunities.json"]:
        v = kv_get(k)
        if v and word in v:
            print(f"  [KV] {k}: {v[:400]}")

def cmd_log(task, agent, state, nxt):
    path = f"logs/{today()}.md"
    line = f"| {task} | {agent} | {state} | {nxt} | {today()} |"
    print(append_line(path, line), "->", path)

def cmd_topic(agent, line):
    path = f"topics/{agent}.md"
    print(append_line(path, f"- {today()} — {line}"), "->", path)

def cmd_decision(id, title, status, summary):
    path = f"decisions/{id}.md"
    body = f"""# {id} — {title}

- **التاريخ:** {today()}
- **الحالة:** {status}
- **صاحب القرار:** المالك
- **الإعداد:** EZZ-CEO
- **القرار:** {summary}
- **السبب:** (يُملأ)
- **الأثر:** (يُملأ)

⭐ المصدر: decisions/{id}.md
"""
    print(gh_write(path, body, f"docs: decision {id} — {title}"), "->", path)

def cmd_agent(id, dept, role):
    print("⛔ إضافة وكيل = تعديل في AGENTS-REGISTRY.md + topics/" + id + ".md + CHANGELOG (يدوي 또는 CEO)")
    print(f"   Agent: {id} |Dept: {dept} | Role: {role}")

def cmd_kv(op, *args):
    if op == "get":
        print(kv_get(args[0]) or "(مفيش)")
    elif op == "set":
        print(kv_set(args[0], open(args[1]).read()))
    elif op == "list":
        tok = os.environ.get("CLOUDFLARE_API_TOKEN")
        url = f"https://api.cloudflare.com/client/v4/accounts/{ACC}/storage/kv/namespaces/{NS}/keys"
        r = urllib.request.Request(url)
        r.add_header("Authorization", "Bearer " + tok)
        with urllib.request.urlopen(r, timeout=30) as resp:
            print(json.dumps(json.load(resp).get("result"), indent=2, ensure_ascii=False))

def cmd_enc(inp, outp):
    from cryptography.fernet import Fernet
    key = os.environ.get("EZZ_FERNET_KEY")
    if not key:
        print("⛔ EZZ_FERNET_KEY غير موجود في البيئة — ولّد مفتاحاً مرة واحدة وخزّنه خارج المستودع")
        return
    f = Fernet(key.encode())
    data = open(inp, "rb").read()
    open(outp, "wb").write(f.encrypt(data))
    print(f"✔ مشفَّر → {outp}  ({len(data)} بايت)")

def cmd_dec(inp, outp):
    from cryptography.fernet import Fernet
    key = os.environ.get("EZZ_FERNET_KEY")
    if not key:
        print("⛔ EZZ_FERNET_KEY غير موجود")
        return
    f = Fernet(key.encode())
    open(outp, "wb").write(f.decrypt(open(inp, "rb").read()))
    print(f"✔ مفكوك → {outp}")

def cmd_export(out):
    data = {"exported": today(), "repo": REPO, "files": {}}
    for dirpath, _, files in os.walk(ROOT):
        if ".git" in dirpath:
            continue
        for fn in files:
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, ROOT)
            if rel.endswith((".md", ".json", ".yaml", ".yml")):
                try:
                    data["files"][rel] = open(p, encoding="utf-8").read()
                except Exception:
                    pass
    for k in ["core/state.json", "core/tasks.json", "core/opportunities.json", "core/agents.json"]:
        v = kv_get(k)
        if v:
            data["files"]["kv:" + k] = v
    open(out, "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"✔ صدَّر {len(data['files'])} عنصر → {out}")

def cmd_restore_test():
    backups = os.path.join(ROOT, "backups")
    if not os.path.isdir(backups):
        print("⚠️ لا يوجد مجلد backups بعد — نفّذ: mkdir -p backups/kv")
        return
    snaps = sorted(f for f in os.listdir(os.path.join(backups, "kv"))) if os.path.isdir(os.path.join(backups, "kv")) else []
    if not snaps:
        print("⚠️ لا توجد نسخ بعد")
        return
    last = os.path.join(backups, "kv", snaps[-1])
    digest = hashlib.sha256(open(last, "rb").read()).hexdigest()[:16]
    print(f"✔ آخر نسخة: {last} · بصمة {digest} · الحجم {os.path.getsize(last)} بايت")
    print("  (الفحص اليدوي: فكّ التشفير وقارن مع core/state.json)")

def cmd_doctor():
    print("=== EZZ DOCTOR ===")
    tok = os.environ.get("GITHUB_TOKEN")
    print("GITHUB_TOKEN:", "متاح" if tok else "⛔ غير متاح")
    print("CLOUDFLARE_API_TOKEN:", "متاح" if os.environ.get("CLOUDFLARE_API_TOKEN") else "⛔ غير متاح")
    for p in ["CONSTITUTION.md", "PROTOCOL.md", "AGENTS-REGISTRY.md", "MEMORY.md", "CHANGELOG.md"]:
        c, _ = gh(p)
        print(f"  {p}: {'✔' if c else '⛔ ناقص'}")
    print("  KV core/state.json:", "✔" if kv_get("core/state.json") else "— (لم يُكتب بعد)")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    a = sys.argv[2:]
    if cmd == "context": cmd_context()
    elif cmd == "search": cmd_search(a[0] if a else "")
    elif cmd == "log": cmd_log(*(a + ["", "", "", ""])[:4])
    elif cmd == "topic": cmd_topic(a[0] if a else "", a[1] if len(a) > 1 else "")
    elif cmd == "decision": cmd_decision(*(a + ["", "", ""])[:4])
    elif cmd == "agent": cmd_agent(*(a + ["", ""])[:3])
    elif cmd == "kv": cmd_kv(*a)
    elif cmd == "enc": cmd_enc(a[0], a[1])
    elif cmd == "dec": cmd_dec(a[0], a[1])
    elif cmd == "export": cmd_export(a[0] if a else "export.json")
    elif cmd == "restore-test": cmd_restore_test()
    elif cmd == "doctor": cmd_doctor()
    else: print(__doc__)

if __name__ == "__main__":
    main()
