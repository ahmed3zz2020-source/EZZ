// ezz-auto2 — بوابة تيليجرام لمؤسسة عز · رد فوري بالكود (٠ توكن)
// ⛔ ما بياخدش قرار شراء/بيع ولا توصية · كل رقم من مصدره · المجهول ⇒ رد فوري + تسجيل
// bindings: M (KV central) · P (KV investment) · GATE_BOT_TOKEN · SEND (service) · DAILY (service)
const SEND_URL = "https://ezz-gate-send.ahmed3zz2020.workers.dev/send";
const CHAT_ID = 2073907990;
const OCTA = "https://octa-prices-production-4ccb.up.railway.app";
const nf = (v, d = 0) => (typeof v === "number" && isFinite(v) ? v : d);
const money = (v) => nf(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pct = (v) => (nf(v) > 0 ? "+" : "") + nf(v).toFixed(2) + "%";
const ar = (v) => nf(v).toLocaleString("en-US");
function norm(t) {
  return (t || "").toLowerCase().replace(/[\u064B-\u0652\u0640]/g, "").replace(/[أإآ]/g, "ا")
    .replace(/ة/g, "ه").replace(/ى/g, "ي").replace(/[^\p{L}\p{N}\s.%/]/gu, " ").replace(/\s+/g, " ").trim();
}
async function kvGet(ns, key) {
  try { const raw = await ns.get(key); if (!raw) return null; try { return JSON.parse(raw); } catch { return raw; } } catch { return null; }
}
async function getJSON(url) {
  try {
    const r = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0" }, signal: AbortSignal.timeout(9000) });
    if (!r.ok) return null; return await r.json();
  } catch { return null; }
}
function dig(obj, keys, depth) {
  depth = depth || 0;
  if (!obj || typeof obj !== "object" || depth > 2) return null;
  for (const k of keys) if (typeof obj[k] === "number" && isFinite(obj[k])) return obj[k];
  for (const v of Object.values(obj)) { const r = dig(v, keys, depth + 1); if (r !== null) return r; }
  return null;
}
async function snapshot(env) {
  const r = await Promise.all([
    kvGet(env.M, "core/state.json"), kvGet(env.M, "core/tasks.json"),
    kvGet(env.P, "portfolio/ezz-investment"), kvGet(env.P, "portfolio/meta"), kvGet(env.P, "portfolio/decisions.json"),
  ]);
  const state = r[0] || {}, tasks = r[1] || {}, port = r[2] || {}, meta = r[3] || {}, dec = r[4] || null;
  const open = [], seen = new Set();
  const all = [].concat(Array.isArray(tasks) ? tasks : (tasks && tasks.open) || [])
    .concat(Array.isArray(state.open_decisions) ? state.open_decisions : []);
  for (const t of all) {
    if (!t || !t.id || seen.has(t.id)) continue; seen.add(t.id);
    const st = t.status || "open";
    if (st === "done" || st === "resolved" || st === "cancelled") continue;
    open.push({ id: t.id, title: t.task || t.title || "", status: st, prio: t.priority || "" });
  }
  return { state, open, capital: nf(port.capital, 100000), cash: nf(port.cash, 100000),
    positions: port.positions || {}, orders: port.orders || {}, meta, decisions: dec,
    budget: state.token_budget || {}, gold: state.gold_bot || {}, content: state.content_direction || {},
    cleanup: state.chat_cleanup || {},
    lastUpdate: port.last_update || meta.session_date || "" };
}
function replyPortfolio(s, live) {
  const nPos = Object.keys(s.positions).length;
  const L = [];
  L.push("💰 عز استثمار — " + new Date().toISOString().slice(0, 10));
  L.push("رأس المال: " + money(s.capital) + " ج.م");
  L.push("كاش: " + money(s.cash) + " ج.م");
  L.push("مراكز مفتوحة: " + nPos);
  if (!nPos) L.push("⇐ كاش 100% (مفيش أوامر منفَّذة)");
  const d = s.decisions;
  if (d && Array.isArray(d.orders) && d.orders.length) {
    L.push("");
    L.push("📝 أوامر مستنية تنفيذك (" + d.orders.length + ") — " + money(d.total) + " ج.م");
    if (live && live.pl !== null && live.pl !== undefined) {
      L.push("💡 لو نُفِّذت بسعر التوصية: " + (live.pl >= 0 ? "ربح " : "خسارة ") + money(Math.abs(live.pl)) + " ج.م (" + (live.pl / nf(d.total) * 100).toFixed(2) + "%)");
    }
  } else {
    L.push("");
    L.push("📝 مفيش أوامر مسجّلة في الداتا.");
  }
  L.push("⛔ التوصية مش أمر — التنفيذ بيدك في ثاندر.");
  if (s.lastUpdate) L.push("آخر تحديث الداتا: " + String(s.lastUpdate).slice(0, 10));
  return L.join("\n");
}
function replyOrders(s, live) {
  const d = s.decisions;
  if (!d || !Array.isArray(d.orders) || !d.orders.length) return "📝 مفيش أوامر مسجّلة في الداتا — قولّي خططها لك أول مرة.";
  const L = [];
  L.push("📝 أوامر مستنية تنفيذك (" + d.orders.length + ")");
  L.push("التاريخ: " + (d.date || "") + " · الإجمالي: " + money(d.total) + " ج.م");
  L.push("");
  for (const o of d.orders) {
    L.push("• " + (o.name || o.code) + " (" + o.code + ") — " + nf(o.qty) + " سهم");
    L.push("سعر التوصية: " + nf(o.price).toFixed(2));
    const p = live && live.prices ? live.prices[o.code] : null;
    if (p && typeof p.price === "number") {
      const pl = p.price - nf(o.price), pc = pl / nf(o.price) * 100;
      L.push("السعر الآن: " + p.price.toFixed(2));
      L.push("التغيّر: " + (pc >= 0 ? "+" : "") + pc.toFixed(2) + "%");
      L.push((pl >= 0 ? "الربح: " : "الخسارة: ") + money(Math.abs(pl * nf(o.qty))) + " ج.м");
    }
    L.push("سعر الوقف: " + nf(o.stop).toFixed(2));
    L.push("");
  }
  if (live && live.pl !== null && live.pl !== undefined) {
    L.push("💡 لو نُفِّذت الأوامر بسعر التوصية:");
    L.push("القيمة الآن: " + money(live.now) + " ج.م");
    L.push("مقابل التوصية: " + money(d.total) + " ج.م");
    L.push("⇐ " + (live.pl >= 0 ? "ربح " : "خسارة ") + money(Math.abs(live.pl)) + " ج.م (" + (live.pl / nf(d.total) * 100).toFixed(2) + "%)");
  }
  L.push("⛔ القرار في إيدك — التنفيذ يدوي في ثاندر.");
  return L.join("\n");
}
function replyTasks(s) {
  const L = [];
  L.push("⚠️ محتاج قرارك (" + s.open.length + ")");
  if (!s.open.length) { L.push("مفيش بند مفتوح."); return L.join("\n"); }
  for (const t of s.open.slice(0, 12)) {
    L.push("• " + t.id + " · " + (t.prio || "") + " · " + (t.status || ""));
    const title = (t.title || "").slice(0, 70);
    if (title) L.push(title);
  }
  if (s.open.length > 12) L.push("… و" + (s.open.length - 12) + " بند تاني.");
  return L.join("\n");
}
function replyDecisions(s) {
  const d = s.decisions;
  const L = ["القرارات"];
  if (d) {
    L.push("قرار المحفظة (" + (d.date || "") + "): " + nf(d.orders ? d.orders.length : 0) + " أوامر ≈ " + money(d.total) + " ج.م — التنفيذ بيدك.");
    L.push("الأوزان: " + Object.entries(d.weights || {}).map(([k, v]) => k + " " + v + "%").join(" · "));
  } else L.push("مفيش قرار محفظة مسجّل في الداتا.");
  const decs = (s.state.open_decisions || []);
  if (decs.length) {
    L.push("قرارات مفتوحة:");
    for (const x of decs.slice(0, 6)) L.push("· " + (x.title || x.task || x.id));
  }
  L.push("⛔ التوصية ≠ الأمر ≠ التنفيذ.");
  return L.join("\n");
}
function replyGold(s, live) {
  const g = s.gold || {};
  const L = [];
  L.push("🥇 الذهب وبوت الذهب");
  const gm = (live && live.gold) || s.meta.gold || {};
  if (gm.gram_egp) {
    L.push("الجرام: " + money(gm.gram_egp) + " ج.م");
    L.push("الدولار: " + nf(gm.egp_per_usd).toFixed(2) + " ج.م");
  } else L.push("سعر الجرام: لا توجد بيانات");
  L.push("");
  L.push("بوت الذهب: " + (g.engine_alive === false ? "مش شغّال" : "شغّال") + (g.schedule ? " · " + g.schedule : ""));
  if (g.m15 !== undefined) L.push("نماذج m15: " + nf(g.m15) + " (محتاج " + nf(g.needed_for_warm) + ") · تسخين: " + (g.warm ? "نعم" : "لا"));
  L.push("مفيش صفقات مغلقة — المحرك في وضع التعلّم.");
  return L.join("\n");
}
function replyMarket(s, live) {
  const L = [];
  const ms = (live && live.idx && live.idx.market_status) || null;
  const idx = (live && live.idx && live.idx.indices) || [];
  L.push("📈 السوق" + (idx.length ? " (آخر جلسة · مباشرة من محرك OCTA)" : ""));
  if (ms) L.push("الحالة: " + (ms.status_ar || ms.status || "") + " · " + String(ms.as_of || "").slice(11, 16) + " UTC");
  for (const it of idx) {
    const v = dig(it, ["value", "last", "price", "close"]), c = dig(it, ["change", "change_pct", "percent", "day_change"]);
    if (v !== null) L.push((it.short_ar || it.id) + " (" + it.id + "): " + nf(v).toLocaleString("en-US") + (c !== null ? " (" + pct(c) + ")" : ""));
  }
  if (!idx.length) {
    const b = (s.meta && s.meta.benchmarks) || {};
    for (const k of Object.keys(b)) if (b[k]) L.push(k + ": " + nf(b[k].value).toLocaleString("en-US") + " (" + pct(b[k].change) + ")");
    L.push("⛔ مفيش أرقام مباشرة — الأرقام من لقطة " + ((s.meta && s.meta.session_date) || "") + " (قديمة)");
  }
  const g = (live && live.gold) || s.meta.gold || {};
  if (g.gram_egp) L.push("🥇 الذهب: " + money(g.gram_egp) + " ج.م/جرام · الدولار: " + nf(g.egp_per_usd).toFixed(2));
  return L.join("\n");
}
async function replyStock(code) {
  const d = await getJSON(OCTA + "/api/explain/" + encodeURIComponent(code));
  if (!d) return "مفيش بيانات للسهم " + code + " من محرك OCTA.";
  const e = d.explanation || {}, L = ["سهم " + code + " — " + (d.name || "")];
  L.push("القطاع: " + (d.sector || "لا توجد بيانات") + " · السعر: " + (d.price !== undefined ? nf(d.price).toFixed(2) : "لا توجد بيانات") + " · المخاطر: " + (d.risk_level || "لا توجد بيانات"));
  if (e.base_score !== undefined) L.push("النتيجة: " + nf(e.base_score).toFixed(1) + " من 100 · ثقة " + nf(e.confidence).toFixed(0) + "%");
  const ax = (a) => (a || []).slice(0, 3).map((x) => (x.text || x.name || x.axis || "") + (x.from ? " (" + x.from + ")" : "")).join(" · ");
  const p1 = ax(e.top_positives), n1 = ax(e.top_negatives);
  if (p1) L.push("أقوى ما يدعمه: " + p1);
  if (n1) L.push("أقوى ما ضده: " + n1);
  if (e.missing_count) L.push("محاور ناقصة: " + nf(e.missing_count));
  L.push("⛔ النتيجة قواعد ثابتة في الكود — مش توصية شراء.");
  return L.join("\n");
}
function replyBudget(s) {
  const b = s.budget;
  if (!b || !b.cost_per_run) return "ميزانية التوكنز: لا توجد بيانات";
  return ["ميزانية التوكنز",
    "تكلفة التشغيل: " + ar(b.cost_per_run) + " توكن (سياق نظيف)",
    "المتوقع: " + ar(b.runs_per_day) + " تشغيل/يوم ≈ " + ar(b.cost_per_day) + " توكن/يوم",
    "السقف المعتمد: " + ar(b.cap_runs_per_day) + " تشغيل/يوم",
    "قبل الإصلاح: " + ar(b.before_fix_per_day) + " توكن/يوم ⇒ توفير " + nf(b.saving_pct) + "%"].join("\n");
}
function replyContent(s) {
  const c = s.content || {}, L = ["اتجاه المحتوى"];
  L.push("الحالة: " + (c.status || "لا توجد بيانات"));
  if (c.primary) L.push("الأساسي: " + c.primary);
  if (Array.isArray(c.paused) && c.paused.length) L.push("متوقف: " + c.paused.join(" · "));
  return L.join("\n");
}
function replyCleanup(s) {
  const c = s.cleanup || {}, L = ["تنظيف الشاتات"];
  L.push(c.done || "لا توجد بيانات");
  L.push("متبقّي: " + (c.pending_count !== undefined ? c.pending_count : 0) + " · مرفوضة (أرشفة): " + (c.stuck_archived || 0));
  return L.join("\n");
}
const CHOICES = ["الحالة (ملخص)", "المحفظة", "الأوامر", "المهام", "القرارات", "السوق", "الذهب", "سهم (رمز)", "التكلفة", "المحتوى", "التقرير"];
function replyHelp() { return ["أقدر أرد عليك فورًا (صفر كريدت) على:", CHOICES.join(" · "), "اكتب سؤالك عادي — مش لازم كلمات certain."].join("\n"); }
function replyFallback(text) {
  return ["مش فاهم عايز إيه بالظبط · اختر:", CHOICES.join(" · "), "سجّلت سؤالك: " + (text || "").slice(0, 80)].join("\n");
}
const INTENTS = [
  { k: "report", w: ["تقرير"] },
  { k: "orders", w: ["امر", "اوامر", "شراء", "شتري", "نشتري", "بيع", "نبيع", "صفقه", "صفقات", "توصيه"] },
  { k: "portfolio", w: ["محفظ", "رصيد", "فلوس", "فلوسي", "كاش", "راس المال", "استثمر", "استثمار", "عندي كام", "كم عندي"] },
  { k: "tasks", w: ["مهمه", "مهام", "شغل", "مطلوب", "محتاج", "توك"] },
  { k: "decisions", w: ["قرار", "قرارات"] },
  { k: "budget", w: ["تكلف", "توكن", "كريديت", "ميزاني", "استهلاك", "بيستهلك"] },
  { k: "content", w: ["محتوى", "القناه", "فيدبو", "فيديو", "content"] },
  { k: "cleanup", w: ["شات", "cron", "تنظيف", "ارشيف", "ارشفة"] },
  { k: "market", w: ["بورص", "مؤشر", "egx", "شريعه"] },
  { k: "gold", w: ["ذهب", "جرام", "دولار", "xau"] },
  { k: "status", w: ["حاله", "حالي", "حالتي", "ملخص", "وضع", "status", "overall"] },
  { k: "help", w: ["مساعده", "help"] },
];
function classify(t) {
  const raw = (t || "").trim();
  if (!raw) return null;
  const s = norm(raw);
  const tid = raw.match(/\bT-\d{2,4}\b/i);
  if (tid) return { k: "taskid", id: tid[0].toUpperCase() };
  const code = raw.match(/\b([A-Z]{3,5})\b/);
  if (code && raw.split(/\s+/).length <= 3) return { k: "stock", code: code[1] };
  if (/^[a-z]{3,5}$/.test(raw.trim())) return { k: "stock", code: raw.trim().toUpperCase() };
  let best = null, bestN = 0, tie = false;
  for (const it of INTENTS) {
    let n = 0;
    for (const w of it.w) if (s.includes(w)) n += w.length;
    if (n > bestN) { best = it.k; bestN = n; tie = false; }
    else if (n === bestN && n > 0) tie = true;
  }
  if (!best) return null;
  if (tie) return { k: "ambiguous" };
  return { k: best };
}
async function answer(env, text) {
  const c = classify(text);
  if (!c) return { kind: null, text: replyFallback(text) };
  if (c.k === "help") return { kind: "help", text: replyHelp() };
  if (c.k === "stock") return { kind: "stock", text: await replyStock(c.code) };
  if (c.k === "taskid") {
    const s0 = await snapshot(env);
    const t = s0.open.find((x) => x.id === c.id);
    return { kind: "task", text: t ? (c.id + " · " + (t.prio || "") + " · " + t.status + "\n" + t.title) : (c.id + " — مش في المهام المفتوحة.") };
  }
  if (c.k === "report") {
    if (!env.DAILY) return { kind: "report", text: "التقرير أقدر أبعتهولك من الشات — قولّي «بعت التقرير»." };
    try {
      const r = await env.DAILY.fetch("https://daily/run?send=1");
      const j = await r.json();
      const ok = j && j.sent && j.sent.ok;
      return { kind: "report", text: ok ? "اتبعت تقرير النهاردة ✅ (رسالة " + nf(j.sent.message_id) + ")" : "مقدرتش أبعته دلوقتي — في خطأ في الإرسال." };
    } catch (e) { return { kind: "report", text: "مقدرتش أبعت التقرير دلوقتي: " + String((e && e.message) || e) }; }
  }
  const s = await snapshot(env);
  const needLive = c.k === "market" || c.k === "gold" || c.k === "status";
  let live = null;
  if (needLive) {
    const [idx, gold] = await Promise.all([getJSON(OCTA + "/api/indices"), getJSON(OCTA + "/api/gold")]);
    live = { idx, gold };
  }
  const orders = (s.decisions && Array.isArray(s.decisions.orders)) ? s.decisions.orders : [];
  if (orders.length && (c.k === "orders" || c.k === "portfolio" || c.k === "status")) {
    const pb = await priceBlock(orders);
    live = live || {};
    live.prices = pb.prices; live.now = pb.now; live.pl = pb.pl;
  }
  if (c.k === "portfolio") return { kind: c.k, text: replyPortfolio(s, live) };
  if (c.k === "orders") return { kind: c.k, text: replyOrders(s, live) };
  if (c.k === "tasks") return { kind: c.k, text: replyTasks(s) };
  if (c.k === "decisions") return { kind: c.k, text: replyDecisions(s) };
  if (c.k === "budget") return { kind: c.k, text: replyBudget(s) };
  if (c.k === "content") return { kind: c.k, text: replyContent(s) };
  if (c.k === "cleanup") return { kind: c.k, text: replyCleanup(s) };
  if (c.k === "market") return { kind: c.k, text: replyMarket(s, live) };
  if (c.k === "gold") return { kind: c.k, text: replyGold(s, live) };
  if (c.k === "status") return { kind: c.k, text: replyPortfolio(s, live) + "\n\n" + replyMarket(s, live) + "\n\n" + replyGold(s, live) };
  return { kind: null, text: replyFallback(text) };
}
async function sendTelegram(env, chat, text) {
  const payload = { chat_id: chat || CHAT_ID, text, disable_web_page_preview: true };
  try {
    const r = await fetch("https://api.telegram.org/bot" + env.GATE_BOT_TOKEN + "/sendMessage", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const j = await r.json();
    return { ok: !!j.ok, message_id: (j.result || {}).message_id, error: j.description };
  } catch (e) {
    try {
      const r2 = await env.SEND.fetch(SEND_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chat_id: chat || CHAT_ID, text }) });
      const j2 = await r2.json();
      return { ok: !!j2.ok, message_id: j2.message_id, error: j2.error };
    } catch (e2) { return { ok: false, error: String((e2 && e2.message) || e2) }; }
  }
}
export default {
  async fetch(e, env) {
    const url = new URL(e.url);
    if (url.pathname !== "/telegram" || e.method !== "POST") return new Response("not found", { status: 404 });
    const expected = await env.M.get("core/gate_secret");
    const got = e.headers.get("x-telegram-bot-api-secret-token") || url.searchParams.get("s");
    if (!expected || !got || got !== expected) return new Response("forbidden", { status: 403 });
    let up = null;
    try { up = await e.json(); } catch {}
    if (!up) return new Response("bad body", { status: 400 });
    const m = (up && up.message) || {};
    const text = m.text || "";
    if (url.searchParams.get("debug") === "1") {
      const a = await answer(env, text);
      return new Response(a.text, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
    }
    const key = "core/inbox";
    const raw = await env.M.get(key);
    let list = [];
    try { list = raw ? JSON.parse(raw) : []; } catch {}
    const entry = { id: up.update_id, at: Date.now(), chat: m.chat ? m.chat.id : null,
      from: m.from ? (m.from.username || m.from.first_name || "owner") : null,
      kind: m.voice ? "voice" : (text ? "text" : (m.document ? "document" : "other")),
      text, voice: m.voice ? m.voice.file_id : null, handled: false, needs_llm: false };
    list.push(entry);
    if (list.length > 60) list = list.slice(-60);
    let auto = null, intent = null;
    if (entry.kind === "text" && text) {
      const a = await answer(env, text);
      auto = a.text; intent = a.kind;
      entry.intent = a.kind || "unknown";
    }
    if (auto) {
      const res = await sendTelegram(env, entry.chat, auto);
      if (res.ok) { entry.handled = true; entry.auto = intent || "auto"; entry.sent = res.message_id; }
      else { entry.needs_llm = true; entry.auto_error = res.error; }
    } else if (entry.kind === "voice") {
      const res = await sendTelegram(env, entry.chat, "وصلتني رسالة صوتية · محتاج أتفريغها.");
      if (res.ok) { entry.needs_llm = true; entry.ack = res.message_id; }
    }
    try { await env.M.put(key, JSON.stringify(list)); }
    catch (err) { return new Response("kv busy: " + String((err && err.message) || err), { status: 503 }); }
    return new Response("ok " + (entry.auto || (entry.needs_llm ? "needs_llm" : "stored")));
  },
};

async function livePrices(codes) {
  const out = {};
  await Promise.all((codes || []).map(async (c) => {
    const d = await getJSON(OCTA + "/api/explain/" + encodeURIComponent(c));
    if (d && typeof d.price === "number") out[c] = { price: d.price, score: (d.explanation || {}).base_score };
  }));
  return out;
}
async function priceBlock(orders) {
  const prices = await livePrices((orders || []).map((o) => o.code));
  let now = 0, pl = 0, have = false;
  for (const o of orders || []) {
    const p = prices[o.code];
    if (!p) continue;
    have = true;
    now += p.price * nf(o.qty);
    pl += (p.price - nf(o.price)) * nf(o.qty);
  }
  return { prices, now: have ? now : null, pl: have ? pl : null };
}
