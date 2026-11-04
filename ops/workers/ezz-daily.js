// ezz-daily — التقرير اليومي للمؤسسة بالكود (٠ توكن)
// يُستدعى بمجدول Cloudflare (scheduled trigger) الساعة ٠٥:٠٠ UTC = ٠٧:٠٠ القاهرة.
//
// bindings:
//   M → KV ezz-central-memory   (state / tasks)
//   P → KV ezz-investment       (portfolio / meta)
//   GATE_BOT_TOKEN → سر البوت
//   SEND → service binding لـezz-gate-send

const CHAT_ID = 2073907990;
const nf = (v, d = 0) => (typeof v === "number" && isFinite(v) ? v : d);
const money = (v) => nf(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pct = (v) => (nf(v) > 0 ? "+" : "") + nf(v).toFixed(2) + "%";

async function kvGet(ns, key) {
  try { const raw = await ns.get(key); if (!raw) return null; try { return JSON.parse(raw); } catch { return raw; } }
  catch { return null; }
}

function cairoDate(d) {
  const t = new Date(d.getTime() + 2 * 3600 * 1000); // مصر = UTC+2 (بلا تغيير صيفي)
  return t.toISOString().slice(0, 10) + " " + t.toISOString().slice(11, 16);
}

function buildReport(state, tasks, port, meta, live, dec) {
  const L = [];
  L.push("تقرير EZZ اليومي — " + cairoDate(new Date()));
  L.push("");

  // ١) المحفظة
  const capital = nf(port && port.capital, 100000);
  const cash = nf(port && port.cash, capital);
  const nPos = Object.keys((port && port.positions) || {}).length;
  L.push("المحفظة");
  L.push("رأس المال " + money(capital) + " ج.م · كاش " + money(cash) + " ج.م");
  L.push(nPos ? "مراكز مفتوحة: " + nPos : "مفيش مراكز — كاش ١٠٠٪");
  if (dec && Array.isArray(dec.orders) && dec.orders.length) {
    L.push("أوامر مستنية تنفيذك: " + dec.orders.length + " · " + nf(dec.total).toLocaleString("en-US") + " ج.م");
    for (const o of dec.orders) L.push("· " + o.code + " " + (o.name || "") + " — " + nf(o.qty) + " @ " + nf(o.price).toFixed(2));
    L.push("⛔ القرار في إيدك — التنفيذ يدوي في ثاندر");
  }
  L.push("");

  // ٢) السوق
  L.push("السوق");
  const liveIdx = (live && live.idx && live.idx.indices) || [];
  const ms = (live && live.idx && live.idx.market_status) || null;
  if (ms) L.push("الحالة: " + (ms.status_ar || ms.status || "") + " · " + String(ms.as_of || "").slice(11, 16) + " UTC");
  if (liveIdx.length) {
    for (const it of liveIdx) {
      const v = dig(it, ["value", "last", "price", "close"]), c = dig(it, ["change", "change_pct", "percent", "day_change"]);
      if (v !== null) L.push(it.id + ": " + nf(v).toLocaleString("en-US") + (c !== null ? " (" + pct(c) + ")" : "") + (it.short_ar ? " · " + it.short_ar : ""));
    }
    L.push("(أرقام آخر جلسة · مباشرة من محرك OCTA)");
  } else {
    const b = (meta && meta.benchmarks) || {};
    for (const k of ["EGX30", "EGX70", "EGX100", "EGX33"]) {
      if (b[k]) L.push(k + ": " + nf(b[k].value).toLocaleString("en-US") + " (" + pct(b[k].change) + " · شهر " + pct(b[k].perf_1m) + ")");
    }
    L.push("⛔ مفيش أرقام مباشرة — دول من لقطة " + ((meta && meta.session_date) || "") + " (قديمة)");
  }
  const g = (live && live.gold) || (meta && meta.gold) || {};
  if (g.gram_egp) L.push("الذهب: " + money(g.gram_egp) + " ج.م/جرام · الدولار " + nf(g.egp_per_usd).toFixed(2));
  L.push("");

  // ٣) القرارات والمهام المفتوحة
  const open = [];
  const seen = new Set();
  const all = []
    .concat(Array.isArray(tasks) ? tasks : (tasks && tasks.open) || [])
    .concat(Array.isArray(state && state.open_decisions) ? state.open_decisions : []);
  for (const t of all) {
    if (!t || !t.id || seen.has(t.id)) continue;
    seen.add(t.id);
    const st = t.status || "open";
    if (st === "done" || st === "resolved" || st === "cancelled") continue;
    open.push({ id: t.id, title: t.task || t.title || "", status: st, prio: t.priority || "" });
  }
  const active = open.filter((t) => t.status !== "paused");
  const paused = open.filter((t) => t.status === "paused");
  L.push("محتاج قرارك (" + active.length + ")");
  if (!active.length) L.push("مفيش قرار معلّق.");
  for (const t of active.slice(0, 8)) {
    const title = (t.title || "").length > 62 ? t.title.slice(0, 62) + "…" : (t.title || "");
    L.push(t.id + " · " + t.prio + " · " + t.status + " — " + title);
  }
  if (paused.length) L.push("متوقف: " + paused.map((t) => t.id).join(" · "));
  L.push("");

  // ٤) بوت الذهب + التوكنز
  const gb = (state && state.gold_bot) || {};
  L.push("الأنظمة");
  L.push("بوت الذهب: " + (gb.engine_alive === false ? "مش شغّال" : "شغّال") + " · " + (gb.schedule || "لا توجد بيانات"));
  const tb = (state && state.token_budget) || {};
  if (tb.cost_per_run) {
    L.push("التوكنز: " + nf(tb.cost_per_day).toLocaleString("en-US") + " /يوم (" + nf(tb.runs_per_day) + " تشغيل · سقف " + nf(tb.cap_runs_per_day) + ")");
  }
  const cd = (state && state.content_direction) || {};
  if (cd.status) L.push("المحتوى: " + cd.status);
  L.push("");
  L.push("⛔ التوصية مش أمر · التنفيذ بيد المالك في ثاندر.");
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
      const r2 = await env.SEND.fetch("https://ezz-gate-send.ahmed3zz2020.workers.dev/send", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chat_id: CHAT_ID, text }),
      });
      const j2 = await r2.json();
      return { ok: !!j2.ok, message_id: j2.message_id, error: j2.error };
    } catch (e2) { return { ok: false, error: String((e2 && e2.message) || e2) }; }
  }
}

