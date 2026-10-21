/* Dashboard giao thông New York — gọi FastAPI /api/v1, vẽ bằng Chart.js + Leaflet.
   Mọi chữ lấy từ API được đưa vào DOM bằng textContent (không innerHTML) để tránh chèn mã. */
"use strict";

const API = "/api/v1";
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const C = {
  s1: css("--series-1"), s2: css("--series-2"), grid: css("--grid"), axis: css("--axis"),
  text2: css("--text-secondary"), muted: css("--text-muted"), outage: css("--outage"),
  low: css("--div-low"), mid: css("--div-mid"), high: css("--div-high"), surface: css("--surface-1"),
};
const nf0 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });
const nf1 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1 });
const nf2 = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 });
const fmt = (v, f = nf1) => (v === null || v === undefined ? "—" : f.format(v));
const compact = (v) => v >= 1e6 ? nf1.format(v / 1e6) + " triệu" : v >= 1e4 ? nf1.format(v / 1e3) + " nghìn" : nf0.format(v);

// ------------------------------------------------------------------ tiện ích
async function get(path, params = {}) {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v !== null && v !== undefined));
  const r = await fetch(`${API}${path}${q.toString() ? "?" + q : ""}`);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body?.error?.message || `HTTP ${r.status}`);
  return body;
}

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else if (k === "on") Object.entries(v).forEach(([ev, fn]) => e.addEventListener(ev, fn));
    else e.setAttribute(k, v);
  }
  for (const c of children.flat()) e.append(c instanceof Node ? c : document.createTextNode(c ?? ""));
  return e;
}

/** columns: [{key, label, num?, f?}] → bảng (bảng là "table view" cho mọi biểu đồ) */
function table(target, rows, columns, onRow) {
  const t = el("table", {},
    el("thead", {}, el("tr", {}, columns.map((c) => el("th", { class: c.num ? "num" : "" }, c.label)))),
    el("tbody", {}, rows.map((r) => {
      const tr = el("tr", { class: onRow ? "click" : "" }, columns.map((c) => {
        const v = c.f ? c.f(r[c.key]) : r[c.key];
        const td = el("td", { class: c.num ? "num" : "" }, v instanceof Node ? v : String(v ?? "—"));
        if (c.neg && typeof r[c.key] === "number" && r[c.key] < 0) td.classList.add("neg");
        return td;
      }));
      if (onRow) tr.addEventListener("click", () => onRow(r));
      return tr;
    })));
  const box = typeof target === "string" ? document.getElementById(target) : target;
  box.replaceChildren(t);
}

function setStatus(msg, err = false) {
  const s = document.getElementById("status");
  s.textContent = msg;
  s.classList.toggle("err", err);
}

// ------------------------------------------------------------------ Chart.js: cấu hình chung theo skill dataviz
Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", sans-serif';
Chart.defaults.font.size = 12;
Chart.defaults.color = C.text2;
Chart.defaults.borderColor = C.grid;
Chart.defaults.animation = false;
Chart.defaults.maintainAspectRatio = false;
Chart.defaults.plugins.tooltip.backgroundColor = "rgba(20,20,19,.92)";
Chart.defaults.plugins.tooltip.padding = 8;
Chart.defaults.plugins.legend.labels.boxWidth = 14;
Chart.defaults.plugins.legend.labels.boxHeight = 2;      // khóa dạng đường kẻ cho line chart

const charts = {};
function draw(id, config) {
  charts[id]?.destroy();
  if (config.type === "bar") {          // chú giải mô phỏng dấu: ô chữ nhật cho cột, đường kẻ cho line
    config.options = config.options || {};
    config.options.plugins = { ...(config.options.plugins || {}) };
    config.options.plugins.legend = { ...(config.options.plugins.legend || {}), labels: { boxWidth: 10, boxHeight: 10 } };
  }
  charts[id] = new Chart(document.getElementById(id), config);
  return charts[id];
}
const axisY = (title, extra = {}) => ({ grid: { color: C.grid }, border: { display: false },
  title: { display: !!title, text: title, color: C.muted }, ticks: { color: C.muted }, ...extra });
