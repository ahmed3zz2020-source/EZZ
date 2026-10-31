#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎙️ توليد الصوت للمشاهد — TTS مُجمَّع (١٠ مشاهد في نداء واحد).

الاستخدام: python3 tts.py scenes.json
يبني: build/<id>/audio.mp3 + build/<id>/durations.json
"""
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
VOICE = "Arabic_FriendlyGuy"
SPEED = 0.97


def sh(cmd):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True)
    return r.stdout


def call_batch(items):
    """items: list of dicts {text, output_file}"""
    args = {"requests": [dict(text=it["text"], voice_id=VOICE, speed=SPEED,
                              output_file=it["output_file"]) for it in items]}
    af = "/tmp/tts_args.json"
    with open(af, "w", encoding="utf-8") as f:
        json.dump(args, f, ensure_ascii=False)
    out = sh("mcode-tools connector call connector__matrix__batch_text_to_audio --args-file %s" % af)
    try:
        return json.loads(out)
    except Exception:
        print(out[:800])
        raise RuntimeError("رد TTS غير مفهوم")


def asset_url(node_id):
    out = sh("mcode-tools get_asset_url %s" % node_id)
    return json.loads(out).get("download_url")


def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    base = os.path.join(ROOT, "build", spec["id"])
    os.makedirs(base, exist_ok=True)
    scenes = spec["scenes"]
    items = []
    for i, sc in enumerate(scenes):
        n = i + 1
        t = sc["narration"]
        items.append({"text": t, "output_file": "v%02d.mp3" % n, "idx": n})
    node_map = {}
    for s in range(0, len(items), 10):
        chunk = items[s:s + 10]
        res = call_batch(chunk)
        ok = res.get("success_items") or []
        for it in res.get("success_items") or []:
            name = it.get("file_name") or ""
            node_map[name] = it.get("node_id")
        if not ok:
            print("❌ فشل:", json.dumps(res, ensure_ascii=False)[:400])
            return 1
        print("  🔊 دفعة %d-%d اتولّدت" % (s + 1, s + len(chunk)))
    durs = {}
    for it in items:
        # node_id لكل ملف: نطابق بالترتيب (success_items بنفس ترتيب الطلب)
        idx = it["idx"]
        nid = None
        for name, n in node_map.items():
            if name == it["output_file"]:
                nid = n
                break
        if nid is None:
            # احتياطي: رتّبهم بالتتابع
            allv = list(node_map.values())
            nid = allv[idx - 1] if idx - 1 < len(allv) else None
        if not nid:
            print("  ❌ مفيش node_id ل", it["output_file"])
            continue
        url = asset_url(nid)
        p = os.path.join(base, it["output_file"])
        with urllib.request.urlopen(url, timeout=120) as r, open(p, "wb") as f:
            f.write(r.read())
        durs[str(idx)] = round(dur(p), 3)
        print("  ✅ %s  %.2fs" % (it["output_file"], durs[str(idx)]))
    json.dump(durs, open(os.path.join(base, "durations.json"), "w"), indent=1)
    # دمج الصوت
    files = ["%s/scene%02d.mp3" % (base, i) for i in range(1, len(scenes) + 1)]
    files = [f.replace("scene", "v") for f in files]
    lst = os.path.join(base, "audio_list.txt")
    with open(lst, "w") as f:
        for x in files:
            f.write("file '%s'\n" % x)
    sh("ffmpeg -y -v error -f concat -safe 0 -i %s -c:a libmp3lame -q:a 4 %s/audio.mp3" % (lst, base))
    print("✅ الصوت:", os.path.join(base, "audio.mp3"))


if __name__ == "__main__":
    sys.exit(main())
