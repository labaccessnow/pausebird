// Pausebird — phone page. Everything from the server or the user is put on the page
// with textContent, never as HTML, so a scam message can't inject anything.
"use strict";

const T = {
  en: {
    title: "Pausebird",
    tagline: "Not sure about a message? Check it here before you reply.",
    tab_msg: "Check a message", tab_acct: "Check my checks",
    paste_label: "Paste the message",
    paste_ph: "Paste the text, email or KakaoTalk message here",
    sender_label: "Who sent it? (optional)", sender_ph: "Phone number, email or name",
    check_btn: "Check it", checking: "Checking…", or: "or",
    stage_shot: "Reading the screenshot…", stage_vm: "Listening to the voicemail…",
    stage_rules: "Checking links and phone numbers…", stage_ai: "Asking the AI for a second opinion…",
    stage_write: "Writing the answer…", stage_checks: "Reading the check pictures…",
    stage_compare: "Comparing your checks…",
    shot_btn: "📷 Screenshot", vm_btn: "🎙️ Voicemail",
    needs_model_note: "Screenshots and voicemails need the AI model, which isn't turned on yet.",
    examples: "Try an example",
    level_SCAM: "Scam — don't reply", level_CAUTION: "Be careful", level_SAFE: "Looks OK",
    sub_SCAM: "Don't click, call back, or pay.",
    sub_CAUTION: "Check with family before you do anything.",
    sub_SAFE: "No scam signs found. If it still feels wrong, ask family.",
    acct_SCAM: "Checks you didn't write were paid", acct_CAUTION: "Some checks need a look",
    acct_SAFE: "Every paid check is yours",
    what_now: "What to do now",
    tell_family: "📣 Tell my family", told_phone: "✓ Your family got an alert.",
    told_console: "✓ Alert written. (Phone alerts aren't set up yet.)",
    told_demo: "✓ This is where the family's phone gets the alert. (Judge demo: nothing was sent.)",
    told_fail: "The alert did not go through. Please call your family.",
    clicked_btn: "I already clicked, called, or paid", clicked_title: "Do these now",
    why: "Why we think so", read_title: "What we read", from: "From",
    score: "Risk score", ai: "AI second opinion",
    acct_intro: "Compare the checks your bank paid with the checks you actually wrote. Fake checks made with your account number show up here.",
    demo_btn: "Try the demo checkbook",
    paid_label: "Checks the bank paid (CSV from your bank)",
    wrote_label: "Checks you wrote (your checkbook, CSV)",
    read_images: "Also read the check pictures with AI",
    compare_btn: "Compare",
    loss: "Paid out on checks you didn't write",
    chk_SCAM: "Not yours", chk_CAUTION: "Look", chk_SAFE: "OK", check_no: "Check",
    footer_private: "Nothing you check is saved. Links in messages are never opened.",
    model_on: "AI model: on", model_off: "AI model: off — rules only",
    privacy_link: "Privacy · warning only, not advice",
    err_needs_model: "This needs the AI model, which isn't turned on yet. Paste the words instead.",
    err_unreadable: "We couldn't read it. Try a clearer picture, or paste the words.",
    err_budget: "The AI budget is used up. Paste the words instead — the checks still work.",
    err_too_big: "That file is too big.",
    err_wrong_type: "That kind of file can't be checked.",
    err_expired: "That result is gone. Please check again.",
    err_empty: "There's nothing to check yet.",
    err_model_error: "The AI didn't answer. Try again, or paste the words.",
    err_network: "Can't reach the checker. Check your internet and try again.",
    err_need_both_files: "Pick both files: the bank's list and your checkbook.",
    err_bad_csv: "We couldn't read that file:",
    err_other: "Something went wrong. Please try again.",
  },
  ko: {
    title: "Pausebird",
    tagline: "의심스러운 메시지가 있나요? 답장하기 전에 여기서 확인하세요.",
    tab_msg: "메시지 확인", tab_acct: "수표 확인",
    paste_label: "메시지를 붙여 넣으세요",
    paste_ph: "문자, 이메일, 카카오톡 메시지를 여기에 붙여 넣으세요",
    sender_label: "보낸 사람 (선택)", sender_ph: "전화번호, 이메일 또는 이름",
    check_btn: "확인하기", checking: "확인 중…", or: "또는",
    stage_shot: "화면 캡처를 읽는 중…", stage_vm: "음성 메시지를 듣는 중…",
    stage_rules: "링크와 전화번호를 확인하는 중…", stage_ai: "AI에게 한 번 더 물어보는 중…",
    stage_write: "답변을 쓰는 중…", stage_checks: "수표 사진을 읽는 중…",
    stage_compare: "수표를 비교하는 중…",
    shot_btn: "📷 화면 캡처", vm_btn: "🎙️ 음성 메시지",
    needs_model_note: "화면 캡처와 음성 메시지는 AI 모델이 필요합니다. 아직 켜져 있지 않습니다.",
    examples: "예시로 해 보기",
    level_SCAM: "사기입니다 — 답하지 마세요", level_CAUTION: "조심하세요", level_SAFE: "괜찮아 보입니다",
    sub_SCAM: "누르거나, 전화하거나, 돈을 보내지 마세요.",
    sub_CAUTION: "무엇이든 하기 전에 가족과 먼저 확인하세요.",
    sub_SAFE: "사기 징후가 없습니다. 그래도 이상하면 가족에게 물어보세요.",
    acct_SCAM: "직접 쓰지 않은 수표가 지급되었습니다", acct_CAUTION: "확인이 필요한 수표가 있습니다",
    acct_SAFE: "지급된 수표가 모두 본인 것입니다",
    what_now: "지금 할 일",
    tell_family: "📣 가족에게 알리기", told_phone: "✓ 가족에게 알림을 보냈습니다.",
    told_console: "✓ 알림을 작성했습니다. (휴대폰 알림은 아직 설정되지 않았습니다.)",
    told_demo: "✓ 실제 앱에서는 이때 가족 휴대폰으로 알림이 갑니다. (심사용 데모: 보내지 않았습니다.)",
    told_fail: "알림이 전달되지 않았습니다. 가족에게 직접 전화하세요.",
    clicked_btn: "이미 눌렀거나, 전화했거나, 돈을 보냈어요", clicked_title: "지금 바로 하세요",
    why: "이렇게 판단한 이유", read_title: "읽은 내용", from: "보낸 사람",
    score: "위험 점수", ai: "AI 의견",
    acct_intro: "은행이 지급한 수표와 직접 쓴 수표를 비교합니다. 내 계좌번호로 만든 가짜 수표를 찾아냅니다.",
    demo_btn: "예시 수표책으로 해 보기",
    paid_label: "은행이 지급한 수표 (은행 CSV 파일)",
    wrote_label: "직접 쓴 수표 (수표책 CSV 파일)",
    read_images: "AI로 수표 사진도 읽기",
    compare_btn: "비교하기",
    loss: "직접 쓰지 않은 수표로 빠져나간 돈",
    chk_SCAM: "내 수표 아님", chk_CAUTION: "확인 필요", chk_SAFE: "정상", check_no: "수표",
    footer_private: "확인한 내용은 저장되지 않습니다. 메시지 속 링크는 절대 열지 않습니다.",
    model_on: "AI 모델: 켜짐", model_off: "AI 모델: 꺼짐 — 규칙만 사용",
    privacy_link: "개인정보 안내 · 경고일 뿐 조언이 아닙니다",
    err_needs_model: "AI 모델이 필요한데 아직 켜져 있지 않습니다. 대신 글자를 붙여 넣으세요.",
    err_unreadable: "읽지 못했습니다. 더 선명한 사진을 쓰거나 글자를 붙여 넣으세요.",
    err_budget: "AI 사용 한도를 다 썼습니다. 글자를 붙여 넣으세요 — 기본 검사는 계속 됩니다.",
    err_too_big: "파일이 너무 큽니다.",
    err_wrong_type: "이 종류의 파일은 확인할 수 없습니다.",
    err_expired: "결과가 사라졌습니다. 다시 확인해 주세요.",
    err_empty: "아직 확인할 내용이 없습니다.",
    err_model_error: "AI가 응답하지 않았습니다. 다시 시도하거나 글자를 붙여 넣으세요.",
    err_network: "검사 서버에 연결할 수 없습니다. 인터넷을 확인하고 다시 시도하세요.",
    err_need_both_files: "두 파일을 모두 고르세요: 은행 목록과 수표책.",
    err_bad_csv: "파일을 읽지 못했습니다:",
    err_other: "문제가 생겼습니다. 다시 시도해 주세요.",
  },
};
const ICON = { SCAM: "⛔", CAUTION: "⚠️", SAFE: "✅" };
const CHANNEL_ICON = { sms: "💬", kakaotalk: "🟡", email: "✉️", voicemail: "🎙️", other: "💬" };

