// ezz-watch — مراقب قرار المحفظة (صفر توكن)
// بيشتغل كل ساعة (Cloudflare Cron Trigger): يفحص وقف الخسارة + درجة المحرك لكل سهم
// مسجّل (أوامر مستنية تنفيذ أو مراكز منفّذة)، ويبعت تنبيه على تيليجرام عند التغيّر فقط.
//
// bindings: M → KV ezz-central-memory · P → KV ezz-investment · GATE_BOT_TOKEN · SEND
const CHAT_ID = 2073907990;
const OCTA = "https://octa-prices-production-4ccb.up.railway.app";
const KEY = "watch/last.json";
const nf = (v, d = 0) => (typeof v === "number" && isFinite(v) ? v : d);
const money = (v) => nf(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

async function kvGet(ns, key) { try { const raw = await ns.get(key); if (!raw) return null; try { return JSON.parse(raw); } catch { return raw; } } catch { return null; } }
async function kvPut(ns, key, val) { try { await ns.put(key, JSON.stringify(val)); } catch {} }
async function getJSON(url) { try { const r = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" }, signal: AbortSignal.timeout(9000) }); if (!r.ok) return null; return await r.json(); } catch { return null; } }

function buildItems(dec, port) {
  const items = [];
  const orders = (dec && Array.isArray(dec.orders)) ? dec.orders : [];
  for (const o of orders) items.push({ code: o.code, name: o.name || o.code, qty: nf(o.qty), entry: nf(o.price), stop: nf(o.stop), state: "مستني تنفيذ" });
  const positions = (port && port.positions) || {};
  for (const [code, p] of Object.entries(positions)) {
    if (items.some((x) => x.code === code)) continue;
    items.push({ code, name: code, qty: nf(p.qty || p.quantity), entry: nf(p.entry_price || p.price), stop: nf(p.stop), state: "منفّذ" });
  }
  return items;
}

async function run(env) {
  const [dec, port, last] = await Promise.all([
    kvGet(env.P, "portfolio/decisions.json"),
    kvGet(env.P, "portfolio/ezz-investment"),
    kvGet(env.M, KEY),
  ]);
  const items = buildItems(dec, port);
  if (!items.length) return { ok: true, note: "مفيش أوامر ولا مراكز", checked: 0, alerts: 0 };
  const prev = (last && last.items) || {};
  const now = {};
  const alerts = [];
  await Promise.all(items.map(async (it) => {
    const d = await getJSON(OCTA + "/api/explain/" + encodeURIComponent(it.code));
    if (!d) return;
    const price = typeof d.price === "number" ? d.price : null;
    const e = d.explanation || {};
    const score = typeof e.base_score === "number" ? e.base_score : null;
    const p = prev[it.code] || {};
    now[it.code] = { price, score, ts: Date.now(), stop_broken: !!(it.stop && price !== null && price <= it.stop) };
    if (price === null) return;
    // ١) وقف الخسارة اتكسر (نitzer لاول مرة بس)
    if (it.stop && price <= it.stop && !p.stop_broken) {
      alerts.push({ kind: "stop", code: it.code, name: it.name, qty: it.qty, entry: it.entry, stop: it.stop, price, state: it.state });
    }
    // ٢) درجة المحرك اتغيّرت ١٠ نقاط أو أكتر
    if (score !== null && typeof p.score === "number" && Math.abs(score - p.score) >= 10) {
      alerts.push({ kind: "score", code: it.code, name: it.name, price, from: p.score, to: score, state: it.state });
    }
  }));
  const text = alerts.length ? alerts.map(alertText).join("\n\n") : "";
  let sent = null;
  if (text) sent = await sendTelegram(env, text);
  const history = ((last && last.history) || []).concat(alerts.map((a) => ({ ...a, ts: Date.now() }))).slice(-20);
  await kvPut(env.M, KEY, { ts: Date.now(), items: now, history, last_alert: alerts.length ? Date.now() : ((last && last.last_alert) || null) });
  return { ok: true, checked: Object.keys(now).length, alerts: alerts.length, sent, items: now };
}

function alertText(a) {
  const L = [];
  if (a.kind === "stop") {
    L.push("🔴 وقف الخسارة اتكسر — " + a.code);
    L.push("السهم: " + (a.name || a.code) + " (" + a.code + ")");
    L.push("سعر التوصية: " + nf(a.entry).toFixed(2));
    L.push("السعر الآن: " + nf(a.price).toFixed(2));
    L.push("وقف الخسارة: " + nf(a.stop).toFixed(2));
    L.push("⇐ السعر تحت الوقف بـ " + money(nf(a.stop) - nf(a.price)) + " ج.م");
    L.push("الحالة: " + (a.state || "") + " · " + nf(a.qty) + " سهم");
    L.push("⛔ القرار في إيدك — التنفيذ يدوي في ثاندر");
  } else {
    const d = nf(a.to) - nf(a.from);
    L.push((d < 0 ? "🟡" : "🟢") + " رأي المحرك اتغيّر — " + a.code);
    L.push("السهم: " + (a.name || a.code) + " (" + a.code + ")");
    L.push("الدرجة: " + nf(a.to).toFixed(1) + " (كانت " + nf(a.from).toFixed(1) + ")");
    L.push((d < 0 ? "⇐ نزلت " : "⇐ قفزت ") + money(Math.abs(d)) + " نقطة");
    L.push("السعر الآن: " + nf(a.price).toFixed(2));
    L.push("الحالة: " + (a.state || ""));
    L.push("⛔ التوصية مش أمر — التنفيذ بيدك في ثاندر");
  }
  return L.join("\n");
}

async function sendTelegram(env, text) {
  try {
    const r = await fetch("https://api.telegram.org/bot" + env.GATE_BOT_TOKEN + "/sendMessage", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: CHAT_ID, text, disable_web_page_preview: true }),
    });
    const j = await r.json();
    return { ok: !!j.ok, message_id: (j.result || {}).message_id, error: j.description };
  } catch (e) {
    try {
      const r2 = await env.SEND.fetch("/send", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chat_id: CHAT_ID, text }),
      });
      const j2 = await r2.json();
      return { ok: !!j2.ok, message_id: j2.message_id, error: j2.error };
    } catch (e2) { return { ok: false, error: String((e2 && e2.message) || e2) }; }
  }
}

