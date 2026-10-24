"""
Smart Expense Tracker Using Cloud
---------------------------------
Flask REST API + web dashboard, SQLite storage.
Cloud features:
  * Runs in Docker (local / VirtualBox VM / AWS EC2)
  * Optional backup of the database to AWS S3 (set S3_BUCKET env variable)
  * /health endpoint for load balancers (AWS ALB / target groups)
Smart features:
  * Auto-categorisation from the description
  * Monthly budget alert
  * End-of-month spending forecast
"""
import csv
import io
import os
import sqlite3
from calendar import monthrange
from datetime import date, datetime

from flask import Flask, Response, g, jsonify, render_template, request

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "expenses.db"))
S3_BUCKET = os.environ.get("S3_BUCKET", "")  # empty = backup disabled
DEFAULT_BUDGET = float(os.environ.get("MONTHLY_BUDGET", "20000"))

CATEGORY_KEYWORDS = {
    "Food": ["swiggy", "zomato", "restaurant", "cafe", "coffee", "lunch", "dinner", "biryani", "grocery", "milk", "snack"],
    "Transport": ["uber", "ola", "petrol", "diesel", "bus", "metro", "train", "auto", "fuel", "cab", "flight"],
    "Shopping": ["amazon", "flipkart", "myntra", "shirt", "shoes", "mall", "clothes"],
    "Bills": ["electricity", "water", "wifi", "internet", "recharge", "rent", "gas", "bill", "emi"],
    "Entertainment": ["movie", "netflix", "spotify", "game", "concert", "prime"],
    "Health": ["doctor", "medicine", "pharmacy", "hospital", "gym", "clinic"],
    "Education": ["book", "course", "fees", "exam", "tuition", "udemy"],
}
CATEGORIES = list(CATEGORY_KEYWORDS) + ["Other"]

app = Flask(__name__)


# ---------------------------------------------------------------- database
def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS expenses(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            spent_on TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        """
    )
    con.commit()
    con.close()


# ------------------------------------------------------------ smart logic
def auto_category(description: str) -> str:
    text = description.lower()
    for cat, words in CATEGORY_KEYWORDS.items():
        if any(w in text for w in words):
            return cat
    return "Other"


def get_budget(db) -> float:
    row = db.execute("SELECT value FROM settings WHERE key='budget'").fetchone()
    return float(row["value"]) if row else DEFAULT_BUDGET


def month_prefix(value=None) -> str:
    return value or date.today().strftime("%Y-%m")


def backup_to_s3():
    """Upload the SQLite file to S3 if configured. Returns a status string."""
    if not S3_BUCKET:
        return "S3 backup disabled (set S3_BUCKET)"
    try:
        import boto3  # imported lazily so the app runs without AWS

        key = f"backups/expenses-{datetime.utcnow():%Y%m%d-%H%M%S}.db"
        boto3.client("s3").upload_file(DB_PATH, S3_BUCKET, key)
        return f"Uploaded to s3://{S3_BUCKET}/{key}"
    except Exception as exc:  # noqa: BLE001
        return f"Backup failed: {exc}"


# ------------------------------------------------------------------ pages
@app.route("/")
def index():
    return render_template("index.html", categories=CATEGORIES, today=date.today().isoformat())


@app.route("/health")
def health():
    return jsonify(status="ok", time=datetime.utcnow().isoformat() + "Z")


# -------------------------------------------------------------------- API
@app.route("/api/expenses", methods=["GET"])
def list_expenses():
    month = request.args.get("month")
    db = get_db()
    if month:
        rows = db.execute(
            "SELECT * FROM expenses WHERE spent_on LIKE ? ORDER BY spent_on DESC, id DESC", (month + "%",)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM expenses ORDER BY spent_on DESC, id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/expenses", methods=["POST"])
def add_expense():
    data = request.get_json(silent=True) or {}
    description = str(data.get("description", "")).strip()
    try:
        amount = float(data.get("amount"))
    except (TypeError, ValueError):
        return jsonify(error="amount must be a number"), 400
    if not description or amount <= 0:
        return jsonify(error="description required and amount must be > 0"), 400

    category = data.get("category") or auto_category(description)
    if category not in CATEGORIES:
        category = "Other"
    spent_on = data.get("spent_on") or date.today().isoformat()
    try:
        datetime.strptime(spent_on, "%Y-%m-%d")
    except ValueError:
        return jsonify(error="spent_on must be YYYY-MM-DD"), 400

    db = get_db()
    cur = db.execute(
        "INSERT INTO expenses(description, amount, category, spent_on) VALUES (?,?,?,?)",
        (description, amount, category, spent_on),
    )
    db.commit()
    return jsonify(id=cur.lastrowid, description=description, amount=amount,
                   category=category, spent_on=spent_on), 201


@app.route("/api/expenses/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    db = get_db()
    cur = db.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="not found"), 404
    return jsonify(deleted=expense_id)


@app.route("/api/summary")
def summary():
    month = month_prefix(request.args.get("month"))
    db = get_db()
    total = db.execute("SELECT COALESCE(SUM(amount),0) t FROM expenses WHERE spent_on LIKE ?",
                       (month + "%",)).fetchone()["t"]
    by_cat = db.execute(
        "SELECT category, ROUND(SUM(amount),2) total FROM expenses WHERE spent_on LIKE ? "
        "GROUP BY category ORDER BY total DESC", (month + "%",)).fetchall()
    by_day = db.execute(
        "SELECT spent_on day, ROUND(SUM(amount),2) total FROM expenses WHERE spent_on LIKE ? "
        "GROUP BY spent_on ORDER BY spent_on", (month + "%",)).fetchall()

    budget = get_budget(db)
    year, mon = map(int, month.split("-"))
    days_in_month = monthrange(year, mon)[1]
    today = date.today()
    days_elapsed = today.day if (today.year, today.month) == (year, mon) else days_in_month
    forecast = round(total / max(days_elapsed, 1) * days_in_month, 2)

    pct = round(total / budget * 100, 1) if budget else 0
    if total > budget:
        alert = "Over budget! You have exceeded your monthly budget."
    elif forecast > budget:
        alert = "Warning: at this pace you will exceed your budget this month."
    elif pct >= 80:
        alert = "Careful: you have used over 80% of your budget."
    else:
        alert = "You are on track."

    return jsonify(month=month, total=round(total, 2), budget=budget, percent_used=pct,
                   forecast=forecast, alert=alert,
                   by_category=[dict(r) for r in by_cat], by_day=[dict(r) for r in by_day])


@app.route("/api/budget", methods=["POST"])
def set_budget():
    try:
        value = float((request.get_json(silent=True) or {}).get("budget"))
    except (TypeError, ValueError):
        return jsonify(error="budget must be a number"), 400
    if value <= 0:
        return jsonify(error="budget must be > 0"), 400
    db = get_db()
    db.execute("INSERT INTO settings(key,value) VALUES('budget',?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(value),))
    db.commit()
    return jsonify(budget=value)


@app.route("/api/export.csv")
def export_csv():
    rows = get_db().execute("SELECT * FROM expenses ORDER BY spent_on").fetchall()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "description", "amount", "category", "spent_on"])
    for r in rows:
        w.writerow([r["id"], r["description"], r["amount"], r["category"], r["spent_on"]])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=expenses.csv"})


@app.route("/api/backup", methods=["POST"])
def backup():
    return jsonify(result=backup_to_s3())


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
