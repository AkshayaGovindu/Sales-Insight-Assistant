from flask import Flask, jsonify, render_template, request
from database import initialize_database
from analytics import get_summary, answer_question

app = Flask(__name__)

# Create/update the local SQLite database when the app starts.
initialize_database()

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/summary")
def summary():
    try:
        return jsonify(get_summary())
    except Exception:
        app.logger.exception("Unable to create dashboard summary")
        return jsonify({"error": "Could not load dashboard data. Check the terminal for details."}), 500

@app.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()

    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    if len(question) > 300:
        return jsonify({"error": "Please keep your question under 300 characters."}), 400

    try:
        result = answer_question(question)
        if not result.get("supported"):
            return jsonify(result), 200
        return jsonify(result)
    except Exception:
        app.logger.exception("Question processing failed")
        return jsonify({"error": "Something went wrong while answering. Please try again."}), 500

if __name__ == "__main__":
    app.run(debug=True)