const $ = (sel) => document.querySelector(sel);
const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode */ } },
};

let status = { model: false, demo: false, lang: "en" };
let lang = store.get("lang") || ((navigator.language || "").toLowerCase().startsWith("ko") ? "ko" : "en");
let current = null; // the result on screen, re-drawn when the language changes
let examples = { messages: [], shots: [] };
let stageTimer = null;
let clickedOpen = false;
let toldText = "";

function t(key) { return (T[lang] && T[lang][key]) || T.en[key] || key; }

// el("p", {class: "x"}, "text", child, ...) — strings become text nodes, never HTML.
function el(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === false || v == null) continue;
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k != null && k !== false) n.append(k instanceof Node ? k : String(k));
  return n;
}

function applyLang() {
  document.documentElement.lang = lang;
  document.title = t("title");
  document.querySelectorAll("[data-i18n]").forEach((n) => { n.textContent = t(n.dataset.i18n); });
  document.querySelectorAll("[data-i18n-ph]").forEach((n) => { n.placeholder = t(n.dataset.i18nPh); });
  $("#lang").textContent = lang === "ko" ? "English" : "한국어";
  $("#model-state").textContent = status.model ? t("model_on") : t("model_off");
  renderExamples();
  if (current) render(current);
}

// ---- talking to the server -------------------------------------------------
// The AI takes a few seconds, so the busy line walks through what is happening.
// The steps are timed on this side; the server doesn't report progress.
function showStages(keys) {
  const line = $("#busy-text");
  let i = 0;
  line.textContent = t(keys[0] || "checking");
  clearInterval(stageTimer);
  stageTimer = setInterval(() => { if (i < keys.length - 1) line.textContent = t(keys[++i]); }, 2200);
}
const aiStages = () => (status.model ? ["stage_ai", "stage_write"] : []);