const axisX = (extra = {}) => ({ grid: { display: false }, border: { color: C.axis }, ticks: { color: C.muted }, ...extra });
const line = (label, data, color, extra = {}) => ({ label, data, borderColor: color, backgroundColor: color, borderWidth: 2,
  pointRadius: 0, pointHoverRadius: 4, tension: 0, ...extra });
const bars = (label, data, color, extra = {}) => ({ label, data, backgroundColor: color, maxBarThickness: 24,
  borderRadius: { topLeft: 4, topRight: 4 }, borderSkipped: "start", ...extra });
const hbars = (label, data, color) => ({ label, data, backgroundColor: color, maxBarThickness: 18,
  borderRadius: { topRight: 4, bottomRight: 4 }, borderSkipped: "start" });

// ------------------------------------------------------------------ TỔNG QUAN
async function loadOverview() {
  const [s, hd, daily, dist] = await Promise.all([
    get("/statistics/summary"), get("/statistics", { dimension: "hour_daytype" }), get("/statistics/daily"),
    get("/statistics", { dimension: "district", metric: "avg_speed" })]);
  const fmtDate = (t) => t ? new Date(t).toLocaleDateString("vi-VN") : "—";
  const tiles = [
    { label: "Bản ghi tích hợp", value: compact(s.records), note: `${nf0.format(s.speed_records)} tốc độ · ${nf0.format(s.volume_records)} lưu lượng`, hero: true },
    { label: "Đường", value: nf0.format(s.roads), note: `${s.roads_with_speed} có tốc độ · ${s.roads_with_volume} có lưu lượng` },
    { label: "Tốc độ trung bình", value: `${fmt(s.mean_speed)} km/h`, note: "toàn thành phố, cả năm" },
    { label: "Bất thường (|z| > 3)", value: nf0.format(s.anomalies), note: "Z-score theo ngữ cảnh" },
    { label: "Thời gian", value: [...new Set([s.first_timestamp, s.last_timestamp].filter(Boolean).map((t) => t.slice(0, 4)))].join("–") || "—", note: `${fmtDate(s.first_timestamp)} – ${fmtDate(s.last_timestamp)} · ${s.outage_days} ngày mất dữ liệu` },
  ];
  document.getElementById("tiles").replaceChildren(...tiles.map((t) =>
    el("div", { class: "tile" + (t.hero ? " hero" : "") }, el("div", { class: "label" }, t.label),
       el("div", { class: "value" }, t.value), el("div", { class: "note" }, t.note))));

  const hours = [...Array(24).keys()];
  const pick = (metric, type) => hours.map((h) => {
    const r = hd.find((x) => x.metric === metric && x.group_key === `${type} ${String(h).padStart(2, "0")}h`);
    return r ? r.mean : null;
  });
  const hourCfg = (metric, unit) => ({
    type: "line",
    data: { labels: hours.map((h) => `${h}h`), datasets: [line("Ngày thường", pick(metric, "Ngày thường"), C.s1),
                                                         line("Cuối tuần", pick(metric, "Cuối tuần"), C.s2)] },
    options: { interaction: { mode: "index", intersect: false }, scales: { x: axisX(), y: axisY(unit) },
               plugins: { tooltip: { callbacks: { label: (c) => ` ${fmt(c.parsed.y)} ${unit} · ${c.dataset.label}` } } } },
  });
  draw("ch-hour-speed", hourCfg("avg_speed", "km/h"));
  draw("ch-hour-volume", hourCfg("vehicle_count", "xe/giờ"));

  const labels = daily.map((d) => d.date);
  draw("ch-daily", {
    type: "line",
    data: { labels, datasets: [line("Tốc độ TB (km/h)", daily.map((d) => d.mean_speed), C.s1, {
      pointRadius: daily.map((d) => (d.is_outage ? 3 : 0)),
      pointBackgroundColor: daily.map((d) => (d.is_outage ? C.outage : C.s1)),
      pointBorderColor: daily.map((d) => (d.is_outage ? C.outage : C.s1)),
      segment: { borderColor: (ctx) => (daily[ctx.p1DataIndex]?.is_outage || daily[ctx.p0DataIndex]?.is_outage ? C.outage : C.s1) },
    })] },
    options: { interaction: { mode: "index", intersect: false },
      scales: { x: axisX({ ticks: { color: C.muted, maxTicksLimit: 12 } }), y: axisY("km/h") },
      plugins: { legend: { display: false }, tooltip: { callbacks: {
        title: (it) => new Date(it[0].label).toLocaleDateString("vi-VN", { weekday: "short", day: "numeric", month: "numeric" }),
        label: (c) => { const d = daily[c.dataIndex];
          return [` ${fmt(d.mean_speed)} km/h`, ` mưa ${fmt(d.rain_mm_per_day)} mm · tuyết ${fmt(d.snow_cm_per_day)} cm`,
                  d.is_outage ? ` mất dữ liệu (độ phủ ${fmt(d.coverage_pct)}%)` : ""].filter(Boolean); } } } } },
  });
  draw("ch-rain", {
    type: "bar",
    data: { labels, datasets: [bars("Mưa (mm/ngày)", daily.map((d) => d.rain_mm_per_day), C.s1, { maxBarThickness: 4, borderRadius: 1 })] },
    options: { scales: { x: axisX({ ticks: { display: false } }), y: axisY("mm", { ticks: { maxTicksLimit: 3, color: C.muted } }) },
               plugins: { legend: { display: false } } },
  });

  const d = [...dist].sort((a, b) => a.mean - b.mean);
  draw("ch-district", {
    type: "bar",
    data: { labels: d.map((x) => x.group_key), datasets: [hbars("Tốc độ TB (km/h)", d.map((x) => x.mean), C.s1)] },
    options: { indexAxis: "y", scales: { x: axisY("km/h"), y: axisX() }, plugins: { legend: { display: false },
      tooltip: { callbacks: { label: (c) => ` ${fmt(c.parsed.x)} km/h · trung vị ${fmt(d[c.dataIndex].median)}` } } } },
  });
  table("tb-district", d, [{ key: "group_key", label: "Quận" }, { key: "n", label: "Số giờ đo", num: true, f: (v) => nf0.format(v) },
    { key: "mean", label: "TB", num: true, f: fmt }, { key: "median", label: "Trung vị", num: true, f: fmt },
    { key: "std", label: "Độ lệch chuẩn", num: true, f: fmt }, { key: "min", label: "Min", num: true, f: fmt },
    { key: "max", label: "Max", num: true, f: fmt }]);
}

