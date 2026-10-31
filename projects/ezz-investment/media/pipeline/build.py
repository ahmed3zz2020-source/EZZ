#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 خط إنتاج فيديو عربي (مشاهد + صوت + مونتاج) — بأقل كريدات ممكنة.

الفكرة: HTML/CSS → صورة عبر Chromium → ffmpeg. مفيش توليد صور بالذكاء الاصطناعي
(مكلف + مش ضروري) ولا مونتاج على جهاز المستخدم.

الاستخدام:
  python3 build.py scenes.json          # يبني المشاهد + الصوت + الفيديو
  python3 build.py scenes.json --only-frames   # المشاهد بس (بلا صوت)
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FORCE = os.environ.get("FORCE_BUILD") == "1"
CHROME = "/root/.cache/ms-playwright/chromium-1243/chrome-linux/chrome"
FONTS = "/usr/share/fonts/truetype/ezz"


def sh(cmd, **kw):
    r = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print("❌", " ".join(cmd) if isinstance(cmd, list) else cmd)
        print((r.stderr or "")[:600])
    return r.stdout


# ─────────────────────────────── HTML ───────────────────────────────
CSS = """
@import url('file://%(fonts)s/Cairo-Regular.ttf');
* { margin:0; padding:0; box-sizing:border-box; }
html,body { width:%(W)dpx; height:%(H)dpx; overflow:hidden; }
body {
  display:flex; flex-direction:column; justify-content:center;
  background:
    radial-gradient(1200px 700px at 85%% -10%%, #1B3A5C 0%%, transparent 60%%),
    radial-gradient(900px 600px at 5%% 110%%, #0E3B36 0%%, transparent 55%%),
    linear-gradient(160deg, #071120 0%%, #0B1B2E 55%%, #0A1726 100%%);
  font-family:'Cairo','Tajawal',sans-serif; color:#EAF2FA; direction:rtl;
  padding:%(pad)dpx;
}
.foot { position:absolute; bottom:%(pad2)dpx; right:%(pad2)dpx; left:%(pad2)dpx;
  display:flex; justify-content:space-between; align-items:center;
  font-size:%(fs)dpx; color:#7FA3C4; letter-spacing:.3px; }
.mark { color:#F2C14E; font-weight:700; }
.rule { position:absolute; top:0; right:0; width:%(bar)dpx; height:6px;
  background:linear-gradient(90deg,#F2C14E,#3FBF9F); }
.kicker { font-size:%(k)dpx; color:#3FBF9F; font-weight:700; margin-bottom:%(gap)dpx; }
h1 { font-size:%(h1)dpx; line-height:1.28; font-weight:800; letter-spacing:-.4px; }
h1 .hl { color:#F2C14E; }
p.lead { font-size:%(lead)dpx; color:#BBD2E8; line-height:1.6; margin-top:%(gap)dpx; }
.cards { display:flex; gap:%(gap)dpx; margin-top:%(gap)dpx; flex-wrap:wrap; }
.card { flex:1 1 0; background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.10);
  border-radius:%(rad)dpx; padding:%(cp)dpx; }
.card .v { font-size:%(cv)dpx; font-weight:800; color:#F2C14E; }
.card .v.up { color:#3FBF9F; } .card .v.dn { color:#E5654B; }
.card .k { font-size:%(ck)dpx; color:#9FBBD4; margin-top:%(gap2)dpx; line-height:1.45; }
ul.pts { list-style:none; margin-top:%(gap)dpx; }
ul.pts li { font-size:%(lead)dpx; color:#D6E6F5; line-height:1.75; padding-right:%(bul)dpx; position:relative; }
ul.pts li:before { content:""; position:absolute; right:0; top:%(bl)dpx; width:12px; height:12px;
  border-radius:3px; background:#3FBF9F; }
ul.pts li.bad:before { background:#E5654B; }
.ladder { margin-top:%(gap)dpx; }
.rung { display:flex; align-items:center; gap:%(gap)dpx; margin-bottom:%(gap2)dpx; }
.rung .lbl { width:%(lw)dpx; font-size:%(ck)dpx; color:#9FBBD4; }
.rung .bar { flex:1; height:%(rh)dpx; border-radius:%(rad)dpx; position:relative; }
.rung .px { position:absolute; left:%(gap)dpx; top:50%%; transform:translateY(-50%%);
  font-size:%(ck)dpx; font-weight:700; color:#EAF2FA; }
.big { font-size:%(huge)dpx; font-weight:800; color:#F2C14E; }
.q { font-size:%(qh)dpx; line-height:1.5; font-weight:700; }
.qsmall { font-size:%(lead)dpx; color:#9FBBD4; margin-top:%(gap)dpx; }
.badge { display:inline-block; padding:%(bp)dpx %(bpx)dpx; border-radius:999px;
  background:rgba(63,191,159,.14); border:1px solid rgba(63,191,159,.4);
  color:#3FBF9F; font-size:%(ck)dpx; font-weight:700; }
"""