async function call(path, opts, keepResult, stages) {
  hideError();
  if (!keepResult) $("#result").hidden = true;
  showStages(stages || []);
  $("#busy").hidden = false;
  document.querySelectorAll("button").forEach((b) => { b.disabled = true; });
  try {
    let res;
    try {
      res = await fetch(path, opts);
    } catch {
      throw new Error("network");
    }
    if (res.status === 401) { location.reload(); throw new Error("locked"); }  // passcode cookie gone
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "other");
    return body;
  } finally {
    clearInterval(stageTimer);
    $("#busy").hidden = true;
    document.querySelectorAll("button").forEach((b) => { b.disabled = false; });
  }
}

function showError(code) {
  const box = $("#error");
  const [key, ...rest] = String(code).split(": ");
  const known = T.en["err_" + key];
  box.textContent = known ? t("err_" + key) + (rest.length ? " " + rest.join(": ") : "") : t("err_other");
  box.hidden = false;
  box.scrollIntoView({ behavior: "smooth", block: "center" });
}
function hideError() { $("#error").hidden = true; }

function forget() {
  if (current && current.preview) URL.revokeObjectURL(current.preview);
  current = null;
}

async function run(path, opts, stages, preview) {
  try {
    const r = await call(path, opts, false, stages);
    clickedOpen = false;
    toldText = "";
    forget();
    r.preview = preview || null;  // stays on this phone; never sent back
    current = r;
    render(r);
    $("#result").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    if (preview) URL.revokeObjectURL(preview);
    showError(e.message);
  }
}