// ------------------------------------------------------------------ BẢN ĐỒ
let map, layer, roadsCache, statsSpeed, statsVol;
function divColor(v, mid, span) {        // phân kỳ: đỏ (chậm) – xám – xanh (nhanh)
  const t = Math.max(-1, Math.min(1, (v - mid) / span));
  const mix = (a, b, k) => { const pa = a.match(/\w\w/g).map((h) => parseInt(h, 16)), pb = b.match(/\w\w/g).map((h) => parseInt(h, 16));
    return "#" + pa.map((x, i) => Math.round(x + (pb[i] - x) * k).toString(16).padStart(2, "0")).join(""); };
  return t < 0 ? mix(C.mid, C.low, -t) : mix(C.mid, C.high, t);
}
async function loadMap() {
  if (!map) {
    map = L.map("map", { preferCanvas: true }).setView([40.70, -73.93], 11);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 18, attribution: "© OpenStreetMap contributors" }).addTo(map);
    [roadsCache, statsSpeed, statsVol] = await Promise.all([get("/roads", { page_size: 1000 }).then((r) => r.items),
      get("/statistics", { dimension: "road", metric: "avg_speed" }), get("/statistics", { dimension: "road", metric: "vehicle_count" })]);
    const sel = document.getElementById("map-district");
    [...new Set(roadsCache.map((r) => r.district).filter(Boolean))].sort().forEach((d) => sel.append(el("option", { value: d }, d)));
    sel.onchange = renderMap;
    document.getElementById("map-mode").onchange = renderMap;
  }
  setTimeout(() => map.invalidateSize(), 50);
  renderMap();
}
function renderMap() {
  const district = document.getElementById("map-district").value;
  const mode = document.getElementById("map-mode").value;
  const stats = Object.fromEntries((mode === "speed" ? statsSpeed : statsVol).map((s) => [s.group_key, s]));
  const means = Object.values(stats).map((s) => s.mean).sort((a, b) => a - b);
  const mid = means[Math.floor(means.length / 2)] ?? 0;
  const span = Math.max(mid - means[0], means[means.length - 1] - mid) || 1;
  layer?.remove();
  layer = L.layerGroup().addTo(map);
  const shown = roadsCache.filter((r) => r.latitude && stats[r.road_id] && (!district || r.district === district));
  for (const r of shown) {
    const s = stats[r.road_id];
    const color = mode === "speed" ? divColor(s.mean, mid, span) : C.s2;
    const radius = mode === "speed" ? 7 : 4 + 10 * Math.sqrt(s.mean / means[means.length - 1]);
    L.circleMarker([r.latitude, r.longitude], { radius, color: C.surface, weight: 2, fillColor: color, fillOpacity: 0.95 })
      .bindTooltip(`${r.road_name} · ${fmt(s.mean)} ${mode === "speed" ? "km/h" : "xe/giờ"}`)
      .on("click", () => showRoad(r.road_id)).addTo(layer);
  }
  const leg = document.getElementById("map-legend");
  leg.replaceChildren(...(mode === "speed"
    ? [el("span", {}, `${fmt(means[0], nf0)} km/h`), el("div", { class: "bar" }), el("span", {}, `${fmt(means[means.length - 1], nf0)} km/h`)]
    : [el("span", {}, `Kích thước điểm ∝ lưu lượng TB · ${shown.length} điểm đếm`)]));
  if (shown.length) map.fitBounds(L.latLngBounds(shown.map((r) => [r.latitude, r.longitude])).pad(0.1), { maxZoom: 13 });
}
async function showRoad(id) {
  const panel = document.getElementById("road-panel");
  panel.style.opacity = 0.5;
  try {
    const [r, ts, an] = await Promise.all([get(`/roads/${encodeURIComponent(id)}`),
      get("/traffic/timeseries", { road_id: id, bucket: "week" }),
      get("/anomalies", { road_id: id, page_size: 8, order: "z" })]);
    const s = r.stats;
    const kv = el("div", { class: "kv" },
      el("span", {}, "Mã"), el("span", {}, r.road_id), el("span", {}, "Quận"), el("span", {}, r.district || "—"),
      el("span", {}, "Tốc độ TB"), el("span", {}, s.n_speed ? `${fmt(s.mean_speed)} km/h (±${fmt(s.std_speed)})` : "không có cảm biến"),
      el("span", {}, "Khoảng tốc độ"), el("span", {}, s.n_speed ? `${fmt(s.min_speed)} – ${fmt(s.max_speed)} km/h` : "—"),
      el("span", {}, "Lưu lượng TB"), el("span", {}, s.n_volume ? `${fmt(s.mean_volume, nf0)} xe/giờ (${nf0.format(s.n_volume)} giờ đếm)` : "không có điểm đếm"),
      el("span", {}, "Số giờ có dữ liệu"), el("span", {}, nf0.format(Math.max(s.n_speed, s.n_volume))),
      el("span", {}, "Bất thường"), el("span", {}, nf0.format(s.anomalies)));
    const canvasBox = el("div", { class: "chart" }, el("canvas", { id: "ch-road" }));
    const anBox = el("div", { class: "table-wrap" });
    panel.replaceChildren(el("h2", {}, r.road_name), kv,
      el("h3", { class: "mini" }, s.n_speed ? "Tốc độ trung bình mỗi tuần (km/h)" : "Lưu lượng trung bình mỗi tuần (xe/giờ)"),
      canvasBox, el("h3", { class: "mini" }, "Bất thường mạnh nhất"), anBox);
    const metric = s.n_speed ? "avg_speed" : "vehicle_count";
    draw("ch-road", { type: "line",
      data: { labels: ts.map((p) => new Date(p.bucket).toLocaleDateString("vi-VN", { day: "numeric", month: "numeric" })),
              datasets: [line(metric === "avg_speed" ? "km/h" : "xe/giờ", ts.map((p) => p[metric]), C.s1, { spanGaps: false, pointRadius: ts.length < 20 ? 3 : 0 })] },
      options: { interaction: { mode: "index", intersect: false }, scales: { x: axisX({ ticks: { color: C.muted, maxTicksLimit: 6 } }), y: axisY() },
                 plugins: { legend: { display: false } } } });
    if (an.items.length) table(anBox, an.items, [
      { key: "timestamp", label: "Thời điểm", f: (v) => v.replace("T", " ").slice(0, 16) },
      { key: "value", label: "Giá trị", num: true, f: fmt }, { key: "expected", label: "Bình thường", num: true, f: fmt },
      { key: "z_score", label: "z", num: true, f: fmt, neg: true }]);
    else anBox.replaceChildren(el("p", { class: "hint" }, "Không có bất thường."));
  } catch (e) { panel.replaceChildren(el("p", { class: "hint" }, `Lỗi: ${e.message}`)); }
  panel.style.opacity = 1;
}

