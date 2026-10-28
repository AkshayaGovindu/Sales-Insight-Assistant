# Sales Insight Assistant

A small student project that lets a user ask common sales questions and see answers calculated from a SQLite database.

## Features
- Dashboard cards for total revenue, transaction count, top product and top region.
- Monthly revenue and product revenue charts.
- Natural-language question matching for total revenue, highest-revenue product, monthly trend, highest-revenue region, and two-month comparison.
- CSV validation notes and an SQLite database.
- Automated tests using `unittest`/`pytest`.

## Tech stack
Python, Flask, Pandas, SQLite, HTML, CSS, JavaScript, Chart.js, and Pytest.

## Run on Windows
1. Install Python 3.10 or later.
2. Extract this project folder and open it in VS Code.
3. Open the terminal inside the project folder.
4. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate
   ```

5. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Start the app:

   ```bash
   python app.py
   ```

7. Open http://127.0.0.1:5000 in your browser.

The SQLite database (`sales.db`) is created automatically on startup from `data/sales_data.csv`.

## Run tests
With the virtual environment activated:

```bash
python -m pytest -v
```

## Example questions
- What is the total revenue?
- Which product generated the highest revenue?
- Show monthly revenue trend.
- Which region generated the highest revenue?
- Compare revenue between January and February.

## Revenue and data quality rules
Revenue is calculated as `(quantity * unit_price) - discount_amount`. Only completed rows that pass validation are included in sales analytics. Returned rows are excluded. Rows with missing/invalid required values, non-positive quantities, duplicate transaction IDs, or invalid discounts are flagged and excluded from the analytics. The original CSV is not modified. All source rows and their validation notes are kept in SQLite for review.

## Architecture
CSV → Pandas validation → SQLite → Flask API → question interpreter and SQL analytics → JSON response → browser UI and charts.

## Important limitation
The initial question interpreter is rule-based, not a large language model. It recognizes a small set of question patterns and does not answer arbitrary questions. This keeps calculations deterministic and avoids executing AI-generated SQL. An LLM can be added later to interpret more varied questions into a restricted intent, while SQL remains responsible for the calculations.

## AI tool disclosure
If you used an AI coding assistant while developing this project, describe which tool you used, which parts it helped with, what you changed or verified yourself, any bugs you encountered, and what you would improve. Do not claim an AI model is integrated into the running app unless you actually add and configure one.
