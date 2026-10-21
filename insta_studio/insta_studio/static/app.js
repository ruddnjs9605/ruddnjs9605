"use strict";

const $ = (id) => document.getElementById(id);
const W = 1080;
const THEMES = [
  ["#141e30", "#243b55"],
  ["#ff5f6d", "#ffc371"],
  ["#134e5e", "#71b280"],
  ["#000000", "#2b2b2b"],
];
const FONT = '"Noto Sans KR", sans-serif';

const state = {
  sourceImageUrl: "",
  background: { type: "theme", index: 0 },
  image: null,
};

function storageGet(key) { try { return localStorage.getItem(key) || ""; } catch { return ""; } }
function storageSet(key, value) { try { localStorage.setItem(key, value); } catch { /* ignore */ } }

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const password = storageGet("insta-studio-password");
  if (password) headers.set("X-App-Password", password);
  const res = await fetch(path, { ...options, headers });
  if (res.status === 401) {
    const entered = prompt("앱 비밀번호를 입력하세요");
    if (entered) { storageSet("insta-studio-password", entered); return api(path, options); }
  }
  if (!res.ok) {
    let message = `오류 (HTTP ${res.status})`;
    try { message = (await res.json()).detail || message; } catch { /* not json */ }
    throw new Error(message);
  }
  return res;
}

function setStatus(id, text, kind = "") {
  const el = $(id);
  el.textContent = text;
  el.className = "hint" + (kind ? " " + kind : "");
}

// ---------- 1. source ----------

async function loadConfig() {
  const cfg = await (await fetch("/api/config")).json();
  for (const [key, label] of Object.entries(cfg.tones)) {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = label.split(":")[0];
    $("tone").append(opt);
  }
  if (!cfg.ai_ready) setStatus("generate-status", "서버에 ANTHROPIC_API_KEY가 설정되지 않았습니다.", "error");
  if (cfg.instagram_ready) $("btn-publish").classList.remove("hidden");
}

async function extract() {
  const url = $("url").value.trim();
  if (!url) return setStatus("extract-status", "링크를 입력하세요.", "error");
  $("btn-extract").disabled = true;
  setStatus("extract-status", "가져오는 중…");
  try {
    const a = await (await api("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    })).json();
    $("source-text").value = a.text || a.description || "";
    $("source-title").value = a.title || "";
    if (a.site_name) $("source-name").value = a.site_name;
    state.sourceImageUrl = a.image_url || "";
    $("bg-source-btn").disabled = !state.sourceImageUrl;
    const note = a.warnings.length ? a.warnings.join(" ") : `본문 ${a.text.length.toLocaleString()}자를 가져왔습니다.`;
    setStatus("extract-status", note, a.warnings.length ? "warn" : "");
  } catch (err) {
    setStatus("extract-status", `${err.message} 본문을 직접 붙여넣어 주세요.`, "error");
  } finally {
    $("btn-extract").disabled = false;
  }
}

async function generate() {
  const text = $("source-text").value.trim();
  if (text.length < 30) return setStatus("generate-status", "본문을 30자 이상 넣어 주세요.", "error");
  $("btn-generate").disabled = true;
  setStatus("generate-status", "AI가 요약하고 제목·캡션을 쓰는 중… (10~40초)");
  try {
    const d = await (await api("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        title: $("source-title").value,
        source: $("source-name").value,
        url: $("url").value.trim(),
        tone: $("tone").value,
      }),
    })).json();
    renderDraft(d);
    setStatus("generate-status", "완료! 아래에서 다듬어 보세요.");
    $("step-draft").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    setStatus("generate-status", err.message, "error");
  } finally {
    $("btn-generate").disabled = false;
  }
}

// ---------- 2. draft ----------

function renderDraft(d) {
  $("summary").replaceChildren(...d.summary.map((s) => {
    const li = document.createElement("li");
    li.textContent = s;
    return li;
  }));

  const chips = d.titles.map((t, i) => {
    const b = document.createElement("button");
    b.className = "chip" + (i === 0 ? " active" : "");
    b.textContent = t.replace(/\\n|\n/g, " ").replace(/\*/g, "");
    b.onclick = () => {
      $("titles").querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
      b.classList.add("active");
      $("img-title").value = t.replace(/\\n/g, "\n");
      draw();
    };
    return b;
  });
  $("titles").replaceChildren(...chips);

  const cautions = $("cautions");
  if (d.cautions.length) {
    const ul = document.createElement("ul");
    d.cautions.forEach((c) => { const li = document.createElement("li"); li.textContent = c; ul.append(li); });
    cautions.replaceChildren(Object.assign(document.createElement("b"), { textContent: "게시 전 확인" }), ul);
    cautions.classList.remove("hidden");
  } else {
    cautions.classList.add("hidden");
  }

  $("caption").value = d.caption;
  $("hashtags").value = d.hashtags.map((h) => "#" + h).join(" ");
  $("img-title").value = (d.titles[0] || "").replace(/\\n/g, "\n");
  $("img-source").value = d.source_label;
  updateCounts();

  ["step-draft", "step-image", "step-export"].forEach((id) => $(id).classList.remove("hidden"));
  draw();
}