// ------------------------------------------------------------------ THỜI TIẾT
async function loadWeather() {
  const all = await get("/statistics/weather-impact");
  const by = (dim) => all.filter((x) => x.dimension === dim);
  const strip = (k) => k.replace(/^\d\.\s*/, "");
  const cond = by("weather_condition");
  draw("ch-wx-cond", { type: "bar",
    data: { labels: cond.map((x) => x.group_key), datasets: [
      bars("Thô", cond.map((x) => x.raw_change_pct), C.s2, { borderRadius: 4, borderSkipped: false }),
      bars("Có kiểm soát (cùng đường, giờ, tháng)", cond.map((x) => x.controlled_month_change_pct), C.s1, { borderRadius: 4, borderSkipped: false })] },
    options: { scales: { x: axisX(), y: axisY("% thay đổi tốc độ") },
               plugins: { tooltip: { callbacks: { label: (c) => ` ${fmt(c.parsed.y, nf2)}% · ${c.dataset.label}` } } } } });
  table("tb-wx-cond", cond, [{ key: "group_key", label: "Thời tiết" }, { key: "n", label: "Số giờ", num: true, f: (v) => nf0.format(v) },
    { key: "n_days", label: "Số ngày", num: true }, { key: "raw_mean", label: "TB thô (km/h)", num: true, f: fmt },
    { key: "raw_change_pct", label: "Thô %", num: true, f: (v) => fmt(v, nf2), neg: true },
    { key: "controlled_change_pct", label: "Kiểm soát %", num: true, f: (v) => fmt(v, nf2), neg: true },
    { key: "controlled_month_change_pct", label: "Kiểm soát + mùa %", num: true, f: (v) => fmt(v, nf2), neg: true },
    { key: "ci95_pct", label: "± KTC 95%", num: true, f: (v) => fmt(v, nf2) }]);
  const single = (id, rows, field, label) => draw(id, { type: "bar",
    data: { labels: rows.map((x) => strip(x.group_key)), datasets: [bars(label, rows.map((x) => x[field]), C.s1, { borderRadius: 4, borderSkipped: false })] },
    options: { scales: { x: axisX(), y: axisY("%") }, plugins: { legend: { display: false },
      tooltip: { callbacks: { label: (c) => ` ${fmt(c.parsed.y, nf2)}% · ${nf0.format(rows[c.dataIndex].n)} giờ, ${rows[c.dataIndex].n_days} ngày` } } } } });
  single("ch-wx-rain", by("rainfall"), "controlled_month_change_pct", "Có kiểm soát");
  const temp = by("temperature");
  draw("ch-wx-temp", { type: "bar",
    data: { labels: temp.map((x) => strip(x.group_key)), datasets: [
      bars("Thô", temp.map((x) => x.raw_change_pct), C.s2, { borderRadius: 4, borderSkipped: false }),
      bars("Có kiểm soát", temp.map((x) => x.controlled_month_change_pct), C.s1, { borderRadius: 4, borderSkipped: false })] },
    options: { scales: { x: axisX(), y: axisY("%") } } });
}

