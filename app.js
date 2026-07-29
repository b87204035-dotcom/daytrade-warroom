const fmt = new Intl.NumberFormat("zh-TW");
const signed = n => `${Number(n) > 0 ? "+" : ""}${fmt.format(Number(n || 0))}`;
const cls = n => Number(n) >= 0 ? "up" : "down";
const text = (id, value) => document.getElementById(id).textContent = value ?? "—";

function rowOrEmpty(items, columns, mapper) {
  if (!items?.length) return `<tr><td class="empty" colspan="${columns}">目前沒有符合條件的標的</td></tr>`;
  return items.map(mapper).join("");
}

async function loadReport() {
  try {
    const res = await fetch(`data/latest.json?t=${Date.now()}`, {cache:"no-store"});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const d = await res.json();

    text("updatedAt", `資料日期：${d.report_date || "—"}｜更新時間：${d.generated_at || "—"}`);
    text("marketBias", d.market?.bias || "中性觀察");
    text("marketReason", d.market?.reason || "等待更多資料確認");
    text("riskLevel", d.market?.risk || "中");
    const tag = document.getElementById("marketTag");
    tag.textContent = d.market?.tag || "中性";
    tag.className = `tag ${d.market?.tone || "neutral"}`;

    text("foreignOI", signed(d.futures?.foreign_net_oi));
    text("trustOI", signed(d.futures?.trust_net_oi));
    text("dealerOI", signed(d.futures?.dealer_net_oi));
    text("pcr", d.futures?.put_call_ratio ?? "—");

    document.getElementById("longRows").innerHTML = rowOrEmpty(d.long_candidates, 9, s => `
      <tr>
        <td><strong>${s.code}</strong></td><td>${s.name}</td><td>${s.close}</td>
        <td class="${cls(s.change_pct)}">${signed(s.change_pct)}%</td>
        <td>${fmt.format(s.volume)}</td><td>${s.volume_ratio ?? "—"}</td>
        <td class="${cls(s.foreign_net)}">${signed(s.foreign_net)}</td>
        <td class="score">${s.score}</td><td>${s.reason}</td>
      </tr>`);

    document.getElementById("reversalRows").innerHTML = rowOrEmpty(d.reversal_watch, 6, s => `
      <tr><td><strong>${s.code}</strong></td><td>${s.name}</td><td>${s.type}</td>
      <td>${fmt.format(s.volume)}</td><td class="${cls(s.foreign_net)}">${signed(s.foreign_net)}</td><td>${s.note}</td></tr>`);

    document.getElementById("riskList").innerHTML = (d.risks || []).map(x => `<li>${x}</li>`).join("") || "<li>目前沒有新增風險警示</li>";
    document.getElementById("sourceStatus").innerHTML = Object.entries(d.sources || {}).map(([k,v]) =>
      `<span class="source-pill ${v.ok ? "ok":"fail"}">${k}：${v.ok ? "正常":"失敗"}${v.note ? `（${v.note}）`:""}</span>`).join("");
  } catch (e) {
    text("updatedAt", `載入失敗：${e.message}`);
    document.getElementById("sourceStatus").innerHTML = `<span class="source-pill fail">網站資料載入失敗</span>`;
  }
}
loadReport();
