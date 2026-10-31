# -*- coding: utf-8 -*-
"""
📒 دفتر المحفظة + سجل القرارات + مخزن KV.

⛔ كل الأرقام الحقيقية هنا — ولهذا السبب تعيش في KV مش في المستودع.
✅ القواعد (سقف ٢٠٪ · ٣٥٪ · ١٫٥–٢٪ · ٦–٨٪) مفروضة برمجياً قبل أي أمر.

🧾 الحالات لازم تفرق:
   recommended → awaiting_approval → approved (بإذن المالك) → filled (بتأكيد المالك)
   ⛔ ما ينفعش صفقة تتسجّل من غير fill_price من المالك.
"""
import json
import os
import time
import urllib.error
import urllib.request

from config import (POLICY, CF_ACCOUNT, KV_NAMESPACE_TITLE, KV_NAMESPACE_ID,
                    KV_KEY_LEDGER, KV_KEY_META, KV_KEY_JOURNAL)


# ────────────────────────────── مخزن KV ──────────────────────────────
class KV:
    """☁️ Cloudflare KV — الكتابة/القراءة المباشرة. ⛔ مفيش أسرار جوّه."""

    def __init__(self, account=None, namespace_id=None, token=None):
        self.account = account or CF_ACCOUNT
        self.token = token or os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        self.ns = (namespace_id or os.environ.get("EZZ_KV_NAMESPACE", "").strip()
                  or KV_NAMESPACE_ID)
        if not self.ns:
            self.ns = self._discover()

    def _discover(self):
        url = ("https://api.cloudflare.com/client/v4/accounts/%s/storage/kv/namespaces" % self.account)
        req = urllib.request.Request(url, headers={"Authorization": "Bearer %s" % self.token})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        for ns in data.get("result") or []:
            if ns.get("title") == KV_NAMESPACE_TITLE:
                return ns["id"]
        raise RuntimeError("مساحة KV %s مش موجودة" % KV_NAMESPACE_TITLE)

    def _url(self, key):
        from urllib.parse import quote
        return ("https://api.cloudflare.com/client/v4/accounts/%s/storage/kv/namespaces/%s/values/%s"
                % (self.account, self.ns, quote(key, safe="")))

    def get(self, key):
        try:
            req = urllib.request.Request(self._url(key), headers={"Authorization": "Bearer %s" % self.token})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def get_json(self, key, default=None):
        raw = self.get(key)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return default

    def put(self, key, value):
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        req = urllib.request.Request(self._url(key), data=value.encode("utf-8"), method="PUT",
                                     headers={"Authorization": "Bearer %s" % self.token,
                                              "Content-Type": "text/plain; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status in (200, 201)
        except urllib.error.HTTPError as e:
            # ⛔ 429 = سقف الكتابة اليومي على مستوى الحساب كله.
            # ⭐ ما بنوقفش التشغيل — بنكمل في الذاكرة وبنبلّغ.
            print("⚠️ KV put %s فشل (%s) — السقف اليومي محتمل" % (key, e.code))
            return False

    def list_keys(self, prefix=""):
        from urllib.parse import quote
        url = ("https://api.cloudflare.com/client/v4/accounts/%s/storage/kv/namespaces/%s/values/?list=true&limit=1000"
               % (self.account, self.ns))
        if prefix:
            url += "&prefix=%s" % quote(prefix, safe="")
        req = urllib.request.Request(url, headers={"Authorization": "Bearer %s" % self.token})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            return []
        return [x.get("name") for x in (data.get("result") or []) if x.get("name")]


# ────────────────────────────── الدفتر ──────────────────────────────
def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Ledger:
    """📒 دفتر المحفظة — مصدر الحقيقة الوحيد لحالة المحفظة.

    ⭐ تخزين مزدوج: KV (الأساسي) + نسخة محلية على القرص.
       ⭐ السبب: سقف KV اليومي (١٠٠٠ write/يوم على مستوى الحساب كله)
         ممكن يكون مستنفد ⇒ ما نخسرش الدفتر.
       ⭐ أولوية القراءة: KV ← ثم المحلي. والكتابة: الاتنين."""

    LOCAL_DIR = os.environ.get("EZZ_STATE_DIR", "/opt/ezz-investment-state")

    def __init__(self, kv, portfolio_id="ezz-investment"):
        self.kv = kv
        self.pid = portfolio_id
        self.local_path = os.path.join(self.LOCAL_DIR, "ledger-%s.json" % portfolio_id)
        self.data = self.kv.get_json(KV_KEY_LEDGER, None)
        if self.data is None:
            self.data = self._local_read()
        if self.data is None:
            self.data = {
                "portfolio_id": portfolio_id,
                "created_at": _now(),
                "capital": None,          # ⛔ يُنسخ من السر عند التهيئة
                "cash": None,
                "positions": {},           # code → {qty, avg_price, cost, entry_date, stop, target1, target2, thesis, risk_egp}
                "orders": {},              # id → order
                "realized_pnl": 0.0,
                "dividends": 0.0,
                "costs": 0.0,
                "equity_peak": None,
                "history": [],             # (date, equity, cash, invested) — للمنحنى
                "last_update": None,
            }

    # ── نسخة محلية ──
    def _local_read(self):
        try:
            with open(self.local_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return None

    def _local_write(self):
        try:
            os.makedirs(self.LOCAL_DIR, exist_ok=True)
            tmp = self.local_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.local_path)
            return True
        except Exception as e:  # noqa: BLE001
            print("⚠️ تعذّر الحفظ المحلي: %s" % str(e)[:90])
            return False

    # ── تهيئة ──
    def seed(self, capital):
        if self.data.get("capital") is None:
            self.data["capital"] = float(capital)
            self.data["cash"] = float(capital)
            self.data["equity_peak"] = float(capital)
            self.data["created_at"] = _now()
            try:
                self.save()
            except Exception as e:  # noqa: BLE001
                print("⚠️ تعذّر حفظ التهيئة: %s" % str(e)[:100])
        return self.data

    def save(self):
        self.data["last_update"] = _now()
        self._local_write()
        try:
            return self.kv.put(KV_KEY_LEDGER, self.data)
        except Exception as e:  # noqa: BLE001
            print("⚠️ تعذّر حفظ الدفتر في KV: %s" % str(e)[:100])
            return False

    # ── حسابات ──
    def equity(self, prices):
        """💰 حالة المحفظة بسعرENCES الحالي."""
        invested = 0.0
        market = 0.0
        cost = 0.0
        by_sector = {}
        for code, p in (self.data.get("positions") or {}).items():
            px = prices.get(code)
            if px is None:
                continue
            mv = px * p.get("qty", 0)
            market += mv
            invested += mv
            cost += p.get("cost", 0.0)
            sec = p.get("sector") or "—"
            by_sector[sec] = by_sector.get(sec, 0.0) + mv
        cash = float(self.data.get("cash") or 0.0)
        equity = cash + market
        unreal = market - cost
        ret_pct = ((equity / float(self.data["capital"]) - 1) * 100.0) if self.data.get("capital") else None
        peak = self.data.get("equity_peak") or equity
        dd = ((equity / peak - 1) * 100.0) if peak else 0.0
        open_risk = 0.0
        for code, p in (self.data.get("positions") or {}).items():
            px = prices.get(code) or p.get("avg_price")
            st = p.get("stop")
            if px and st and px > st:
                open_risk += (px - st) * p.get("qty", 0)
        return {
            "capital": self.data.get("capital"), "cash": cash, "invested": market,
            "cost": cost, "equity": equity, "unrealized": unreal,
            "realized": self.data.get("realized_pnl", 0.0),
            "dividends": self.data.get("dividends", 0.0),
            "costs": self.data.get("costs", 0.0),
            "return_pct": round(ret_pct, 2) if ret_pct is not None else None,
            "drawdown_pct": round(dd, 2), "peak": peak,
            "open_risk": open_risk,
            "open_risk_pct": round(open_risk / equity * 100, 2) if equity else 0.0,
            "sector_exposure": {k: round(v / equity * 100, 1) for k, v in by_sector.items()} if equity else {},
            "n_positions": len(self.data.get("positions") or {}),
        }

    # ── أوامر ──
    def new_order(self, oid, code, side, qty, limit_price, **kw):
        o = {"id": oid, "code": code, "side": side, "qty": qty, "limit_price": limit_price,
             "status": "recommended", "created_at": _now(), "notes": kw.get("notes", ""),
             "stop": kw.get("stop"), "target1": kw.get("target1"), "target2": kw.get("target2"),
             "thesis": kw.get("thesis", ""), "risk_egp": kw.get("risk_egp"),
             "sector": kw.get("sector"), "reason": kw.get("reason", ""),
             "fill_price": None, "fill_qty": None, "fill_date": None, "commission": None}
        self.data.setdefault("orders", {})[oid] = o
        return o

    def clear_recommended(self):
        """🧹 شيل الأوامر المقترحة القديمة — الخطة الجديدة بتلغيها.
        ⛔ ما بنمسحش ولا approved ولا filled (دي تاريخ حقيقي)."""
        orders = self.data.get("orders") or {}
        gone = [k for k, v in orders.items() if v.get("status") == "recommended"]
        for k in gone:
            orders.pop(k, None)
        return gone

    def approve(self, oid):
        o = self.data["orders"].get(oid)
        if o:
            o["status"] = "approved"
            o["approved_at"] = _now()
        return o

    def apply_fill(self, oid, price, qty=None, commission=0.0, date=None):
        """✅ تنفيذ مؤكد من المالك ⇒ يتسجّل في الدفتر."""
        o = self.data["orders"].get(oid)
        if not o:
            raise KeyError("أمر مش موجود: %s" % oid)
        qty = int(qty if qty is not None else o.get("qty") or 0)
        gross = price * qty
        comm = float(commission or 0.0)
        self.data["cash"] = float(self.data.get("cash") or 0) - gross - comm
        self.data["costs"] = float(self.data.get("costs") or 0) + comm
        pos = self.data.setdefault("positions", {}).get(o["code"]) or {
            "qty": 0, "avg_price": 0.0, "cost": 0.0, "entry_date": date or _now()[:10],
            "stop": o.get("stop"), "target1": o.get("target1"), "target2": o.get("target2"),
            "thesis": o.get("thesis", ""), "sector": o.get("sector"), "risk_egp": 0.0}
        new_qty = pos.get("qty", 0) + qty
        pos["cost"] = float(pos.get("cost", 0.0)) + gross
        pos["qty"] = new_qty
        pos["avg_price"] = round(pos["cost"] / new_qty, 4) if new_qty else 0.0
        if o.get("stop"):
            pos["stop"] = o["stop"]
        if o.get("thesis"):
            pos["thesis"] = o["thesis"]
        if o.get("sector"):
            pos["sector"] = o["sector"]
        self.data["positions"][o["code"]] = pos
        o.update({"status": "filled", "fill_price": price, "fill_qty": qty,
                  "fill_date": date or _now()[:10], "commission": comm,
                  "filled_at": _now()})
        self.save()
        return o

    def sell_position(self, code, price, qty=None, commission=0.0, date=None, reason=""):
        """💵 إغلاق (أو جزئي) لمركز — نفس قواعد التأكيد."""
        pos = (self.data.get("positions") or {}).get(code)
        if not pos:
            raise KeyError("مفيش مركز على %s" % code)
        qty = int(qty if qty is not None else pos.get("qty", 0))
        qty = min(qty, pos.get("qty", 0))
        gross = price * qty
        comm = float(commission or 0.0)
        cost_out = pos.get("avg_price", 0.0) * qty
        pnl = gross - cost_out - comm
        self.data["realized_pnl"] = float(self.data.get("realized_pnl", 0.0)) + pnl
        self.data["cash"] = float(self.data.get("cash") or 0) + gross - comm
        self.data["costs"] = float(self.data.get("costs") or 0) + comm
        pos["qty"] -= qty
        pos["cost"] = round(pos.get("cost", 0.0) - cost_out, 4)
        if pos["qty"] <= 0:
            self.data["positions"].pop(code, None)
        oid = "SELL-%s-%s" % (code, (date or _now()[:10]).replace("-", ""))
        self.data.setdefault("orders", {})[oid] = {
            "id": oid, "code": code, "side": "sell", "qty": qty, "limit_price": price,
            "status": "filled", "fill_price": price, "fill_qty": qty,
            "fill_date": date or _now()[:10], "commission": comm, "filled_at": _now(),
            "notes": reason, "reason": reason}
        self.save()
        return {"pnl": round(pnl, 2), "order_id": oid}

    # ── سياسة ──
    def policy_check(self, order, prices, eq):
        """🚧 فحص السياسة قبل أي أمر: تركيز · سيولة · مخاطرة · أنواع ممنوعة."""
        reasons = []
        px = order.get("limit_price")
        qty = order.get("qty") or 0
        if POLICY["no_leverage"] and order.get("side") == "sell" and order.get("code") not in (self.data.get("positions") or {}):
            reasons.append("بيع سهم مش موجود — ممنوع (short)")
        if order.get("side") == "buy":
            val = px * qty
            w = val / eq["equity"] * 100 if eq["equity"] else 0
            if w > POLICY["max_position_pct"] + 0.01:
                reasons.append("وزن السهم %.1f%% > %.0f%%" % (w, POLICY["max_position_pct"]))
            sec = order.get("sector") or "—"
            cur = eq["sector_exposure"].get(sec, 0.0)
            if cur + w > POLICY["max_sector_pct"] + 0.01:
                reasons.append("قطاع %s %.1f%% + %.1f%% > %.0f%%"
                               % (sec, cur, w, POLICY["max_sector_pct"]))
            risk = order.get("risk_egp") or 0.0
            rp = risk / eq["equity"] * 100 if eq["equity"] else 0
            if rp > POLICY["risk_per_trade_max_pct"] + 0.01:
                reasons.append("مخاطرة الصفقة %.2f%% > %.1f%%" % (rp, POLICY["risk_per_trade_max_pct"]))
            # ⭐ مخاطرة أقل من ١٫٥٪ مقبولة (أأمن) — السقف ٢٠٪ وزن ممكن يمنع بلوغ ١٫٥٪
            if eq["open_risk_pct"] + rp > POLICY["open_risk_max_pct"] + 0.01:
                reasons.append("المخاطرة المفتوحة %.1f%% + %.1f%% > %.0f%%"
                               % (eq["open_risk_pct"], rp, POLICY["open_risk_max_pct"]))
            if eq["n_positions"] >= POLICY["max_positions"]:
                reasons.append("عدد المراكز مكتمل (%d)" % eq["n_positions"])
        return reasons

    def record_equity(self, equity):
        peak = self.data.get("equity_peak") or equity
        if equity > peak:
            self.data["equity_peak"] = equity
        self.data.setdefault("history", []).append(
            {"date": _now()[:10], "ts": _now(), "equity": round(equity, 2)})


# ─────────────────────────── سجل القرارات ───────────────────────────
class Journal:
    """🗒️ سجل قرارات دائم — append-only. ⛔ ما بنعدلش قرار قديم."""

    def __init__(self, kv, prefix=KV_KEY_JOURNAL):
        self.kv = kv
        self.prefix = prefix

    def append(self, entry):
        entry = dict(entry)
        entry.setdefault("ts", _now())
        key = self.prefix + entry["ts"][:10]
        raw = self.kv.get(key) or ""
        lines = [l for l in raw.split("\n") if l.strip()]
        lines.append(json.dumps(entry, ensure_ascii=False))
        payload = "\n".join(lines)
        try:
            self.kv.put(key, payload)
        except Exception as e:  # noqa: BLE001
            print("⚠️ السجل: KV فشل (%s) — بنكتب محلياً" % str(e)[:60])
        try:
            os.makedirs(self.LOCAL_DIR, exist_ok=True)
            with open(os.path.join(self.LOCAL_DIR, key.replace("/", "_")), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001
            pass
        return key

    def read(self, date):
        raw = self.kv.get(self.prefix + date) or ""
        out = []
        for l in raw.split("\n"):
            if l.strip():
                try:
                    out.append(json.loads(l))
                except Exception:  # noqa: BLE001
                    pass
        return out
