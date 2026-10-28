import re
import sqlite3
from datetime import datetime
from database import connect_db

VALID_SALES = "status = 'Completed' AND is_valid = 1"

def query_all(sql, params=()):
    with connect_db() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

def query_one(sql, params=()):
    with connect_db() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else {}

def money(value):
    return round(float(value or 0), 2)

def get_summary():
    kpis = query_one(f"""
        SELECT COALESCE(SUM(net_revenue), 0) AS total_revenue,
               COUNT(*) AS transaction_count
        FROM sales_transactions WHERE {VALID_SALES}
    """)
    top_product = query_one(f"""
        SELECT product, SUM(net_revenue) AS revenue
        FROM sales_transactions WHERE {VALID_SALES}
        GROUP BY product ORDER BY revenue DESC, product ASC LIMIT 1
    """)
    top_region = query_one(f"""
        SELECT region, SUM(net_revenue) AS revenue
        FROM sales_transactions WHERE {VALID_SALES}
        GROUP BY region ORDER BY revenue DESC, region ASC LIMIT 1
    """)
    monthly = query_all(f"""
        SELECT substr(order_date, 1, 7) AS month,
               SUM(net_revenue) AS revenue
        FROM sales_transactions WHERE {VALID_SALES}
        GROUP BY month ORDER BY month
    """)
    products = query_all(f"""
        SELECT product, SUM(net_revenue) AS revenue
        FROM sales_transactions WHERE {VALID_SALES}
        GROUP BY product ORDER BY revenue DESC, product ASC
    """)
    quality = query_one("""
        SELECT COUNT(*) AS total_rows,
               SUM(CASE WHEN is_valid = 0 THEN 1 ELSE 0 END) AS flagged_rows,
               SUM(CASE WHEN status = 'Returned' THEN 1 ELSE 0 END) AS returned_rows
        FROM sales_transactions
    """)
    return {
        "total_revenue": money(kpis.get("total_revenue")),
        "transaction_count": int(kpis.get("transaction_count") or 0),
        "top_product": top_product.get("product", "N/A"),
        "top_product_revenue": money(top_product.get("revenue")),
        "top_region": top_region.get("region", "N/A"),
        "top_region_revenue": money(top_region.get("revenue")),
        "monthly": [{"month": r["month"], "revenue": money(r["revenue"])} for r in monthly],
        "products": [{"product": r["product"], "revenue": money(r["revenue"])} for r in products],
        "data_quality": {
            "total_rows": int(quality.get("total_rows") or 0),
            "flagged_rows": int(quality.get("flagged_rows") or 0),
            "returned_rows": int(quality.get("returned_rows") or 0)
        }
    }

MONTHS = {
    "jan": "01", "january": "01", "feb": "02", "february": "02",
    "mar": "03", "march": "03", "apr": "04", "april": "04",
    "may": "05", "jun": "06", "june": "06", "jul": "07", "july": "07",
    "aug": "08", "august": "08", "sep": "09", "september": "09",
    "oct": "10", "october": "10", "nov": "11", "november": "11",
    "dec": "12", "december": "12"
}

def month_from_text(text, month_name):
    month_num = MONTHS[month_name.lower()]
    # Dataset contains 2026; allow a year in the question, otherwise use 2026.
    match = re.search(rf"\b{re.escape(month_name)}\s+(20\d{{2}})\b", text, re.I)
    year = match.group(1) if match else "2026"
    return f"{year}-{month_num}"