// ------------------------------------------------------------------ BẤT THƯỜNG
let anPage = 1;
async function loadAnomalies(first = false) {
  if (first) {
    const dsel = document.getElementById("an-district");
    ["Bronx", "Brooklyn", "Manhattan", "Queens", "Staten Island"].forEach((d) => dsel.append(el("option", { value: d }, d)));
    ["an-metric", "an-district", "an-direction", "an-z"].forEach((id) =>
      (document.getElementById(id).onchange = () => { anPage = 1; loadAnomalyList(); loadAnomalySummary(); }));
    document.getElementById("an-prev").onclick = () => { anPage--; loadAnomalyList(); };
    document.getElementById("an-next").onclick = () => { anPage++; loadAnomalyList(); };
    const daily = await get("/anomalies/daily");
    draw("ch-an-daily", { type: "line",
      data: { labels: daily.map((d) => d.date), datasets: [
        line("Chậm bất thường", daily.map((d) => d.slow_anomalies), C.s1),
        line("Nhanh bất thường", daily.map((d) => d.fast_anomalies), C.s2)] },
      options: { interaction: { mode: "index", intersect: false },
        scales: { x: axisX({ ticks: { color: C.muted, maxTicksLimit: 12 } }), y: axisY("số bản ghi") },
        plugins: { tooltip: { callbacks: {
          title: (it) => new Date(it[0].label).toLocaleDateString("vi-VN", { weekday: "short", day: "numeric", month: "numeric" }),
          afterBody: (it) => { const d = daily[it[0].dataIndex];
            return [`tỉ lệ ${fmt(d.anomaly_rate_pct, nf2)}% · mưa ${fmt(d.rain_mm_per_day)} mm · tuyết ${fmt(d.snow_cm_per_day)} cm`,
                    d.coverage_pct !== null && d.coverage_pct < 50 ? `độ phủ dữ liệu chỉ ${fmt(d.coverage_pct)}%` : ""].filter(Boolean); } } } } } });
  }
  await Promise.all([loadAnomalyList(), loadAnomalySummary()]);
}
function anFilters() {
  return { metric: document.getElementById("an-metric").value, district: document.getElementById("an-district").value,
           direction: document.getElementById("an-direction").value, min_abs_z: document.getElementById("an-z").value };
}
async function loadAnomalySummary() {
  const s = await get("/anomalies/summary", { min_abs_z: anFilters().min_abs_z });
  const c = (arr, k) => arr.find((x) => x.key === k)?.count ?? 0;
  document.getElementById("an-tiles").replaceChildren(...[
    ["Bất thường", nf0.format(s.total), `|z| ≥ ${anFilters().min_abs_z}`],
    ["Tốc độ", nf0.format(c(s.by_metric, "avg_speed")), "chủ yếu là chậm bất thường"],
    ["Lưu lượng", nf0.format(c(s.by_metric, "vehicle_count")), "chỉ để tham khảo: dữ liệu đếm thưa"],
    ["Đường nhiều nhất", s.top_roads[0]?.road_name ?? "—", s.top_roads[0] ? `${nf0.format(s.top_roads[0].count)} lần` : ""],
  ].map(([l, v, n]) => el("div", { class: "tile" }, el("div", { class: "label" }, l),
         el("div", { class: "value" + (String(v).length > 12 ? " text" : "") }, v), el("div", { class: "note" }, n))));
}
async function loadAnomalyList() {
  const box = document.getElementById("tb-anomalies");
  box.style.opacity = 0.5;
  const r = await get("/anomalies", { ...anFilters(), page: anPage, page_size: 25 });
  const pages = Math.max(1, Math.ceil(r.total / r.page_size));
  document.getElementById("an-count").textContent = `${nf0.format(r.total)} bản ghi, sắp theo |z| giảm dần`;
  document.getElementById("an-page").textContent = `Trang ${r.page} / ${pages}`;
  document.getElementById("an-prev").disabled = r.page <= 1;
  document.getElementById("an-next").disabled = r.page >= pages;
  table(box, r.items, [
    { key: "timestamp", label: "Thời điểm", f: (v) => v.replace("T", " ").slice(0, 16) },
    { key: "road_name", label: "Đường" }, { key: "district", label: "Quận" },
    { key: "metric", label: "Chỉ số", f: (v) => (v === "avg_speed" ? "tốc độ" : "lưu lượng") },
    { key: "value", label: "Giá trị", num: true, f: fmt }, { key: "expected", label: "Bình thường", num: true, f: fmt },
    { key: "z_score", label: "z", num: true, f: fmt, neg: true }, { key: "weather_condition", label: "Thời tiết" }],
    (row) => { document.querySelector('[data-tab="map"]').click(); setTimeout(() => showRoad(row.road_id), 300); });
  box.style.opacity = 1;
}

