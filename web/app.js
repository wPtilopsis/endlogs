const authBadge = document.getElementById("authBadge");
const authMessage = document.getElementById("authMessage");
const btnLogin = document.getElementById("btnLogin");
const btnRefreshProfile = document.getElementById("btnRefreshProfile");
const btnLogout = document.getElementById("btnLogout");
const btnToggleManual = document.getElementById("btnToggleManual");
const btnReport = document.getElementById("btnReport");
const manualForm = document.getElementById("manualForm");
const queryForm = document.getElementById("queryForm");
const queryStatus = document.getElementById("queryStatus");
const resultsEl = document.getElementById("results");
const btnQuery = document.getElementById("btnQuery");
const startDateEl = document.getElementById("startDate");
const endDateEl = document.getElementById("endDate");

let pollTimer = null;
let lastProfile = null;
let lastQuery = null;

function todayISO() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function formatZhDate(iso) {
  if (!iso) return "";
  const parts = iso.split("-").map(Number);
  if (parts.length !== 3 || parts.some((n) => Number.isNaN(n))) return iso;
  const [y, m, d] = parts;
  return `${y}年${m}月${d}日`;
}

function pad2(n) {
  return String(n).padStart(2, "0");
}

function daysInMonth(year, month) {
  return new Date(year, month, 0).getDate();
}

function parseISODate(iso) {
  if (!iso) return null;
  const parts = iso.split("-").map(Number);
  if (parts.length !== 3 || parts.some((n) => Number.isNaN(n))) return null;
  const [y, m, d] = parts;
  if (y < 1 || m < 1 || m > 12 || d < 1 || d > daysInMonth(y, m)) return null;
  return { y, m, d };
}

function toISODate(y, m, d) {
  return `${y}-${pad2(m)}-${pad2(d)}`;
}

function bindDateField(nativeEl) {
  const field = nativeEl.closest("[data-date-field]");
  if (!field) return;

  const yearEl = field.querySelector('[data-part="year"]');
  const monthEl = field.querySelector('[data-part="month"]');
  const dayEl = field.querySelector('[data-part="day"]');
  const partEls = [yearEl, monthEl, dayEl];

  function syncPartsFromNative() {
    const parsed = parseISODate(nativeEl.value);
    if (!parsed) return;
    yearEl.value = String(parsed.y);
    monthEl.value = String(parsed.m);
    dayEl.value = String(parsed.d);
  }

  function commitParts() {
    const y = Number(yearEl.value);
    const m = Number(monthEl.value);
    const d = Number(dayEl.value);
    if (!Number.isInteger(y) || y < 1970 || y > 2100) {
      syncPartsFromNative();
      return;
    }
    if (!Number.isInteger(m) || m < 1 || m > 12) {
      syncPartsFromNative();
      return;
    }
    const maxDay = daysInMonth(y, m);
    if (!Number.isInteger(d) || d < 1 || d > maxDay) {
      syncPartsFromNative();
      return;
    }
    nativeEl.value = toISODate(y, m, d);
    syncPartsFromNative();
  }

  function onlyDigits(el) {
    el.value = el.value.replace(/\D/g, "");
  }

  yearEl.addEventListener("input", () => {
    onlyDigits(yearEl);
    if (yearEl.value.length >= 4) monthEl.focus();
  });
  monthEl.addEventListener("input", () => {
    onlyDigits(monthEl);
    if (monthEl.value.length >= 2) dayEl.focus();
  });
  dayEl.addEventListener("input", () => {
    onlyDigits(dayEl);
    if (dayEl.value.length >= 2) commitParts();
  });

  partEls.forEach((el) => {
    el.addEventListener("blur", commitParts);
    el.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        commitParts();
        el.blur();
      }
      if (ev.key === "ArrowLeft" && el.selectionStart === 0) {
        const idx = partEls.indexOf(el);
        if (idx > 0) {
          ev.preventDefault();
          partEls[idx - 1].focus();
        }
      }
      if (ev.key === "ArrowRight" && el.selectionStart === el.value.length) {
        const idx = partEls.indexOf(el);
        if (idx < partEls.length - 1) {
          ev.preventDefault();
          partEls[idx + 1].focus();
        }
      }
      if (ev.key === "Backspace" && el.value.length === 0) {
        const idx = partEls.indexOf(el);
        if (idx > 0) {
          ev.preventDefault();
          partEls[idx - 1].focus();
        }
      }
    });
    el.addEventListener("focus", () => {
      requestAnimationFrame(() => el.select());
    });
  });

  nativeEl.addEventListener("change", syncPartsFromNative);
  nativeEl.addEventListener("input", syncPartsFromNative);

  syncPartsFromNative();
}

