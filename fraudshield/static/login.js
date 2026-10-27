// Passcode screen, shown instead of the page until this phone has entered the passcode once.
"use strict";
const TEXT = {
  wrong_code: "비밀번호가 맞지 않습니다. · That passcode isn't right.",
  slow_down: "너무 많이 틀렸습니다. 10분 뒤에 다시 해 보세요. · Too many tries. Try again in 10 minutes.",
  network: "연결할 수 없습니다. 인터넷을 확인하세요. · Can't connect. Check your internet.",
};
const form = document.getElementById("login");
const msg = document.getElementById("msg");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = form.querySelector("button");
  msg.hidden = true;
  btn.disabled = true;
  try {
    const res = await fetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: document.getElementById("code").value }) });
    if (res.ok) { location.replace("/"); return; }
    const body = await res.json().catch(() => ({}));
    msg.textContent = TEXT[body.detail] || TEXT.wrong_code;
  } catch {
    msg.textContent = TEXT.network;
  }
  msg.hidden = false;
  btn.disabled = false;
});
