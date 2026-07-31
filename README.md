# UF Academic Dates and Deadlines Hub

An automated, reusable academic data repository that monitors, scrapes, and normalizes the official academic dates and deadlines from the University of Florida.

This repository is maintained automatically by a GitHub Action that runs every morning. It updates a suite of clean, normalized JSON and CSV files, enabling any Streamlit application or external service to fetch up-to-date academic deadlines with a single line of code.

---

## 🚀 The Workflow

1. **Daily Execution:** A GitHub Action triggers every morning at 10:00 AM UTC (or manually on-demand).
2. **Dynamic Detection:** The parser fetches the main [UF Dates & Deadlines Catalog](https://catalog.ufl.edu/UGRD/dates-deadlines/) and dynamically finds the current and upcoming academic years' URLs.
3. **Robust Scraper:** It downloads the respective pages, parses 2-column and 3-column layouts, and extracts events for every semester/term (e.g., Summer A, Summer B, Summer C, Fall, Spring).
4. **Data Normalization:**
   - Dates are fully resolved to calendar years (e.g., correctly determining that January in "Fall 2026" belongs to 2027, and October in "Spring 2027" belongs to 2026).
   - Footnotes and references are stripped.
   - Ranges and lists of dates are processed into clean ISO-formatted start and end dates.
   - Events are automatically categorized into `Registration`, `Financial`, `Holiday`, `Commencement`, and `Academic`.
5. **Auto-commit:** If any data is modified, GitHub Actions commits the updated datasets and pushes them back to the repository.

---

## 📁 File Structure

```text
uf-dates/
├── .github/
│   └── workflows/
│       └── update_dates.yml     # Automated updater workflow
├── data/
│   ├── last_update.txt         # Timestamp of last successful scraper execution
│   ├── calendar.json/.csv      # Master collection of ALL academic events
│   ├── uf_dates.json/.csv      # Backwards-compatible main file
│   ├── deadlines.json/.csv     # Filtered collection of non-holiday deadlines
│   ├── holidays.json/.csv      # University holidays and student breaks
│   ├── registration.json/.csv  # Drop/add and course registration dates
│   ├── commencement.json/.csv  # Graduation and commencement ceremonies
│   └── important_dates.json/csv# Curated subset of high-priority academic dates
├── scripts/
│   └── update_dates.py         # Main python scraper & normalizer script
├── requirements.txt            # Python dependencies
└── README.md                   # This documentation
```

---

## 🛠️ Reusable Datasets (How to Use in Streamlit / Python)

Since this repository is public and updated automatically, you can stream the latest normalized academic data directly in any Python/Streamlit application using `pandas`. No scraping required inside your apps!

### 1. Show Curated Key Deadlines
```python
import pandas as pd
import streamlit as st

st.title("🐊 UF Important Deadlines")

# Fetch curated important dates
df = pd.read_json(
    "https://raw.githubusercontent.com/yourname/uf-dates/main/data/important_dates.json"
)

# Render a nice table
st.dataframe(df, use_container_width=True)
```

### 2. Filter Financial Deadlines
```python
import pandas as pd

# Load master calendar
df = pd.read_json(
    "https://raw.githubusercontent.com/yourname/uf-dates/main/data/calendar.json"
)

# Filter for financial categories
financial_deadlines = df[df["category"] == "Financial"]
print(financial_deadlines[["term", "event", "date"]])
```

---

## 💻 Local Setup & Development

If you want to run the scraper or customize the parsing logic locally:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourname/uf-dates.git
   cd uf-dates
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the parser:**
   ```bash
   python scripts/update_dates.py
   ```

This will run the full scraping sequence, print descriptive progress logs, and save the updated JSON/CSV datasets directly to the `data/` directory.
