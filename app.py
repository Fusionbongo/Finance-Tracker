from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import date

app = Flask(__name__)

DB_PATH = "finance.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    return conn


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        amount = float(request.form["amount"])
        category = request.form["category"]
        description = request.form.get("description", "")
        date_str = request.form["date"]

        conn = get_connection()
        c = conn.cursor()

        # Ensure table exists (safe if it already does)
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL
            )
            """
        )

        # Determine smallest available positive id to reuse gaps
        c.execute("SELECT id FROM transactions ORDER BY id")
        rows = [r[0] for r in c.fetchall()]
        next_id = 1
        for existing in rows:
            if existing == next_id:
                next_id += 1
            elif existing > next_id:
                break

        c.execute(
            "INSERT INTO transactions (id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            (next_id, amount, category, description, date_str),
        )
        conn.commit()
        conn.close()

        return render_template(
            "success.html", message=f"Transaction added successfully! (ID {next_id})"
        )

    return render_template("add.html")


@app.route("/transactions")
def transactions():
    conn = get_connection()
    c = conn.cursor()

    # Ensure table exists so queries don't fail on a brand-new DB
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL
        )
        """
    )

    # Get all transactions
    c.execute("SELECT id, amount, category, description, date FROM transactions")
    transactions_list = c.fetchall()

    total_count = len(transactions_list)

    # We treat positive amounts as "spent" and negative as "money added"
    total_spent = 0.0
    total_income = 0.0

    for (_id, amount, _cat, _desc, _date_str) in transactions_list:
        if amount > 0:
            total_spent += amount
        elif amount < 0:
            total_income += -amount  # store as positive income

    # Total Money = income - spent
    total_money = total_income - total_spent

    # Totals per category (only expenses, so the chart is "spending by category")
    category_totals = {}
    for (_id, amount, category, _desc, _date_str) in transactions_list:
        if amount > 0:  # only count spending
            category_totals[category] = category_totals.get(category, 0) + amount

    category_totals_list = list(category_totals.items())

    conn.close()

    return render_template(
        "transactions.html",
        transactions=transactions_list,
        total_count=total_count,
        total_spent=total_spent,
        total_money=total_money,
        category_totals=category_totals_list,
    )


@app.route("/delete/<int:id>", methods=["GET", "POST"])
def delete(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return render_template("delete.html", id=id)


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    conn = get_connection()
    c = conn.cursor()

    if request.method == "POST":
        amount = float(request.form["amount"])
        category = request.form["category"]
        description = request.form.get("description", "")
        date_str = request.form["date"]

        c.execute(
            """
            UPDATE transactions
            SET amount = ?, category = ?, description = ?, date = ?
            WHERE id = ?
            """,
            (amount, category, description, date_str, id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("transactions"))

    # GET: fetch current transaction
    c.execute(
        "SELECT id, amount, category, description, date FROM transactions WHERE id = ?",
        (id,),
    )
    transaction = c.fetchone()
    conn.close()
    if not transaction:
        return redirect(url_for("transactions"))
    return render_template("edit.html", transaction=transaction)


@app.route("/add-money", methods=["GET", "POST"])
def add_money():
    if request.method == "POST":
        amount = float(request.form["amount"])

        conn = get_connection()
        c = conn.cursor()

        # Ensure table exists
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL
            )
            """
        )

        # Reuse smallest available ID
        c.execute("SELECT id FROM transactions ORDER BY id")
        rows = [r[0] for r in c.fetchall()]
        next_id = 1
        for existing in rows:
            if existing == next_id:
                next_id += 1
            elif existing > next_id:
                break

        today_str = date.today().isoformat()

        # Store as a negative amount so it counts as "income"
        c.execute(
            "INSERT INTO transactions (id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
            (next_id, -amount, "Deposit", "Money added to total", today_str),
        )
        conn.commit()
        conn.close()

        return render_template(
            "success.html",
            message=f"Added ${amount:.2f} to total successfully! (ID {next_id})",
        )

    return render_template("add_money.html")


if __name__ == "__main__":
    app.run(debug=True)