// ------------------------------------------------------------------ THỐNG KÊ
const DIM_LABEL = { overall: "Toàn bộ", hour: "Giờ", hour_daytype: "Giờ × loại ngày", day_of_week: "Thứ trong tuần",
  day_type: "Loại ngày", month: "Tháng", district: "Quận", road: "Đường", weather_condition: "Thời tiết" };
async function loadStats(first = false) {
  if (first) {
    const dims = await get("/statistics/dimensions");
    const sel = document.getElementById("st-dim");
    dims.forEach((d) => sel.append(el("option", { value: d.dimension }, `${DIM_LABEL[d.dimension] || d.dimension} (${d.groups})`)));
    sel.value = "hour";
    sel.onchange = () => loadStats();
    document.getElementById("st-metric").onchange = () => loadStats();
    document.getElementById("lv-run").onclick = runLive;
  }
  const dim = document.getElementById("st-dim").value, metric = document.getElementById("st-metric").value;
  const rows = await get("/statistics", { dimension: dim, metric });
  const unit = metric === "avg_speed" ? "km/h" : "xe/giờ";
  document.getElementById("st-title").textContent = `${metric === "avg_speed" ? "Tốc độ" : "Lưu lượng"} theo ${(DIM_LABEL[dim] || dim).toLowerCase()}`;
  const shown = dim === "road" ? [...rows].sort((a, b) => a.mean - b.mean).slice(0, 30) : rows;
  draw("ch-stats", { type: "bar",
    data: { labels: shown.map((x) => x.group_key), datasets: [bars(`Trung bình (${unit})`, shown.map((x) => x.mean), C.s1)] },
    options: { scales: { x: axisX({ ticks: { color: C.muted, autoSkip: true, maxRotation: 60 } }), y: axisY(unit) },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => { const x = shown[c.dataIndex];
        return [` TB ${fmt(x.mean)} ${unit} · trung vị ${fmt(x.median)}`, ` n = ${nf0.format(x.n)} · std ${fmt(x.std)}`]; } } } } } });
  table("tb-stats", rows, [{ key: "group_key", label: "Nhóm" }, { key: "n", label: "n", num: true, f: (v) => nf0.format(v) },
    { key: "mean", label: "Mean", num: true, f: fmt }, { key: "std", label: "Std", num: true, f: fmt },
    { key: "min", label: "Min", num: true, f: fmt }, { key: "median", label: "Median", num: true, f: fmt },
    { key: "max", label: "Max", num: true, f: fmt }]);
}
async function runLive() {
  const t0 = performance.now();
  const box = document.getElementById("tb-live");
  box.style.opacity = 0.5;
  try {
    const rows = await get("/statistics/live", { group_by: document.getElementById("lv-group").value,
      metric: document.getElementById("st-metric").value,
      start: document.getElementById("lv-start").value, end: document.getElementById("lv-end").value });
    document.getElementById("lv-time").textContent = `${rows.length} nhóm · ${nf0.format(performance.now() - t0)} ms (gồm cả mạng)`;
    table(box, rows, [{ key: "group_key", label: "Nhóm" }, { key: "n", label: "n", num: true, f: (v) => nf0.format(v) },
      { key: "mean", label: "Mean", num: true, f: (v) => fmt(v, nf2) }, { key: "std", label: "Std", num: true, f: (v) => fmt(v, nf2) },
      { key: "min", label: "Min", num: true, f: fmt }, { key: "median", label: "Median", num: true, f: fmt },
      { key: "max", label: "Max", num: true, f: fmt }]);
  } catch (e) { document.getElementById("lv-time").textContent = `Lỗi: ${e.message}`; }
  box.style.opacity = 1;
}