def esc(s):
    """⛔ HTML-escape + تمييز النصوص بـ*نص* (بيطلع ذهبي)."""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    parts = s.split("*")
    out = []
    for i, part in enumerate(parts):
        out.append('<span class="hl">%s</span>' % part if i % 2 == 1 else part)
    return "".join(out).replace("\n", "<br>")


def build_html(sc, W, H):
    t = sc.get("type", "bullets")
    # ⭐ مقاس الخط: العرضي (16:9) من الارتفاع · الرأسي (9:16) من العرض×1.45
    S = H if W >= H else W * 1.45
    pad = int(W * 0.075) if W >= H else int(W * 0.07)
    gap = int(S * 0.028)
    fs = int(S * 0.021)
    body = []
    if sc.get("kicker"):
        body.append('<div class="kicker">%s</div>' % esc(sc["kicker"]))
    if t == "hero":
        body.append('<h1>%s</h1>' % esc(sc.get("h", "")))
        if sc.get("lead"):
            body.append('<p class="lead">%s</p>' % esc(sc["lead"]))
    elif t == "stats":
        body.append('<h1 style="font-size:%dpx">%s</h1>' % (int(S * 0.052), esc(sc.get("h", ""))))
        cards = []
        for c in sc.get("cards", []):
            cls = c.get("tone", "")
            cards.append('<div class="card"><div class="v %s">%s</div><div class="k">%s</div></div>'
                         % (cls, esc(c["v"]), esc(c["k"])))
        body.append('<div class="cards">%s</div>' % "".join(cards))
        if sc.get("lead"):
            body.append('<p class="lead">%s</p>' % esc(sc["lead"]))
    elif t == "ladder":
        body.append('<h1 style="font-size:%dpx">%s</h1>' % (int(S * 0.052), esc(sc.get("h", ""))))
        rungs = []
        maxv = max([float(r["v"]) for r in sc.get("rungs", [])] or [1])
        minv = min([float(r["v"]) for r in sc.get("rungs", [])] or [0])
        span = max(1e-9, maxv - minv)
        for r in sc.get("rungs", []):
            w = 20 + 80 * (float(r["v"]) - minv) / span
            color = r.get("color", "#3FBF9F")
            rungs.append('<div class="rung"><div class="lbl">%s</div>'
                         '<div class="bar" style="width:%.1f%%;background:%s"></div>'
                         '<div class="px">%s</div></div>'
                         % (esc(r["k"]), w, color, esc(r["px"])))
        body.append('<div class="ladder">%s</div>' % "".join(rungs))
        if sc.get("lead"):
            body.append('<p class="lead">%s</p>' % esc(sc["lead"]))
    elif t == "quote":
        body.append('<div class="badge">%s</div>' % esc(sc.get("kicker", "تسجيل")))
        body.append('<div class="q" style="margin-top:%dpx">%s</div>' % (gap, esc(sc.get("q", ""))))
        if sc.get("lead"):
            body.append('<div class="qsmall">%s</div>' % esc(sc["lead"]))
    elif t == "end":
        body.append('<h1 style="font-size:%dpx">%s</h1>' % (int(S * 0.058), esc(sc.get("h", ""))))
        if sc.get("lead"):
            body.append('<p class="lead">%s</p>' % esc(sc["lead"]))
        if sc.get("cards"):
            cards = ['<div class="card"><div class="v %s">%s</div><div class="k">%s</div></div>'
                     % (c.get("tone", ""), esc(c["v"]), esc(c["k"])) for c in sc["cards"]]
            body.append('<div class="cards">%s</div>' % "".join(cards))
    else:  # bullets
        body.append('<h1 style="font-size:%dpx">%s</h1>' % (int(S * 0.05), esc(sc.get("h", ""))))
        items = []
        for p in sc.get("pts", []):
            bad = " bad" if p.startswith("!") else ""
            items.append('<li class="%s">%s</li>' % (bad.strip(), esc(p.lstrip("! "))))
        body.append('<ul class="pts">%s</ul>' % "".join(items))
        if sc.get("lead"):
            body.append('<p class="lead">%s</p>' % esc(sc["lead"]))

    prog = ""
    if sc.get("n") and sc.get("total"):
        pct = int(100 * sc["n"] / float(sc["total"]))
        prog = ('<div style="position:absolute;bottom:0;left:0;right:0;height:6px;'
                'background:rgba(255,255,255,.08)">'
                '<div style="position:absolute;bottom:0;right:0;width:%d%%;height:100%%;'
                'background:linear-gradient(270deg,#F2C14E,#3FBF9F)"></div></div>') % pct

    css = CSS % {
        "fonts": FONTS, "W": W, "H": H, "pad": pad, "pad2": int(W * 0.05),
        "fs": fs, "bar": int(W * 0.30), "k": int(S * 0.024), "gap": gap,
        "gap2": int(S * 0.012), "h1": int(S * 0.062), "lead": int(S * 0.030),
        "rad": int(S * 0.018), "cp": int(S * 0.026), "cv": int(S * 0.050),
        "ck": int(S * 0.021), "bul": int(S * 0.026), "bl": int(S * 0.014),
        "rh": int(S * 0.034), "lw": int(S * 0.115), "huge": int(S * 0.13),
        "qh": int(S * 0.042), "bp": int(S * 0.010), "bpx": int(S * 0.018),
    }
    return """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<style>%s</style></head><body>
<div class="rule"></div>
%s
%s
<div class="foot"><span class="mark">محفظة 100 ألف · عز استثمار</span>
<span>البورصة المصرية · توثيق قرار</span></div>
</body></html>""" % (css, "".join(body), prog)


