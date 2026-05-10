from pathlib import Path
import csv
import json
import sqlite3


PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "patents.db"
OUTPUT_DIR = PROJECT_DIR / "outputs"
DASHBOARD_PATH = OUTPUT_DIR / "patent_intelligence_dashboard.html"
INVENTOR_YEARLY_PATH = OUTPUT_DIR / "inventor_yearly_trends.csv"
DISPLAY_START_YEAR = 1976
DISPLAY_END_YEAR = 2025


def fetch_all(conn, query, params=()):
    conn.row_factory = sqlite3.Row
    rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return [dict(row) for row in csv.DictReader(f)]


def read_report():
    report_path = OUTPUT_DIR / "report.json"
    if not report_path.exists():
        return {}

    with open(report_path, encoding="utf-8") as f:
        return json.load(f)


def normalize_ints(rows, fields):
    for row in rows:
        for field in fields:
            if field in row and row[field] not in (None, ""):
                row[field] = int(row[field])
    return rows


def complete_years(rows, start_year=DISPLAY_START_YEAR, end_year=DISPLAY_END_YEAR):
    counts = {row["year"]: row["patent_count"] for row in rows}
    actual_max_year = max(counts, default=end_year)
    final_year = max(end_year, actual_max_year)
    return [
        {"year": year, "patent_count": counts.get(year, 0)}
        for year in range(start_year, final_year + 1)
    ]