// ------------------------------------------------------------------ NHẬP DỮ LIỆU
async function loadLogs() {
  const r = await get("/import/logs", { page_size: 20 });
  table("tb-logs", r.items, [{ key: "id", label: "#", num: true },
    { key: "started_at", label: "Thời điểm", f: (v) => v.replace("T", " ").slice(0, 19) },
    { key: "target", label: "Bảng" }, { key: "source", label: "Nguồn", f: (v) => (v.length > 60 ? "…" + v.slice(-58) : v) },
    { key: "mode", label: "Cách" }, { key: "rows_loaded", label: "Đã ghi", num: true, f: (v) => nf0.format(v) },
    { key: "rows_rejected", label: "Từ chối", num: true, f: (v) => nf0.format(v) }, { key: "status", label: "Trạng thái" }]);
}
function initImport() {
  document.getElementById("imp-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const out = document.getElementById("imp-result");
    const file = document.getElementById("imp-file").files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    const target = document.getElementById("imp-target").value;
    const aon = document.getElementById("imp-aon").checked;
    out.replaceChildren(el("p", { class: "hint" }, "Đang tải lên…"));
    const r = await fetch(`${API}/import/${target}/file?all_or_nothing=${aon}`, { method: "POST", body: fd });
    const b = await r.json();
    const res = r.ok ? b : b.error?.details;
    if (!res || typeof res !== "object" || res.received === undefined) {
      out.replaceChildren(el("p", { class: "result" }, el("span", { class: "bad" }, "Lỗi: "), b.error?.message || `HTTP ${r.status}`));
      return;
    }
    const head = el("p", { class: "result" }, el("span", { class: res.rejected ? "bad" : "ok" }, res.status.toUpperCase()),
      ` · nhận ${nf0.format(res.received)} · thêm mới ${nf0.format(res.inserted)} · cập nhật ${nf0.format(res.updated)} · từ chối ${nf0.format(res.rejected)}`
      + (res.new_roads?.length ? ` · đường mới: ${res.new_roads.join(", ")}` : ""));
    const box = el("div", { class: "table-wrap" });
    out.replaceChildren(head, box);
    if (res.rejected_rows?.length)
      table(box, res.rejected_rows, [{ key: "row", label: "Dòng", num: true }, { key: "errors", label: "Lý do", f: (v) => v.join("; ") }]);
    loadLogs();
  });
}

