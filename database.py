import sqlite3

# Connect to a database (or create it if it doesn't exist)
conn = sqlite3.connect("finance.db")

# Create a cursor
c = conn.cursor()

# Check current table definition to see if it uses AUTOINCREMENT
c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='transactions'")
row = c.fetchone()
needs_migration = False
if row and row[0] and 'AUTOINCREMENT' in row[0].upper():
    needs_migration = True

if not row:
    # Table doesn't exist yet — create without AUTOINCREMENT
    c.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        amount REAL,
        category TEXT,
        description TEXT,
        date TEXT
    )
    ''')
    conn.commit()
    print("Database and table created (no AUTOINCREMENT).")
else:
    if needs_migration:
        print("Found AUTOINCREMENT in existing table — migrating to non-AUTOINCREMENT schema...")
        try:
            # Perform migration in a transaction
            c.execute("BEGIN")

            # Create new table without AUTOINCREMENT
            c.execute('''
            CREATE TABLE IF NOT EXISTS transactions_new (
                id INTEGER PRIMARY KEY,
                amount REAL,
                category TEXT,
                description TEXT,
                date TEXT
            )
            ''')

            # Copy data
            c.execute('''
            INSERT INTO transactions_new(id, amount, category, description, date)
            SELECT id, amount, category, description, date FROM transactions
            ''')

            # Drop old table and rename new
            c.execute('DROP TABLE transactions')
            c.execute('ALTER TABLE transactions_new RENAME TO transactions')

            # Remove any sqlite_sequence entry for transactions (leftover from AUTOINCREMENT)
            c.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")

            conn.commit()
            print("Migration complete — table now uses INTEGER PRIMARY KEY (no AUTOINCREMENT).")
        except Exception as e:
            conn.rollback()
            print("Migration failed:", e)
            raise
    else:
        print("Table exists and does not use AUTOINCREMENT — no action needed.")

# Close connection
conn.close()