def build_dashboard_data():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    report = read_report()
    yearly_trends = complete_years(
        normalize_ints(read_csv(OUTPUT_DIR / "yearly_trends.csv"), ["year", "patent_count"])
    )
    top_inventors = normalize_ints(read_csv(OUTPUT_DIR / "top_inventors.csv"), ["patent_count"])
    top_companies = normalize_ints(read_csv(OUTPUT_DIR / "top_companies.csv"), ["patent_count"])
    top_countries = normalize_ints(read_csv(OUTPUT_DIR / "top_countries.csv"), ["patent_count"])

    with sqlite3.connect(DB_PATH) as conn:
        entity_counts = fetch_all(
            conn,
            """
            SELECT 'inventors' AS entity, COUNT(*) AS count FROM inventors
            UNION ALL
            SELECT 'companies' AS entity, COUNT(*) AS count FROM companies
            UNION ALL
            SELECT 'countries' AS entity, COUNT(DISTINCT country) AS count
            FROM locations
            WHERE country IS NOT NULL AND country != '';
            """,
        )
        entity_counts = {row["entity"]: row["count"] for row in entity_counts}

        inventor_ids = [row["inventor_id"] for row in top_inventors]
        placeholders = ",".join("?" for _ in inventor_ids)
        inventor_yearly = []
        if inventor_ids:
            inventor_yearly = fetch_all(
                conn,
                f"""
                SELECT
                    i.inventor_id,
                    i.name,
                    p.year,
                    COUNT(DISTINCT p.patent_id) AS patent_count
                FROM inventors i
                JOIN patent_inventor_relationships pir
                    ON i.inventor_id = pir.inventor_id
                JOIN patents p
                    ON pir.patent_id = p.patent_id
                WHERE i.inventor_id IN ({placeholders})
                    AND p.year IS NOT NULL
                GROUP BY i.inventor_id, i.name, p.year
                ORDER BY i.name, p.year;
                """,
                inventor_ids,
            )

    metrics = {
        "total_patents": int(report.get("total_patents", sum(row["patent_count"] for row in yearly_trends))),
        "total_inventors": int(entity_counts.get("inventors", 0)),
        "total_companies": int(entity_counts.get("companies", 0)),
        "total_countries": int(entity_counts.get("countries", len(top_countries))),
        "first_year": DISPLAY_START_YEAR,
        "last_year": DISPLAY_END_YEAR,
    }

    peak_year = max(yearly_trends, key=lambda row: row["patent_count"]) if yearly_trends else None
    loaded_years = [row for row in yearly_trends if row["patent_count"] > 0]
    latest_year = loaded_years[-1] if loaded_years else None
    previous_year = loaded_years[-2] if len(loaded_years) > 1 else None
    yoy_change = None
    if latest_year and previous_year and previous_year["patent_count"]:
        yoy_change = (
            (latest_year["patent_count"] - previous_year["patent_count"])
            / previous_year["patent_count"]
        ) * 100

    metrics.update(
        {
            "peak_year": peak_year["year"] if peak_year else None,
            "peak_year_patents": peak_year["patent_count"] if peak_year else None,
            "latest_year": latest_year["year"] if latest_year else None,
            "latest_year_patents": latest_year["patent_count"] if latest_year else None,
            "latest_yoy_change": yoy_change,
        }
    )

    write_csv(
        INVENTOR_YEARLY_PATH,
        inventor_yearly,
        ["inventor_id", "name", "year", "patent_count"],
    )

    return {
        "metrics": metrics,
        "yearly_trends": yearly_trends,
        "top_inventors": top_inventors,
        "top_companies": top_companies,
        "top_countries": top_countries,
        "inventor_yearly": inventor_yearly,
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Patent Intelligence Dashboard</title>
  <style>
    :root {
      --ink: #17202a;
      --muted: #667085;
      --line: #d8dee8;
      --panel: #ffffff;
      --page: #f5f7fb;
      --blue: #2563eb;
      --teal: #0f766e;
      --amber: #b45309;
      --red: #b42318;
      --green: #15803d;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--page);
      color: var(--ink);
      font-family: Inter, Segoe UI, Arial, sans-serif;
      letter-spacing: 0;
    }

    .shell {
      width: min(1440px, calc(100% - 32px));
      margin: 0 auto;
      padding: 24px 0 32px;
    }

    header {
      display: flex;
      align-items: flex-end;
      justify-content: space-between;
      gap: 20px;
      padding: 8px 0 20px;
      border-bottom: 1px solid var(--line);
    }

    h1, h2, h3, p { margin: 0; }

    h1 {
      font-size: clamp(28px, 3vw, 44px);
      line-height: 1.05;
      font-weight: 800;
    }

    .subtitle {
      margin-top: 8px;
      max-width: 820px;
      color: var(--muted);
      font-size: 15px;
      line-height: 1.45;
    }

    .toolbar {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }

    select {
      min-width: 260px;
      height: 40px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 0 12px;
      font: inherit;
    }

    .grid {
      display: grid;
      gap: 16px;
      margin-top: 18px;
    }

    .metrics {
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }

    .metric, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }

    .metric {
      min-height: 112px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .metric span {
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }

    .metric strong {
      font-size: clamp(22px, 2.2vw, 32px);
      line-height: 1.1;
    }

    .metric small {
      color: var(--muted);
      font-size: 12px;
    }

    .main-layout {
      grid-template-columns: minmax(0, 1.25fr) minmax(360px, .75fr);
      align-items: start;
    }

    .two-col {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .panel {
      padding: 16px;
      min-width: 0;
    }

    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }

    .panel h2 {
      font-size: 17px;
      line-height: 1.25;
    }

    .panel-note {
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }

    .chart {
      width: 100%;
      height: 320px;
      display: block;
      overflow: visible;
    }

    .chart text {
      fill: var(--muted);
      font-size: 11px;
      font-family: inherit;
    }

    .axis { stroke: #bac3d1; stroke-width: 1; }
    .grid-line { stroke: #e7ebf2; stroke-width: 1; }
    .line-series { fill: none; stroke: var(--blue); stroke-width: 3; }
    .line-series-alt { fill: none; stroke: var(--teal); stroke-width: 3; }
    .area-series { fill: rgba(37, 99, 235, .12); }
    .dot { fill: var(--blue); stroke: #fff; stroke-width: 2; }
    .bar-blue { fill: var(--blue); }
    .bar-teal { fill: var(--teal); }
    .bar-amber { fill: var(--amber); }

    .positive { color: var(--green); }
    .negative { color: var(--red); }

    @media (max-width: 1100px) {
      .metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .main-layout, .two-col { grid-template-columns: 1fr; }
    }

    @media (max-width: 720px) {
      .shell {
        width: min(100% - 20px, 1440px);
        padding-top: 14px;
      }

      header {
        align-items: stretch;
        flex-direction: column;
      }

      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      select { width: 100%; min-width: 0; }
      .chart { height: 280px; }
      .panel { padding: 12px; }
    }

    @media (max-width: 480px) {
      .metrics { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div>
        <h1>Patent Intelligence Dashboard</h1>
        <p class="subtitle">Portfolio-level analytics for patent volume, geographic concentration, leading inventors, company ownership, and inventor production over time.</p>
      </div>
      <div class="toolbar">
        <select id="inventorSelect" aria-label="Choose inventor"></select>
      </div>
    </header>

    <section class="grid metrics" id="metrics"></section>

    <section class="grid main-layout">
      <div class="panel">
        <div class="panel-head">
          <h2>Patent Trends Over Time</h2>
          <span class="panel-note" id="trendNote"></span>
        </div>
        <svg class="chart" id="yearlyChart" role="img" aria-label="Patent yearly trend chart"></svg>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>Top 10 Countries</h2>
          <span class="panel-note">Inventor location</span>
        </div>
        <svg class="chart" id="countryChart" role="img" aria-label="Top countries chart"></svg>
      </div>
    </section>

    <section class="grid main-layout">
      <div class="panel">
        <div class="panel-head">
          <h2>Selected Inventor Over Years</h2>
          <span class="panel-note" id="inventorNote"></span>
        </div>
        <svg class="chart" id="inventorYearChart" role="img" aria-label="Selected inventor yearly patent chart"></svg>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>Top 10 Inventor Ranking</h2>
          <span class="panel-note">Visual</span>
        </div>
        <svg class="chart" id="inventorRankChart" role="img" aria-label="Top inventor ranking chart"></svg>
      </div>
    </section>

    <section class="grid two-col">
      <div class="panel">
        <div class="panel-head">
          <h2>Top 10 Inventors by Patent Count</h2>
          <span class="panel-note">Ranked</span>
        </div>
        <svg class="chart" id="inventorBarChart" role="img" aria-label="Top inventors bar chart"></svg>
      </div>

      <div class="panel">
        <div class="panel-head">
          <h2>Top 10 Companies</h2>
          <span class="panel-note">Assignee ownership</span>
        </div>
        <svg class="chart" id="companyChart" role="img" aria-label="Top companies chart"></svg>
      </div>
    </section>
  </main>

  <script id="dashboardData" type="application/json">__DASHBOARD_DATA__</script>
  <script>
    const data = JSON.parse(document.getElementById("dashboardData").textContent);
    const fmt = new Intl.NumberFormat("en-US");
    const pct = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1, signDisplay: "exceptZero" });

    function metric(label, value, detail, cls = "") {
      return `<article class="metric"><span>${label}</span><strong class="${cls}">${value}</strong><small>${detail || ""}</small></article>`;
    }

    function renderMetrics() {
      const m = data.metrics;
      const yoy = m.latest_yoy_change;
      const yoyClass = yoy === null || yoy === undefined ? "" : (yoy >= 0 ? "positive" : "negative");
      document.getElementById("metrics").innerHTML = [
        metric("Total patents", fmt.format(m.total_patents), `${m.first_year}-${m.last_year}`),
        metric("Inventors", fmt.format(m.total_inventors), "Disambiguated records"),
        metric("Companies", fmt.format(m.total_companies), "Assignee records"),
        metric("Countries", fmt.format(m.total_countries), "Inventor locations"),
        metric("Peak year", m.peak_year, `${fmt.format(m.peak_year_patents)} patents`),
        metric("Latest year", fmt.format(m.latest_year_patents), `${m.latest_year} YoY ${yoy === null || yoy === undefined ? "n/a" : pct.format(yoy) + "%"}`, yoyClass)
      ].join("");
      document.getElementById("trendNote").textContent = `${m.first_year}-${m.last_year}`;
    }

    function dims(svg) {
      const rect = svg.getBoundingClientRect();
      return { width: Math.max(rect.width, 320), height: Math.max(rect.height, 240) };
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

    function addText(svg, text, x, y, attrs = {}) {
      const el = node("text", { x, y, ...attrs });
      el.textContent = text;
      svg.appendChild(el);
      return el;
    }

    function drawLineChart(svgId, rows, xKey, yKey, options = {}) {
      const svg = document.getElementById(svgId);
      clear(svg);
      const { width, height } = dims(svg);
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      const margin = { top: 18, right: 18, bottom: 38, left: 58 };
      const plotW = width - margin.left - margin.right;
      const plotH = height - margin.top - margin.bottom;
      const xs = rows.map(r => Number(r[xKey]));
      const ys = rows.map(r => Number(r[yKey]));
      const minX = Math.min(...xs);
      const maxX = Math.max(...xs);
      const minY = 0;
      const maxY = Math.max(...ys) * 1.08;

      for (let i = 0; i <= 4; i++) {
        const yVal = minY + (maxY - minY) * (i / 4);
        const y = scale(yVal, minY, maxY, margin.top + plotH, margin.top);
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

      const points = rows.map(r => {
        const x = scale(Number(r[xKey]), minX, maxX, margin.left, margin.left + plotW);
        const y = scale(Number(r[yKey]), minY, maxY, margin.top + plotH, margin.top);
        return [x, y];
      });
      const linePath = points.map((p, i) => `${i ? "L" : "M"} ${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(" ");
      const areaPath = `${linePath} L ${points[points.length - 1][0].toFixed(2)} ${margin.top + plotH} L ${points[0][0].toFixed(2)} ${margin.top + plotH} Z`;
      svg.appendChild(node("path", { d: areaPath, class: "area-series" }));
      svg.appendChild(node("path", { d: linePath, class: options.alt ? "line-series-alt" : "line-series" }));

      points.forEach((p, i) => {
        if (i === 0 || i === points.length - 1 || i % Math.ceil(points.length / 9) === 0) {
          svg.appendChild(node("circle", { cx: p[0], cy: p[1], r: 4, class: "dot" }));
        }
      });
    }

    function truncateLabel(label, max = 20) {
      return label.length > max ? `${label.slice(0, max - 1)}...` : label;
    }

    function drawBarChart(svgId, rows, labelKey, valueKey, barClass = "bar-blue") {
      const svg = document.getElementById(svgId);
      clear(svg);
      const { width, height } = dims(svg);
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      const margin = { top: 10, right: 88, bottom: 18, left: 128 };
      const plotW = width - margin.left - margin.right;
      const rowH = (height - margin.top - margin.bottom) / rows.length;
      const maxValue = Math.max(...rows.map(r => Number(r[valueKey])));

      rows.forEach((row, index) => {
        const y = margin.top + index * rowH + 5;
        const barH = Math.max(10, rowH - 10);
        const barW = scale(Number(row[valueKey]), 0, maxValue, 0, plotW);
        addText(svg, truncateLabel(String(row[labelKey])), margin.left - 10, y + barH / 2 + 4, { "text-anchor": "end" });
        svg.appendChild(node("rect", { x: margin.left, y, width: barW, height: barH, rx: 4, class: barClass }));
        addText(svg, fmt.format(row[valueKey]), margin.left + barW + 8, y + barH / 2 + 4);
      });
    }

    function drawRankChart(svgId, rows, labelKey, valueKey) {
      const svg = document.getElementById(svgId);
      clear(svg);
      const { width, height } = dims(svg);
      svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
      const margin = { top: 18, right: 104, bottom: 24, left: 150 };
      const plotW = width - margin.left - margin.right;
      const rowH = (height - margin.top - margin.bottom) / rows.length;
      const maxValue = Math.max(...rows.map(row => Number(row[valueKey]))) || 1;

      rows.forEach((row, index) => {
        const y = margin.top + index * rowH + rowH / 2;
        const x = margin.left + scale(Number(row[valueKey]), 0, maxValue, 0, plotW);
        addText(svg, `${index + 1}. ${truncateLabel(String(row[labelKey]), 20)}`, margin.left - 12, y + 4, { "text-anchor": "end" });
        svg.appendChild(node("line", { x1: margin.left, y1: y, x2: margin.left + plotW, y2: y, class: "grid-line" }));
        svg.appendChild(node("circle", { cx: x, cy: y, r: 7, class: "dot" }));
        addText(svg, fmt.format(row[valueKey]), x + 12, y + 4);
      });
    }

    function renderInventorSelector() {
      const select = document.getElementById("inventorSelect");
      select.innerHTML = data.top_inventors.map(row => `<option value="${row.inventor_id}">${row.name}</option>`).join("");
      select.addEventListener("change", renderSelectedInventor);
      renderSelectedInventor();
    }

    function renderSelectedInventor() {
      const inventorId = document.getElementById("inventorSelect").value;
      const rows = data.inventor_yearly.filter(row => row.inventor_id === inventorId);
      const inventor = data.top_inventors.find(row => row.inventor_id === inventorId);
      const total = rows.reduce((sum, row) => sum + Number(row.patent_count), 0);
      document.getElementById("inventorNote").textContent = inventor ? `${inventor.name} - ${fmt.format(total)} patents in trend` : "";
      drawLineChart("inventorYearChart", rows, "year", "patent_count", { alt: true });
    }

    function renderAll() {
      renderMetrics();
      renderInventorSelector();
      drawLineChart("yearlyChart", data.yearly_trends, "year", "patent_count");
      drawBarChart("countryChart", data.top_countries, "country", "patent_count", "bar-teal");
      drawBarChart("inventorBarChart", data.top_inventors, "name", "patent_count", "bar-blue");
      drawBarChart("companyChart", data.top_companies, "name", "patent_count", "bar-amber");
      drawRankChart("inventorRankChart", data.top_inventors, "name", "patent_count");
    }

    window.addEventListener("resize", () => {
      window.clearTimeout(window.__dashboardResize);
      window.__dashboardResize = window.setTimeout(renderAll, 120);
    });

    renderAll();
  </script>
</body>
</html>
"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dashboard_data = build_dashboard_data()
    html = HTML_TEMPLATE.replace(
        "__DASHBOARD_DATA__",
        json.dumps(dashboard_data, ensure_ascii=False),
    )
    DASHBOARD_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard created: {DASHBOARD_PATH}")
    print(f"Inventor yearly trends created: {INVENTOR_YEARLY_PATH}")


if __name__ == "__main__":
    main()
