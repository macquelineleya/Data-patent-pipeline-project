from pathlib import Path
import csv
import sqlite3

from flask import Flask, jsonify, render_template_string, request


PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "patents.db"
OUTPUT_DIR = PROJECT_DIR / "outputs"
DISPLAY_START_YEAR = 1976
DISPLAY_END_YEAR = 2025

app = Flask(__name__)


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def read_csv(name):
    path = OUTPUT_DIR / name
    if not path.exists():
        return []

    with open(path, newline="", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def int_fields(records, fields):
    for record in records:
        for field in fields:
            if field in record and record[field] not in (None, ""):
                record[field] = int(record[field])
    return records


def rows(conn, query, params=()):
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def scalar(conn, query, params=(), default=0):
    value = conn.execute(query, params).fetchone()
    return value[0] if value and value[0] is not None else default


def parse_int(value, fallback=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def parse_countries(value):
    if not value:
        return []
    return [country.strip() for country in value.split(",") if country.strip()]


def selected_filters(yearly_trends):
    min_year = DISPLAY_START_YEAR
    max_year = max(DISPLAY_END_YEAR, max((row["year"] for row in yearly_trends), default=DISPLAY_END_YEAR))
    start_year = parse_int(request.args.get("start_year"), min_year)
    end_year = parse_int(request.args.get("end_year"), max_year)

    if start_year > end_year:
        start_year, end_year = end_year, start_year

    countries = parse_countries(request.args.get("countries"))
    return {
        "min_year": min_year,
        "max_year": max_year,
        "start_year": max(start_year, min_year),
        "end_year": min(end_year, max_year),
        "countries": countries,
    }


def load_fast_data():
    yearly_trends = int_fields(read_csv("yearly_trends.csv"), ["year", "patent_count"])
    top_inventors = int_fields(read_csv("top_inventors.csv"), ["patent_count"])
    top_companies = int_fields(read_csv("top_companies.csv"), ["patent_count"])
    top_countries = int_fields(read_csv("top_countries.csv"), ["patent_count"])
    inventor_yearly = int_fields(
        read_csv("inventor_yearly_trends.csv"),
        ["year", "patent_count"],
    )
    return yearly_trends, top_inventors, top_companies, top_countries, inventor_yearly


def complete_years(rows, start_year=DISPLAY_START_YEAR, end_year=DISPLAY_END_YEAR):
    counts = {row["year"]: row["patent_count"] for row in rows}
    actual_max_year = max(counts, default=end_year)
    final_year = max(end_year, actual_max_year)
    return [
        {"year": year, "patent_count": counts.get(year, 0)}
        for year in range(start_year, final_year + 1)
    ]


@app.get("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.get("/api/options")
def options():
    yearly_trends, top_inventors, _, top_countries, _ = load_fast_data()
    min_year = DISPLAY_START_YEAR
    max_year = max(DISPLAY_END_YEAR, max((row["year"] for row in yearly_trends), default=DISPLAY_END_YEAR))

    return jsonify(
        {
            "min_year": min_year,
            "max_year": max_year,
            "countries": [row["country"] for row in top_countries],
            "inventors": top_inventors,
        }
    )


@app.get("/api/dashboard")
def dashboard_data():
    yearly_trends, top_inventors, top_companies, top_countries, inventor_yearly = load_fast_data()
    yearly_trends = complete_years(yearly_trends)
    filters = selected_filters(yearly_trends)
    filtered_yearly = [
        row
        for row in yearly_trends
        if filters["start_year"] <= row["year"] <= filters["end_year"]
    ]

    selected_countries = set(filters["countries"])
    filtered_countries = [
        row for row in top_countries if not selected_countries or row["country"] in selected_countries
    ]

    default_inventor = top_inventors[0]["inventor_id"] if top_inventors else None
    inventor_id = request.args.get("inventor_id") or default_inventor
    selected_inventor = next(
        (row for row in top_inventors if row["inventor_id"] == inventor_id),
        None,
    )
    filtered_inventor_yearly = [
        row
        for row in inventor_yearly
        if row["inventor_id"] == inventor_id
        and filters["start_year"] <= row["year"] <= filters["end_year"]
    ]

    # These totals are from the fast summary layer. Country filtering narrows the
    # visible country chart; yearly filtering narrows trend-based metrics.
    total_patents = sum(row["patent_count"] for row in filtered_yearly)
    with connect() as conn:
        total_inventors = scalar(conn, "SELECT COUNT(*) FROM inventors")
        total_companies = scalar(conn, "SELECT COUNT(*) FROM companies")
        total_countries = scalar(
            conn,
            "SELECT COUNT(DISTINCT country) FROM locations WHERE country IS NOT NULL AND country != ''",
        )

    peak_year = max(filtered_yearly, key=lambda row: row["patent_count"]) if filtered_yearly else None
    loaded_years = [row for row in filtered_yearly if row["patent_count"] > 0]
    latest = loaded_years[-1] if loaded_years else None
    previous = loaded_years[-2] if len(loaded_years) > 1 else None
    yoy = None
    if latest and previous and previous["patent_count"]:
        yoy = ((latest["patent_count"] - previous["patent_count"]) / previous["patent_count"]) * 100

    return jsonify(
        {
            "filters": filters,
            "metrics": {
                "total_patents": total_patents,
                "total_inventors": total_inventors,
                "total_companies": total_companies,
                "total_countries": total_countries,
                "year_range": f"{filters['start_year']}-{filters['end_year']}",
                "peak_year": peak_year["year"] if peak_year else None,
                "peak_year_patents": peak_year["patent_count"] if peak_year else 0,
                "latest_year": latest["year"] if latest else None,
                "latest_year_patents": latest["patent_count"] if latest else 0,
                "latest_yoy_change": yoy,
                "display_start_year": DISPLAY_START_YEAR,
                "display_end_year": DISPLAY_END_YEAR,
            },
            "yearly_trends": filtered_yearly,
            "top_inventors": top_inventors,
            "top_companies": top_companies,
            "top_countries": filtered_countries,
            "selected_inventor": selected_inventor,
            "inventor_yearly": filtered_inventor_yearly,
        }
    )


DASHBOARD_HTML = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Patent Intelligence Web Dashboard</title>
  <style>
    :root {
      --bg: #f8fafd;
      --sidebar: #ffffff;
      --panel: #fff;
      --ink: #202124;
      --muted: #5f6368;
      --line: #dadce0;
      --blue: #1a73e8;
      --green: #188038;
      --rose: #d93025;
      --amber: #f9ab00;
      --violet: #8430ce;
      --shadow: 0 1px 2px rgba(60, 64, 67, .16), 0 2px 6px rgba(60, 64, 67, .10);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, Segoe UI, Arial, sans-serif;
      letter-spacing: 0;
    }

    .app {
      display: grid;
      grid-template-columns: 292px 1fr;
      min-height: 100vh;
    }

    aside {
      position: sticky;
      top: 0;
      height: 100vh;
      background: var(--sidebar);
      border-right: 1px solid var(--line);
      padding: 24px 18px;
      overflow-y: auto;
    }

    main {
      padding: 24px 36px 48px;
      min-width: 0;
    }

    h1, h2, h3, p { margin: 0; }

    h1 {
      font-size: 30px;
      line-height: 1.1;
      margin-bottom: 6px;
      font-weight: 700;
    }

    h2 {
      font-size: 21px;
      margin: 28px 0 16px;
      font-weight: 650;
    }

    h3 {
      font-size: 16px;
      margin-bottom: 12px;
      font-weight: 650;
    }

    .subtitle {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.45;
      max-width: 920px;
    }

    .filter-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 19px;
      font-weight: 700;
      margin-bottom: 24px;
    }

    .brand-dot {
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: conic-gradient(from 90deg, #1a73e8, #34a853, #fbbc04, #ea4335, #1a73e8);
      box-shadow: inset 0 0 0 4px #fff;
    }

    label {
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin: 18px 0 7px;
      font-weight: 700;
    }

    select, input {
      width: 100%;
      height: 40px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fff;
      color: var(--ink);
      padding: 0 10px;
      font: inherit;
      outline: none;
    }

    select:focus, input:focus {
      border-color: var(--blue);
      box-shadow: 0 0 0 3px rgba(26, 115, 232, .15);
    }

    select[multiple] {
      height: 132px;
      padding: 8px;
    }

    .range-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    button {
      width: 100%;
      height: 40px;
      margin-top: 18px;
      border: 0;
      border-radius: 999px;
      background: var(--blue);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
      box-shadow: var(--shadow);
    }

    button:hover { background: #1558b0; }

    .tiny {
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 14px;
      margin-top: 24px;
    }

    .metric {
      min-height: 116px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      box-shadow: var(--shadow);
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 8px;
    }

    .metric strong {
      display: block;
      font-size: clamp(24px, 2.4vw, 34px);
      line-height: 1;
      font-weight: 600;
    }

    .metric small {
      display: block;
      color: var(--muted);
      margin-top: 8px;
      font-size: 12px;
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 22px;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      min-width: 0;
      box-shadow: var(--shadow);
    }

    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 10px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 0 10px;
      border-radius: 999px;
      background: #e8f0fe;
      color: #174ea6;
      font-size: 12px;
      font-weight: 650;
      white-space: nowrap;
    }

    .chart {
      width: 100%;
      height: 360px;
      display: block;
    }

    .chart text {
      fill: var(--muted);
      font-size: 11px;
      font-family: inherit;
    }

    .axis { stroke: #c7ceda; stroke-width: 1; }
    .grid-line { stroke: #edf0f5; stroke-width: 1; }
    .line-blue { fill: none; stroke: var(--blue); stroke-width: 3; }
    .line-violet { fill: none; stroke: var(--violet); stroke-width: 3; }
    .area-blue { fill: rgba(22, 114, 201, .11); }
    .bar-blue { fill: var(--blue); }
    .bar-green { fill: var(--green); }
    .bar-amber { fill: var(--amber); }
    .dot { fill: var(--blue); stroke: #fff; stroke-width: 2; }
    .hoverable { transition: opacity .15s ease, filter .15s ease; }
    .hoverable:hover { opacity: .82; filter: drop-shadow(0 2px 4px rgba(60, 64, 67, .28)); }

    .status {
      margin-top: 18px;
      color: var(--muted);
      font-size: 13px;
    }

    @media (max-width: 1100px) {
      .app { grid-template-columns: 1fr; }
      aside {
        position: relative;
        height: auto;
      }
      main { padding: 24px 18px 36px; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid { grid-template-columns: 1fr; }
    }

    @media (max-width: 560px) {
      .metrics { grid-template-columns: 1fr; }
      .range-row { grid-template-columns: 1fr; }
      .chart { height: 300px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <div class="filter-title"><span class="brand-dot"></span> Filters</div>

      <label>Select Year Range</label>
      <div class="range-row">
        <input id="startYear" type="number">
        <input id="endYear" type="number">
      </div>

      <label>Select Countries</label>
      <select id="countrySelect" multiple></select>

      <label>Inventor Trend</label>
      <select id="inventorSelect"></select>

      <button id="applyBtn">Update Dashboard</button>
      <p class="tiny">This dashboard uses the latest report outputs and SQLite counts. After loading new patent data, regenerate reports and refresh this page.</p>
      <p class="status" id="status">Loading dashboard...</p>
    </aside>

    <main>
      <h1>Patent Intelligence Dashboard</h1>
      <p class="subtitle">Live patent analytics for key metrics, 1976-2025 trend coverage, top countries, top inventors, top companies, and inventor performance by year.</p>

      <section class="metrics" id="metrics"></section>

      <h2 class="section-title">Trends & Analytics</h2>
      <section class="grid">
        <div class="panel">
          <div class="panel-head">
            <h3>Patents Over Time</h3>
            <span class="chip" id="yearCoverageChip">1976-2025</span>
          </div>
          <svg class="chart" id="yearlyChart"></svg>
        </div>
        <div class="panel">
          <div class="panel-head">
            <h3>Top Inventors</h3>
            <span class="chip">Top 10</span>
          </div>
          <svg class="chart" id="inventorChart"></svg>
        </div>
      </section>

      <h2 class="section-title">Geographic & Ownership</h2>
      <section class="grid">
        <div class="panel">
          <div class="panel-head">
            <h3>Top Countries</h3>
            <span class="chip">Visualization</span>
          </div>
          <svg class="chart" id="countryChart"></svg>
        </div>
        <div class="panel">
          <div class="panel-head">
            <h3>Top Companies</h3>
            <span class="chip">Assignees</span>
          </div>
          <svg class="chart" id="companyChart"></svg>
        </div>
      </section>

      <h2 class="section-title">Inventor Analytics Over Years</h2>
      <section class="grid">
        <div class="panel">
          <div class="panel-head">
            <h3 id="inventorTrendTitle">Selected Inventor</h3>
            <span class="chip">Yearly trend</span>
          </div>
          <svg class="chart" id="inventorYearChart"></svg>
        </div>
        <div class="panel">
          <div class="panel-head">
            <h3>Top 10 Inventor Ranking</h3>
            <span class="chip">Visual</span>
          </div>
          <svg class="chart" id="inventorRankChart"></svg>
        </div>
      </section>
    </main>
  </div>

  <script>
    const fmt = new Intl.NumberFormat("en-US");
    let options = null;

    function $(id) { return document.getElementById(id); }

    async function loadOptions() {
      const res = await fetch("/api/options");
      options = await res.json();
      $("startYear").value = options.min_year;
      $("endYear").value = options.max_year;
      $("countrySelect").innerHTML = options.countries.map(country => `<option value="${country}">${country}</option>`).join("");
      $("inventorSelect").innerHTML = options.inventors.map(inv => `<option value="${inv.inventor_id}">${inv.name}</option>`).join("");
    }

    function selectedCountries() {
      return Array.from($("countrySelect").selectedOptions).map(option => option.value);
    }

    function queryString() {
      const params = new URLSearchParams({
        start_year: $("startYear").value,
        end_year: $("endYear").value,
        inventor_id: $("inventorSelect").value
      });
      const countries = selectedCountries();
      if (countries.length) params.set("countries", countries.join(","));
      return params.toString();
    }

    async function loadDashboard() {
      $("status").textContent = "Updating dashboard...";
      const res = await fetch(`/api/dashboard?${queryString()}`);
      const data = await res.json();
      renderDashboard(data);
      const countryText = data.filters.countries.length ? data.filters.countries.join(", ") : "All countries";
      $("status").textContent = `${countryText} - ${data.filters.start_year}-${data.filters.end_year}`;
    }

    function renderDashboard(data) {
      const m = data.metrics;
      const yoy = m.latest_yoy_change;
      $("yearCoverageChip").textContent = `${m.display_start_year}-${m.display_end_year}`;
      $("metrics").innerHTML = [
        metric("Total Patents", fmt.format(m.total_patents), m.year_range),
        metric("Total Inventors", fmt.format(m.total_inventors), "Filtered inventors"),
        metric("Total Companies", fmt.format(m.total_companies), "Filtered assignees"),
        metric("Countries", fmt.format(m.total_countries), "Inventor locations"),
        metric("Latest Loaded Year", fmt.format(m.latest_year_patents), `${m.latest_year || ""} YoY ${yoy == null ? "n/a" : yoy.toFixed(1) + "%"}`)
      ].join("");

      drawLineChart("yearlyChart", data.yearly_trends, "year", "patent_count", "line-blue");
      drawBarChart("inventorChart", data.top_inventors, "name", "patent_count", "bar-blue");
      drawBarChart("countryChart", data.top_countries, "country", "patent_count", "bar-green");
      drawBarChart("companyChart", data.top_companies, "name", "patent_count", "bar-amber");
      drawLineChart("inventorYearChart", data.inventor_yearly, "year", "patent_count", "line-violet");
      drawRankChart("inventorRankChart", data.top_inventors, "name", "patent_count");
      $("inventorTrendTitle").textContent = data.selected_inventor ? `${data.selected_inventor.name} Over Years` : "Selected Inventor";
    }

    function metric(label, value, detail) {
      return `<article class="metric"><span>${label}</span><strong>${value}</strong><small>${detail || ""}</small></article>`;
    }

    function dims(svg) {
      const rect = svg.getBoundingClientRect();
      return { width: Math.max(rect.width, 320), height: Math.max(rect.height, 260) };
    }

    function scale(value, min, max, outMin, outMax) {
      if (max === min) return (outMin + outMax) / 2;
      return outMin + ((value - min) / (max - min)) * (outMax - outMin);
    }

    function clear(svg) {
      while (svg.firstChild) svg.removeChild(svg.firstChild);
    }

    function node(name, attrs = {}) {
      const el = document.createElementNS("http://www.w3.org/2000/svg", name);
      Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
      return el;
    }

    function addTitle(el, text) {
      const title = node("title");
      title.textContent = text;
      el.appendChild(title);
      return el;
    }

    function addText(svg, text, x, y, attrs = {}) {
      const el = node("text", { x, y, ...attrs });
      el.textContent = text;
      svg.appendChild(el);
      return el;
    }

    function drawEmpty(svg, message) {
      clear(svg);
      const { width, height } = dims(svg);
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      addText(svg, message, width / 2, height / 2, { "text-anchor": "middle" });
    }

    function drawLineChart(svgId, rows, xKey, yKey, cls) {
      const svg = $(svgId);
      if (!rows || !rows.length) {
        drawEmpty(svg, "No data for current filters");
        return;
      }

      clear(svg);
      const { width, height } = dims(svg);
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      const margin = { top: 18, right: 20, bottom: 38, left: 62 };
      const plotW = width - margin.left - margin.right;
      const plotH = height - margin.top - margin.bottom;
      const xs = rows.map(row => Number(row[xKey]));
      const ys = rows.map(row => Number(row[yKey]));
      const minX = Math.min(...xs);
      const maxX = Math.max(...xs);
      const maxY = Math.max(...ys) * 1.1 || 1;

      for (let i = 0; i <= 4; i++) {
        const yVal = maxY * (i / 4);
        const y = scale(yVal, 0, maxY, margin.top + plotH, margin.top);
        svg.appendChild(node("line", { x1: margin.left, y1: y, x2: width - margin.right, y2: y, class: "grid-line" }));
        addText(svg, fmt.format(Math.round(yVal)), margin.left - 8, y + 4, { "text-anchor": "end" });
      }

      svg.appendChild(node("line", { x1: margin.left, y1: margin.top + plotH, x2: width - margin.right, y2: margin.top + plotH, class: "axis" }));
      svg.appendChild(node("line", { x1: margin.left, y1: margin.top, x2: margin.left, y2: margin.top + plotH, class: "axis" }));

      const tickCount = Math.min(6, rows.length);
      for (let i = 0; i < tickCount; i++) {
        const year = Math.round(minX + (maxX - minX) * (i / Math.max(tickCount - 1, 1)));
        const x = scale(year, minX, maxX, margin.left, margin.left + plotW);
        addText(svg, String(year), x, height - 12, { "text-anchor": "middle" });
      }

      const points = rows.map(row => [
        scale(Number(row[xKey]), minX, maxX, margin.left, margin.left + plotW),
        scale(Number(row[yKey]), 0, maxY, margin.top + plotH, margin.top)
      ]);
      const line = points.map((point, idx) => `${idx ? "L" : "M"} ${point[0].toFixed(2)} ${point[1].toFixed(2)}`).join(" ");
      const area = `${line} L ${points[points.length - 1][0].toFixed(2)} ${margin.top + plotH} L ${points[0][0].toFixed(2)} ${margin.top + plotH} Z`;
      svg.appendChild(node("path", { d: area, class: "area-blue" }));
      svg.appendChild(node("path", { d: line, class: cls }));

      points.forEach((point, idx) => {
        if (idx === 0 || idx === points.length - 1 || idx % Math.ceil(points.length / 10) === 0) {
          const row = rows[idx];
          const circle = node("circle", { cx: point[0], cy: point[1], r: 4, class: "dot hoverable" });
          svg.appendChild(addTitle(circle, `${row[xKey]}: ${fmt.format(row[yKey])} patents`));
        }
      });
    }

    function drawBarChart(svgId, rows, labelKey, valueKey, barClass) {
      const svg = $(svgId);
      if (!rows || !rows.length) {
        drawEmpty(svg, "No data for current filters");
        return;
      }

      clear(svg);
      const { width, height } = dims(svg);
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      const margin = { top: 8, right: 88, bottom: 18, left: 142 };
      const plotW = width - margin.left - margin.right;
      const rowH = (height - margin.top - margin.bottom) / rows.length;
      const maxValue = Math.max(...rows.map(row => Number(row[valueKey]))) || 1;

      rows.slice().reverse().forEach((row, index) => {
        const y = margin.top + index * rowH + 5;
        const barH = Math.max(10, rowH - 10);
        const barW = scale(Number(row[valueKey]), 0, maxValue, 0, plotW);
        addText(svg, truncate(String(row[labelKey])), margin.left - 10, y + barH / 2 + 4, { "text-anchor": "end" });
        const rect = node("rect", { x: margin.left, y, width: barW, height: barH, rx: 3, class: `${barClass} hoverable` });
        svg.appendChild(addTitle(rect, `${row[labelKey]}: ${fmt.format(row[valueKey])} patents`));
        addText(svg, fmt.format(row[valueKey]), margin.left + barW + 8, y + barH / 2 + 4);
      });
    }

    function drawRankChart(svgId, rows, labelKey, valueKey) {
      const svg = $(svgId);
      if (!rows || !rows.length) {
        drawEmpty(svg, "No data for current filters");
        return;
      }

      clear(svg);
      const { width, height } = dims(svg);
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      const margin = { top: 18, right: 108, bottom: 24, left: 154 };
      const plotW = width - margin.left - margin.right;
      const rowH = (height - margin.top - margin.bottom) / rows.length;
      const maxValue = Math.max(...rows.map(row => Number(row[valueKey]))) || 1;

      rows.forEach((row, index) => {
        const y = margin.top + index * rowH + rowH / 2;
        const x = margin.left + scale(Number(row[valueKey]), 0, maxValue, 0, plotW);
        addText(svg, `${index + 1}. ${truncate(String(row[labelKey]), 20)}`, margin.left - 12, y + 4, { "text-anchor": "end" });
        svg.appendChild(node("line", { x1: margin.left, y1: y, x2: margin.left + plotW, y2: y, class: "grid-line" }));
        const dot = node("circle", { cx: x, cy: y, r: 7, class: "dot hoverable" });
        svg.appendChild(addTitle(dot, `${row[labelKey]}: ${fmt.format(row[valueKey])} patents`));
        addText(svg, fmt.format(row[valueKey]), x + 12, y + 4);
      });
    }

    function truncate(value, max = 22) {
      return value.length > max ? `${value.slice(0, max - 1)}...` : value;
    }

    $("applyBtn").addEventListener("click", loadDashboard);
    $("inventorSelect").addEventListener("change", loadDashboard);
    window.addEventListener("resize", () => {
      window.clearTimeout(window.__resize);
      window.__resize = window.setTimeout(loadDashboard, 150);
    });

    loadOptions().then(loadDashboard).catch(err => {
      $("status").textContent = `Error: ${err.message}`;
      console.error(err);
    });
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit(f"Database not found: {DB_PATH}")
    app.run(host="127.0.0.1", port=8501, debug=False, use_reloader=False)