// ------------------------------------------------------------------ điều hướng tab
const loaders = { overview: loadOverview, map: loadMap, weather: loadWeather, anomalies: () => loadAnomalies(true),
                  stats: () => loadStats(true), import: () => { initImport(); return loadLogs(); } };
const loaded = new Set();
async function openTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  document.querySelectorAll(".tab").forEach((s) => s.classList.toggle("active", s.id === `tab-${name}`));
  history.replaceState(null, "", `#${name}`);
  if (name === "map" && map) setTimeout(() => map.invalidateSize(), 50);
  if (loaded.has(name)) return;
  loaded.add(name);
  try { await loaders[name](); }
  catch (e) { loaded.delete(name); setStatus(`Lỗi khi tải "${name}": ${e.message}`, true); }
}
document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => openTab(b.dataset.tab)));
window.addEventListener("hashchange", () => { const t = location.hash.slice(1); if (loaders[t]) openTab(t); });

(async function start() {
  try {
    const h = await get("/health/db");
    setStatus(`API hoạt động · ${h.database} · schema ${h.schema_revision ?? "—"}`);
  } catch (e) {
    setStatus(`Không gọi được API: ${e.message}`, true);
  }
  const first = location.hash.slice(1);
  openTab(loaders[first] ? first : "overview");
})();