def render_frames(spec, outdir, W, H, spec_mtime=None):
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for i, sc in enumerate(spec["scenes"]):
        sc = dict(sc)
        sc["n"] = i + 1
        sc["total"] = len(spec["scenes"])
        html = build_html(sc, W, H)
        hp = os.path.join(outdir, "scene%02d.html" % (i + 1))
        with open(hp, "w", encoding="utf-8") as f:
            f.write(html)
        png = os.path.join(outdir, "scene%02d.png" % (i + 1))
        # ⭐ لو الصورة موجودة وحديثة (أحدث من ملف المواصفات) ⇒ متارسمهاش تاني
        if os.path.exists(png) and not FORCE:
            paths.append(png)
            print("  🖼️  مشهد %d (موجود)" % (i + 1))
            continue
        sh([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
            "--force-device-scale-factor=1", "--window-size=%d,%d" % (W, H),
            "--screenshot=" + png, "file://" + hp])
        paths.append(png)
        print("  🎬 مشهد %d/%d" % (i + 1, len(spec["scenes"])))
    return paths


def assemble(spec, frames, audpath, outdir, W, H, fps=24):
    """ffmpeg: مقطع لكل مشهد (بمدة صوته) ⇒ concat ⇒ mux مع الصوت."""
    durs = json.load(open(os.path.join(outdir, "durations.json"), encoding="utf-8"))
    atempo = float(spec.get("atempo", 1.0))
    segs = []
    for i, png in enumerate(frames):
        d = float(durs.get(str(i + 1), durs.get(i + 1, 4.0))) / atempo + 0.30
        seg = os.path.join(outdir, "clip%02d.mp4" % (i + 1))
        fresh = os.path.exists(seg) and not FORCE
        if not fresh:
            if spec.get("motion", "none") == "none":
                sh(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", png, "-t", "%.3f" % d,
                    "-vf", "scale=%d:%d,fade=t=in:st=0:d=0.35,fade=t=out:st=%.3f:d=0.35"
                    % (W, H, max(0.1, d - 0.35)), "-r", str(fps), "-c:v", "libx264",
                    "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p", seg])
            else:
                sh(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", png, "-t", "%.3f" % d,
                    "-vf", "scale=%d:%d,zoompan=z='min(zoom+0.0004,1.07)':d=1:s=%dx%d:fps=%d"
                    % (W, H, W, H, fps), "-r", str(fps), "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", seg])
        segs.append(seg)
    lst = os.path.join(outdir, "concat.txt")
    with open(lst, "w") as f:
        for seg in segs:
            f.write("file '%s\n" % seg)
    silent = os.path.join(outdir, "silent.mp4")
    sh(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst,
        "-c", "copy", silent])
    if atempo != 1.0:
        fast = os.path.join(outdir, "audio_fast.mp3")
        if not os.path.exists(fast):
            sh(["ffmpeg", "-y", "-v", "error", "-i", audpath, "-filter:a",
                "atempo=%.3f" % atempo, "-q:a", "3", fast])
        audpath = fast
    out = os.path.join(outdir, spec.get("out", "video.mp4"))
    sh(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", audpath,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", out])
    return out


