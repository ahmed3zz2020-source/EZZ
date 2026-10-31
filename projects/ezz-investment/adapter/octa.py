# -*- coding: utf-8 -*-
"""
🔌 محوّل OCTA — طبقة قراءة فقط.

⛔ مفيش أي كتابة على إنتاج. كل النداءات GET إلا mint_session (جلسة تشخيص).
⛔ مفيش تعديل على كود OCTA ولا على قواعد التقييم.
✅ كل نداء بيتسجّل في fetch_log (تدقيق) + snapshot_id بيتتبّع مع كل رد.

📌 في مصدرين لبيانات السوق داخل المنصة:
   ① الـAPI الحي (octa-prices على Railway) — الأسعار لحظ آخر جلسة + لقطة الأساسيات
   ② الملفات في GitHub — نسخة أقدم (data_full.json بتاريخ ٩ أكتوبر)
   ⭐ القاعدة: المصدر الحي هو المرجع. الملفات للتدقيق فقط.
"""
import json
import os
import time
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) EZZ-InvestmentAdapter/1.0"


class OctaError(RuntimeError):
    pass


class OctaAdapter:
    """⛔ read-only ⭐ مفيش method واحد بيكتب على بيانات."""

    def __init__(self, api_base=None, admin_token=None, timeout=45):
        self.base = (api_base or os.environ.get("OCTA_API_BASE")
                     or "https://octa-prices-production-4ccb.up.railway.app").rstrip("/")
        self.admin_token = admin_token or os.environ.get("OCTA_ADMIN_TOKEN", "").strip()
        self.timeout = timeout
        self._tok = None
        self._tok_at = 0.0
        self.last_snapshot = None
        self.fetch_log = []

    # ─────────────────────── منخفض المستوى ───────────────────────
    def _http(self, path, method="GET", body=None, headers=None, auth=False, retries=2):
        url = self.base + path
        data = json.dumps(body).encode() if body is not None else None
        h = {"User-Agent": UA, "Accept": "application/json"}
        if data:
            h["Content-Type"] = "application/json"
        if headers:
            h.update(headers)
        if auth and self._tok:
            h["Cookie"] = "octa_token=%s" % self._tok
        last = None
        for i in range(retries + 1):
            try:
                req = urllib.request.Request(url, data=data, headers=h, method=method)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    out = json.loads(r.read().decode("utf-8", "replace"))
                    self.fetch_log.append({"path": path, "ok": True,
                                           "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
                    if isinstance(out, dict) and out.get("snapshot_id"):
                        self.last_snapshot = out["snapshot_id"]
                    return out
            except Exception as e:  # noqa: BLE001
                last = e
                time.sleep(1.5 * (i + 1))
        self.fetch_log.append({"path": path, "ok": False, "error": str(last)[:120]})
        raise OctaError("%s → %s" % (path, last))

    # ─────────────────────── الجلسة ───────────────────────
    def session(self, force=False):
        """🔑 جلسة إدارية مؤقتة (نفس مسار /api/admin/mint_session).
        ⛔ الأداة دي تشخيص إداري — التوكن بينتهي تلقائياً."""
        if self._tok and not force and (time.time() - self._tok_at) < 1800:
            return self._tok
        if not self.admin_token:
            raise OctaError("مفيش OCTA_ADMIN_TOKEN في البيئة")
        admin = {"X-OCTA-Admin": self.admin_token}
        users = self._http("/api/admin/users", headers=admin)
        email = ""
        if isinstance(users, dict) and users.get("users"):
            email = users["users"][0].get("email") or ""
        if not email:
            raise OctaError("مفيش مستخدمين مسجّلين على السيرفر")
        out = self._http("/api/admin/mint_session", method="POST",
                         body={"email": email}, headers=admin)
        tok = out.get("token") or out.get("session") or ""
        if not tok:
            raise OctaError("mint_session فشل: %s" % str(out)[:140])
        self._tok, self._tok_at = tok, time.time()
        return tok

    # ─────────────────────── البيانات ───────────────────────
    def health(self):
        """💓 حالة الـAPI + نسخة البيانات."""
        return self._http("/api/health")

    def universe(self):
        """📊 الكون كله: ٢٨٦ سهم × ٥٤ حقل. snapshot_id بيتسجّل."""
        d = self._http("/api/stocks", auth=True)
        return d.get("egx30") or [], d.get("snapshot_id")

    def egx_full(self):
        """🌱 طبقة الأساسيات الطازجة (TradingView + StartMarkets) — بتتحدّث يومياً.
        ⭐ فيها حقول مش موجودة في الكون: pe · roe · cagr3y · frm52hi · mdd · s_ma50/200 · h52/l52."""
        return self._http("/api/egx_full", auth=True)

    def indices(self):
        """📈 المؤشرات الرسمية (٤) + قيمها + حالة السوق."""
        return self._http("/api/indices")

    def index_series(self, days=90):
        """📉 سلاسل تاريخية مؤشّرة (نقاط مُطبَّعة) + العائد + الـdrawdown + التذبذب."""
        ids = ",".join(["EGX30", "EGX70", "EGX100", "EGX33"])
        return self._http("/api/indices/compare?ids=%s&days=%d" % (ids, days), auth=True)

    def gold(self):
        """🥇 سعر جرام ٢٤ قيراط + سعر الدولار."""
        return self._http("/api/gold")

    def dividends(self):
        """💰 كل أحداث التوزيعات."""
        d = self._http("/api/dividends")
        return d.get("actions") or []

    def sector_stats(self):
        """🏭 متوسطات كل قطاع (P/E · P/B · D/E) — أساس التقييم النسبي."""
        return self._http("/api/sector-stats")

    def strategies(self):
        """🎯 استراتيجيات OCTA (أساس الـshadow portfolios)."""
        return self._http("/api/strategies").get("strategies") or []

    def opportunities(self):
        """🚀 الفرص اللي المحرك شايفها (مرجع — مش قرار)."""
        d = self._http("/api/opportunities")
        return d.get("all") or []

    def backtest(self):
        """🧪 قياس التتبّع الأمامي — بشروطه المعلنة."""
        return self._http("/api/backtest")

    def detail(self, code):
        """🔍 تفاصيل سهم واحد: فني + أساسي + مخاطرة + معنويات + شرح النتيجة."""
        out = {}
        for key, path in (("technical", "/api/technical/"), ("fundamental", "/api/fundamental/"),
                          ("risk", "/api/risk/"), ("sentiment", "/api/sentiment/"),
                          ("explain", "/api/explain/")):
            try:
                out[key] = self._http(path + code)
            except OctaError:
                out[key] = None
        return out

    def candles(self, code, n=250):
        """🕯️ شموع تاريخية."""
        d = self._http("/api/candles/%s?n=%d" % (code, n))
        return d.get("candles") or []

    def strategy_view(self, code, strategy="aggressive"):
        """🎯 نتيجة السهم تحت استراتيجية معيّنة (shadow portfolio)."""
        return self._http("/api/strategy/%s/%s" % (code, strategy))

    # ─────────────────────── مساعدات ───────────────────────
    def session_date(self, idx=None):
        """📅 تاريخ آخر جلسة تداول رسمي."""
        try:
            idx = idx or self.indices()
        except Exception:  # noqa: BLE001
            return None
        best = None
        for ix in idx.get("indices") or []:
            lo = (ix.get("live_official") or {}).get("day")
            if lo and (best is None or lo > best):
                best = lo
        return (best or "")[:10] or None
