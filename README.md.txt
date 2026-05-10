# Global Patent Intelligence Data Pipeline

## Project Overview
This project is a mini end-to-end data pipeline built using real-world patent data from the PatentsView Granted Patent Disambiguated dataset.

The pipeline performs the following steps:

1. Reads raw patent data files
2. Cleans and structures the data using pandas
3. Stores the cleaned data in a SQLite database
4. Runs analytical SQL queries
5. Generates reports in console, CSV, and JSON formats

This project was developed for the **Global Patent Intelligence Data Pipeline** mini project.

---

## Objectives
The system helps answer key patent intelligence questions such as:

- Who are the top inventors?
- Which companies own the most patents?
- Which countries produce the most patents?
- How do patent counts change over time?
- How do leading inventors' patent counts change year by year?

---

## Tools and Technologies Used
- Python
- pandas
- SQLite
- SQL
- HTML/CSS/JavaScript
- Git/GitHub

---

## Patent Intelligence Dashboard

Generate the standalone HTML dashboard with:

```bash
python scripts/generate_dashboard.py
```

This creates:

- `outputs/patent_intelligence_dashboard.html`
- `outputs/inventor_yearly_trends.csv`

Open `outputs/patent_intelligence_dashboard.html` in a browser to view the analytics dashboard. It includes key metrics, patent trends over time, top countries, top 10 inventors, top companies, and a dropdown for viewing each leading inventor's patent counts by year.

Run the web dashboard with:

```bash
python scripts/web_dashboard.py
```

Then open:

```text
http://127.0.0.1:8501
```

The web dashboard reads from the latest generated output files and the SQLite database. It displays a 1976-2025 reporting window; if 2025 records have not been loaded yet, 2025 appears as an empty year until the data is refreshed. After loading future patent data, rerun the report/dashboard scripts and refresh the browser.

---

## SQLite Database

The cleaned CSV files in `data/cleaned/` are loaded into `patents.db` for reuse. Current database tables include:

- `patents`
- `inventors`
- `companies`
- `locations`
- `patent_company_relationships`
- `patent_inventor_relationships`

To rebuild the database from the cleaned CSV files:

```bash
python scripts/load_to_sqlite.py
python scripts/add_indexes.py
```

---

## Dataset Used
Source: **PatentsView Granted Patent Disambiguated Data**

Files used in this project:
- `g_patent.tsv`
- `g_patent_abstract.tsv`
- `g_inventor_disambiguated.tsv`
- `g_assignee_disambiguated.tsv`
- `g_location_disambiguated.tsv`

---

## Project Structure

```text
patent_pipeline_project/
│
├── data/
│   ├── raw/
│   ├── raw/extracted/
│   └── cleaned/
│
├── outputs/
│   ├── top_inventors.csv
│   ├── top_companies.csv
│   ├── top_countries.csv
│   ├── yearly_trends.csv
│   ├── country_trends.csv
│   ├── inventor_yearly_trends.csv
│   ├── patent_intelligence_dashboard.html
│   └── report.json
│
├── scripts/
│   ├── download_data.py
│   ├── inspect_data.py
│   ├── clean_core_data.py
│   ├── clean_inventor_data.py
│   ├── merge_patent_abstracts.py
│   ├── load_to_sqlite.py
│   ├── generate_reports.py
│   ├── generate_dashboard.py
│   ├── web_dashboard.py
│   ├── run_queries.py
│   ├── add_indexes.py
│   ├── check_tables.py
│   └── check_patents_schema.py
│
├── sql/
│   ├── schema.sql
│   └── queries.sql
│
├── patents.db
└── README.md