def make_thumbnail(spec, outdir):
    """🖼️ صورة الغلاف — نفس نظام التصميم."""
    sc = dict(spec["thumb"])
    sc["n"] = 1
    sc["total"] = 1
    W, H = 1280, 720
    html = build_html(sc, W, H)
    hp = os.path.join(outdir, "thumb.html")
    open(hp, "w", encoding="utf-8").write(html)
    png = os.path.join(outdir, "thumb.png")
    sh([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--window-size=%d,%d" % (W, H),
        "--screenshot=" + png, "file://" + hp])
    return png


def make_thumbnail(spec, outdir):
    """🖼️ صورة الغلاف — نفس نظام التصميم."""
    sc = dict(spec["thumb"])
    sc["n"] = 1
    sc["total"] = 1
    W, H = 1280, 720
    html = build_html(sc, W, H)
    hp = os.path.join(outdir, "thumb.html")
    open(hp, "w", encoding="utf-8").write(html)
    png = os.path.join(outdir, "thumb.png")
    sh([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--window-size=%d,%d" % (W, H),
        "--screenshot=" + png, "file://" + hp])
    return png


def make_thumbnail(spec, outdir):
    """🖼️ صورة الغلاف — نفس نظام التصميم."""
    sc = dict(spec["thumb"])
    sc["n"] = 1
    sc["total"] = 1
    W, H = 1280, 720
    html = build_html(sc, W, H)
    hp = os.path.join(outdir, "thumb.html")
    open(hp, "w", encoding="utf-8").write(html)
    png = os.path.join(outdir, "thumb.png")
    sh([CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--force-device-scale-factor=1", "--window-size=%d,%d" % (W, H),
        "--screenshot=" + png, "file://" + hp])
    return png


def main():
    path = sys.argv[1]
    only = "--only-frames" in sys.argv
    spec = json.load(open(path, encoding="utf-8"))
    base = os.path.join(ROOT, "build", spec["id"])
    os.makedirs(base, exist_ok=True)
    # ⛔ ما نمسحش الصوت ولا المدد (TTS مكلف) — نمسح المشاهد بس
    for f in os.listdir(base):
        if f.startswith("scene") and f.endswith((".png", ".html")):
            os.remove(os.path.join(base, f))
    W = spec.get("w", 1920)
    H = spec.get("h", 1080)
    print("▶ %s (%dx%d)" % (spec["id"], W, H))
    try:
        spec_mtime = os.path.getmtime(path)
    except Exception:
        spec_mtime = None
    frames = render_frames(spec, base, W, H, spec_mtime)
    if only:
        print("🖼️  المشاهد في", base)
        return 0
    aud = os.path.join(base, "audio.mp3")
    if not os.path.exists(aud):
        print("❌ مفيش صوت — شغّل tts.py الأول")
        return 1
    out = assemble(spec, frames, aud, base, W, H)
    print("✅", out, os.path.getsize(out) // 1024, "KB")
    if spec.get("thumb"):
        t = make_thumbnail(spec, base)
        print("🖼️ ", t, os.path.getsize(t) // 1024, "KB")
    if spec.get("thumb"):
        t = make_thumbnail(spec, base)
        print("🖼️ ", t, os.path.getsize(t) // 1024, "KB")
    if spec.get("thumb"):
        t = make_thumbnail(spec, base)
        print("🖼️ ", t, os.path.getsize(t) // 1024, "KB")


if __name__ == "__main__":
    sys.exit(main())