const today = todayISO();
startDateEl.value = today;
endDateEl.value = today;
bindDateField(startDateEl);
bindDateField(endDateEl);

async function api(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg || JSON.stringify(d)).join("; ")
      : detail || data.message || `HTTP ${resp.status}`;
    throw new Error(message);
  }
  return data;
}

function setAuthUI(status) {
  const loggedIn = Boolean(status.logged_in);
  authBadge.textContent = loggedIn ? "已登录" : "未登录";
  authBadge.classList.toggle("ok", loggedIn);

  const profileCard = document.getElementById("profileCard");
  const profile = status.profile || (status.browser_login && status.browser_login.profile) || null;
  lastProfile = profile;
  const hasProfile = Boolean(profile && (profile.uid || profile.nick_name));
  if (loggedIn && hasProfile) {
    profileCard.classList.remove("hidden");
    document.getElementById("profileName").textContent = profile.nick_name || "-";
    document.getElementById("profileUid").textContent = profile.uid || "-";
    document.getElementById("profileChannel").textContent = profile.channel_name || "-";
    document.getElementById("profileServer").textContent =
      profile.server_name || profile.server_display || profile.server_id || "-";
    document.getElementById("profileLevel").textContent =
      profile.level === 0 || profile.level ? String(profile.level) : "-";
  } else {
    profileCard.classList.add("hidden");
  }

  const browser = status.browser_login || {};
  if (browser.status === "waiting") {
    authMessage.textContent = browser.message || "等待浏览器登录…";
  } else if (browser.status === "failed") {
    authMessage.textContent = browser.message || "登录失败";
  } else if (loggedIn && hasProfile) {
    authMessage.textContent = "角色信息已同步。";
  } else if (loggedIn) {
    authMessage.textContent =
      "已保存会话，但缺少角色资料。请点「浏览器登录」或粘贴 binding token 后刷新。";
  } else {
    authMessage.textContent = "通过浏览器登录后，程序会自动捕获 token 与角色信息。";
  }
}

async function refreshAuth() {
  const status = await api("/api/auth/status");
  setAuthUI(status);
  if (status.browser_login && status.browser_login.status === "waiting") {
    schedulePoll();
  } else if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  return status;
}

function schedulePoll() {
  if (pollTimer) return;
  pollTimer = setInterval(() => {
    refreshAuth().catch(() => {});
  }, 1500);
}

btnLogin.addEventListener("click", async () => {
  btnLogin.disabled = true;
  try {
    await api("/api/auth/browser-login", { method: "POST", body: "{}" });
    await refreshAuth();
    schedulePoll();
  } catch (err) {
    authMessage.textContent = err.message;
  } finally {
    btnLogin.disabled = false;
  }
});

btnLogout.addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST", body: "{}" });
  lastProfile = null;
  await refreshAuth();
});

btnRefreshProfile.addEventListener("click", async () => {
  btnRefreshProfile.disabled = true;
  try {
    await api("/api/auth/refresh-profile", { method: "POST", body: "{}" });
    await refreshAuth();
  } catch (err) {
    authMessage.textContent = err.message;
  } finally {
    btnRefreshProfile.disabled = false;
  }
});

btnToggleManual.addEventListener("click", () => {
  manualForm.classList.toggle("hidden");
});

manualForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/auth/manual", {
      method: "POST",
      body: JSON.stringify({
        account_token: document.getElementById("accountToken").value.trim(),
        role_token: document.getElementById("roleToken").value.trim(),
        role_server_id: document.getElementById("serverId").value.trim() || "1",
        binding_token: document.getElementById("bindingToken").value.trim(),
      }),
    });
    manualForm.classList.add("hidden");
    await refreshAuth();
  } catch (err) {
    authMessage.textContent = err.message;
  }
});

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderBars(byDay) {
  const maxVal = Math.max(1, ...byDay.map((d) => Math.max(d.gain, d.consume)));
  return byDay
    .filter((d) => d.gain || d.consume)
    .map((d) => {
      const gainW = Math.round((d.gain / maxVal) * 100);
      const consumeW = Math.round((d.consume / maxVal) * 100);
      return `
        <div class="bar-row">
          <span>${escapeHtml(formatZhDate(d.date).replace(/^\d+年/, ""))}</span>
          <div>
            <div class="bar-track"><div class="bar-fill" style="width:${gainW}%"></div></div>
            <div class="bar-track" style="margin-top:4px"><div class="bar-fill consume" style="width:${consumeW}%"></div></div>
          </div>
          <span class="muted">${d.net >= 0 ? "+" : ""}${d.net}</span>
        </div>`;
    })
    .join("");
}

function pct(part, whole) {
  if (!whole) return 0;
  return Math.round((part / whole) * 1000) / 10;
}

function renderReasonGroup(title, rows, total, kind) {
  if (!rows.length) {
    return `<div class="reason-group"><h5>${title}</h5><p class="muted">无数据</p></div>`;
  }
  const maxVal = Math.max(1, ...rows.map((r) => Number(r.amount) || 0));
  const bars = rows
    .map((r) => {
      const amount = Number(r.amount) || 0;
      const width = Math.round((amount / maxVal) * 100);
      const share = pct(amount, total);
      const fillClass = kind === "consume" ? "bar-fill consume" : "bar-fill";
      return `
        <div class="bar-row reason-bar">
          <span class="reason-name" title="${escapeHtml(r.label)}">${escapeHtml(r.label)}</span>
          <div class="bar-track"><div class="${fillClass}" style="width:${width}%"></div></div>
          <span class="reason-meta">${amount}<small>${share}%</small></span>
        </div>`;
    })
    .join("");
  const body = rows
    .map(
      (r) => `<tr>
        <td>${escapeHtml(r.label)}</td>
        <td>${r.count}</td>
        <td>${r.amount}</td>
        <td>${pct(Number(r.amount) || 0, total)}%</td>
      </tr>`
    )
    .join("");
  return `<div class="reason-group">
    <h5>${title}<span class="muted">合计 ${total}</span></h5>
    <div class="bars">${bars}</div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>原因</th><th>次数</th><th>数量</th><th>占比</th></tr></thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  </div>`;
}

function renderReasonSummary(rows, summary) {
  if (!rows.length) return "<p class=\"muted\">暂无分类数据</p>";
  const gains = rows.filter((r) => r.kind === "gain");
  const consumes = rows.filter((r) => r.kind === "consume");
  return `<div class="reason-summary">
    ${renderReasonGroup("获取", gains, summary.gain || 0, "gain")}
    ${renderReasonGroup("消耗", consumes, summary.consume || 0, "consume")}
  </div>`;
}

function renderRecords(records) {
  if (!records.length) return "<p class=\"muted\">该区间无记录</p>";
  const body = records
    .slice(0, 200)
    .map(
      (r) => `<tr>
        <td>${escapeHtml(r.changeTimeText)}</td>
        <td>${escapeHtml(r.changeTypeName)}</td>
        <td>${escapeHtml(r.changeReasonLabel)}</td>
        <td>${r.changeNum}</td>
        <td>${r.after}</td>
      </tr>`
    )
    .join("");
  const note =
    records.length > 200
      ? `<p class="muted">仅展示前 200 条，完整明细请导出 CSV（共 ${records.length} 条）。</p>`
      : "";
  return `${note}<div class="table-wrap"><table>
    <thead><tr><th>时间</th><th>类型</th><th>原因</th><th>变动</th><th>存量</th></tr></thead>
    <tbody>${body}</tbody>
  </table></div>`;
}