function fullCaption() {
  const tags = $("hashtags").value.trim();
  return $("caption").value.trim() + (tags ? "\n\n" + tags : "");
}

function updateCounts() {
  $("caption-count").textContent = fullCaption().length.toLocaleString();
  $("tag-count").textContent = ($("hashtags").value.match(/#[^\s#]+/g) || []).length;
}

// ---------- 3. image ----------

// "*키워드*" marks text drawn in the accent color.
function parseRich(text) {
  const chars = [];
  let hl = false;
  for (const ch of text) {
    if (ch === "*") { hl = !hl; continue; }
    chars.push({ ch, hl });
  }
  return chars;
}

const runText = (chars) => chars.map((c) => c.ch).join("");

function wrapRich(ctx, text, maxWidth) {
  const lines = [];
  for (const para of text.split("\n")) {
    const chars = parseRich(para);
    let line = [];
    let i = 0;
    while (i < chars.length) {
      // next token: a run of spaces or a run of non-spaces
      const space = chars[i].ch === " ";
      let j = i;
      while (j < chars.length && (chars[j].ch === " ") === space) j++;
      const token = chars.slice(i, j);
      i = j;
      const candidate = line.concat(token);
      if (!line.length || ctx.measureText(runText(candidate).trimEnd()).width <= maxWidth) {
        line = candidate;
      } else {
        lines.push(line);
        line = space ? [] : token;
      }
      // a single word wider than the line: break by character
      while (ctx.measureText(runText(line)).width > maxWidth && line.length > 1) {
        let cut = line.length - 1;
        while (cut > 1 && ctx.measureText(runText(line.slice(0, cut))).width > maxWidth) cut--;
        lines.push(line.slice(0, cut));
        line = line.slice(cut);
      }
    }
    lines.push(line);
  }
  // trim spaces at the ends of each line
  return lines.map((l) => {
    let a = 0, b = l.length;
    while (a < b && l[a].ch === " ") a++;
    while (b > a && l[b - 1].ch === " ") b--;
    return l.slice(a, b);
  }).filter((l, idx, all) => l.length || (idx > 0 && idx < all.length - 1));
}

function drawRichLine(ctx, line, x, y, align, accent) {
  const width = ctx.measureText(runText(line)).width;
  let cx = align === "center" ? x - width / 2 : x;
  ctx.textAlign = "left";
  // draw consecutive characters of the same color together so kerning stays natural
  let k = 0;
  while (k < line.length) {
    let m = k;
    while (m < line.length && line[m].hl === line[k].hl) m++;
    const part = runText(line.slice(k, m));
    ctx.fillStyle = line[k].hl ? accent : "#ffffff";
    ctx.fillText(part, cx, y);
    cx += ctx.measureText(part).width;
    k = m;
  }
}

function drawPhoto(ctx, img, layout, H) {
  if (layout === "band") {
    // photo fills the width at the top; the rest stays black for the title
    const scale = W / img.width;
    const h = Math.min(img.height * scale, H * 0.72);
    const sh = h / scale;
    ctx.drawImage(img, 0, (img.height - sh) / 2, img.width, sh, 0, 0, W, h);
    return h;
  }
  const scale = Math.max(W / img.width, H / img.height);
  const w = img.width * scale, h = img.height * scale;
  ctx.drawImage(img, (W - w) / 2, (H - h) / 2, w, h);
  return H;
}

function draw() {
  const canvas = $("canvas");
  const H = Number($("ratio").value);
  if (canvas.height !== H) canvas.height = H;
  const ctx = canvas.getContext("2d");
  const layout = $("layout").value;
  const align = $("align").value;
  const accent = $("accent").value;
  const shade = Number($("shade").value) / 100;
  const pad = 70;

  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, W, H);
  if (state.background.type === "image" && state.image) {
    const photoBottom = drawPhoto(ctx, state.image, layout, H);
    if (layout === "band") {
      // soften the photo edge into the black band
      const g = ctx.createLinearGradient(0, photoBottom - 220, 0, photoBottom);
      g.addColorStop(0, "rgba(0,0,0,0)");
      g.addColorStop(1, "rgba(0,0,0,1)");
      ctx.fillStyle = g;
      ctx.fillRect(0, photoBottom - 220, W, 221);
    }
  } else {
    const [a, b] = THEMES[state.background.index] || THEMES[0];
    const g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, a);
    g.addColorStop(1, b);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
  }

  // bottom black gradient behind the title
  if (shade > 0) {
    const g = ctx.createLinearGradient(0, H, 0, H * 0.45);
    g.addColorStop(0, `rgba(0,0,0,${shade})`);
    g.addColorStop(0.45, `rgba(0,0,0,${0.85 * shade})`);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(0, H * 0.45, W, H * 0.55);
  }

  const size = Number($("font-size").value);
  ctx.font = `900 ${size}px ${FONT}`;
  const lines = wrapRich(ctx, $("img-title").value.trim(), W - pad * 2);
  const lineH = size * 1.28;
  const source = $("img-source").value.trim();
  const bottomGap = source ? 120 : 90;
  let y = H - bottomGap - lines.length * lineH;
  const x = align === "center" ? W / 2 : pad;

  ctx.textBaseline = "top";
  ctx.shadowColor = "rgba(0,0,0,.6)";
  ctx.shadowBlur = 12;
  for (const line of lines) { drawRichLine(ctx, line, x, y, align, accent); y += lineH; }

  if (source) {
    ctx.shadowBlur = 6;
    ctx.fillStyle = "rgba(255,255,255,.7)";
    ctx.font = `400 26px ${FONT}`;
    ctx.textAlign = align === "center" ? "center" : "left";
    ctx.textBaseline = "bottom";
    ctx.fillText(source, x, H - 40);
  }
  ctx.shadowBlur = 0;
  ctx.textAlign = "left";
}