// ---- drawing a result --------------------------------------------------------
function render(r) {
  const box = $("#result");
  const lvl = r.level;
  box.className = "result " + lvl.toLowerCase();
  const head = r.kind === "account" ? t("acct_" + lvl) : t("level_" + lvl);
  const sub = r.kind === "account" ? "" : t("sub_" + lvl);
  const body = el("div", { class: "body" });

  if (r.kind === "account" && r.total_loss > 0) {
    body.append(el("p", { class: "loss" }, t("loss"),
      el("strong", {}, "$" + r.total_loss.toLocaleString("en-US", { minimumFractionDigits: 2 }))));
  }
  body.append(el("p", { class: "summary" }, r.summary[lang] || r.summary.en));

  if (r.read) {
    // DOM append() would print a null as the word "null" (a voicemail has no picture or sender)
    body.append(...[el("h3", {}, t("read_title")),
      r.preview ? el("img", { class: "read-shot", src: r.preview, alt: "" }) : null,
      r.read.sender ? el("p", { class: "meta" }, t("from") + ": " + r.read.sender) : null,
      el("p", { class: "read" }, r.read.text)].filter(Boolean));
  }
  if (r.kind === "account") body.append(checkList(r.findings));

  const steps = r.steps[lang] || r.steps.en;
  if (steps.length) body.append(el("h3", {}, t("what_now")), el("ol", { class: "steps" }, steps.map((s) => el("li", {}, s))));

  if (lvl !== "SAFE") body.append(actions(r));

  if (r.kind === "message" && r.signals.length) {
    // The model's reason shows once: as a listed reason when it raised the risk, else on its own line.
    const ai = r.model && (typeof r.model === "string" ? r.model : r.model[lang] || r.model.en);
    const aiListed = r.signals.some((s) => s.code === "model.judgement");
    body.append(el("details", {},
      el("summary", {}, t("why")),
      el("ul", { class: "why" }, r.signals.map((s) => el("li", { class: s.hard ? "hard" : "" },
        s[lang] || s.en, el("br"), el("span", { class: "evidence" }, s.evidence)))),
      ai && !aiListed ? el("p", { class: "meta" }, t("ai") + ": " + ai) : null,
      el("p", { class: "meta" }, t("score") + ": " + r.score + "/100")));
  }

  box.replaceChildren(
    el("div", { class: "banner" }, el("span", { class: "icon", "aria-hidden": "true" }, ICON[lvl]),
      el("div", {}, el("h2", {}, head), sub ? el("p", {}, sub) : null)),
    body);
  box.hidden = false;
}

function actions(r) {
  const wrap = el("div", { class: "actions" });
  const tell = el("button", { type: "button", class: "tell", onclick: () => tellFamily(r, tell) }, t("tell_family"));
  const failed = toldText === "told_fail";
  if (toldText && !failed) tell.disabled = true;
  wrap.append(tell);
  if (toldText) wrap.append(el("p", { class: failed ? "sent failed" : "sent" }, t(toldText)));
  if (r.kind === "message") {
    const panel = el("div", { class: "urgent" }, el("h3", {}, t("clicked_title")),
      el("ol", { class: "steps" }, (r.clicked_steps[lang] || r.clicked_steps.en).map((s) => el("li", {}, s))));
    panel.hidden = !clickedOpen;
    wrap.append(el("button", { type: "button", class: "clicked", "aria-expanded": String(clickedOpen),
      onclick: (e) => { clickedOpen = !clickedOpen; panel.hidden = !clickedOpen;
        e.currentTarget.setAttribute("aria-expanded", String(clickedOpen));
        if (clickedOpen) panel.scrollIntoView({ behavior: "smooth", block: "nearest" }); } }, t("clicked_btn")), panel);
  }
  return wrap;
}

function checkList(findings) {
  const money = (n) => "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2 });
  const rank = { SCAM: 0, CAUTION: 1, SAFE: 2 };  // problems first, then the rest by date
  const sorted = [...findings].sort((a, b) => rank[a.level] - rank[b.level]);
  return el("ul", { class: "checks" }, sorted.map((f) => el("li", { class: f.level.toLowerCase() },
    el("div", { class: "line1" }, el("span", {}, t("check_no") + " #" + f.number + " · " + money(f.amount)),
      el("span", { class: "tag" }, t("chk_" + f.level))),
    el("div", { class: "line2" }, [f.payee, f.date].filter(Boolean).join(" · ")),
    f.reasons.length ? el("ul", {}, f.reasons.map((x) => el("li", {}, x[lang] || x.en))) : null,
    f.image && f.level !== "SAFE" ? el("img", { src: f.image, alt: t("check_no") + " #" + f.number, loading: "lazy" }) : null)));
}

async function tellFamily(r, btn) {
  try {
    const res = await call("/api/alert", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: r.id }) }, true);
    toldText = !res.sent ? "told_fail" : res.via === "phone" ? "told_phone"
      : res.via === "demo" ? "told_demo" : "told_console";
    render(current);
  } catch (e) {
    showError(e.message);
    render(current);
  }
  btn.blur();
}

// ---- wiring -------------------------------------------------------------------
function showTab(which) {
  const msg = which === "msg";
  $("#tab-msg").setAttribute("aria-selected", String(msg));
  $("#tab-acct").setAttribute("aria-selected", String(!msg));
  $("#panel-msg").hidden = !msg;
  $("#panel-acct").hidden = msg;
  $("#result").hidden = true;
  hideError();
  forget();
}

function upload(path, file, extra, stages, preview) {
  const fd = new FormData();
  fd.append("file", file);
  for (const [k, v] of Object.entries(extra || {})) fd.append(k, v);
  return run(path, { method: "POST", body: fd }, stages, preview);
}

