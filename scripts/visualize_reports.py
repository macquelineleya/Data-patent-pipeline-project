from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

PROJECT_DIR = Path(r"H:\patent_pipeline_project")
OUTPUT_DIR = PROJECT_DIR / "outputs"
FIG_DIR = PROJECT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Top inventors
top_inventors = pd.read_csv(OUTPUT_DIR / "top_inventors.csv")
plt.figure(figsize=(10, 6))
plt.bar(top_inventors["name"], top_inventors["patent_count"])
plt.xticks(rotation=75)
plt.title("Top 10 Inventors by Patent Count")
plt.ylabel("Patent Count")
plt.tight_layout()
plt.savefig(FIG_DIR / "top_inventors.png")
plt.close()

# Top companies
top_companies = pd.read_csv(OUTPUT_DIR / "top_companies.csv")
plt.figure(figsize=(10, 6))
plt.bar(top_companies["name"], top_companies["patent_count"])
plt.xticks(rotation=75)
plt.title("Top 10 Companies by Patent Count")
plt.ylabel("Patent Count")
plt.tight_layout()
plt.savefig(FIG_DIR / "top_companies.png")
plt.close()

# Top countries
top_countries = pd.read_csv(OUTPUT_DIR / "top_countries.csv")
plt.figure(figsize=(10, 6))
plt.bar(top_countries["country"], top_countries["patent_count"])
plt.xticks(rotation=45)
plt.title("Top 10 Countries by Patent Count")
plt.ylabel("Patent Count")
plt.tight_layout()
plt.savefig(FIG_DIR / "top_countries.png")
plt.close()

# Yearly trends
yearly_trends = pd.read_csv(OUTPUT_DIR / "yearly_trends.csv")
plt.figure(figsize=(10, 6))
plt.plot(yearly_trends["year"], yearly_trends["patent_count"])
plt.title("Patent Trends Over Time")
plt.xlabel("Year")
plt.ylabel("Patent Count")
plt.tight_layout()
plt.savefig(FIG_DIR / "yearly_trends.png")
plt.close()

print("Visualizations saved in the figures folder.")