export default {
  async fetch(e, env, ctx) {
    const url = new URL(e.url);
    const run = async (doSend) => {
      const [state, tasks, port, meta, dec, live] = await Promise.all([
        kvGet(env.M, "core/state.json"),
        kvGet(env.M, "core/tasks.json"),
        kvGet(env.P, "portfolio/ezz-investment"),
        kvGet(env.P, "portfolio/meta"),
        kvGet(env.P, "portfolio/decisions.json"),
        liveMarket(),
      ]);
      const text = buildReport(state, tasks, port, meta, live, dec);
      let sent = { ok: false, error: "dry-run" };
      if (doSend) sent = await sendTelegram(env, text);
      return { text, sent };
    };

    // جدولة Cloudflare
    if (e.request && e.request.headers.get("x-cron-trigger") !== null) {
      const r = await run(true);
      return new Response(JSON.stringify({ mode: "scheduled", ok: r.sent.ok, message_id: r.sent.message_id }), { headers: { "Content-Type": "application/json" } });
    }
    // تشغيل يدوي
    if (url.pathname === "/run" || url.pathname === "/") {
      const doSend = url.searchParams.get("send") !== "0";
      const r = await run(doSend);
      return new Response(JSON.stringify({ mode: "manual", sent: r.sent, preview: r.text }), { headers: { "Content-Type": "application/json" } });
    }
    return new Response("not found", { status: 404 });
  },

  async scheduled(e, env, ctx) {
    const [state, tasks, port, meta, dec, live] = await Promise.all([
      kvGet(env.M, "core/state.json"),
      kvGet(env.M, "core/tasks.json"),
      kvGet(env.P, "portfolio/ezz-investment"),
      kvGet(env.P, "portfolio/meta"),
      kvGet(env.P, "portfolio/decisions.json"),
      liveMarket(),
    ]);
    const text = buildReport(state, tasks, port, meta, live, dec);
    const sent = await sendTelegram(env, text);
    return { ok: sent.ok, message_id: sent.message_id, error: sent.error };
  },
};

async function getJSON(url) {
  try { const r = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" }, signal: AbortSignal.timeout(9000) }); if (!r.ok) return null; return await r.json(); } catch { return null; }
}
async function liveMarket() {
  const [idx, gold] = await Promise.all([
    getJSON("https://octa-prices-production-4ccb.up.railway.app/api/indices"),
    getJSON("https://octa-prices-production-4ccb.up.railway.app/api/gold"),
  ]);
  return { idx, gold };
}
function dig(obj, keys, depth) {
  depth = depth || 0;
  if (!obj || typeof obj !== "object" || depth > 2) return null;
  for (const k of keys) if (typeof obj[k] === "number" && isFinite(obj[k])) return obj[k];
  for (const v of Object.values(obj)) { const r = dig(v, keys, depth + 1); if (r !== null) return r; }
  return null;
}
