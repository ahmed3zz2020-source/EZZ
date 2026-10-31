#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 استخراج نص الراوي من سكريبت الوكيل + دمج الجزء البصري.

⭐ الهدف: ما نكتبش نفس النص مرتين (توفير كريدت + ضمان التطابق).
المصدر: EZZ-نص-أول-فيديو-ABUK.md (نص الوكيل) + visuals.json (الجزء البصري بتاعي).
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = "/workspace/output/EZZ-نص-أول-فيديو-ABUK.md"

# ⛔ تصحيح أخلاقي: الصفقة مرخصّة ومطموسة، وغير منفّذة ⇒ نصوّرها «قرار» مش «شراء تم»
FIX = [
    ("في يوم 29 أكتوبر اشتريت أول سهم في محفظة 100 ألف جنيه بتاعتنا في البورصة المصرية.\n"
     "السعر: 88.03 جنيه. الكمية: 220 سهم.",
     "في يوم 29 أكتوبر صدر أول قرار شراء في محفظة 100 ألف جنيه بتاعتنا في البورصة المصرية.\n"
     "السهم: أبو قير للأسمدة. الكمية: 220 سهم. سعر الأمر: 88.03 جنيه."),
    ("طب اشترينا كام؟", "طب الكمية إيه؟"),
    (" orient ", " "),
    ("وده اللي خلّانا نختاره", "وده اللي خلّاني نختاره"),
]


def extract_narration(path):
    s = open(path, encoding="utf-8").read()
    blocks = re.findall(r"\*\*(\d+:\d+)\s*—\s*([^*]+)\*\*\s*«(.+?)»", s, re.S)
    out = []
    for ts, name, body in blocks:
        body = re.sub(r"\s*\n\s*", " ", body).strip()
        for a, b in FIX:
            body = body.replace(a, b)
        out.append({"ts": ts, "name": name.strip(), "narration": body})
    return out


def main():
    script_path = sys.argv[1] if len(sys.argv) > 1 else SRC
    vis = json.load(open(os.path.join(ROOT, "visuals.json"), encoding="utf-8"))
    narr = extract_narration(script_path)
    if len(narr) != len(vis["scenes"]):
        print("⚠️ عدد المشاهد مختلف: النص %d · البصري %d" % (len(narr), len(vis["scenes"])))
        print("   العناوين:", [n["name"] for n in narr])
    spec = dict(vis)
    scenes = []
    for i, v in enumerate(vis["scenes"]):
        sc = dict(v)
        if i < len(narr):
            sc["narration"] = narr[i]["narration"]
            sc["ts"] = narr[i]["ts"]
            sc["name"] = narr[i]["name"]
        scenes.append(sc)
    spec["scenes"] = scenes
    out = os.path.join(ROOT, spec["id"] + ".json")
    json.dump(spec, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("✅", out, "| مشاهد:", len(scenes),
          "| أطول نص: %d حرف" % max(len(s.get("narration", "")) for s in scenes))
    for s in scenes:
        print("   %-6s %-34s %4d حرف" % (s.get("ts", ""), s.get("name", "")[:34],
                                         len(s.get("narration", ""))))


if __name__ == "__main__":
    main()