function checkShot(file) {
  return upload("/api/check/screenshot", file, null, ["stage_shot", "stage_rules", ...aiStages()],
    URL.createObjectURL(file));
}

const acctStages = () => ($("#read-images").checked ? ["stage_checks", "stage_compare"] : ["stage_compare"]);

function wire() {
  $("#lang").addEventListener("click", () => { lang = lang === "ko" ? "en" : "ko"; store.set("lang", lang); applyLang(); });
  $("#tab-msg").addEventListener("click", () => showTab("msg"));
  $("#tab-acct").addEventListener("click", () => showTab("acct"));

  $("#msg-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const text = $("#msg-text").value.trim();
    if (!text) { showError("empty"); return; }
    run("/api/check/message", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, sender: $("#msg-sender").value.trim() || null }) },
      ["stage_rules", ...aiStages()]);
  });

  $("#shot-btn").addEventListener("click", () => (status.model ? $("#shot-file").click() : showError("needs_model")));
  $("#vm-btn").addEventListener("click", () => (status.model ? $("#vm-file").click() : showError("needs_model")));
  $("#shot-file").addEventListener("change", (e) => {
    const f = e.target.files[0]; e.target.value = "";
    if (f) checkShot(f);
  });
  $("#vm-file").addEventListener("change", (e) => {
    const f = e.target.files[0]; e.target.value = "";
    if (f) upload("/api/check/voicemail", f, { lang }, ["stage_vm", "stage_rules", ...aiStages()]);
  });

  $("#demo-acct").addEventListener("click", () => {
    const fd = new FormData();
    fd.append("use_demo", "true");
    fd.append("read_images", String($("#read-images").checked));
    run("/api/check/account", { method: "POST", body: fd }, acctStages());
  });
  $("#acct-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const paid = $("#paid-file").files[0], wrote = $("#wrote-file").files[0];
    if (!paid || !wrote) { showError("need_both_files"); return; }
    const fd = new FormData();
    fd.append("paid", paid);
    fd.append("wrote", wrote);
    fd.append("read_images", String($("#read-images").checked));
    run("/api/check/account", { method: "POST", body: fd }, acctStages());
  });
}

async function loadExamples() {
  const get = (path) => fetch(path).then((r) => r.json()).catch(() => []);
  const [messages, shots] = await Promise.all([get("/api/demo/messages"),
    status.model ? get("/api/demo/screenshots") : []]);
  examples = { messages, shots };
  renderExamples();
}

async function tryShot(s) {
  try {
    const blob = await fetch(s.url).then((r) => { if (!r.ok) throw new Error(); return r.blob(); });
    checkShot(new File([blob], s.id + ".png", { type: blob.type || "image/png" }));
  } catch {
    showError("network");
  }
}

function renderExamples() {
  const { messages, shots } = examples;
  if (!messages.length && !shots.length) return;
  $("#example-list").replaceChildren(
    ...shots.map((s) => el("button", { type: "button", onclick: () => tryShot(s) },
      el("span", {}, "📷 " + (s.label[lang] || s.label.en)))),
    ...messages.map((m) => el("button", { type: "button", onclick: () => {
      $("#msg-text").value = m.text;
      $("#msg-sender").value = m.sender || "";
      $("#msg-form").requestSubmit();
    } }, el("span", {}, (CHANNEL_ICON[m.channel] || "💬") + " " + m.text))));
  $("#examples").hidden = false;
}

// A phone "Share" lands on /share, which sends us back here with #r=<id> or #err=<code>.
async function fromShare() {
  const h = new URLSearchParams(location.hash.slice(1));
  history.replaceState(null, "", location.pathname);
  if (h.get("err")) showError(h.get("err"));
  if (h.get("r")) {
    try {
      const r = await call("/api/result/" + encodeURIComponent(h.get("r")));
      if (r.kind === "account") showTab("acct");
      current = r;
      render(r);
      $("#result").scrollIntoView({ behavior: "smooth", block: "start" });  // the answer is below the examples
    } catch (e) {
      showError(e.message);
    }
  }
}

async function start() {
  wire();
  status = await fetch("/api/status").then((r) => r.json()).catch(() => status);
  if (!store.get("lang") && status.lang && !(navigator.language || "").toLowerCase().startsWith("ko")) lang = status.lang;
  $("#model-note").hidden = status.model;
  $("#read-images-row").hidden = !status.model || !status.demo;
  $("#demo-acct").hidden = !status.demo;
  applyLang();
  if (status.demo) loadExamples();
  if (location.hash) fromShare();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
}

start();