function renderResult(item, startDate, endDate, changeType) {
  const s = item.summary;
  const exportUrl = `/api/export.csv?start_date=${startDate}&end_date=${endDate}&currency_type=${item.currencyType}&change_type=${changeType}`;
  const recordCount = s.recordCount || (item.records || []).length || 0;
  return `<article class="result-card">
    <h3>${escapeHtml(item.currencyName)}</h3>
    <div class="summary-grid">
      <div class="stat"><span class="label">期初</span><span class="value">${s.opening ?? "-"}</span></div>
      <div class="stat"><span class="label">期末</span><span class="value">${s.closing ?? "-"}</span></div>
      <div class="stat"><span class="label">净变化</span><span class="value">${s.net ?? "-"}</span></div>
      <div class="stat gain"><span class="label">获取</span><span class="value">+${s.gain}</span></div>
      <div class="stat consume"><span class="label">消耗</span><span class="value">-${s.consume}</span></div>
    </div>
    <h4 class="section-title">按日</h4>
    <div class="bars">${renderBars(item.byDay) || '<p class="muted">无日度数据</p>'}</div>
    <h4 class="section-title">按原因分类汇总</h4>
    ${renderReasonSummary(item.byReason, s)}
    <details class="fold-block">
      <summary>明细<span class="muted">共 ${recordCount} 条</span></summary>
      <div class="fold-body">${renderRecords(item.records)}</div>
    </details>
    <div class="export-row"><a class="btn ghost" href="${exportUrl}">导出 CSV</a></div>
  </article>`;
}

function topReasons(rows, kind, limit = 6) {
  return (rows || [])
    .filter((r) => r.kind === kind)
    .slice()
    .sort((a, b) => Number(b.amount) - Number(a.amount))
    .slice(0, limit);
}

const REPORT_COLORS = {
  ink: "#1a2330",
  muted: "#6a7886",
  accent: "#0b5a50",
  gain: "#3f6f8f", // 柔和蓝
  consume: "#a35d55", // 柔和红
  line: "rgba(26, 35, 48, 0.10)",
  card: "rgba(255, 255, 255, 0.55)",
};

function buildReportBlocks(profile, query) {
  const channel = (profile && (profile.channel_name || "官服")) || "官服";
  const nick = (profile && profile.nick_name) || "-";
  const level =
    profile && (profile.level === 0 || profile.level)
      ? `Lv.${profile.level}`
      : "Lv.-";
  const startZh = formatZhDate(query.startDate);
  const endZh = formatZhDate(query.endDate);
  const blocks = [
    { type: "title", text: "ENDLOGS 资源汇总" },
    { type: "meta", text: `${channel}  ·  ${nick}  ·  ${level}` },
    {
      type: "range",
      text: startZh === endZh ? `统计区间  ${startZh}` : `统计区间  ${startZh}  —  ${endZh}`,
    },
  ];

  for (const item of query.results || []) {
    const s = item.summary || {};
    const gains = topReasons(item.byReason, "gain");
    const consumes = topReasons(item.byReason, "consume");
    blocks.push({
      type: "currency",
      name: item.currencyName || `资源${item.currencyType}`,
      gain: Number(s.gain) || 0,
      consume: Number(s.consume) || 0,
      net: Number(s.net) || 0,
      gains,
      consumes,
    });
  }
  return blocks;
}

function drawAlignedText(ctx, text, x, y, align = "left") {
  ctx.textAlign = align;
  ctx.fillText(text, x, y);
  ctx.textAlign = "left";
}

