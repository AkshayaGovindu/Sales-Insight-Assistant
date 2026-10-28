import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "sales_data.csv"
DB_PATH = ROOT / "sales.db"

EXPECTED_COLUMNS = [
    "Transaction_Id", "Order_date", "Product", "Category", "Region",
    "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"
]

def connect_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_database():
    """Load the supplied CSV into SQLite and retain validation notes per row."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    missing_columns = [column for column in EXPECTED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")

    # Normalize types while keeping invalid rows in the database for auditability.
    df["Order_date"] = pd.to_datetime(df["Order_date"], format="%d-%m-%Y", errors="coerce")
    for column in ["Quantity", "Unit_price", "Discount_amount"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    records = []
    seen_ids = set()
    for _, row in df.iterrows():
        transaction_id = str(row["Transaction_Id"]).strip()
        status = str(row["Status"]).strip().title()
        reasons = []

        if not transaction_id or transaction_id.lower() == "nan":
            reasons.append("Missing transaction ID")
        elif transaction_id in seen_ids:
            reasons.append("Duplicate transaction ID")
        seen_ids.add(transaction_id)

        order_date = row["Order_date"]
        if pd.isna(order_date):
            reasons.append("Invalid or missing order date")

        product = str(row["Product"]).strip()
        region = str(row["Region"]).strip()
        if not product or product.lower() == "nan":
            reasons.append("Missing product")
        if not region or region.lower() == "nan":
            reasons.append("Missing region")

        quantity = row["Quantity"]
        unit_price = row["Unit_price"]
        discount = row["Discount_amount"]

        if pd.isna(quantity) or quantity <= 0:
            reasons.append("Quantity must be greater than zero")
        if pd.isna(unit_price) or unit_price < 0:
            reasons.append("Unit price is missing or invalid")
        if pd.isna(discount) or discount < 0:
            reasons.append("Discount is missing or invalid")

        gross = None
        net_revenue = None
        if not pd.isna(quantity) and not pd.isna(unit_price):
            gross = float(quantity) * float(unit_price)
            if not pd.isna(discount):
                net_revenue = gross - float(discount)
                if net_revenue < 0:
                    reasons.append("Discount exceeds gross sales")

        if status not in {"Completed", "Returned"}:
            reasons.append("Unsupported transaction status")

        is_valid = 1 if not reasons else 0
        if status == "Returned":
            reasons.append("Returned transaction excluded from completed revenue")
        validation_note = "; ".join(dict.fromkeys(reasons)) if reasons else "Valid completed transaction"

        records.append((
            transaction_id,
            order_date.strftime("%Y-%m-%d") if not pd.isna(order_date) else None,
            product if product.lower() != "nan" else None,
            str(row["Category"]).strip() if not pd.isna(row["Category"]) else None,
            region if region.lower() != "nan" else None,
            str(row["Sales_channel"]).strip() if not pd.isna(row["Sales_channel"]) else None,
            int(quantity) if not pd.isna(quantity) and float(quantity).is_integer() else (float(quantity) if not pd.isna(quantity) else None),
            float(unit_price) if not pd.isna(unit_price) else None,
            float(discount) if not pd.isna(discount) else None,
            status,
            float(net_revenue) if net_revenue is not None else None,
            is_valid,
            validation_note
        ))

    with connect_db() as conn:
        conn.execute("DROP TABLE IF EXISTS sales_transactions")
        conn.execute("""
            CREATE TABLE sales_transactions (
                transaction_id TEXT,
                order_date TEXT,
                product TEXT,
                category TEXT,
                region TEXT,
                sales_channel TEXT,
                quantity REAL,
                unit_price REAL,
                discount_amount REAL,
                status TEXT,
                net_revenue REAL,
                is_valid INTEGER NOT NULL,
                validation_note TEXT
            )
        """)
        conn.executemany("""
            INSERT INTO sales_transactions (
                transaction_id, order_date, product, category, region,
                sales_channel, quantity, unit_price, discount_amount, status,
                net_revenue, is_valid, validation_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_transactions(order_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_product ON sales_transactions(product)")
        conn.commit()
