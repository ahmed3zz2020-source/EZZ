# -*- coding: utf-8 -*-
"""
⚙️ إعدادات «عز استثمار» — القواعد فقط.

⛔ الأرقام الحقيقية (رأس المال · المراكز · الأرباح · التكاليف) لا تُwritten في هذا الملف.
   ⭐ السبب: المستودع عام — أي رقم محفظة فيه = تسريب.
   ⭐ الحقيقة في: Cloudflare KV (مساحة ezz-investment) + نسخة يومية في Drive.
   ⭐ هذا الملف = السياسة + العتبات + مسارات الخدمة فقط.

🧠 مبدأ التشغيل (مكتوب بالنيابة عن المالك):
   ⭐ «كل الإدارة معاك — عز استثمار. المالك هو التنفيذ فقط في الوسيط (ثاندر)
      لحد ما نلاقي وسيط في السوق المصري يسمح بربط برمجي.
     التوصية ≠ الأمر ≠ التنفيذ — والفرق ده بيتسجّل في الدفتر.»
"""

# ─────────────────────────────── الخدمة ───────────────────────────────
OCTA_API_BASE = "https://octa-prices-production-4ccb.up.railway.app"
CF_ACCOUNT = "74e046678adabf0706024b97b205882b"
KV_NAMESPACE_TITLE = "ezz-investment"
KV_NAMESPACE_ID = "a4509b030f394d478736ed1d186778fb"
KV_KEY_LEDGER = "portfolio/ezz-investment"
KV_KEY_META = "portfolio/meta"
KV_KEY_JOURNAL = "journal/"
KV_KEY_REPORTS = "reports/"

TELEGRAM_CHAT_ID = "2073907990"               # @Ahmedazizeldin
TELEGRAM_TOKEN_ENV = "OFFICE_TELEGRAM_TOKEN"  # بوت @EzzDeskBot
SESSION_TTL = 1800                            # ثانية — قبل ما الجلسة تموت
HTTP_TIMEOUT = 45

# ────────────────────────────── المحافظ ──────────────────────────────
PORTFOLIOS = {
    "ezz-investment": {
        "name_ar": "عز استثمار",
        "broker_ar": "ثاندر",
        "execution_mode": "manual_by_owner",   # ⛔ المنفّذ هو المالك
        "style": "aggressive_growth_long",
        "horizon": "swing_to_long",
        "base_currency": "EGP",
        "benchmarks": ["EGX30", "EGX70", "EGX100", "EGX33", "GOLD_24K", "USD_EGP"],
        "shadow_strategies": ["aggressive", "growth", "value", "swing", "income", "balanced", "conservative"],
    }
}

# ────────────────────────────── السياسة ──────────────────────────────
POLICY = {
    "max_position_pct": 20.0,        # أقصى وزن لسهم واحد
    "max_sector_pct": 35.0,          # أقصى وزن لقطاع واحد
    "max_positions": 12,             # أقصى عدد مراكز مفتوحة

    "risk_per_trade_min_pct": 1.5,   # أدنى مخاطرة مقبولة للصفقة
    "risk_per_trade_max_pct": 2.0,   # أقصى مخاطرة مقبولة للصفقة
    "open_risk_min_pct": 6.0,        # الحد الأدنى للمخاطرة المفتوحة المستهدفة
    "open_risk_max_pct": 8.0,        # السقف المطلق للمخاطرة المفتوحة

    "no_leverage": True,
    "no_short": True,
    "no_derivatives": True,
    "no_margin": True,

    "min_liquidity_score": 40.0,     # أقل سيولة مقبولة
    "min_data_coverage": 0.55,       # أدنى تغطية بيانات مطلوبة للصفقة
    "min_position_egp": 3000.0,      # ⭐ أقل حجم مركز معقول (تحت كده = عملية غير مجدية)
    "min_liquidity_cap_egp": 3000.0, # ⭐ سقف السيولة الآمن لازم يدعم مركز مفيد
    "drawdown_review_pct": 15.0,     # مراجعة شاملة
    "drawdown_alert_pct": 20.0,      # إنذار
    "max_report_chars": 3900,        # حد تيليجرام
    "max_watch_items": 5,
}

# ─────────────────────── أوزان طبقة الفهم المستقلة ───────────────────────
# ⭐ دي أوزان «عز» مش أوزان OCTA. OCTA نتيجة من ٦ محاور (تقني ٢٠٪ · أساسي ٢٤٪
#   سيولة ٢٠٪ · أخبار ٥٪ · معنويات ٤٪ · مخاطرة ٢٧٪). إحنا بنحسب عواملنا بنفسنا
#   من الحقول الخام + المقارنة القطاعية، وبعدين نقارن بالنتيجة بتاعة OCTA.
FACTOR_WEIGHTS = {
    "momentum": 0.26,
    "quality": 0.25,
    "value": 0.16,
    "liquidity": 0.13,
    "risk": 0.14,
    "catalyst": 0.06,
}

# عتبات筛查
GATES = {
    "min_my_score": 55.0,        # حد القبول من درجتنا المستقلة
    "max_rsi_entry": 78.0,       # لا نشتري في ذروة زخم مت overheated
    "min_perf_1m": -12.0,        # لا نشتري أصلاً هابط بقوة خلال شهر
    "min_liquidity": 40.0,
}

# ⭐ قواعد التحقق من البيانات
DATA_RULES = {
    "max_price_age_days": 5,     # أقدم سعر مقبول للتقييم
    "max_fundamental_age_days": 60,
    "require_index_session": True,
    "discrepancy_alert_pct": 1.0,
}