export default {
  async fetch(e, env) {
    const url = new URL(e.url);
    if (url.pathname === "/probe") {
      const out = { token: typeof env.GATE_BOT_TOKEN === "string" && env.GATE_BOT_TOKEN.length > 10, send: !!env.SEND, m: !!env.M, p: !!env.P };
      try { const r = await fetch("https://api.telegram.org/bot" + env.GATE_BOT_TOKEN + "/getMe", { headers: { "User-Agent": "Mozilla/5.0" }, signal: AbortSignal.timeout(9000) }); out.tgStatus = r.status; const j = await r.json(); out.tgOk = j.ok; out.tgErr = j.description; } catch (e) { out.tgThrow = String((e && e.message) || e); }
      try { const r2 = await fetch(OCTA + "/api/explain/ABUK", { headers: { "User-Agent": "Mozilla/5.0" }, signal: AbortSignal.timeout(9000) }); out.octaStatus = r2.status; } catch (e) { out.octaThrow = String((e && e.message) || e); }
      try { const k = await env.M.get("core/state.json"); out.kv = k ? "ok" : "null"; } catch (e) { out.kvThrow = String((e && e.message) || e); }
      return new Response(JSON.stringify(out), { headers: { "Content-Type": "application/json" } });
    }
    if (url.pathname === "/status") {
      const last = await kvGet(env.M, KEY);
      return new Response(JSON.stringify({ ok: true, last }), { headers: { "Content-Type": "application/json" } });
    }
    const res = await run(env);
    return new Response(JSON.stringify(res), { headers: { "Content-Type": "application/json" } });
  },
  async scheduled(e, env, ctx) { const res = await run(env); console.log("watch", JSON.stringify(res)); },
};
