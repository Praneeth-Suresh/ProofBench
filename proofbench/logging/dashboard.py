from __future__ import annotations

import base64
import json
from pathlib import Path

from proofbench.logging.result_store import summarize


def write_dashboard(rows: list[dict], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = summarize(rows)
    payload = json.dumps({"rows": rows, "summary": summary}, ensure_ascii=False)
    payload_b64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    output_path.write_text(_template(payload_b64), encoding="utf-8")
    return output_path


def _template(payload_b64: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ProofBench Dashboard</title>
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3' fill='%232f7d7e'/%3E%3Cpath d='M4 8.2 6.4 10.6 12.2 4.8' fill='none' stroke='white' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0; background: #f7f7f4; color: #1f2933; }}
    header {{ padding: 28px 32px 16px; border-bottom: 1px solid #d8d8d0; background: #ffffff; }}
    main {{ padding: 24px 32px 40px; max-width: 1180px; margin: 0 auto; }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    h2 {{ font-size: 18px; margin: 0 0 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 18px; }}
    .panel {{ background: #ffffff; border: 1px solid #d8d8d0; border-radius: 8px; padding: 16px; }}
    .actions {{ display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }}
    button {{ border: 1px solid #8aa3a8; background: #eef6f6; color: #11343b; border-radius: 6px; padding: 8px 10px; cursor: pointer; }}
    button.secondary {{ background: #ffffff; border-color: #c9d1d3; color: #1f2933; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; background: #fff; border: 1px solid #d8d8d0; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #e7e7df; font-size: 13px; }}
    th {{ background: #eceee8; }}
    svg {{ width: 100%; height: 260px; }}
    .empty {{ padding: 24px; background: #fff; border: 1px solid #d8d8d0; border-radius: 8px; }}
    .modal-backdrop {{ position: fixed; inset: 0; background: rgba(15, 23, 42, 0.58); display: none; align-items: center; justify-content: center; padding: 22px; z-index: 20; }}
    .modal-backdrop.open {{ display: flex; }}
    .modal {{ width: min(1080px, 96vw); max-height: 90vh; background: #ffffff; border-radius: 8px; border: 1px solid #cfd8d9; box-shadow: 0 24px 80px rgba(15, 23, 42, 0.34); display: grid; grid-template-rows: auto 1fr; overflow: hidden; }}
    .modal-header {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; padding: 16px 18px; border-bottom: 1px solid #e1e6e6; background: #f5f8f7; }}
    .modal-title {{ margin: 0; font-size: 18px; }}
    .modal-meta {{ margin: 6px 0 0; color: #526066; font-size: 13px; }}
    .modal-body {{ overflow: auto; padding: 18px; display: grid; gap: 16px; }}
    .detail-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }}
    .detail-stat {{ border: 1px solid #e1e6e6; background: #fbfcfb; border-radius: 6px; padding: 10px; }}
    .detail-label {{ display: block; color: #66757b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; }}
    .detail-value {{ font-size: 14px; font-weight: 700; }}
    .detail-section h3 {{ margin: 0 0 8px; font-size: 14px; }}
    pre {{ margin: 0; padding: 12px; border: 1px solid #dce4e4; border-radius: 6px; background: #101820; color: #eef7f2; overflow: auto; white-space: pre-wrap; word-break: break-word; font-size: 12px; line-height: 1.5; }}
    pre.diagnostics {{ background: #fcfbf6; color: #2f3437; }}
    @media (max-width: 720px) {{
      main {{ padding: 16px; }}
      th, td {{ padding: 7px 8px; }}
      .modal-backdrop {{ padding: 10px; align-items: stretch; }}
      .modal {{ width: 100%; max-height: 96vh; }}
    }}
  </style>
</head>
<body>
<header>
  <h1>ProofBench Results</h1>
  <p>Compiler-verified accuracy, continuous proof-quality signals, model/tool efficiency, and runtime comparison.</p>
</header>
<main>
  <div id="app"></div>
</main>
<script id="payload" type="application/json">{payload_b64}</script>
<script>
const data = JSON.parse(atob(document.getElementById("payload").textContent.trim()));
const app = document.getElementById("app");
function trimTrailingZeros(text) {{
  return text.replace(/\\.?0+$/, "").replace(/\\.$/, "");
}}

function formatMetricValue(value) {{
  if (value === null || value === undefined) {{
    return "";
  }}
  if (!Number.isFinite(value)) {{
    return String(value);
  }}
  if (value === 0) {{
    return "0";
  }}

  const abs = Math.abs(value);
  if (abs >= 1) {{
    return trimTrailingZeros(value.toFixed(3));
  }}
  if (abs >= 1e-1) {{
    return trimTrailingZeros(value.toFixed(4));
  }}
  if (abs >= 1e-3) {{
    return trimTrailingZeros(value.toFixed(5));
  }}
  if (abs >= 1e-6) {{
    return trimTrailingZeros(value.toFixed(6));
  }}
  return value.toExponential(3);
}}

function escapeHtml(value) {{
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}}

function formatJson(value) {{
  if (value === null || value === undefined) {{
    return "";
  }}
  return JSON.stringify(value, null, 2);
}}

const metrics = [
  ["accuracy", "Accuracy"],
  ["avg_proof_quality_score", "Avg Proof Quality"],
  ["avg_proof_progress", "Avg Proof Progress"],
  ["avg_total_tokens", "Avg Tokens"],
  ["avg_model_calls", "Avg Model Calls"],
  ["avg_tool_calls", "Avg Tool Calls"],
  ["avg_total_elapsed_s", "Avg Runtime (s)"]
];

function download(filename, content, type) {{
  const blob = new Blob([content], {{type}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}}

function csv() {{
  const header = ["agent","task_id","accuracy","proof_quality_score","proof_progress","failure_profile","model_calls","total_tokens","tool_calls","total_elapsed_s","verifier","verifier_available"];
  const lines = [header.join(",")];
  for (const row of data.rows) {{
    lines.push([
      row.agent,
      row.task_id,
      row.accuracy,
      row.proof_quality_score,
      row.proof_progress,
      row.failure_profile,
      row.efficiency.model_calls,
      row.efficiency.total_tokens,
      row.efficiency.tool_calls,
      row.speed.total_elapsed_s,
      row.verification.verifier,
      row.verification.verifier_available
    ].map(v => JSON.stringify(v)).join(","));
  }}
  return lines.join("\\n");
}}

function chart(metric, title) {{
  const entries = Object.entries(data.summary);
  const max = Math.max(1e-9, ...entries.map(([, v]) => Number(v[metric] || 0)));
  const width = 640, height = 260, left = 120, right = 24, barH = 26, gap = 16;
  let parts = [`<svg viewBox="0 0 ${{width}} ${{height}}" data-title="${{title}}">`];
  parts.push(`<text x="0" y="18" font-size="15" font-weight="700">${{title}}</text>`);
  entries.forEach(([agent, vals], i) => {{
    const y = 44 + i * (barH + gap);
    const val = Number(vals[metric] || 0);
    const w = (width - left - right) * (val / max);
    parts.push(`<text x="0" y="${{y + 18}}" font-size="12">${{agent}}</text>`);
    parts.push(`<rect x="${{left}}" y="${{y}}" width="${{Math.max(1, w)}}" height="${{barH}}" fill="#2f7d7e"></rect>`);
    parts.push(`<text x="${{left + w + 8}}" y="${{y + 18}}" font-size="12">${{formatMetricValue(val)}}</text>`);
  }});
  parts.push(`</svg>`);
  return parts.join("");
}}

function openRunModal(index) {{
  const row = data.rows[index];
  const modal = document.getElementById("run-modal");
  const content = document.getElementById("run-modal-content");
  const failureProfile = row.failure_profile || row.verification?.failure_profile || {{}};
  const diagnostics = row.verification?.diagnostics || "";
  const rawAnswer = row.raw_answer || "";
  content.innerHTML = `
    <div class="modal-header">
      <div>
        <h2 class="modal-title">${{escapeHtml(row.agent)}} on ${{escapeHtml(row.task_id)}}</h2>
        <p class="modal-meta">${{escapeHtml(row.model || "unknown model")}} · ${{escapeHtml(row.verification?.verifier || "unknown verifier")}}</p>
      </div>
      <button class="secondary" onclick="closeRunModal()" aria-label="Close run output">Close</button>
    </div>
    <div class="modal-body">
      <div class="detail-grid">
        <div class="detail-stat"><span class="detail-label">Accuracy</span><span class="detail-value">${{formatMetricValue(row.accuracy)}}</span></div>
        <div class="detail-stat"><span class="detail-label">Proof quality</span><span class="detail-value">${{formatMetricValue(row.proof_quality_score)}}</span></div>
        <div class="detail-stat"><span class="detail-label">Proof progress</span><span class="detail-value">${{formatMetricValue(row.proof_progress)}}</span></div>
        <div class="detail-stat"><span class="detail-label">Verifier available</span><span class="detail-value">${{escapeHtml(row.verification?.verifier_available)}}</span></div>
      </div>
      <section class="detail-section">
        <h3>LLM Output</h3>
        <pre id="modal-raw-answer"><code>${{escapeHtml(rawAnswer)}}</code></pre>
      </section>
      <section class="detail-section">
        <h3>Lean Diagnostics</h3>
        <pre class="diagnostics" id="modal-diagnostics"><code>${{escapeHtml(diagnostics || "No diagnostics recorded.")}}</code></pre>
      </section>
      <section class="detail-section">
        <h3>Failure Profile</h3>
        <pre class="diagnostics" id="modal-failure-profile"><code>${{escapeHtml(formatJson(failureProfile))}}</code></pre>
      </section>
    </div>`;
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
}}

function closeRunModal() {{
  const modal = document.getElementById("run-modal");
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}}

document.addEventListener("keydown", (event) => {{
  if (event.key === "Escape") {{
    closeRunModal();
  }}
}});

function render() {{
  if (!data.rows.length) {{
    app.innerHTML = `<div class="empty">No results found. Run <code>proofbench run</code> first.</div>`;
    return;
  }}
  const panels = metrics.map(([metric, title], idx) => `
    <section class="panel">
      <h2>${{title}}</h2>
      <div id="chart-${{idx}}">${{chart(metric, title)}}</div>
      <div class="actions">
        <button onclick="download('proofbench-${{metric}}.svg', document.querySelector('#chart-${{idx}} svg').outerHTML, 'image/svg+xml')">Download SVG</button>
      </div>
    </section>`).join("");
  const rows = data.rows.map((row, idx) => `
    <tr>
      <td>${{row.agent}}</td><td>${{row.task_id}}</td><td>${{row.accuracy}}</td>
      <td>${{formatMetricValue(row.proof_quality_score)}}</td><td>${{formatMetricValue(row.proof_progress)}}</td>
      <td>${{row.efficiency.total_tokens}}</td><td>${{row.efficiency.tool_calls}}</td>
      <td>${{formatMetricValue(row.speed.total_elapsed_s)}}</td><td>${{row.verification.verifier}}</td>
      <td><button class="secondary" onclick="openRunModal(${{idx}})">View output</button></td>
    </tr>`).join("");
  app.innerHTML = `
    <div class="actions">
      <button onclick="download('proofbench-results.csv', csv(), 'text/csv')">Download CSV</button>
      <button onclick="download('proofbench-results.json', JSON.stringify(data.rows, null, 2), 'application/json')">Download JSON</button>
    </div>
    <div class="grid">${{panels}}</div>
    <table>
      <thead><tr><th>Agent</th><th>Task</th><th>Accuracy</th><th>Quality</th><th>Progress</th><th>Tokens</th><th>Tool Calls</th><th>Total s</th><th>Verifier</th><th>Output</th></tr></thead>
      <tbody>${{rows}}</tbody>
    </table>
    <div id="run-modal" class="modal-backdrop" aria-hidden="true" role="dialog" aria-modal="true" onclick="if (event.target === this) closeRunModal()">
      <div class="modal" id="run-modal-content"></div>
    </div>`;
}}
render();
</script>
</body>
</html>
"""
