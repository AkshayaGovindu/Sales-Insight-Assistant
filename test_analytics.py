import unittest
from analytics import answer_question, get_summary
from database import initialize_database

class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        initialize_database()

    def test_summary_has_valid_transactions(self):
        summary = get_summary()
        self.assertGreater(summary["transaction_count"], 0)
        self.assertGreater(summary["total_revenue"], 0)

    def test_total_revenue_question(self):
        result = answer_question("What is the total revenue?")
        self.assertTrue(result["supported"])
        self.assertIn("Total revenue", result["answer"])

    def test_highest_revenue_product(self):
        result = answer_question("Which product generated the highest revenue?")
        self.assertTrue(result["supported"])
        self.assertTrue(result["table"])
        self.assertIn("Product", result["table"][0])

    def test_monthly_trend(self):
        result = answer_question("Show monthly revenue trend")
        self.assertTrue(result["supported"])
        self.assertGreaterEqual(len(result["table"]), 1)

    def test_highest_region(self):
        result = answer_question("Which region generated the highest revenue?")
        self.assertTrue(result["supported"])
        self.assertIn("Region", result["table"][0])

    def test_unsupported_question(self):
        result = answer_question("What is the weather tomorrow?")
        self.assertFalse(result["supported"])
        self.assertIn("message", result)

    def test_month_comparison(self):
        result = answer_question("Compare revenue between January and February")
        self.assertTrue(result["supported"])
        self.assertIn("Change", [row.get("Month") for row in result["table"]])

if __name__ == "__main__":
    unittest.main()