def answer_question(question):
    q = question.lower().strip()
    if not q:
        return {"supported": False, "message": "Please enter a question."}

    if any(word in q for word in ["total revenue", "overall revenue", "revenue overall", "total sales"]):
        row = query_one(f"""
            SELECT COALESCE(SUM(net_revenue), 0) AS revenue
            FROM sales_transactions WHERE {VALID_SALES}
        """)
        revenue = money(row.get("revenue"))
        return {
            "supported": True,
            "answer": f"Total revenue from valid completed transactions is ₹{revenue:,.2f}.",
            "table": [{"Metric": "Total revenue", "Value": f"₹{revenue:,.2f}"}],
            "chart": {"type": "none", "labels": [], "values": []}
        }

    if "product" in q and any(word in q for word in ["highest", "top", "most", "best"]):
        rows = query_all(f"""
            SELECT product, SUM(net_revenue) AS revenue
            FROM sales_transactions WHERE {VALID_SALES}
            GROUP BY product ORDER BY revenue DESC, product ASC LIMIT 5
        """)
        if not rows:
            return {"supported": True, "answer": "No valid completed sales were found.", "table": [], "chart": {"type":"bar","labels":[],"values":[]}}
        top = rows[0]
        return {
            "supported": True,
            "answer": f"{top['product']} generated the highest revenue: ₹{money(top['revenue']):,.2f}.",
            "table": [{"Product": r["product"], "Revenue": f"₹{money(r['revenue']):,.2f}"} for r in rows],
            "chart": {"type": "bar", "labels": [r["product"] for r in reversed(rows)], "values": [money(r["revenue"]) for r in reversed(rows)]}
        }

    if "region" in q and any(word in q for word in ["highest", "top", "most", "best", "sales", "revenue"]):
        rows = query_all(f"""
            SELECT region, SUM(net_revenue) AS revenue
            FROM sales_transactions WHERE {VALID_SALES}
            GROUP BY region ORDER BY revenue DESC, region ASC
        """)
        if not rows:
            return {"supported": True, "answer": "No valid completed sales were found.", "table": [], "chart": {"type":"bar","labels":[],"values":[]}}
        top = rows[0]
        return {
            "supported": True,
            "answer": f"{top['region']} generated the highest revenue: ₹{money(top['revenue']):,.2f}.",
            "table": [{"Region": r["region"], "Revenue": f"₹{money(r['revenue']):,.2f}"} for r in rows],
            "chart": {"type": "bar", "labels": [r["region"] for r in rows], "values": [money(r["revenue"]) for r in rows]}
        }

    if any(word in q for word in ["between", "change", "compare", "comparison", "from"]) and len(re.findall(r"\b(" + "|".join(MONTHS.keys()) + r")\b", q, re.I)) >= 2:
        found = re.findall(r"\b(" + "|".join(MONTHS.keys()) + r")\b", q, re.I)
        # Keep only first appearance of each month name.
        names = []
        for name in found:
            if name.lower() not in [n.lower() for n in names]:
                names.append(name)
        if len(names) >= 2:
            old_month = month_from_text(q, names[0])
            new_month = month_from_text(q, names[1])
            rows = query_all(f"""
                SELECT substr(order_date, 1, 7) AS month, SUM(net_revenue) AS revenue
                FROM sales_transactions
                WHERE {VALID_SALES} AND substr(order_date, 1, 7) IN (?, ?)
                GROUP BY month
            """, (old_month, new_month))
            totals = {r["month"]: money(r["revenue"]) for r in rows}
            old_total, new_total = totals.get(old_month, 0), totals.get(new_month, 0)
            change = money(new_total - old_total)
            pct = (change / old_total * 100) if old_total else None
            pct_text = f"{pct:.2f}%" if pct is not None else "not available because the earlier month's revenue is zero"
            return {
                "supported": True,
                "answer": f"Revenue changed by ₹{change:,.2f} from {old_month} to {new_month}. Percentage change: {pct_text}.",
                "table": [
                    {"Month": old_month, "Revenue": f"₹{old_total:,.2f}"},
                    {"Month": new_month, "Revenue": f"₹{new_total:,.2f}"},
                    {"Month": "Change", "Revenue": f"₹{change:,.2f}"}
                ],
                "chart": {"type": "bar", "labels": [old_month, new_month], "values": [old_total, new_total]}
            }
        return {"supported": False, "message": "Please name two months, for example: Compare revenue between January and February."}

    if "month" in q or "monthly" in q or "trend" in q:
        rows = query_all(f"""
            SELECT substr(order_date, 1, 7) AS month, SUM(net_revenue) AS revenue
            FROM sales_transactions WHERE {VALID_SALES}
            GROUP BY month ORDER BY month
        """)
        return {
            "supported": True,
            "answer": "Here is the monthly revenue trend for valid completed transactions.",
            "table": [{"Month": r["month"], "Revenue": f"₹{money(r['revenue']):,.2f}"} for r in rows],
            "chart": {"type": "line", "labels": [r["month"] for r in rows], "values": [money(r["revenue"]) for r in rows]}
        }

    return {
        "supported": False,
        "message": "I can answer questions about total revenue, highest-revenue product, monthly revenue trend, highest-revenue region, or revenue changes between two months."
    }