function generateReportImage(profile, query) {
  const blocks = buildReportBlocks(profile, query);
  const width = 920;
  const padX = 52;
  const padY = 48;
  const contentRight = width - padX;
  const col = {
    label: padX,
    amount: contentRight - 120,
    pct: contentRight,
  };
  const summaryCols = [
    { key: "gain", x: padX, label: "获取" },
    { key: "consume", x: padX + 250, label: "消耗" },
    { key: "net", x: padX + 500, label: "净变化" },
  ];

  const measureHeight = () => {
    let h = padY + 10;
    for (const block of blocks) {
      if (block.type === "title") {
        h += 56;
        continue;
      }
      if (block.type === "meta") {
        h += 36;
        continue;
      }
      if (block.type === "range") {
        h += 42;
        continue;
      }
      const headerH = 124;
      const gainsH = block.gains.length ? 30 + block.gains.length * 28 : 0;
      const consumesH = block.consumes.length ? 30 + block.consumes.length * 28 : 0;
      h += headerH + gainsH + consumesH + 22;
    }
    return h + padY;
  };

  const height = Math.max(measureHeight(), 420);
  const canvas = document.createElement("canvas");
  const scale = Math.min(2, window.devicePixelRatio || 1);
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;

  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  ctx.textBaseline = "alphabetic";

  const grad = ctx.createLinearGradient(0, 0, width, height);
  grad.addColorStop(0, "#eef4f1");
  grad.addColorStop(0.5, "#f7f8f6");
  grad.addColorStop(1, "#f3efe9");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = REPORT_COLORS.line;
  ctx.lineWidth = 1;
  ctx.strokeRect(20, 20, width - 40, height - 40);

  let y = padY + 10;

  for (const block of blocks) {
    if (block.type === "title") {
      ctx.fillStyle = REPORT_COLORS.ink;
      ctx.font = "700 40px Syne, Noto Sans SC, sans-serif";
      ctx.fillText(block.text, padX, y + 32);
      y += 56;
      continue;
    }
    if (block.type === "meta") {
      ctx.fillStyle = REPORT_COLORS.accent;
      ctx.font = "500 22px Noto Sans SC, sans-serif";
      ctx.fillText(block.text, padX, y + 18);
      y += 36;
      continue;
    }
    if (block.type === "range") {
      ctx.fillStyle = REPORT_COLORS.muted;
      ctx.font = "400 17px Noto Sans SC, sans-serif";
      ctx.fillText(block.text, padX, y + 14);
      y += 42;
      continue;
    }

    const headerH = 124;
    const gainsH = block.gains.length ? 30 + block.gains.length * 28 : 0;
    const consumesH = block.consumes.length ? 30 + block.consumes.length * 28 : 0;
    const cardH = headerH + gainsH + consumesH;
    const cardTop = y;

    ctx.fillStyle = REPORT_COLORS.card;
    roundRect(ctx, padX - 18, cardTop, width - padX * 2 + 36, cardH, 16);
    ctx.fill();

    let cy = cardTop + 34;
    ctx.fillStyle = REPORT_COLORS.ink;
    ctx.font = "700 24px Noto Sans SC, sans-serif";
    ctx.fillText(block.name, padX, cy);

    cy += 28;
    ctx.font = "500 14px Noto Sans SC, sans-serif";
    ctx.fillStyle = REPORT_COLORS.muted;
    for (const c of summaryCols) {
      ctx.fillText(c.label, c.x, cy);
    }

    cy += 28;
    ctx.font = "600 24px IBM Plex Mono, Noto Sans SC, monospace";
    for (const c of summaryCols) {
      let value = "";
      let color = REPORT_COLORS.ink;
      if (c.key === "gain") {
        value = `+${block.gain}`;
        color = REPORT_COLORS.gain;
      } else if (c.key === "consume") {
        value = `-${block.consume}`;
        color = REPORT_COLORS.consume;
      } else {
        value = `${block.net >= 0 ? "+" : ""}${block.net}`;
        color =
          block.net > 0
            ? REPORT_COLORS.gain
            : block.net < 0
              ? REPORT_COLORS.consume
              : REPORT_COLORS.ink;
      }
      ctx.fillStyle = color;
      ctx.fillText(value, c.x, cy);
    }

    cy += 18;
    ctx.strokeStyle = REPORT_COLORS.line;
    ctx.beginPath();
    ctx.moveTo(padX, cy);
    ctx.lineTo(contentRight, cy);
    ctx.stroke();
    cy += 26;

    const drawReasonSection = (title, rows, total, tone) => {
      if (!rows.length) return;
      ctx.fillStyle = tone;
      ctx.font = "600 15px Noto Sans SC, sans-serif";
      ctx.fillText(title, padX, cy);
      cy += 26;

      for (const r of rows) {
        const amount = Number(r.amount) || 0;
        const share = pct(amount, total);
        ctx.fillStyle = REPORT_COLORS.ink;
        ctx.font = "400 16px Noto Sans SC, sans-serif";
        ctx.fillText(
          truncateText(ctx, String(r.label || "-"), col.amount - col.label - 24),
          col.label,
          cy
        );

        ctx.fillStyle = tone;
        ctx.font = "500 16px IBM Plex Mono, Noto Sans SC, monospace";
        drawAlignedText(ctx, String(amount), col.amount, cy, "right");

        ctx.fillStyle = REPORT_COLORS.muted;
        ctx.font = "400 14px IBM Plex Mono, Noto Sans SC, monospace";
        drawAlignedText(ctx, `${share}%`, col.pct, cy, "right");
        cy += 28;
      }
      cy += 4;
    };

    drawReasonSection("获取原因", block.gains, block.gain, REPORT_COLORS.gain);
    drawReasonSection("消耗原因", block.consumes, block.consume, REPORT_COLORS.consume);

    y = cardTop + cardH + 22;
  }

  return canvas;
}