async function loadImageFromBlob(blob) {
  const url = URL.createObjectURL(blob);
  try {
    const img = new Image();
    img.src = url;
    await img.decode();
    return img;
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

async function useSourceImage() {
  try {
    const res = await api("/api/image-proxy?url=" + encodeURIComponent(state.sourceImageUrl));
    state.image = await loadImageFromBlob(await res.blob());
    state.background = { type: "image" };
    draw();
  } catch (err) {
    setStatus("bg-warning", "원문 이미지를 불러오지 못했습니다: " + err.message, "error");
  }
}

function selectBg(button) {
  document.querySelectorAll("#bg-options .chip").forEach((c) => c.classList.remove("active"));
  button.classList.add("active");
}

// ---------- 4. export ----------

function canvasBlob() {
  return new Promise((resolve) => $("canvas").toBlob(resolve, "image/jpeg", 0.92));
}

async function copyCaption() {
  try {
    await navigator.clipboard.writeText(fullCaption());
    setStatus("export-status", "캡션을 복사했습니다.");
  } catch {
    $("caption").select();
    setStatus("export-status", "자동 복사가 막혀 있습니다. 캡션 칸을 길게 눌러 복사하세요.", "warn");
  }
}

async function download() {
  const blob = await canvasBlob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `insta-${Date.now()}.jpg`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

async function share() {
  await copyCaption();
  const file = new File([await canvasBlob()], `insta-${Date.now()}.jpg`, { type: "image/jpeg" });
  if (navigator.canShare && navigator.canShare({ files: [file] })) {
    try {
      await navigator.share({ files: [file] });
      setStatus("export-status", "공유 완료. 인스타그램에서 캡션을 붙여넣으세요.");
    } catch (err) {
      if (err.name !== "AbortError") setStatus("export-status", "공유 실패: " + err.message, "error");
    }
  } else {
    await download();
    setStatus("export-status", "이 브라우저는 파일 공유를 지원하지 않아 이미지를 저장했습니다. 캡션은 복사되어 있습니다.", "warn");
  }
}

async function publish() {
  let question = "지금 인스타그램 계정에 바로 게시할까요?";
  if ($("ratio").value === "1440") {
    question += "\n\n참고: Instagram API는 4:5보다 세로로 긴 이미지를 거부할 수 있습니다. 실패하면 비율을 4:5로 바꿔 다시 시도하세요.";
  }
  if (!confirm(question)) return;
  $("btn-publish").disabled = true;
  setStatus("export-status", "게시하는 중…");
  try {
    const form = new FormData();
    form.append("image", await canvasBlob(), "post.jpg");
    form.append("caption", fullCaption());
    const r = await (await api("/api/publish", { method: "POST", body: form })).json();
    setStatus("export-status", `게시 완료! (media id ${r.media_id})`);
  } catch (err) {
    setStatus("export-status", err.message, "error");
  } finally {
    $("btn-publish").disabled = false;
  }
}

// ---------- wiring ----------

function bind() {
  $("btn-extract").onclick = extract;
  $("btn-generate").onclick = generate;
  $("btn-copy").onclick = copyCaption;
  $("btn-download").onclick = download;
  $("btn-share").onclick = share;
  $("btn-publish").onclick = publish;

  ["caption", "hashtags"].forEach((id) => $(id).addEventListener("input", updateCounts));
  ["img-title", "img-source", "ratio", "layout", "align", "accent"].forEach((id) => $(id).addEventListener("input", draw));
  [["font-size", "font-size-out"], ["shade", "shade-out"]].forEach(([id, out]) => {
    $(id).addEventListener("input", () => { $(out).textContent = $(id).value; draw(); });
  });

  document.querySelectorAll("#bg-options button[data-bg]").forEach((b) => {
    b.onclick = () => {
      selectBg(b);
      if (b.dataset.bg === "source") return useSourceImage();
      state.background = { type: "theme", index: Number(b.dataset.bg.split("-")[1]) };
      draw();
    };
  });
  $("bg-upload").onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    state.image = await loadImageFromBlob(file);
    state.background = { type: "image" };
    selectBg(e.target.closest(".chip"));
    draw();
  };
}

bind();
loadConfig().catch(() => setStatus("generate-status", "서버에 연결할 수 없습니다.", "error"));
document.fonts.load(`900 68px ${FONT}`).then(() => document.fonts.ready).then(draw);