function truncateText(ctx, text, maxWidth) {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let out = text;
  while (out.length > 1 && ctx.measureText(`${out}…`).width > maxWidth) {
    out = out.slice(0, -1);
  }
  return `${out}…`;
}

function roundRect(ctx, x, y, w, h, r) {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}

function downloadCanvas(canvas, filename) {
  const link = document.createElement("a");
  link.download = filename;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

const reportModal = document.getElementById("reportModal");
const reportPreview = document.getElementById("reportPreview");
const btnSaveReport = document.getElementById("btnSaveReport");
let pendingReport = null;

function openReportPreview(canvas, filename) {
  pendingReport = { canvas, filename };
  reportPreview.src = canvas.toDataURL("image/png");
  reportModal.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeReportPreview() {
  reportModal.classList.add("hidden");
  document.body.style.overflow = "";
  reportPreview.removeAttribute("src");
  pendingReport = null;
}

reportModal.querySelectorAll("[data-close-report]").forEach((el) => {
  el.addEventListener("click", () => {
    closeReportPreview();
  });
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !reportModal.classList.contains("hidden")) {
    closeReportPreview();
  }
});

btnSaveReport.addEventListener("click", () => {
  if (!pendingReport) return;
  downloadCanvas(pendingReport.canvas, pendingReport.filename);
  queryStatus.textContent = "汇总报告已保存";
  closeReportPreview();
});

btnReport.addEventListener("click", () => {
  if (!lastQuery || !lastQuery.results || !lastQuery.results.length) {
    queryStatus.textContent = "请先完成一次查询";
    return;
  }
  try {
    const canvas = generateReportImage(lastProfile, lastQuery);
    const name = `endlogs_${lastQuery.startDate}_${lastQuery.endDate}.png`;
    openReportPreview(canvas, name);
    queryStatus.textContent = "已生成预览，确认后可保存";
  } catch (err) {
    queryStatus.textContent = err.message || "生成报告失败";
  }
});

queryForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const startDate = startDateEl.value;
  const endDate = endDateEl.value;
  const changeType = Number(document.getElementById("changeType").value);
  const currencyTypes = [...document.querySelectorAll('input[name="currency"]:checked')].map((el) =>
    Number(el.value)
  );

  if (!currencyTypes.length) {
    queryStatus.textContent = "请至少选择一种资源";
    return;
  }

  btnQuery.disabled = true;
  btnReport.disabled = true;
  queryStatus.textContent = "正在拉取并汇总，区间越长耗时越久…";
  resultsEl.classList.add("hidden");
  resultsEl.innerHTML = "";

  try {
    const data = await api("/api/query", {
      method: "POST",
      body: JSON.stringify({
        start_date: startDate,
        end_date: endDate,
        currency_types: currencyTypes,
        change_type: changeType,
      }),
    });
    lastQuery = {
      startDate,
      endDate,
      changeType,
      results: data.results || [],
    };
    resultsEl.innerHTML = data.results
      .map((item) => renderResult(item, startDate, endDate, changeType))
      .join("");
    resultsEl.classList.remove("hidden");
    const total = data.results.reduce((n, r) => n + (r.summary?.recordCount || 0), 0);
    queryStatus.textContent = `完成：共 ${total} 条记录（${formatZhDate(startDate)} — ${formatZhDate(endDate)}）`;
    btnReport.disabled = !data.results.length;
  } catch (err) {
    lastQuery = null;
    queryStatus.textContent = err.message;
  } finally {
    btnQuery.disabled = false;
  }
});

refreshAuth().catch((err) => {
  authMessage.textContent = err.message;
});
